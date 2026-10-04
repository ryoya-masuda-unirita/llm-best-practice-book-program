"""LLM provider and model enums."""

from enum import StrEnum


class LLMProvider(StrEnum):
    """LLM provider identifiers."""

    OPENAI = "openai"
    # GEMINI = "gemini"
    ANTHROPIC = "anthropic"


class OpenAIModel(StrEnum):
    """OpenAI model identifiers."""

    GPT_5_5 = "openai.gpt-5.5"
    GPT_5_4 = "openai.gpt-5.4"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in OpenAIModel]


# class GeminiModel(StrEnum):
#     """Gemini model identifiers."""
#
#     GEMINI_2_5_PRO = "gemini-2.5-pro"
#     GEMINI_2_5_FLASH = "gemini-2.5-flash"
#     GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"
#     GEMINI_3_5_FLASH = "gemini-3.5-flash"
#     GEMINI_3_1_FLASH_LITE = "gemini-3.1-flash-lite"
#
#     @staticmethod
#     def list_str() -> list[str]:
#         return [model for model in GeminiModel]


class AnthropicModel(StrEnum):
    """Anthropic model identifiers."""

    CLAUDE_SONNET_4_6 = "global.anthropic.claude-sonnet-4-6"
    CLAUDE_HAIKU_4_5 = "global.anthropic.claude-haiku-4-5-20251001-v1:0"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in AnthropicModel]
