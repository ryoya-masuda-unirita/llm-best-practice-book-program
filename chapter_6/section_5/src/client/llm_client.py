from enum import StrEnum

from openai import AsyncOpenAI
from src.config import config


class LLMProvider(StrEnum):
    """Enum for LLM providers."""

    OPENAI = "openai"


class OpenAIModel(StrEnum):
    GPT_5 = "gpt-5"
    GPT_5_MINI = "gpt-5-mini"
    GPT_5_NANO = "gpt-5-nano"
    GPT_4_1 = "gpt-4.1"
    GPT_4_1_MINI = "gpt-4.1-mini"
    GPT_4_1_NANO = "gpt-4.1-nano"
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"

    @staticmethod
    def list_str() -> list[str]:
        return [model.value for model in OpenAIModel]


openai_client = AsyncOpenAI(api_key=config.openai_api_key)
