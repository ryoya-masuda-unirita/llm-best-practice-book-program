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

    google_api_key: Secret[str] = Field(
        default=os.environ.get("GOOGLE_API_KEY", ""), description="API key for Google GenAI"
    )
    openai_api_key: Secret[str] = Field(default=os.environ.get("OPENAI_API_KEY", ""), description="API key for OpenAI")

    usage_log_directory: str = Field(
        default=os.environ.get("USAGE_LOG_DIRECTORY", "usage_logs"), description="Directory for logs"
    )


config = Config()
