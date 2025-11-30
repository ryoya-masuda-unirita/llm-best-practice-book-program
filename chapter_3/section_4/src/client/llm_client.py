from enum import StrEnum


class LLMProvider(StrEnum):
    """Enum for LLM providers."""

    OPENAI = "openai"
    GEMINI = "gemini"


class OpenAIModel(StrEnum):
    """Enum for OpenAI models."""

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
        return list(OpenAIModel)


class GeminiModel(StrEnum):
    """Enum for Gemini models."""

    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"

    @staticmethod
    def list_str() -> list[str]:
        return list(GeminiModel)
