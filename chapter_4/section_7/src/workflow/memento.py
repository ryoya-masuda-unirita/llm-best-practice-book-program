"""Memento Pattern: Checkpoint and recovery for workflow execution."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.logger import make_logger
from src.workflow.base import ExecutionContext
from src.workflow.state import WorkflowState

logger = make_logger(__name__)


class WorkflowMemento(BaseModel):
    """
    Memento Pattern: Captures and externalizes workflow state for checkpointing.
    Enables recovery from failures without violating encapsulation.
    """

    model_config = ConfigDict(
        validate_assignment=True,
        extra="allow",
        arbitrary_types_allowed=True,
    )

    workflow_id: str = Field(..., description="Workflow ID")
    checkpoint_id: str = Field(..., description="Unique checkpoint ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="Checkpoint timestamp")
    workflow_state: dict[str, Any] = Field(..., description="Serialized workflow state")
    execution_context: dict[str, Any] = Field(..., description="Serialized execution context")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def to_json(self) -> str:
        """Serialize memento to JSON."""
        data = {
            "workflow_id": self.workflow_id,
            "checkpoint_id": self.checkpoint_id,
            "timestamp": self.timestamp.isoformat(),
            "workflow_state": self.workflow_state,
            "execution_context": self.execution_context,
            "metadata": self.metadata,
        }
        return json.dumps(
            data, indent=2, default=lambda obj: obj.isoformat() if isinstance(obj, datetime) else str(obj)
        )

    @classmethod
    def from_json(cls, json_str: str) -> "WorkflowMemento":
        """Deserialize memento from JSON."""
        data = json.loads(json_str)
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class CheckpointManager:
    """
    Manages workflow checkpoints using the Memento pattern.
    Provides checkpoint creation, storage, and recovery functionality.
    """

    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Checkpoint manager initialized with directory: {self.checkpoint_dir}")

    def create_checkpoint(
        self,
        workflow_id: str,
        workflow_state: WorkflowState,
        execution_context: ExecutionContext,
        checkpoint_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowMemento:
        """Create a checkpoint of the current workflow state."""
        from uuid import uuid4

        checkpoint_id = checkpoint_id or uuid4().hex

        memento = WorkflowMemento(
            workflow_id=workflow_id,
            checkpoint_id=checkpoint_id,
            workflow_state=workflow_state.model_dump(),
            execution_context=execution_context.model_dump(),
            metadata=metadata or {},
        )

        logger.info(f"Created checkpoint {checkpoint_id} for workflow {workflow_id}")
        return memento

    def save_checkpoint(self, memento: WorkflowMemento) -> Path:
        """Save a checkpoint to disk."""
        checkpoint_file = self.checkpoint_dir / f"{memento.workflow_id}_{memento.checkpoint_id}.json"

        with open(checkpoint_file, "w", encoding="utf-8") as f:
            f.write(memento.to_json())

        logger.info(f"Saved checkpoint to {checkpoint_file}")
        return checkpoint_file

    def load_checkpoint(self, workflow_id: str, checkpoint_id: str) -> WorkflowMemento:
        """Load a checkpoint from disk."""
        checkpoint_file = self.checkpoint_dir / f"{workflow_id}_{checkpoint_id}.json"

        if not checkpoint_file.exists():
            raise FileNotFoundError(f"Checkpoint file not found: {checkpoint_file}")

        with open(checkpoint_file, encoding="utf-8") as f:
            json_str = f.read()

        memento = WorkflowMemento.from_json(json_str)
        logger.info(f"Loaded checkpoint {checkpoint_id} for workflow {workflow_id}")
        return memento

    def load_latest_checkpoint(self, workflow_id: str) -> WorkflowMemento | None:
        """Load the latest checkpoint for a workflow."""
        checkpoint_files = sorted(
            self.checkpoint_dir.glob(f"{workflow_id}_*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        )

        if not checkpoint_files:
            logger.warning(f"No checkpoints found for workflow {workflow_id}")
            return None

        with open(checkpoint_files[0], encoding="utf-8") as f:
            json_str = f.read()

        memento = WorkflowMemento.from_json(json_str)
        logger.info(f"Loaded latest checkpoint {memento.checkpoint_id} for workflow {workflow_id}")
        return memento

    def list_checkpoints(self, workflow_id: str) -> list[dict[str, Any]]:
        """List all checkpoints for a workflow."""
        checkpoints = []
        for cp_file in sorted(
            self.checkpoint_dir.glob(f"{workflow_id}_*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        ):
            # Skip empty or invalid checkpoint files
            if cp_file.stat().st_size == 0:
                logger.warning(f"Skipping empty checkpoint file: {cp_file}")
                continue

            try:
                with open(cp_file, encoding="utf-8") as f:
                    content = f.read()
                    if not content.strip():
                        logger.warning(f"Skipping empty checkpoint file: {cp_file}")
                        continue
                    data = json.loads(content)
                    checkpoints.append({"checkpoint_id": data["checkpoint_id"], "timestamp": data["timestamp"]})
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping invalid checkpoint file {cp_file}: {e}")
                continue
        return checkpoints

    def restore_from_checkpoint(self, memento: WorkflowMemento) -> tuple[WorkflowState, ExecutionContext]:
        """Restore workflow state and execution context from a memento."""
        workflow_state = WorkflowState(**memento.workflow_state)
        execution_context = ExecutionContext(**memento.execution_context)

        logger.info(f"Restored workflow state from checkpoint {memento.checkpoint_id}")
        return workflow_state, execution_context
