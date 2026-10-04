import os

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, Secret


class Config(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    if os.path.exists(".envrc"):
        load_dotenv(".envrc")

    aws_region: str = Field(default=os.environ.get("AWS_REGION", "us-east-1"), description="AWS region for Bedrock")
    bedrock_api_key: Secret[str] | None = Field(
        default=os.environ.get("AWS_BEARER_TOKEN_BEDROCK"),
        description="API key for Bedrock. If not set, a short-term key is generated from AWS credentials",
    )

    llm_request_timeout: float = Field(
        default=float(os.getenv("LLM_REQUEST_TIMEOUT", "10.0")), description="Timeout for LLM API requests in seconds"
    )
    cache_ttl: int = Field(
        default=int(os.getenv("CACHE_TTL", "3600")), description="Cache time-to-live in seconds (default: 1 hour)"
    )


config = Config()
