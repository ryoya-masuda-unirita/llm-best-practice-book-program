from enum import StrEnum

from aws_bedrock_token_generator import provide_token
from src.client.anthropic_wrapper_client import AsyncAnthropicWrapperClient

# from src.client.gemini_wrapper_client import GenAIWrapperClient
from src.client.openai_wrapper_client import AsyncOpenAIWrapperClient
from src.config import config


class LLMProvider(StrEnum):
    """Enum for LLM providers."""

    OPENAI = "openai"
    # GEMINI = "gemini"
    ANTHROPIC = "anthropic"


class OpenAIModel(StrEnum):
    GPT_5_5 = "openai.gpt-5.5"
    GPT_5_4 = "openai.gpt-5.4"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in OpenAIModel]


# class GeminiModel(StrEnum):
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
    CLAUDE_SONNET_4_6 = "global.anthropic.claude-sonnet-4-6"
    CLAUDE_HAIKU_4_5 = "global.anthropic.claude-haiku-4-5-20251001-v1:0"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in AnthropicModel]


bedrock_api_key = (
    config.bedrock_api_key.get_secret_value() if config.bedrock_api_key else provide_token(region=config.aws_region)
)

openai_client = AsyncOpenAIWrapperClient(
    api_key=bedrock_api_key,
    base_url=f"https://bedrock-mantle.{config.aws_region}.api.aws/openai/v1",
)
# google_genai_client = GenAIWrapperClient(api_key=config.google_api_key)
anthropic_client = AsyncAnthropicWrapperClient(aws_region=config.aws_region)
