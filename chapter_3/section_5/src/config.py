import os

from pydantic import BaseModel, ConfigDict, Field, Secret


class Config(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    aws_region: str = Field(default=os.environ.get("AWS_REGION", "us-east-1"), description="AWS region for Bedrock")
    bedrock_api_key: Secret[str] | None = Field(
        default=os.environ.get("AWS_BEARER_TOKEN_BEDROCK"),
        description="API key for Bedrock. If not set, a short-term key is generated from AWS credentials",
    )
    backend_url: str = Field(default=os.environ.get("BACKEND_URL", "http://localhost:8000"), description="Backend URL")
    proxy_url: str = Field(default=os.environ.get("PROXY_URL", "http://localhost:8080"), description="Proxy URL")
    proxy_max_retries: int = Field(
        default=int(os.environ.get("PROXY_MAX_RETRIES", "3")), description="Proxy max retries"
    )
    proxy_retry_backoff: float = Field(
        default=float(os.environ.get("PROXY_RETRY_BACKOFF", "2.0")), description="Proxy retry backoff in seconds"
    )
    gateway_url: str = Field(
        default=os.environ.get("GATEWAY_URL", "http://localhost:8080"), description="Gateway server URL"
    )
    gateway_api_token: Secret[str] = Field(
        default=os.environ.get("GATEWAY_API_TOKEN", "dev-token-12345"),
        description="API token for gateway authentication",
    )
    gateway_timeout: float = Field(
        default=float(os.environ.get("GATEWAY_TIMEOUT", "30.0")), description="Gateway request timeout in seconds"
    )


config = Config()
