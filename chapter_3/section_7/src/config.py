import os

from pydantic import BaseModel, ConfigDict, Field, Secret


class Config(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    gemini_api_key: Secret[str] = Field(default=os.environ["GEMINI_API_KEY"], description="API key for Gemini")
    openai_api_key: Secret[str] = Field(default=os.environ["OPENAI_API_KEY"], description="API key for OpenAI")

    # Redis configuration
    redis_host: str = Field(default=os.environ.get("REDIS_HOST", "localhost"), description="Redis host")
    redis_port: int = Field(default=int(os.environ.get("REDIS_PORT", "6379")), description="Redis port")
    redis_db: int = Field(default=int(os.environ.get("REDIS_DB", "0")), description="Redis database number")

    # Queue processing configuration
    high_priority_ratio: float = Field(default=0.7, description="Processing capacity ratio for high priority queue")
    medium_priority_ratio: float = Field(default=0.2, description="Processing capacity ratio for medium priority queue")
    low_priority_ratio: float = Field(default=0.1, description="Processing capacity ratio for low priority queue")

    # Task timeout configuration
    task_timeout_seconds: int = Field(default=300, description="Maximum time to wait for task completion (seconds)")
    max_retry_attempts: int = Field(default=3, description="Maximum number of retry attempts for failed tasks")


config = Config()
