from enum import StrEnum

from anthropic import AsyncAnthropic
from google import genai
from openai import AsyncOpenAI

from src.config import config


class LLMProvider(StrEnum):
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"


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
        return [model for model in OpenAIModel]


class GeminiModel(StrEnum):
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in GeminiModel]


class AnthropicModel(StrEnum):
    CLAUDE_SONNET_4_5 = "claude-sonnet-4-5"
    CLAUDE_OPUS_4_1 = "claude-opus-4-1"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in AnthropicModel]


google_genai_client = genai.Client(api_key=config.gemini_api_key)

openai_client = AsyncOpenAI(api_key=config.openai_api_key)

anthropic_client = AsyncAnthropic(api_key=config.anthropic_api_key)
