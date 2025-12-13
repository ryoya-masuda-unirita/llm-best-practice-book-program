"""State Pattern: Manages execution states of nodes and workflows."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExecutionState(str, Enum):
    """Enum for node/workflow execution states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class NodeExecutionRecord(BaseModel):
    """Record of a node's execution."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    node_id: str = Field(..., description="Node ID")
    state: ExecutionState = Field(default=ExecutionState.PENDING, description="Execution state")
    started_at: datetime | None = Field(default=None, description="Start time")
    completed_at: datetime | None = Field(default=None, description="Completion time")
    error: str | None = Field(default=None, description="Error message if failed")
    output: Any = Field(default=None, description="Node output")
    retry_count: int = Field(default=0, description="Number of retries")


class WorkflowState(BaseModel):
    """
    State Pattern: Represents the current state of workflow execution.
    Manages execution states and tracks progress.
    """

    model_config = ConfigDict(
        validate_assignment=True,
        extra="allow",
        arbitrary_types_allowed=True,
    )

    workflow_id: str = Field(..., description="Workflow ID")
    state: ExecutionState = Field(default=ExecutionState.PENDING, description="Overall workflow state")
    started_at: datetime | None = Field(default=None, description="Workflow start time")
    completed_at: datetime | None = Field(default=None, description="Workflow completion time")
    current_node_id: str | None = Field(default=None, description="Currently executing node")
    node_records: dict[str, NodeExecutionRecord] = Field(
        default_factory=dict, description="Execution records for each node"
    )
    variables: dict[str, Any] = Field(default_factory=dict, description="Workflow variables")
    error: str | None = Field(default=None, description="Error message if workflow failed")

    def start_workflow(self) -> None:
        """Mark workflow as started."""
        self.state = ExecutionState.RUNNING
        self.started_at = datetime.now()

    def complete_workflow(self) -> None:
        """Mark workflow as completed."""
        self.state = ExecutionState.COMPLETED
        self.completed_at = datetime.now()

    def fail_workflow(self, error: str) -> None:
        """Mark workflow as failed."""
        self.state = ExecutionState.FAILED
        self.completed_at = datetime.now()
        self.error = error

    def pause_workflow(self) -> None:
        """Mark workflow as paused."""
        self.state = ExecutionState.PAUSED

    def resume_workflow(self) -> None:
        """Resume workflow from paused state."""
        if self.state == ExecutionState.PAUSED:
            self.state = ExecutionState.RUNNING

    def cancel_workflow(self) -> None:
        """Cancel workflow execution."""
        self.state = ExecutionState.CANCELLED
        self.completed_at = datetime.now()

    def start_node(self, node_id: str) -> None:
        """Mark a node as started."""
        if node_id not in self.node_records:
            self.node_records[node_id] = NodeExecutionRecord(node_id=node_id)

        self.node_records[node_id].state = ExecutionState.RUNNING
        self.node_records[node_id].started_at = datetime.now()
        self.current_node_id = node_id

    def complete_node(self, node_id: str, output: Any = None) -> None:
        """Mark a node as completed."""
        if node_id in self.node_records:
            self.node_records[node_id].state = ExecutionState.COMPLETED
            self.node_records[node_id].completed_at = datetime.now()
            self.node_records[node_id].output = output

    def fail_node(self, node_id: str, error: str) -> None:
        """Mark a node as failed."""
        if node_id in self.node_records:
            self.node_records[node_id].state = ExecutionState.FAILED
            self.node_records[node_id].completed_at = datetime.now()
            self.node_records[node_id].error = error

    def increment_retry(self, node_id: str) -> int:
        """Increment retry count for a node and return new count."""
        if node_id in self.node_records:
            self.node_records[node_id].retry_count += 1
            return self.node_records[node_id].retry_count
        return 0

    def get_node_state(self, node_id: str) -> ExecutionState | None:
        """Get the execution state of a node."""
        return self.node_records[node_id].state if node_id in self.node_records else None

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "state": self.state.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "current_node_id": self.current_node_id,
            "error": self.error,
            "node_records": {
                node_id: {
                    "state": record.state.value,
                    "started_at": record.started_at.isoformat() if record.started_at else None,
                    "completed_at": record.completed_at.isoformat() if record.completed_at else None,
                    "error": record.error,
                    "retry_count": record.retry_count,
                }
                for node_id, record in self.node_records.items()
            },
        }
