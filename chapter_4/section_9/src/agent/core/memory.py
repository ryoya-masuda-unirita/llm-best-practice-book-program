"""Core memory abstractions with Memento pattern support.

This module defines the abstract interface for agent memory management.
Concrete memory implementations should be placed in the extensions layer.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agent.core.base import Action, MetadataDict, ToolResult


@dataclass
class MemorySnapshot:
    """Memento: Snapshot of memory state for restoration.

    This dataclass captures a point-in-time state of the memory,
    enabling rollback and recovery operations.
    """

    timestamp: datetime
    observations: list["str | ToolResult"]
    actions: list["Action"]
    metadata: "MetadataDict"


class Memory(ABC):
    """Abstract base class for context/memory management.

    This interface defines how agents store and retrieve context information.
    Concrete implementations can provide different storage strategies
    (e.g., list-based, conversation-based, vector-based).
    """

    @abstractmethod
    def get_context(self) -> dict[str, object]:
        """Get the current context."""
        pass

    @abstractmethod
    def add_observation(self, observation: "str | ToolResult") -> None:
        """Add an observation to memory."""
        pass

    @abstractmethod
    def add_action(self, action: "Action") -> None:
        """Add an action to memory."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear the memory."""
        pass

    @abstractmethod
    def save_snapshot(self) -> MemorySnapshot:
        """Save a snapshot of current memory state (Memento pattern)."""
        pass

    @abstractmethod
    def restore_snapshot(self, snapshot: MemorySnapshot) -> None:
        """Restore memory from a snapshot."""
        pass
