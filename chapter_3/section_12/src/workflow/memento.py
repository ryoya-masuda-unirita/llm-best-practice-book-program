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
        """
        Serialize memento to JSON.

        Returns:
            JSON string
        """

        def json_serializer(obj):
            """Handle datetime and other non-serializable objects."""
            if isinstance(obj, datetime):
                return obj.isoformat()
            return str(obj)

        def remove_circular_refs(obj, seen=None, depth=0, max_depth=10):
            """Recursively remove circular references from nested data structures."""
            if seen is None:
                seen = set()

            # Limit recursion depth
            if depth > max_depth:
                return "<max depth exceeded>"

            # Handle different types
            if isinstance(obj, (str, int, float, bool, type(None))):
                return obj
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                obj_id = id(obj)
                if obj_id in seen:
                    return "<circular reference>"

                seen.add(obj_id)
                result = {}
                for key, value in obj.items():
                    # Special handling for outputs/variables to prevent deep nesting
                    if key in ("outputs", "variables") and depth > 3:
                        result[key] = f"<truncated at depth {depth}>"
                    else:
                        result[key] = remove_circular_refs(value, seen.copy(), depth + 1, max_depth)
                return result
            elif isinstance(obj, (list, tuple)):
                return [remove_circular_refs(item, seen.copy(), depth + 1, max_depth) for item in obj]
            else:
                return str(obj)

        # Clean the data
        data = {
            "workflow_id": self.workflow_id,
            "checkpoint_id": self.checkpoint_id,
            "timestamp": self.timestamp.isoformat(),
            "workflow_state": remove_circular_refs(self.workflow_state),
            "execution_context": remove_circular_refs(self.execution_context),
            "metadata": self.metadata,
        }

        return json.dumps(data, indent=2, default=json_serializer)

    @classmethod
    def from_json(cls, json_str: str) -> "WorkflowMemento":
        """
        Deserialize memento from JSON.

        Args:
            json_str: JSON string

        Returns:
            WorkflowMemento instance
        """
        data = json.loads(json_str)
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class CheckpointManager:
    """
    Manages workflow checkpoints using the Memento pattern.
    Provides checkpoint creation, storage, and recovery functionality.
    """

    def __init__(self, checkpoint_dir: str = "checkpoints"):
        """
        Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory to store checkpoints
        """
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
        """
        Create a checkpoint of the current workflow state.

        Args:
            workflow_id: Workflow ID
            workflow_state: Current workflow state
            execution_context: Current execution context
            checkpoint_id: Optional checkpoint ID (auto-generated if not provided)
            metadata: Optional metadata

        Returns:
            WorkflowMemento instance
        """
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
        """
        Save a checkpoint to disk.

        Args:
            memento: Memento to save

        Returns:
            Path to saved checkpoint file
        """
        checkpoint_file = self.checkpoint_dir / f"{memento.workflow_id}_{memento.checkpoint_id}.json"

        with open(checkpoint_file, "w", encoding="utf-8") as f:
            f.write(memento.to_json())

        logger.info(f"Saved checkpoint to {checkpoint_file}")
        return checkpoint_file

    def load_checkpoint(self, workflow_id: str, checkpoint_id: str) -> WorkflowMemento:
        """
        Load a checkpoint from disk.

        Args:
            workflow_id: Workflow ID
            checkpoint_id: Checkpoint ID

        Returns:
            WorkflowMemento instance

        Raises:
            FileNotFoundError: If checkpoint file not found
        """
        checkpoint_file = self.checkpoint_dir / f"{workflow_id}_{checkpoint_id}.json"

        if not checkpoint_file.exists():
            raise FileNotFoundError(f"Checkpoint file not found: {checkpoint_file}")

        with open(checkpoint_file, encoding="utf-8") as f:
            json_str = f.read()

        memento = WorkflowMemento.from_json(json_str)
        logger.info(f"Loaded checkpoint {checkpoint_id} for workflow {workflow_id}")
        return memento

    def load_latest_checkpoint(self, workflow_id: str) -> WorkflowMemento | None:
        """
        Load the latest checkpoint for a workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            WorkflowMemento instance or None if no checkpoints found
        """
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
        """
        List all checkpoints for a workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            List of checkpoint metadata
        """
        checkpoint_files = sorted(
            self.checkpoint_dir.glob(f"{workflow_id}_*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        )

        checkpoints = []
        for checkpoint_file in checkpoint_files:
            with open(checkpoint_file, encoding="utf-8") as f:
                data = json.loads(f.read())
                checkpoints.append(
                    {
                        "checkpoint_id": data["checkpoint_id"],
                        "timestamp": data["timestamp"],
                        "file_path": str(checkpoint_file),
                    }
                )

        return checkpoints

    def delete_checkpoint(self, workflow_id: str, checkpoint_id: str) -> bool:
        """
        Delete a checkpoint.

        Args:
            workflow_id: Workflow ID
            checkpoint_id: Checkpoint ID

        Returns:
            True if deleted, False if not found
        """
        checkpoint_file = self.checkpoint_dir / f"{workflow_id}_{checkpoint_id}.json"

        if checkpoint_file.exists():
            checkpoint_file.unlink()
            logger.info(f"Deleted checkpoint {checkpoint_id} for workflow {workflow_id}")
            return True

        logger.warning(f"Checkpoint {checkpoint_id} not found for workflow {workflow_id}")
        return False

    def restore_from_checkpoint(self, memento: WorkflowMemento) -> tuple[WorkflowState, ExecutionContext]:
        """
        Restore workflow state and execution context from a memento.

        Args:
            memento: Memento to restore from

        Returns:
            Tuple of (WorkflowState, ExecutionContext)
        """
        workflow_state = WorkflowState(**memento.workflow_state)
        execution_context = ExecutionContext(**memento.execution_context)

        logger.info(f"Restored workflow state from checkpoint {memento.checkpoint_id}")
        return workflow_state, execution_context
