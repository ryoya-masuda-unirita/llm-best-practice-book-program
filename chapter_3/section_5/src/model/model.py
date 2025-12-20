import json
import time
import uuid
from enum import StrEnum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from src.client.llm_client import LLMProvider


class Priority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class UserTier(StrEnum):
    ENTERPRISE = "enterprise"
    PREMIUM = "premium"
    FREE = "free"


class TaskStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class Gender(StrEnum):
    FEMALE = "female"
    MALE = "male"


class CharacterRequest(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    gender: Gender = Field(..., description="The gender of the character.")
    age: int = Field(..., description="The age of the character.", ge=0, le=100)
    additional_instructions: Optional[str] = Field(..., description="Additional instructions for character generation.")


class CharacterPersonality(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    short_personality: str = Field(..., description="A short description of the character's personality.")
    description: str = Field(..., description="A description of the character's personality traits and behaviors.")


class CharacterResponse(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    first_name: str = Field(..., description="The first name of the character.")
    last_name: str = Field(..., description="The last name of the character.")
    gender: Gender = Field(Gender.MALE, description="The gender of the character.")
    age: int = Field(..., description="The age of the character.", ge=0, le=100)
    personalities: list[CharacterPersonality] = Field(
        ..., description="The three most important personality traits of the character."
    )

    @staticmethod
    def detailed_model() -> dict:
        params = {}
        for k, v in CharacterResponse.model_fields.items():
            if k in ["first_name", "last_name"]:
                params[k] = f"string; {v.description}"
            elif k == "gender":
                params[k] = f"enum; {v.description}; {[g.value for g in Gender]}"
            elif k == "age":
                params[k] = f"number; {v.description}; 0-100"
            elif k == "personalities":
                params[k] = []
                for i in range(3):
                    params[k].append(
                        {
                            "short_personality": f"string; {v.description} (personality {i + 1})",
                            "description": f"string; {v.description} (detailed description for personality {i + 1})",
                        }
                    )
        return params

    def save_as_json(self, file_path: str) -> None:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=4, ensure_ascii=False)


class LLMRequest(BaseModel):
    provider: LLMProvider = Field(..., description="The LLM provider to use (openai)")
    model: str = Field(..., description="The model name to use for generation")
    character_request: CharacterRequest = Field(..., description="Character generation request parameters")
    user_tier: UserTier = Field(default=UserTier.FREE, description="User tier for priority assignment")


class QueuedTask(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique task identifier")
    priority: Priority = Field(..., description="Priority level of the task")
    user_tier: UserTier = Field(..., description="User tier that submitted the task")
    provider: str = Field(..., description="LLM provider")
    model: str = Field(..., description="Model name")
    character_request: CharacterRequest = Field(..., description="Character generation request")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current status of the task")
    created_at: float = Field(default_factory=time.time, description="Timestamp when task was created")
    started_at: Optional[float] = Field(default=None, description="Timestamp when processing started")
    completed_at: Optional[float] = Field(default=None, description="Timestamp when processing completed")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    error_message: Optional[str] = Field(default=None, description="Error message if task failed")
    result: Optional[dict[str, Any]] = Field(default=None, description="Task result data")


class LLMResponse(BaseModel):
    character: CharacterResponse = Field(..., description="Generated character information")
    provider: str = Field(..., description="LLM provider used")
    model: str = Field(..., description="Model used")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")


class TaskSubmissionResponse(BaseModel):
    task_id: str = Field(..., description="Unique identifier for the submitted task")
    priority: Priority = Field(..., description="Priority level assigned to the task")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Initial status of the task")
    estimated_wait_time_seconds: Optional[float] = Field(
        default=None, description="Estimated wait time before processing starts"
    )
    message: str = Field(..., description="Human-readable message about the submission")


class TaskStatusResponse(BaseModel):
    task_id: str = Field(..., description="Task identifier")
    priority: Priority = Field(..., description="Priority level of the task")
    status: TaskStatus = Field(..., description="Current status of the task")
    created_at: float = Field(..., description="Timestamp when task was created")
    started_at: Optional[float] = Field(default=None, description="Timestamp when processing started")
    completed_at: Optional[float] = Field(default=None, description="Timestamp when processing completed")
    result: Optional[LLMResponse] = Field(default=None, description="Task result if completed")
    error_message: Optional[str] = Field(default=None, description="Error message if task failed")
    queue_position: Optional[int] = Field(default=None, description="Position in queue if still pending")


class QueueStatsResponse(BaseModel):
    high_priority_count: int = Field(..., description="Number of tasks in high priority queue")
    medium_priority_count: int = Field(..., description="Number of tasks in medium priority queue")
    low_priority_count: int = Field(..., description="Number of tasks in low priority queue")
    total_pending: int = Field(..., description="Total number of pending tasks")
    processing_count: int = Field(..., description="Number of tasks currently being processed")


class HealthResponse(BaseModel):
    status: Literal["healthy"] = "healthy"
    timestamp: float = Field(default_factory=time.time)
