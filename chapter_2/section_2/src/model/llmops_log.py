"""Structured logging models for LLMOps."""

import json
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class StorageType(StrEnum):
    """Types of prompt storage backends."""

    LOCAL = "local"


class LogLevel(StrEnum):
    """Log levels for structured logs."""

    INFO = "INFO"
    DEBUG = "DEBUG"
    ERROR = "ERROR"
    WARNING = "WARNING"


class LLMOpsLogEntry(BaseModel):
    """Structured log entry for LLM operations."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=False,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 formatted timestamp of when the log was created",
    )
    request_id: str = Field(..., description="Unique identifier for the entire request")
    prompt_id: str = Field(..., description="Unique identifier to retrieve prompt content from data store")
    user_id: Optional[str] = Field(None, description="User identifier (if available)")
    model: str = Field(..., description="LLM model name used for the request")
    temperature: Optional[float] = Field(None, description="Temperature parameter used for generation", ge=0.0, le=2.0)
    latency_ms: Optional[float] = Field(None, description="Response time in milliseconds", ge=0.0)
    status_code: Optional[int] = Field(None, description="API response status code")
    error_message: Optional[str] = Field(None, description="Error message if request failed")
    level: LogLevel = Field(default=LogLevel.INFO, description="Log level")
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    def to_json_string(self) -> str:
        """Convert log entry to JSON string for logging."""
        return json.dumps(self.model_dump(exclude_none=True), ensure_ascii=False)

    def save_to_file(self, file_path: str) -> None:
        """Save log entry to a JSON file."""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(exclude_none=True), f, indent=2, ensure_ascii=False)
