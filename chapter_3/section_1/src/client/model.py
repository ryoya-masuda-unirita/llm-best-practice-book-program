"""LLM provider and model enums."""

from enum import StrEnum


class LLMProvider(StrEnum):
    """LLM provider identifiers."""

    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"


class OpenAIModel(StrEnum):
    """OpenAI model identifiers."""

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
    """Gemini model identifiers."""

    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in GeminiModel]


class AnthropicModel(StrEnum):
    """Anthropic model identifiers."""

    CLAUDE_OPUS_4_6 = "claude-opus-4-6"
    CLAUDE_SONNET_4_6 = "claude-sonnet-4-6"
    CLAUDE_HAIKU_4_5 = "claude-haiku-4-5"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in AnthropicModel]
