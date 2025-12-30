"""Preemptible Lock (Priority Lock) Memory Implementation.

This module implements a memory strategy where higher-priority agents can
preempt locks held by lower-priority agents. Shadow copies protect data
from the preempted operation for later reconciliation.

Use cases:
- Emergency response systems (urgent customer support)
- Real-time applications requiring immediate access
- Hierarchical agent systems with priority levels
"""

import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Generator
from uuid import uuid4

from src.agent.extensions.memory.lock_manager import (
    LocalDictLockManager,
    LockAcquisitionError,
    LockManager,
)
from src.agent.extensions.memory.models import (
    MemoryDocument,
    MemoryEntry,
    MemoryEntryType,
    ShadowCopy,
)


class PreemptedError(Exception):
    """Exception raised when an agent's lock has been preempted."""

    def __init__(
        self,
        resource_id: str,
        preempted_by: str,
        shadow_copy_id: str | None = None,
    ):
        self.resource_id = resource_id
        self.preempted_by = preempted_by
        self.shadow_copy_id = shadow_copy_id
        super().__init__(f"Lock on {resource_id} was preempted by {preempted_by}")


class PreemptibleLockMemory:
    """Memory with priority-based preemptible locking strategy.

    This implementation allows higher-priority agents to forcibly acquire
    locks held by lower-priority agents. The original data is preserved
    in a shadow copy for potential reconciliation.

    Key characteristics:
    - Priority-based lock acquisition
    - Shadow copy mechanism for data protection
    - Preempted agents receive notification
    - Requires manual reconciliation of shadow copies

    Tradeoffs:
    - Enables real-time responsiveness for critical operations
    - Complex shadow copy management
    - Potential for data inconsistency if not properly reconciled
    - Lower-priority agents may starve under high load
    """

    # Priority levels for common agent types
    PRIORITY_LOW = 10
    PRIORITY_NORMAL = 50
    PRIORITY_HIGH = 80
    PRIORITY_CRITICAL = 100

    def __init__(
        self,
        memory_dir: str | Path,
        agent_id: str,
        priority: int = 50,
        lock_manager: LockManager | None = None,
        lock_ttl_seconds: int = 300,
    ) -> None:
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.shadow_dir = self.memory_dir / "shadow_copies"
        self.shadow_dir.mkdir(parents=True, exist_ok=True)
        self.agent_id = agent_id
        self.priority = priority
        self.lock_manager = lock_manager or LocalDictLockManager()
        self.lock_ttl_seconds = lock_ttl_seconds
        self._held_locks: set[str] = set()
        self._preempted_resources: set[str] = set()

    def _get_file_path(self, resource_id: str) -> Path:
        return self.memory_dir / f"{resource_id}.json"

    def _get_shadow_file_path(self, shadow_id: str) -> Path:
        return self.shadow_dir / f"{shadow_id}.json"

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

    def _save_shadow_copy(
        self,
        resource_id: str,
        preempted_by: str,
        data: dict[str, Any],
    ) -> str:
        shadow_id = f"{resource_id}_{self.agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        shadow = ShadowCopy(
            original_resource_id=resource_id,
            holder_id=self.agent_id,
            preempted_by=preempted_by,
            timestamp=datetime.now(),
            data=data,
        )
        shadow_path = self._get_shadow_file_path(shadow_id)
        with open(shadow_path, "w", encoding="utf-8") as f:
            json.dump(shadow.model_dump(mode="json"), f, indent=2, default=str)
        return shadow_id

    def _load_shadow_copy(self, shadow_id: str) -> ShadowCopy | None:
        shadow_path = self._get_shadow_file_path(shadow_id)
        if shadow_path.exists():
            with open(shadow_path, encoding="utf-8") as f:
                data = json.load(f)
                return ShadowCopy.model_validate(data)
        return None

    def _check_preempted(self, resource_id: str) -> None:
        if resource_id in self._preempted_resources:
            raise PreemptedError(resource_id, "unknown")

        lock_info = self.lock_manager.get_lock_info(resource_id)
        if lock_info and lock_info.holder_id != self.agent_id:
            self._held_locks.discard(resource_id)
            raise PreemptedError(resource_id, lock_info.holder_id)

    @contextmanager
    def acquire_lock(
        self,
        resource_id: str,
        force_preempt: bool = True,
    ) -> Generator[None, None, None]:
        current_data: dict[str, Any] | None = None
        file_path = self._get_file_path(resource_id)
        if file_path.exists():
            with open(file_path, encoding="utf-8") as f:
                current_data = json.load(f)

        try:
            lock_info, shadow_copy = self.lock_manager.preempt_lock(
                resource_id=resource_id,
                new_holder_id=self.agent_id,
                new_priority=self.priority,
                shadow_data=current_data if force_preempt else None,
            )
            self._held_locks.add(resource_id)

            if shadow_copy:
                self._save_shadow_copy(
                    resource_id,
                    shadow_copy.holder_id,
                    shadow_copy.data,
                )

        except LockAcquisitionError:
            if not force_preempt:
                raise
            raise

        try:
            yield
        finally:
            if resource_id in self._held_locks:
                self.lock_manager.release_lock(resource_id, self.agent_id)
                self._held_locks.discard(resource_id)

    def read(self, resource_id: str) -> MemoryDocument:
        if resource_id not in self._held_locks:
            raise RuntimeError(f"Cannot read {resource_id} without holding lock.")
        self._check_preempted(resource_id)
        return self._load_document(resource_id)

    def write(self, resource_id: str, document: MemoryDocument) -> None:
        if resource_id not in self._held_locks:
            raise RuntimeError(f"Cannot write {resource_id} without holding lock.")
        self._check_preempted(resource_id)
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
        self._check_preempted(resource_id)

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

    def list_shadow_copies(
        self,
        resource_id: str | None = None,
    ) -> list[tuple[str, ShadowCopy]]:
        result: list[tuple[str, ShadowCopy]] = []
        for shadow_file in self.shadow_dir.glob("*.json"):
            shadow_id = shadow_file.stem
            shadow = self._load_shadow_copy(shadow_id)
            if shadow:
                if resource_id is None or shadow.original_resource_id == resource_id:
                    result.append((shadow_id, shadow))
        return sorted(result, key=lambda x: x[1].timestamp)

    def get_shadow_copy(self, shadow_id: str) -> ShadowCopy | None:
        return self._load_shadow_copy(shadow_id)

    def delete_shadow_copy(self, shadow_id: str) -> bool:
        shadow_path = self._get_shadow_file_path(shadow_id)
        if shadow_path.exists():
            shadow_path.unlink()
            return True
        return False

    def reconcile_shadow_copy(
        self,
        shadow_id: str,
        merge_fn: "Callable[[MemoryDocument, dict[str, Any]], MemoryDocument]",
    ) -> MemoryDocument:
        """Merge changes from a preempted operation back into the current document."""
        shadow = self._load_shadow_copy(shadow_id)
        if shadow is None:
            raise ValueError(f"Shadow copy {shadow_id} not found")

        resource_id = shadow.original_resource_id

        with self.acquire_lock(resource_id, force_preempt=False):
            current_doc = self.read(resource_id)
            merged_doc = merge_fn(current_doc, shadow.data)
            self.write(resource_id, merged_doc)
            self.delete_shadow_copy(shadow_id)
            return merged_doc

    def holds_lock(self, resource_id: str) -> bool:
        if resource_id not in self._held_locks:
            return False
        try:
            self._check_preempted(resource_id)
            return True
        except PreemptedError:
            return False

    def cleanup_old_shadow_copies(self, max_age_hours: int = 24) -> int:
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        deleted = 0
        for shadow_file in self.shadow_dir.glob("*.json"):
            if shadow_file.stat().st_mtime < cutoff:
                shadow_file.unlink()
                deleted += 1
        return deleted
