import os

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr

if os.path.exists(".envrc"):
    load_dotenv(".envrc")


class Config(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    gemini_api_key: SecretStr = Field(
        description="API key for Gemini",
    )


config = Config(gemini_api_key=os.environ.get("GEMINI_API_KEY", ""))
