"""Checkpoint management for workflow state persistence."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from src.logger import make_logger
from src.workflow.models import ExecutionContext, WorkflowState

logger = make_logger(__name__)


class Checkpoint(BaseModel):
    """Serializable workflow checkpoint."""

    model_config = ConfigDict(validate_assignment=True, extra="allow", arbitrary_types_allowed=True)

    workflow_id: str
    checkpoint_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    workflow_state: dict[str, Any]
    execution_context: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(
            {
                "workflow_id": self.workflow_id,
                "checkpoint_id": self.checkpoint_id,
                "timestamp": self.timestamp.isoformat(),
                "workflow_state": self.workflow_state,
                "execution_context": self.execution_context,
                "metadata": self.metadata,
            },
            indent=2,
            default=str,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Checkpoint":
        data = json.loads(json_str)
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class CheckpointManager:
    """Manages workflow checkpoints for fault tolerance."""

    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def create_checkpoint(
        self,
        workflow_id: str,
        state: WorkflowState,
        context: ExecutionContext,
        checkpoint_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Checkpoint:
        return Checkpoint(
            workflow_id=workflow_id,
            checkpoint_id=checkpoint_id or uuid4().hex,
            workflow_state=state.model_dump(),
            execution_context=context.model_dump(),
            metadata=metadata or {},
        )

    def save_checkpoint(self, checkpoint: Checkpoint) -> Path:
        path = self.checkpoint_dir / f"{checkpoint.workflow_id}_{checkpoint.checkpoint_id}.json"
        path.write_text(checkpoint.to_json(), encoding="utf-8")
        return path

    def load_checkpoint(self, workflow_id: str, checkpoint_id: str) -> Checkpoint:
        path = self.checkpoint_dir / f"{workflow_id}_{checkpoint_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {path}")
        return Checkpoint.from_json(path.read_text(encoding="utf-8"))

    def load_latest_checkpoint(self, workflow_id: str) -> Checkpoint | None:
        files = sorted(
            self.checkpoint_dir.glob(f"{workflow_id}_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not files:
            return None
        return Checkpoint.from_json(files[0].read_text(encoding="utf-8"))

    def list_checkpoints(self, workflow_id: str) -> list[dict[str, Any]]:
        result = []
        for path in sorted(
            self.checkpoint_dir.glob(f"{workflow_id}_*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        ):
            if path.stat().st_size == 0:
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                result.append({"checkpoint_id": data["checkpoint_id"], "timestamp": data["timestamp"]})
            except (json.JSONDecodeError, KeyError):
                continue
        return result

    def restore_from_checkpoint(self, checkpoint: Checkpoint) -> tuple[WorkflowState, ExecutionContext]:
        return (
            WorkflowState(**checkpoint.workflow_state),
            ExecutionContext(**checkpoint.execution_context),
        )
