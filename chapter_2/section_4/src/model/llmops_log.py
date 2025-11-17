"""Structured logging models for LLMOps."""

import json
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class StorageType(StrEnum):
    """Types of prompt storage backends."""

    LOCAL = "local"


class LLMOpsLogEntry(BaseModel):
    """Structured log entry for LLM operations."""

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    request_id: str
    prompt_id: str
    user_id: str | None = None
    model: str
    temperature: float | None = None
    latency_ms: float | None = None
    status_code: int | None = None
    error_message: str | None = None
    level: str = "INFO"
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_json_string(self) -> str:
        """Convert log entry to JSON string for logging."""
        return json.dumps(self.model_dump(exclude_none=True), ensure_ascii=False)
