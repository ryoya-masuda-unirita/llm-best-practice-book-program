from enum import StrEnum

import boto3
from anthropic import AsyncAnthropicBedrock
from src.config import config


class AnthropicModel(StrEnum):
    CLAUDE_SONNET_4_6 = "global.anthropic.claude-sonnet-4-6"
    CLAUDE_HAIKU_4_5 = "global.anthropic.claude-haiku-4-5-20251001-v1:0"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in AnthropicModel]


class BedrockEmbeddingModel(StrEnum):
    TITAN_EMBED_TEXT_V2 = "amazon.titan-embed-text-v2:0"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in BedrockEmbeddingModel]


anthropic_client = AsyncAnthropicBedrock(aws_region=config.aws_region)

bedrock_runtime_client = boto3.client("bedrock-runtime", region_name=config.aws_region)
