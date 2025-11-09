"""Base abstractions for AI Agent system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ActionType(Enum):
    """Types of actions an agent can take."""

    TOOL_CALL = "tool_call"
    FINAL_ANSWER = "final_answer"
    THINK = "think"
    OBSERVE = "observe"


@dataclass
class Action:
    """Represents an action to be taken by the agent."""

    type: ActionType
    tool_name: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    answer: Any = None
    thought: str | None = None


@dataclass
class ToolResult:
    """Result from a tool execution."""

    success: bool
    data: Any
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class Tool(ABC):
    """Abstract base class for tools that agents can use."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    def validate_params(self, params: dict[str, Any]) -> bool:
        """Validate tool parameters. Override for custom validation."""
        return True

    def get_schema(self) -> dict[str, Any]:
        """Get the tool's parameter schema."""
        return {"name": self.name, "description": self.description}


class Strategy(ABC):
    """Abstract base class for thinking strategies."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def think(self, goal: str, context: dict[str, Any], available_tools: list[Tool]) -> Action:
        """Generate the next action based on the goal and context."""
        pass

    def update_context(self, context: dict[str, Any], action: Action, result: Any) -> dict[str, Any]:
        """Update context after an action. Default implementation."""
        return context


class Memory(ABC):
    """Abstract base class for context/memory management."""

    @abstractmethod
    def get_context(self) -> dict[str, Any]:
        """Get the current context."""
        pass

    @abstractmethod
    def add_observation(self, observation: Any) -> None:
        """Add an observation to memory."""
        pass

    @abstractmethod
    def add_action(self, action: Action) -> None:
        """Add an action to memory."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear the memory."""
        pass

    @abstractmethod
    def save_snapshot(self) -> Any:
        """Save a snapshot of current memory state (Memento pattern)."""
        pass

    @abstractmethod
    def restore_snapshot(self, snapshot: Any) -> None:
        """Restore memory from a snapshot."""
        pass
