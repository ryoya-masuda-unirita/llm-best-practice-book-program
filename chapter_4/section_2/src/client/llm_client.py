from enum import StrEnum

from anthropic import AsyncAnthropicBedrock
from src.config import config


class AnthropicModel(StrEnum):
    CLAUDE_SONNET_4_6 = "global.anthropic.claude-sonnet-4-6"
    CLAUDE_HAIKU_4_5 = "global.anthropic.claude-haiku-4-5-20251001-v1:0"

    @classmethod
    def all_models(cls) -> list[str]:
        return list(cls)

    @classmethod
    def free_plan_models(cls) -> list[str]:
        return [cls.CLAUDE_SONNET_4_6]

    @classmethod
    def standard_plan_models(cls) -> list[str]:
        return cls.all_models()


anthropic_client = AsyncAnthropicBedrock(aws_region=config.aws_region)
