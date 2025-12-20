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

    gemini_api_key: Secret[str] = Field(default=os.environ["GEMINI_API_KEY"], description="API key for Gemini")
    openai_api_key: Secret[str] = Field(default=os.environ["OPENAI_API_KEY"], description="API key for OpenAI")
    anthropic_api_key: Secret[str] = Field(default=os.environ["ANTHROPIC_API_KEY"], description="API key for Anthropic")

    num_candidates: int = Field(default=3, description="Number of candidates to generate for Best-of-N", ge=1, le=10)
    quality_threshold: float = Field(
        default=3.0, description="Minimum quality threshold for accepting a candidate", ge=1.0, le=5.0
    )
    max_retries: int = Field(default=3, description="Maximum retries when all candidates fail threshold", ge=1, le=10)


config = Config()
