from enum import StrEnum

from anthropic import AsyncAnthropic

from src.config import config


class LLMProvider(StrEnum):
    """Enum for LLM providers."""

    ANTHROPIC = "anthropic"


class AnthropicModel(StrEnum):
    """Enum for Anthropic model identifiers."""

    CLAUDE_SONNET_4_5 = "claude-sonnet-4-5"
    CLAUDE_OPUS_4_1 = "claude-opus-4-1"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in AnthropicModel]


anthropic_client = AsyncAnthropic(api_key=config.anthropic_api_key)
