import os
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, Secret


class CacheBackend(StrEnum):
    """Enum for cache backend types."""

    MEMORY = "memory"
    REDIS = "redis"


class Config(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    gemini_api_key: Secret[str] = Field(default=os.environ["GEMINI_API_KEY"], description="API key for Gemini")
    openai_api_key: Secret[str] = Field(default=os.environ["OPENAI_API_KEY"], description="API key for OpenAI")

    # Cache configuration
    cache_enabled: bool = Field(
        default=os.environ.get("CACHE_ENABLED", "true").lower() == "true",
        description="Enable or disable caching",
    )
    cache_backend: CacheBackend = Field(
        default=CacheBackend(os.environ.get("CACHE_BACKEND", "memory")),
        description="Cache backend type (memory or redis)",
    )
    cache_ttl: int = Field(default=int(os.environ.get("CACHE_TTL", "3600")), description="Cache TTL in seconds", ge=0)

    # Redis configuration (used when cache_backend is redis)
    redis_host: str = Field(default=os.environ.get("REDIS_HOST", "localhost"), description="Redis host")
    redis_port: int = Field(default=int(os.environ.get("REDIS_PORT", "6379")), description="Redis port", ge=1)
    redis_db: int = Field(default=int(os.environ.get("REDIS_DB", "0")), description="Redis database number", ge=0)
    redis_password: Secret[str] | None = Field(
        default=os.environ.get("REDIS_PASSWORD"), description="Redis password (optional)"
    )


config = Config()
