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

    # Gateway configuration
    gateway_api_token: Secret[str] = Field(
        default=os.environ.get("GATEWAY_API_TOKEN", "dev-token-12345"),
        description="API token for gateway authentication",
    )
    gateway_max_retries: int = Field(
        default=int(os.environ.get("GATEWAY_MAX_RETRIES", "3")), description="Gateway max retries"
    )
    gateway_retry_backoff: float = Field(
        default=float(os.environ.get("GATEWAY_RETRY_BACKOFF", "2.0")), description="Gateway retry backoff in seconds"
    )
    gateway_timeout: float = Field(
        default=float(os.environ.get("GATEWAY_TIMEOUT", "30.0")), description="Gateway request timeout in seconds"
    )
    gateway_enable_cache: bool = Field(
        default=os.environ.get("GATEWAY_ENABLE_CACHE", "false").lower() == "true",
        description="Enable response caching in gateway",
    )
    gateway_cache_ttl: int = Field(
        default=int(os.environ.get("GATEWAY_CACHE_TTL", "300")), description="Cache TTL in seconds"
    )


config = Config()
