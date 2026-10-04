from enum import StrEnum

from aws_bedrock_token_generator import provide_token
from openai import AsyncOpenAI
from src.config import config


class LLMProvider(StrEnum):
    """Enum for LLM providers."""

    OPENAI = "openai"


class OpenAIModel(StrEnum):
    GPT_5_5 = "openai.gpt-5.5"
    GPT_5_4 = "openai.gpt-5.4"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in OpenAIModel]


bedrock_api_key = (
    config.bedrock_api_key.get_secret_value() if config.bedrock_api_key else provide_token(region=config.aws_region)
)

openai_client = AsyncOpenAI(
    api_key=bedrock_api_key,
    base_url=f"https://bedrock-mantle.{config.aws_region}.api.aws/openai/v1",
)
