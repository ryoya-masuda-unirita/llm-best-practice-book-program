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

    llm_request_timeout: float = Field(
        default=float(os.getenv("LLM_REQUEST_TIMEOUT", "10.0")), description="Timeout for LLM API requests in seconds"
    )
    cache_ttl: int = Field(
        default=int(os.getenv("CACHE_TTL", "3600")), description="Cache time-to-live in seconds (default: 1 hour)"
    )


config = Config()
