from enum import StrEnum


class LLMProvider(StrEnum):
    """Enum for LLM providers."""

    ANTHROPIC = "anthropic"


class AnthropicModel(StrEnum):
    CLAUDE_SONNET_5 = "claude-sonnet-5"
    CLAUDE_OPUS_4_8 = "claude-opus-4-8"
    CLAUDE_OPUS_4_7 = "claude-opus-4-7"
    CLAUDE_SONNET_4_6 = "claude-sonnet-4-6"
    CLAUDE_HAIKU_4_5 = "claude-haiku-4-5"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in AnthropicModel]
