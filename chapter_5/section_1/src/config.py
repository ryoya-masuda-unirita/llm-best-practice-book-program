import os

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

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


config = Config()
