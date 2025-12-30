"""Lock manager interface and implementations.

This module provides an abstract interface for lock management that can be
implemented with different backends (local dict, Redis, RDB, etc.).
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from threading import Lock
from typing import Any

from src.agent.extensions.memory.models import LockInfo, ShadowCopy


class LockAcquisitionError(Exception):
    """Exception raised when lock acquisition fails."""

    def __init__(self, resource_id: str, holder_id: str, message: str = ""):
        self.resource_id = resource_id
        self.holder_id = holder_id
        super().__init__(message or f"Failed to acquire lock on {resource_id}, held by {holder_id}")


class LockNotHeldError(Exception):
    """Exception raised when trying to release a lock not held by the caller."""

    def __init__(self, resource_id: str, requester_id: str):
        self.resource_id = resource_id
        self.requester_id = requester_id
        super().__init__(f"Lock on {resource_id} is not held by {requester_id}")


class VersionMismatchError(Exception):
    """Exception raised when version check fails in optimistic locking."""

    def __init__(self, resource_id: str, expected_version: int, actual_version: int):
        self.resource_id = resource_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(f"Version mismatch for {resource_id}: expected {expected_version}, got {actual_version}")


class LockManager(ABC):
    """Abstract interface for lock management.

    This interface can be implemented with different backends:
    - LocalDictLockManager: In-memory dict for testing/simple use cases
    - RedisLockManager: Redis-based distributed locking
    - RDBLockManager: Database-based locking
    """

    @abstractmethod
    def acquire_lock(
        self,
        resource_id: str,
        holder_id: str,
        ttl_seconds: int | None = None,
        priority: int = 0,
        wait: bool = False,
        timeout_seconds: float = 30.0,
    ) -> LockInfo:
        """Acquire a lock on a resource.

        Args:
            resource_id: ID of the resource to lock
            holder_id: ID of the agent acquiring the lock
            ttl_seconds: Time-to-live for the lock (auto-release)
            priority: Priority of the lock holder (for preemptible locks)
            wait: Whether to wait for lock availability
            timeout_seconds: Maximum time to wait for lock

        Returns:
            LockInfo with lock details

        Raises:
            LockAcquisitionError: If lock cannot be acquired
        """
        pass

    @abstractmethod
    def release_lock(self, resource_id: str, holder_id: str) -> bool:
        """Release a lock on a resource.

        Args:
            resource_id: ID of the resource to unlock
            holder_id: ID of the agent releasing the lock

        Returns:
            True if lock was released, False if not held

        Raises:
            LockNotHeldError: If lock is not held by the requester
        """
        pass

    @abstractmethod
    def is_locked(self, resource_id: str) -> bool:
        pass

    @abstractmethod
    def get_lock_info(self, resource_id: str) -> LockInfo | None:
        pass

    @abstractmethod
    def get_version(self, resource_id: str) -> int:
        pass

    @abstractmethod
    def increment_version(self, resource_id: str) -> int:
        pass

    @abstractmethod
    def check_and_set_version(self, resource_id: str, expected_version: int, holder_id: str) -> int:
        """Atomically check version and increment. Raises VersionMismatchError on mismatch."""
        pass

    @abstractmethod
    def preempt_lock(
        self,
        resource_id: str,
        new_holder_id: str,
        new_priority: int,
        shadow_data: dict[str, Any] | None = None,
    ) -> tuple[LockInfo, ShadowCopy | None]:
        """Attempt to preempt if new holder has higher priority. Raises LockAcquisitionError on failure."""
        pass

    @abstractmethod
    def get_shadow_copies(self, resource_id: str) -> list[ShadowCopy]:
        pass

    @abstractmethod
    def cleanup_expired_locks(self) -> int:
        pass


class LocalDictLockManager(LockManager):
    """In-memory lock manager using local dictionary.

    Thread-safe implementation suitable for testing and single-process use cases.
    For production multi-agent systems, use Redis or RDB-based implementations.
    """

    def __init__(self) -> None:
        self._locks: dict[str, LockInfo] = {}
        self._versions: dict[str, int] = {}
        self._shadow_copies: dict[str, list[ShadowCopy]] = {}
        self._mutex = Lock()

    def acquire_lock(
        self,
        resource_id: str,
        holder_id: str,
        ttl_seconds: int | None = None,
        priority: int = 0,
        wait: bool = False,
        timeout_seconds: float = 30.0,
    ) -> LockInfo:
        import time

        start_time = time.time()

        while True:
            with self._mutex:
                self._cleanup_expired_locks_internal()

                if resource_id not in self._locks:
                    expires_at = None
                    if ttl_seconds:
                        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

                    lock_info = LockInfo(
                        resource_id=resource_id,
                        holder_id=holder_id,
                        priority=priority,
                        acquired_at=datetime.now(),
                        expires_at=expires_at,
                        version=self._versions.get(resource_id, 1),
                    )
                    self._locks[resource_id] = lock_info
                    return lock_info

                existing_lock = self._locks[resource_id]
                if existing_lock.holder_id == holder_id:
                    return existing_lock

            if not wait:
                raise LockAcquisitionError(resource_id, self._locks[resource_id].holder_id)

            if time.time() - start_time > timeout_seconds:
                raise LockAcquisitionError(
                    resource_id,
                    self._locks[resource_id].holder_id,
                    f"Timeout waiting for lock on {resource_id}",
                )

            time.sleep(0.1)

    def release_lock(self, resource_id: str, holder_id: str) -> bool:
        with self._mutex:
            if resource_id not in self._locks:
                return False

            lock_info = self._locks[resource_id]
            if lock_info.holder_id != holder_id:
                raise LockNotHeldError(resource_id, holder_id)

            del self._locks[resource_id]
            return True

    def is_locked(self, resource_id: str) -> bool:
        with self._mutex:
            self._cleanup_expired_locks_internal()
            return resource_id in self._locks

    def get_lock_info(self, resource_id: str) -> LockInfo | None:
        with self._mutex:
            self._cleanup_expired_locks_internal()
            return self._locks.get(resource_id)

    def get_version(self, resource_id: str) -> int:
        with self._mutex:
            return self._versions.get(resource_id, 1)

    def increment_version(self, resource_id: str) -> int:
        with self._mutex:
            current = self._versions.get(resource_id, 1)
            new_version = current + 1
            self._versions[resource_id] = new_version
            return new_version

    def check_and_set_version(self, resource_id: str, expected_version: int, holder_id: str) -> int:
        with self._mutex:
            current_version = self._versions.get(resource_id, 1)
            if current_version != expected_version:
                raise VersionMismatchError(resource_id, expected_version, current_version)

            new_version = current_version + 1
            self._versions[resource_id] = new_version
            return new_version

    def preempt_lock(
        self,
        resource_id: str,
        new_holder_id: str,
        new_priority: int,
        shadow_data: dict[str, Any] | None = None,
    ) -> tuple[LockInfo, ShadowCopy | None]:
        with self._mutex:
            self._cleanup_expired_locks_internal()

            if resource_id not in self._locks:
                lock_info = LockInfo(
                    resource_id=resource_id,
                    holder_id=new_holder_id,
                    priority=new_priority,
                    acquired_at=datetime.now(),
                    version=self._versions.get(resource_id, 1),
                )
                self._locks[resource_id] = lock_info
                return lock_info, None

            existing_lock = self._locks[resource_id]

            if existing_lock.holder_id == new_holder_id:
                return existing_lock, None

            if new_priority <= existing_lock.priority:
                raise LockAcquisitionError(
                    resource_id,
                    existing_lock.holder_id,
                    f"Priority {new_priority} not higher than current {existing_lock.priority}",
                )

            shadow_copy = None
            if shadow_data:
                shadow_copy = ShadowCopy(
                    original_resource_id=resource_id,
                    holder_id=existing_lock.holder_id,
                    preempted_by=new_holder_id,
                    timestamp=datetime.now(),
                    data=shadow_data,
                )
                if resource_id not in self._shadow_copies:
                    self._shadow_copies[resource_id] = []
                self._shadow_copies[resource_id].append(shadow_copy)

            new_lock = LockInfo(
                resource_id=resource_id,
                holder_id=new_holder_id,
                priority=new_priority,
                acquired_at=datetime.now(),
                version=self._versions.get(resource_id, 1),
            )
            self._locks[resource_id] = new_lock
            return new_lock, shadow_copy

    def get_shadow_copies(self, resource_id: str) -> list[ShadowCopy]:
        with self._mutex:
            return list(self._shadow_copies.get(resource_id, []))

    def cleanup_expired_locks(self) -> int:
        with self._mutex:
            return self._cleanup_expired_locks_internal()

    def _cleanup_expired_locks_internal(self) -> int:
        now = datetime.now()
        expired = [rid for rid, lock in self._locks.items() if lock.expires_at and lock.expires_at < now]
        for rid in expired:
            del self._locks[rid]
        return len(expired)

    def clear_all(self) -> None:
        with self._mutex:
            self._locks.clear()
            self._versions.clear()
            self._shadow_copies.clear()
