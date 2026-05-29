from enum import StrEnum

from src.client.anthropic_wrapper_client import AsyncAnthropicWrapperClient
from src.client.gemini_wrapper_client import GenAIWrapperClient
from src.client.openai_wrapper_client import AsyncOpenAIWrapperClient
from src.config import config


class LLMProvider(StrEnum):
    """Enum for LLM providers."""

    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"


class OpenAIModel(StrEnum):
    GPT_5_5 = "gpt-5.5"
    GPT_5_4 = "gpt-5.4"
    GPT_5_4_MINI = "gpt-5.4-mini"
    GPT_5_4_NANO = "gpt-5.4-nano"
    GPT_5_2 = "gpt-5.2"
    GPT_5_1 = "gpt-5.1"
    GPT_5 = "gpt-5"
    GPT_5_MINI = "gpt-5-mini"
    GPT_5_NANO = "gpt-5-nano"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in OpenAIModel]


class GeminiModel(StrEnum):
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"
    GEMINI_3_5_FLASH = "gemini-3.5-flash"
    GEMINI_3_1_FLASH_LITE = "gemini-3.1-flash-lite"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in GeminiModel]


class AnthropicModel(StrEnum):
    CLAUDE_OPUS_4_7 = "claude-opus-4-7"
    CLAUDE_SONNET_4_6 = "claude-sonnet-4-6"
    CLAUDE_HAIKU_4_5 = "claude-haiku-4-5"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in AnthropicModel]


openai_client = AsyncOpenAIWrapperClient(api_key=config.openai_api_key)
google_genai_client = GenAIWrapperClient(api_key=config.google_api_key)
anthropic_client = AsyncAnthropicWrapperClient(api_key=config.anthropic_api_key)
