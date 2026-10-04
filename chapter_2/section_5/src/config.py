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
    redis_host: str = Field(default=os.environ.get("REDIS_HOST", "localhost"), description="Redis host")
    redis_port: int = Field(default=int(os.environ.get("REDIS_PORT", "6379")), description="Redis port")
    redis_db: int = Field(default=int(os.environ.get("REDIS_DB", "0")), description="Redis database")


config = Config()
