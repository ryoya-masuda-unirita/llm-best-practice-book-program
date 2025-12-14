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

    anthropic_api_key: Secret[str] = Field(default=os.environ["ANTHROPIC_API_KEY"], description="API key for Anthropic")


config = Config()
