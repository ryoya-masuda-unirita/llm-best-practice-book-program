import asyncio
import json
from enum import StrEnum

import boto3
from anthropic import AsyncAnthropicBedrock
from aws_bedrock_token_generator import provide_token
from openai import AsyncOpenAI
from src.config import config


class LLMProvider(StrEnum):
    """Enum for LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class OpenAIModel(StrEnum):
    GPT_5_5 = "openai.gpt-5.5"
    GPT_5_4 = "openai.gpt-5.4"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in OpenAIModel]


class AnthropicModel(StrEnum):
    CLAUDE_SONNET_4_6 = "global.anthropic.claude-sonnet-4-6"
    CLAUDE_HAIKU_4_5 = "global.anthropic.claude-haiku-4-5-20251001-v1:0"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in AnthropicModel]


anthropic_client = AsyncAnthropicBedrock(aws_region=config.aws_region)

bedrock_api_key = (
    config.bedrock_api_key.get_secret_value() if config.bedrock_api_key else provide_token(region=config.aws_region)
)

openai_client = AsyncOpenAI(
    api_key=bedrock_api_key,
    base_url=f"https://bedrock-mantle.{config.aws_region}.api.aws/openai/v1",
)


bedrock_runtime_client = boto3.client("bedrock-runtime", region_name=config.aws_region)


async def get_bedrock_embedding(
    text: str | list[dict],
) -> list[float]:
    """Get embeddings from Amazon Titan Text Embeddings on Bedrock."""
    _input = text if isinstance(text, str) else json.dumps(text)

    response = await asyncio.to_thread(
        bedrock_runtime_client.invoke_model,
        modelId="amazon.titan-embed-text-v2:0",
        body=json.dumps({"inputText": _input}),
    )
    return json.loads(response["body"].read())["embedding"]


# Bedrock上ではOpenAI・Anthropicのどちらを使う場合も、埋め込みはTitanで生成する
get_openai_embedding = get_bedrock_embedding
get_anthropic_embedding = get_bedrock_embedding
