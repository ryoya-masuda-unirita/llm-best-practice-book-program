"""Core abstractions for AI Agent system.

This module defines the fundamental interfaces and data structures that form
the foundation of the agent system. These abstractions are designed to be stable
and rarely change, allowing extension layer implementations to evolve independently.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class AgentExecutionError(Exception):
    """Exception raised when agent execution fails before completion."""

    def __init__(self, message: str, reason: str | None = None):
        self.message = message
        self.reason = reason
        super().__init__(message)


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
    """Abstract base class for tools that agents can use.

    This interface defines the contract for all tools in the system.
    Concrete tool implementations should be placed in the extensions layer.
    """

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
    """Abstract base class for thinking strategies.

    This interface defines how agents reason about goals and decide actions.
    Concrete strategy implementations (e.g., CoT, ReAct) should be placed
    in the extensions layer.
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def think(self, goal: str, context: dict[str, object], available_tools: list[Tool]) -> Action:
        """Generate the next action based on the goal and context."""
        pass

    def update_context(self, context: dict[str, object], action: Action, result: ToolResult | str) -> dict[str, object]:
        """Update context after an action. Default implementation."""
        return context
