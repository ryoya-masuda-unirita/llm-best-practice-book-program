from enum import StrEnum

from openai import AsyncOpenAI
from src.config import config


class LLMProvider(StrEnum):
    """Enum for LLM providers."""

    OPENAI = "openai"


class OpenAIModel(StrEnum):
    GPT_5_4 = "gpt-5.4"
    GPT_5_4_MINI = "gpt-5.4-mini"
    GPT_5_4_NANO = "gpt-5.4-nano"
    GPT_5_2 = "gpt-5.2"
    GPT_5_1 = "gpt-5.1"
    GPT_5 = "gpt-5"
    GPT_5_MINI = "gpt-5-mini"
    GPT_5_NANO = "gpt-5-nano"

    @classmethod
    def list_str(cls) -> list[str]:
        return list(cls)


openai_client = AsyncOpenAI(api_key=config.openai_api_key)
