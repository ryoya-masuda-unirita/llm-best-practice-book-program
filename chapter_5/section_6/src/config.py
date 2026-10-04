import os

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, Secret

if os.path.exists(".envrc"):
    load_dotenv(".envrc")


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


config = Config()
