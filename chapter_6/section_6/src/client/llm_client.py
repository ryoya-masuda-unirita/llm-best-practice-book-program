from enum import StrEnum

from anthropic import AsyncAnthropicBedrock
from src.config import config


class LLMProvider(StrEnum):
    ANTHROPIC = "anthropic"


class AnthropicModel(StrEnum):
    CLAUDE_SONNET_4_6 = "global.anthropic.claude-sonnet-4-6"
    CLAUDE_HAIKU_4_5 = "global.anthropic.claude-haiku-4-5-20251001-v1:0"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in AnthropicModel]


anthropic_client = AsyncAnthropicBedrock(aws_region=config.aws_region)
