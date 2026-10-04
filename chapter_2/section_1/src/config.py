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

    # gemini_api_key: Secret[str] = Field(default=os.environ["GEMINI_API_KEY"], description="API key for Gemini")
    aws_region: str = Field(default=os.environ.get("AWS_REGION", "us-east-1"), description="AWS region for Bedrock")
    bedrock_api_key: Secret[str] | None = Field(
        default=os.environ.get("AWS_BEARER_TOKEN_BEDROCK"),
        description="API key for Bedrock. If not set, a short-term key is generated from AWS credentials",
    )


config = Config()
