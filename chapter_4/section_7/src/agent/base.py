"""Base abstractions for AI Agent system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agent.memory import MemorySnapshot


class AgentExecutionError(Exception):
    """Exception raised when agent execution fails or terminates without a result."""

    pass


ParamValue = str | int | float | bool | list | dict | None
ToolParams = dict[str, ParamValue]
ToolData = str | int | float | dict | list | None
MetadataDict = dict[str, str | int | float | bool | None]


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
    params: ToolParams = field(default_factory=dict)
    answer: str | None = None
    thought: str | None = None


@dataclass
class ToolResult:
    """Result from a tool execution."""

    success: bool
    data: ToolData
    error: str | None = None
    metadata: MetadataDict = field(default_factory=dict)


@dataclass
class ContextData:
    """Context data structure passed to strategies."""

    observations: list[str | ToolResult]
    actions: list[Action]
    metadata: MetadataDict
    history_length: int
    steps: list[dict[str, str | int | ToolResult | None]] = field(default_factory=list)
    num_turns: int = 0


class Tool(ABC):
    """Abstract base class for tools that agents can use."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, params: ToolParams) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    def validate_params(self, params: ToolParams) -> bool:
        """Validate tool parameters. Override for custom validation."""
        return True

    def get_schema(self) -> dict[str, str | dict]:
        """Get the tool's parameter schema."""
        return {"name": self.name, "description": self.description}


@dataclass
class StepInfo:
    """Information about a single execution step."""

    iteration: int
    thought: str | None
    action: str
    result: ToolResult | str | None


class Strategy(ABC):
    """Abstract base class for thinking strategies."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def think(self, goal: str, context: dict[str, object], available_tools: list[Tool]) -> Action:
        """Generate the next action based on the goal and context."""
        pass

    def update_context(self, context: dict[str, object], action: Action, result: ToolResult | str) -> dict[str, object]:
        """Update context after an action. Default implementation."""
        return context


class Memory(ABC):
    """Abstract base class for context/memory management."""

    @abstractmethod
    def get_context(self) -> dict[str, object]:
        """Get the current context."""
        pass

    @abstractmethod
    def add_observation(self, observation: str | ToolResult) -> None:
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
    def save_snapshot(self) -> "MemorySnapshot":
        """Save a snapshot of current memory state (Memento pattern)."""
        pass

    @abstractmethod
    def restore_snapshot(self, snapshot: "MemorySnapshot") -> None:
        """Restore memory from a snapshot."""
        pass
