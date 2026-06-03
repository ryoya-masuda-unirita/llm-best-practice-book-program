"""Optimistic Lock Memory Implementation.

This module implements a memory strategy that does not lock during reads,
but validates version numbers at write time to detect conflicts.

Use cases:
- Collaborative editing where conflicts are rare
- High-throughput systems where blocking is costly
- Scenarios where retry is acceptable
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, TypeVar
from uuid import uuid4

from src.agent.extensions.memory.lock_manager import (
    LocalDictLockManager,
    LockManager,
    VersionMismatchError,
)
from src.agent.extensions.memory.models import (
    MemoryDocument,
    MemoryEntry,
    MemoryEntryType,
)

T = TypeVar("T")


class OptimisticLockConflictError(Exception):
    """Exception raised when optimistic lock conflict is detected."""

    def __init__(self, resource_id: str, read_version: int, current_version: int):
        self.resource_id = resource_id
        self.read_version = read_version
        self.current_version = current_version
        super().__init__(f"Conflict on {resource_id}: read version {read_version}, current version {current_version}")


class OptimisticLockMemory:
    """Memory with optimistic locking strategy.

    This implementation reads without locking, then validates the version
    at write time. If the version has changed, the write fails and the
    caller must retry with fresh data.

    Key characteristics:
    - No blocking on reads
    - Version check on writes
    - Retry required on conflicts
    - Higher throughput when conflicts are rare

    Tradeoffs:
    - Better parallelism than pessimistic locking
    - Wasted work on conflicts (especially costly for LLM inference)
    - Best when conflict rate < 20%
    """

    def __init__(
        self,
        memory_dir: str | Path,
        agent_id: str,
        lock_manager: LockManager | None = None,
        max_retries: int = 3,
    ) -> None:
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.agent_id = agent_id
        self.lock_manager = lock_manager or LocalDictLockManager()
        self.max_retries = max_retries

    def _get_file_path(self, resource_id: str) -> Path:
        return self.memory_dir / f"{resource_id}.json"

    def _load_document(self, resource_id: str) -> MemoryDocument:
        file_path = self._get_file_path(resource_id)
        if file_path.exists():
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
                return MemoryDocument.model_validate(data)
        return MemoryDocument(id=resource_id, version=1)

    def _save_document(self, document: MemoryDocument) -> None:
        file_path = self._get_file_path(document.id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(document.model_dump(mode="json"), f, indent=2, default=str)

    def read(self, resource_id: str) -> tuple[MemoryDocument, int]:
        version = self.lock_manager.get_version(resource_id)
        document = self._load_document(resource_id)
        return document, version

    def write(
        self,
        resource_id: str,
        document: MemoryDocument,
        expected_version: int,
    ) -> int:
        """Write with version check. Raises OptimisticLockConflictError on conflict."""
        try:
            new_version = self.lock_manager.check_and_set_version(resource_id, expected_version, self.agent_id)
        except VersionMismatchError as e:
            raise OptimisticLockConflictError(resource_id, expected_version, e.actual_version) from e

        document.version = new_version
        document.updated_at = datetime.now()
        self._save_document(document)
        return new_version

    def update_with_retry(
        self,
        resource_id: str,
        update_fn: Callable[[MemoryDocument], MemoryDocument],
        max_retries: int | None = None,
    ) -> tuple[MemoryDocument, int]:
        """Update with automatic retry on conflicts. For LLM inference, use manual retry."""
        retries = max_retries if max_retries is not None else self.max_retries

        for attempt in range(retries + 1):
            document, version = self.read(resource_id)
            updated_document = update_fn(document)

            try:
                new_version = self.write(resource_id, updated_document, version)
                return updated_document, new_version
            except OptimisticLockConflictError:
                if attempt == retries:
                    raise

        raise RuntimeError("Unreachable code")

    def add_entry(
        self,
        resource_id: str,
        entry_type: MemoryEntryType,
        content: str,
        expected_version: int,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[MemoryEntry, int]:
        document, current_version = self.read(resource_id)

        if current_version != expected_version:
            raise OptimisticLockConflictError(resource_id, expected_version, current_version)

        entry = MemoryEntry(
            id=str(uuid4()),
            type=entry_type,
            content=content,
            agent_id=self.agent_id,
            metadata=metadata or {},
        )
        document.add_entry(entry)

        new_version = self.write(resource_id, document, expected_version)
        return entry, new_version

    def add_entry_with_retry(
        self,
        resource_id: str,
        entry_type: MemoryEntryType,
        content: str,
        metadata: dict[str, Any] | None = None,
        max_retries: int | None = None,
    ) -> tuple[MemoryEntry, int]:
        entry_id = str(uuid4())

        def create_entry(doc: MemoryDocument) -> MemoryDocument:
            entry = MemoryEntry(
                id=entry_id,
                type=entry_type,
                content=content,
                agent_id=self.agent_id,
                metadata=metadata or {},
            )
            doc.add_entry(entry)
            return doc

        document, new_version = self.update_with_retry(resource_id, create_entry, max_retries)

        created_entry = next((e for e in document.entries if e.id == entry_id), None)
        if created_entry is None:
            raise RuntimeError("Entry was not added")

        return created_entry, new_version


class OptimisticTransaction:
    """Context manager for optimistic lock transactions.

    Provides a cleaner interface for read-modify-write operations.

    Usage:
        async with OptimisticTransaction(memory, "resource_id") as tx:
            tx.document.entries.append(new_entry)
            # Modifications are automatically committed on exit
    """

    def __init__(
        self,
        memory: OptimisticLockMemory,
        resource_id: str,
        auto_retry: bool = False,
        max_retries: int = 3,
    ) -> None:
        self.memory = memory
        self.resource_id = resource_id
        self.auto_retry = auto_retry
        self.max_retries = max_retries
        self.document: MemoryDocument | None = None
        self.version: int = 0
        self._committed = False

    def __enter__(self) -> "OptimisticTransaction":
        self.document, self.version = self.memory.read(self.resource_id)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_type is not None:
            return False

        if self.document is None:
            return False

        if self.auto_retry:
            for attempt in range(self.max_retries + 1):
                try:
                    self.memory.write(self.resource_id, self.document, self.version)
                    self._committed = True
                    return False
                except OptimisticLockConflictError:
                    if attempt == self.max_retries:
                        raise
                    self.document, self.version = self.memory.read(self.resource_id)
        else:
            self.memory.write(self.resource_id, self.document, self.version)
            self._committed = True

        return False
