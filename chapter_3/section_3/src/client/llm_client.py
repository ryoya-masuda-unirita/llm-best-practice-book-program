from enum import StrEnum

from anthropic import AsyncAnthropic

from src.config import config


class AnthropicModel(StrEnum):
    CLAUDE_SONNET_4_5 = "claude-sonnet-4-5"
    CLAUDE_OPUS_4 = "claude-opus-4"

    @classmethod
    def all_models(cls) -> list[str]:
        return list(cls)

    @classmethod
    def free_plan_models(cls) -> list[str]:
        return [cls.CLAUDE_SONNET_4_5]

    @classmethod
    def standard_plan_models(cls) -> list[str]:
        return cls.all_models()


anthropic_client = AsyncAnthropic(api_key=config.anthropic_api_key)
