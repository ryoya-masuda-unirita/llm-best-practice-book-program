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
    anthropic_api_key: Secret[str] = Field(default=os.environ["ANTHROPIC_API_KEY"], description="API key for Anthropic")
    redis_host: str = Field(default=os.environ.get("REDIS_HOST", "localhost"), description="Redis host")
    redis_port: int = Field(default=int(os.environ.get("REDIS_PORT", "6379")), description="Redis port")
    redis_db: int = Field(default=int(os.environ.get("REDIS_DB", "0")), description="Redis database")


config = Config()
