"""Models for batch processing jobs."""

import time
import uuid
from enum import StrEnum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.model.model import CharacterRequest, CharacterResponse


class JobStatus(StrEnum):
    """Status of a batch job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BatchJobRequest(BaseModel):
    """Request model for submitting a batch job."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    provider: str = Field(..., description="LLM provider to use (openai or gemini)")
    model: str = Field(..., description="Model name to use")
    character_requests: list[CharacterRequest] = Field(
        ..., description="List of character generation requests", min_length=1, max_length=100
    )


class BatchJobResponse(BaseModel):
    """Response model after submitting a batch job."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    job_id: str = Field(..., description="Unique job ID")
    status: JobStatus = Field(default=JobStatus.PENDING, description="Job status")
    total_tasks: int = Field(..., description="Total number of tasks in the batch")
    submitted_at: float = Field(default_factory=time.time, description="Timestamp when job was submitted")


class TaskStatus(BaseModel):
    """Status of an individual task within a batch job."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    task_index: int = Field(..., description="Index of the task in the batch")
    status: JobStatus = Field(..., description="Status of this task")
    character: Optional[CharacterResponse] = Field(None, description="Generated character (if completed)")
    error: Optional[str] = Field(None, description="Error message (if failed)")
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")


class BatchJobStatusResponse(BaseModel):
    """Response model for checking batch job status."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    job_id: str = Field(..., description="Unique job ID")
    status: JobStatus = Field(..., description="Overall job status")
    total_tasks: int = Field(..., description="Total number of tasks")
    completed_tasks: int = Field(default=0, description="Number of completed tasks")
    failed_tasks: int = Field(default=0, description="Number of failed tasks")
    pending_tasks: int = Field(default=0, description="Number of pending tasks")
    submitted_at: float = Field(..., description="Timestamp when job was submitted")
    started_at: Optional[float] = Field(None, description="Timestamp when processing started")
    completed_at: Optional[float] = Field(None, description="Timestamp when job completed")


class BatchJobResultResponse(BaseModel):
    """Response model for retrieving batch job results."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    job_id: str = Field(..., description="Unique job ID")
    status: JobStatus = Field(..., description="Overall job status")
    provider: str = Field(..., description="LLM provider used")
    model: str = Field(..., description="Model used")
    tasks: list[TaskStatus] = Field(..., description="Status and results of each task")
    submitted_at: float = Field(..., description="Timestamp when job was submitted")
    completed_at: Optional[float] = Field(None, description="Timestamp when job completed")


class InternalJobData(BaseModel):
    """Internal job data stored in Redis queue."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique job ID")
    provider: str = Field(..., description="LLM provider")
    model: str = Field(..., description="Model name")
    character_requests: list[dict[str, Any]] = Field(..., description="Character requests as dicts")
    submitted_at: float = Field(default_factory=time.time, description="Submission timestamp")
