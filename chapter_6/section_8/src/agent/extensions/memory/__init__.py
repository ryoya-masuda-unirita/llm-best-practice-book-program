"""Memory implementations for AI agents.

This module provides concrete memory implementations including:
- Context and conversational memory
- Lock-based memory strategies (conservative, optimistic, preemptible)
- Immutable append-only memory
"""

from src.agent.extensions.memory.caretaker import MemoryCaretaker
from src.agent.extensions.memory.conservative_lock import (
    ConservativeLockMemory,
    LockHandle,
)
from src.agent.extensions.memory.context import ContextMemory
from src.agent.extensions.memory.conversational import ConversationalMemory
from src.agent.extensions.memory.immutable_memory import (
    ImmutableMemory,
    SessionMemory,
)
from src.agent.extensions.memory.lock_manager import (
    LocalDictLockManager,
    LockAcquisitionError,
    LockManager,
    LockNotHeldError,
    VersionMismatchError,
)
from src.agent.extensions.memory.models import (
    CompactionResult,
    ImmutableMemoryEntry,
    LockInfo,
    MemoryDocument,
    MemoryEntry,
    MemoryEntryType,
    ShadowCopy,
)
from src.agent.extensions.memory.optimistic_lock import (
    OptimisticLockConflictError,
    OptimisticLockMemory,
    OptimisticTransaction,
)
from src.agent.extensions.memory.preemptible_lock import (
    PreemptedError,
    PreemptibleLockMemory,
)

__all__ = [
    # Core memory
    "ContextMemory",
    "ConversationalMemory",
    "MemoryCaretaker",
    # Lock manager
    "LockManager",
    "LocalDictLockManager",
    "LockAcquisitionError",
    "LockNotHeldError",
    "VersionMismatchError",
    # Models
    "MemoryDocument",
    "MemoryEntry",
    "MemoryEntryType",
    "LockInfo",
    "ShadowCopy",
    "ImmutableMemoryEntry",
    "CompactionResult",
    # Conservative lock
    "ConservativeLockMemory",
    "LockHandle",
    # Optimistic lock
    "OptimisticLockMemory",
    "OptimisticLockConflictError",
    "OptimisticTransaction",
    # Preemptible lock
    "PreemptibleLockMemory",
    "PreemptedError",
    # Immutable memory
    "ImmutableMemory",
    "SessionMemory",
]
