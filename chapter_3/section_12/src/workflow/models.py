"""Core workflow models: context, state, and graph structures."""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ExecutionState(str, Enum):
    """Workflow/node execution states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class ExecutionContext(BaseModel):
    """Carries data between nodes during workflow execution."""

    model_config = ConfigDict(validate_assignment=True, extra="allow", arbitrary_types_allowed=True)

    workflow_id: str = Field(default_factory=lambda: uuid4().hex)
    variables: dict[str, Any] = Field(default_factory=dict)
    node_outputs: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None

    def set_variable(self, key: str, value: Any) -> None:
        self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def set_node_output(self, node_id: str, output: Any) -> None:
        self.node_outputs[node_id] = output

    def get_node_output(self, node_id: str, default: Any = None) -> Any:
        return self.node_outputs.get(node_id, default)


class WorkflowState(BaseModel):
    """Tracks workflow execution progress."""

    model_config = ConfigDict(validate_assignment=True, extra="allow", arbitrary_types_allowed=True)

    workflow_id: str
    state: ExecutionState = ExecutionState.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    current_node_id: str | None = None
    node_states: dict[str, ExecutionState] = Field(default_factory=dict)
    retry_counts: dict[str, int] = Field(default_factory=dict)
    error: str | None = None

    def start_workflow(self) -> None:
        self.state = ExecutionState.RUNNING
        self.started_at = datetime.now()

    def complete_workflow(self) -> None:
        self.state = ExecutionState.COMPLETED
        self.completed_at = datetime.now()

    def fail_workflow(self, error: str) -> None:
        self.state = ExecutionState.FAILED
        self.completed_at = datetime.now()
        self.error = error

    def pause_workflow(self) -> None:
        self.state = ExecutionState.PAUSED

    def resume_workflow(self) -> None:
        if self.state == ExecutionState.PAUSED:
            self.state = ExecutionState.RUNNING

    def start_node(self, node_id: str) -> None:
        self.node_states[node_id] = ExecutionState.RUNNING
        self.current_node_id = node_id

    def complete_node(self, node_id: str, output: Any = None) -> None:
        self.node_states[node_id] = ExecutionState.COMPLETED

    def fail_node(self, node_id: str, error: str) -> None:
        self.node_states[node_id] = ExecutionState.FAILED

    def increment_retry(self, node_id: str) -> int:
        self.retry_counts[node_id] = self.retry_counts.get(node_id, 0) + 1
        return self.retry_counts[node_id]


class Edge(BaseModel):
    """Directed edge in the workflow DAG."""

    model_config = ConfigDict(validate_assignment=True, frozen=True)

    from_node_id: str
    to_node_id: str
    condition: str | None = None

    def should_traverse(self, context: ExecutionContext) -> bool:
        if self.condition is None:
            return True
        try:
            return eval(self.condition, {"context": context, "variables": context.variables})
        except Exception:
            return False


class Node(ABC):
    """Abstract base class for workflow nodes."""

    def __init__(self, node_id: str, name: str | None = None):
        self.node_id = node_id
        self.name = name or node_id
        self.next_nodes: list[str] = []

    @abstractmethod
    async def execute(self, context: ExecutionContext) -> Any:
        pass

    def add_next_node(self, node_id: str) -> None:
        if node_id not in self.next_nodes:
            self.next_nodes.append(node_id)

    def get_next_nodes(self) -> list[str]:
        return self.next_nodes.copy()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.node_id})"
