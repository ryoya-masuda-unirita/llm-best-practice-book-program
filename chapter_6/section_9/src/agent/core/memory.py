"""Core memory abstractions with Memento pattern support."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agent.core.base import Action, MetadataDict, ToolResult


@dataclass
class MemorySnapshot:
    """Memento: Snapshot of memory state for restoration."""

    timestamp: datetime
    observations: list["str | ToolResult"]
    actions: list["Action"]
    metadata: "MetadataDict"


class Memory(ABC):
    """Abstract base class for context/memory management."""

    @abstractmethod
    def get_context(self) -> dict[str, object]:
        pass

    @abstractmethod
    def add_observation(self, observation: "str | ToolResult") -> None:
        pass

    @abstractmethod
    def add_action(self, action: "Action") -> None:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass

    @abstractmethod
    def save_snapshot(self) -> MemorySnapshot:
        pass

    @abstractmethod
    def restore_snapshot(self, snapshot: MemorySnapshot) -> None:
        pass
