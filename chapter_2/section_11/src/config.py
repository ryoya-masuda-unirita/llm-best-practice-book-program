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

    gemini_api_key: Secret[str] = Field(default=os.environ.get("GEMINI_API_KEY", ""), description="API key for Gemini")
    openai_api_key: Secret[str] = Field(default=os.environ.get("OPENAI_API_KEY", ""), description="API key for OpenAI")
    anthropic_api_key: Secret[str] = Field(
        default=os.environ.get("ANTHROPIC_API_KEY", ""), description="API key for Anthropic"
    )


config = Config()
