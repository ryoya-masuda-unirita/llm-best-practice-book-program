"""
LLM client configuration and model definitions.

This module provides OpenAI model definitions used by the learning platform.
"""

from enum import StrEnum

from aws_bedrock_token_generator import provide_token
from src.config import config


class OpenAIModel(StrEnum):
    """Available OpenAI models for the learning platform."""

    GPT_5_5 = "openai.gpt-5.5"
    GPT_5_4 = "openai.gpt-5.4"

    @staticmethod
    def list_str() -> list[str]:
        """Return list of all available model names."""
        return list(OpenAIModel)


bedrock_api_key = (
    config.bedrock_api_key.get_secret_value() if config.bedrock_api_key else provide_token(region=config.aws_region)
)

bedrock_openai_base_url = f"https://bedrock-mantle.{config.aws_region}.api.aws/openai/v1"
