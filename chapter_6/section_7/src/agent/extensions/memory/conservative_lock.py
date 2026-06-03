"""Conservative Lock (Pessimistic Lock) Memory Implementation.

This module implements a memory strategy that acquires locks before any operation
and holds them until the operation is complete. This is the safest approach for
data integrity but can cause blocking when multiple agents access the same resource.

Use cases:
- Complex update operations requiring strict consistency
- Multi-file transactions (e.g., item trading between agents)
- Critical data that cannot tolerate any conflicts
"""

import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator
from uuid import uuid4

from src.agent.extensions.memory.lock_manager import (
    LocalDictLockManager,
    LockManager,
)
from src.agent.extensions.memory.models import (
    MemoryDocument,
    MemoryEntry,
    MemoryEntryType,
)


class ConservativeLockMemory:
    """Memory with pessimistic locking strategy.

    This implementation acquires an exclusive lock before reading or writing,
    ensuring no concurrent modifications can occur. The lock is held for the
    entire duration of the operation, including LLM inference time.

    Key characteristics:
    - Acquires lock before read
    - Holds lock during processing
    - Releases lock after write
    - Blocks other agents during lock hold

    Tradeoffs:
    - High data consistency
    - Potential for long blocking times
    - Risk of deadlocks if not ordered properly
    """

    def __init__(
        self,
        memory_dir: str | Path,
        agent_id: str,
        lock_manager: LockManager | None = None,
        lock_ttl_seconds: int = 300,
    ) -> None:
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.agent_id = agent_id
        self.lock_manager = lock_manager or LocalDictLockManager()
        self.lock_ttl_seconds = lock_ttl_seconds
        self._held_locks: set[str] = set()

    def _get_file_path(self, resource_id: str) -> Path:
        return self.memory_dir / f"{resource_id}.json"

    def _load_document(self, resource_id: str) -> MemoryDocument:
        file_path = self._get_file_path(resource_id)
        if file_path.exists():
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
                return MemoryDocument.model_validate(data)
        return MemoryDocument(id=resource_id)

    def _save_document(self, document: MemoryDocument) -> None:
        file_path = self._get_file_path(document.id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(document.model_dump(mode="json"), f, indent=2, default=str)

    @contextmanager
    def acquire_lock(
        self,
        resource_id: str,
        wait: bool = True,
        timeout_seconds: float = 30.0,
    ) -> Generator[None, None, None]:
        self.lock_manager.acquire_lock(
            resource_id=resource_id,
            holder_id=self.agent_id,
            ttl_seconds=self.lock_ttl_seconds,
            wait=wait,
            timeout_seconds=timeout_seconds,
        )
        self._held_locks.add(resource_id)
        try:
            yield
        finally:
            self.lock_manager.release_lock(resource_id, self.agent_id)
            self._held_locks.discard(resource_id)

    @contextmanager
    def acquire_multiple_locks(
        self,
        resource_ids: list[str],
        wait: bool = True,
        timeout_seconds: float = 30.0,
    ) -> Generator[None, None, None]:
        """Acquire locks in sorted order to prevent deadlocks."""
        sorted_ids = sorted(resource_ids)
        acquired: list[str] = []

        try:
            for resource_id in sorted_ids:
                self.lock_manager.acquire_lock(
                    resource_id=resource_id,
                    holder_id=self.agent_id,
                    ttl_seconds=self.lock_ttl_seconds,
                    wait=wait,
                    timeout_seconds=timeout_seconds,
                )
                acquired.append(resource_id)
                self._held_locks.add(resource_id)
            yield
        finally:
            for resource_id in reversed(acquired):
                self.lock_manager.release_lock(resource_id, self.agent_id)
                self._held_locks.discard(resource_id)

    def read(self, resource_id: str) -> MemoryDocument:
        if resource_id not in self._held_locks:
            raise RuntimeError(f"Cannot read {resource_id} without holding lock. Use acquire_lock() context manager.")
        return self._load_document(resource_id)

    def write(self, resource_id: str, document: MemoryDocument) -> None:
        if resource_id not in self._held_locks:
            raise RuntimeError(f"Cannot write {resource_id} without holding lock. Use acquire_lock() context manager.")
        document.updated_at = datetime.now()
        self._save_document(document)
        self.lock_manager.increment_version(resource_id)

    def add_entry(
        self,
        resource_id: str,
        entry_type: MemoryEntryType,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        if resource_id not in self._held_locks:
            raise RuntimeError(f"Cannot add entry to {resource_id} without holding lock.")

        document = self._load_document(resource_id)
        entry = MemoryEntry(
            id=str(uuid4()),
            type=entry_type,
            content=content,
            agent_id=self.agent_id,
            metadata=metadata or {},
        )
        document.add_entry(entry)
        self._save_document(document)
        self.lock_manager.increment_version(resource_id)
        return entry

    def read_with_lock(
        self,
        resource_id: str,
        wait: bool = True,
        timeout_seconds: float = 30.0,
    ) -> tuple[MemoryDocument, "LockHandle"]:
        """Read a document and return a lock handle for later release."""
        self.lock_manager.acquire_lock(
            resource_id=resource_id,
            holder_id=self.agent_id,
            ttl_seconds=self.lock_ttl_seconds,
            wait=wait,
            timeout_seconds=timeout_seconds,
        )
        self._held_locks.add(resource_id)
        document = self._load_document(resource_id)
        return document, LockHandle(self, resource_id)

    def is_locked(self, resource_id: str) -> bool:
        return self.lock_manager.is_locked(resource_id)

    def holds_lock(self, resource_id: str) -> bool:
        return resource_id in self._held_locks


class LockHandle:
    """Handle for manually managing lock lifecycle."""

    def __init__(self, memory: ConservativeLockMemory, resource_id: str) -> None:
        self.memory = memory
        self.resource_id = resource_id
        self._released = False

    def write(self, document: MemoryDocument) -> None:
        if self._released:
            raise RuntimeError("Lock handle has been released")
        self.memory.write(self.resource_id, document)

    def release(self) -> None:
        if not self._released:
            self.memory.lock_manager.release_lock(self.resource_id, self.memory.agent_id)
            self.memory._held_locks.discard(self.resource_id)
            self._released = True

    def __enter__(self) -> "LockHandle":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.release()
