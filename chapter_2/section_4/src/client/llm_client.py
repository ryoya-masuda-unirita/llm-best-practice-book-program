from enum import StrEnum

from anthropic import AsyncAnthropic
from google import genai
from openai import AsyncOpenAI
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


google_genai_client = genai.Client(api_key=config.gemini_api_key)

openai_client = AsyncOpenAI(api_key=config.openai_api_key)

anthropic_client = AsyncAnthropic(api_key=config.anthropic_api_key)
