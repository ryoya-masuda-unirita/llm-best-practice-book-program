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

    num_candidates: int = Field(default=3, description="Number of candidates to generate for Best-of-N", ge=1, le=10)
    quality_threshold: float = Field(
        default=3.0, description="Minimum quality threshold for accepting a candidate", ge=1.0, le=5.0
    )
    max_retries: int = Field(default=3, description="Maximum retries when all candidates fail threshold", ge=1, le=10)


config = Config()
