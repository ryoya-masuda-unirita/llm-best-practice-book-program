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
    backend_url: str = Field(default=os.environ.get("BACKEND_URL", "http://localhost:8000"), description="Backend URL")
    proxy_url: str = Field(default=os.environ.get("PROXY_URL", "http://localhost:8080"), description="Proxy URL")
    proxy_max_retries: int = Field(
        default=int(os.environ.get("PROXY_MAX_RETRIES", "3")), description="Proxy max retries"
    )
    proxy_retry_backoff: float = Field(
        default=float(os.environ.get("PROXY_RETRY_BACKOFF", "2.0")), description="Proxy retry backoff in seconds"
    )


config = Config()
