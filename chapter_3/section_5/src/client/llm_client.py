from enum import StrEnum


class LLMProvider(StrEnum):
    """Enum for LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class OpenAIModel(StrEnum):
    """Enum for OpenAI models."""

    GPT_5_5 = "openai.gpt-5.5"
    GPT_5_4 = "openai.gpt-5.4"

    @staticmethod
    def list_str() -> list[str]:
        return list(OpenAIModel)


class AnthropicModel(StrEnum):
    """Enum for Anthropic models."""

    CLAUDE_SONNET_4_6 = "global.anthropic.claude-sonnet-4-6"
    CLAUDE_HAIKU_4_5 = "global.anthropic.claude-haiku-4-5-20251001-v1:0"

    @staticmethod
    def list_str() -> list[str]:
        return list(AnthropicModel)
