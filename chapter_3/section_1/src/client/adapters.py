"""Adapter implementations for OpenAI, Anthropic, and Gemini APIs."""

from typing import Any

from anthropic import AsyncAnthropicBedrock
from aws_bedrock_token_generator import provide_token

# from google import genai
# from google.genai.types import GenerateContentConfig
from openai import AsyncOpenAI
from pydantic import BaseModel
from src.client.base import LLMClient
from src.client.model import LLMProvider
from src.config import config
from src.logger import make_logger

logger = make_logger(__name__)


class OpenAIAdapter(LLMClient):
    """OpenAI API adapter with structured output support."""

    def __init__(self, model: str):
        bedrock_api_key = (
            config.bedrock_api_key.get_secret_value()
            if config.bedrock_api_key
            else provide_token(region=config.aws_region)
        )
        self._client = AsyncOpenAI(
            api_key=bedrock_api_key,
            base_url=f"https://bedrock-mantle.{config.aws_region}.api.aws/openai/v1",
        )
        self._model = model
        logger.info(f"Initialized OpenAI adapter with model: {model}")

    async def chat(
        self,
        messages: list[dict[str, str]],
        response_format: type,
        **kwargs: Any,
    ) -> BaseModel:
        logger.debug(f"OpenAI request: model={self._model}")
        result = await self._client.responses.parse(
            model=self._model,
            input=messages,
            text_format=response_format,
            **kwargs,
        )
        return result.output_parsed

    def get_provider_name(self) -> str:
        return LLMProvider.OPENAI

    def get_model_name(self) -> str:
        return self._model

    async def aclose(self) -> None:
        await self._client.close()
        logger.debug("Closed OpenAI client")


# class GeminiAdapter(LLMClient):
#     """Google Gemini API adapter with response schema support."""
#
#     def __init__(self, model: str):
#         self._client = genai.Client(api_key=config.gemini_api_key)
#         self._model = model
#         logger.info(f"Initialized Gemini adapter with model: {model}")
#
#     async def chat(
#         self,
#         messages: list[dict[str, str]] | tuple[str, str],
#         response_format: type,
#         **kwargs: Any,
#     ) -> BaseModel:
#         logger.debug(f"Gemini request: model={self._model}")
#
#         if isinstance(messages, tuple):
#             system_instruction, user_content = messages
#         else:
#             system_instruction = None
#             user_content = None
#             for msg in messages:
#                 if msg["role"] == "system":
#                     system_instruction = msg["content"]
#                 elif msg["role"] == "user":
#                     user_content = msg["content"]
#
#         config = GenerateContentConfig(response_mime_type="application/json")
#         if system_instruction:
#             config.system_instruction = system_instruction
#         if response_format:
#             config.response_schema = response_format
#
#         result = await self._client.aio.models.generate_content(
#             model=self._model,
#             contents=user_content,
#             config=config,
#             **kwargs,
#         )
#         return result.parsed
#
#     def get_provider_name(self) -> str:
#         return LLMProvider.GEMINI
#
#     def get_model_name(self) -> str:
#         return self._model
#
#     async def aclose(self) -> None:
#         await self._client.aio.aclose()
#         logger.debug("Closed Gemini client")


class AnthropicAdapter(LLMClient):
    """Anthropic Claude API adapter (via Amazon Bedrock) with structured outputs."""

    def __init__(self, model: str):
        self._client = AsyncAnthropicBedrock(aws_region=config.aws_region)
        self._model = model
        logger.info(f"Initialized Anthropic adapter with model: {model}")

    async def chat(
        self,
        messages: list[dict[str, str]],
        response_format: type,
        **kwargs: Any,
    ) -> BaseModel:
        logger.debug(f"Anthropic request: model={self._model}")
        result = await self._client.messages.parse(
            model=self._model,
            max_tokens=kwargs.get("max_tokens", 1024),
            messages=messages,
            output_format=response_format,
            **{k: v for k, v in kwargs.items() if k != "max_tokens"},
        )
        return result.parsed_output

    def get_provider_name(self) -> str:
        return LLMProvider.ANTHROPIC

    def get_model_name(self) -> str:
        return self._model

    async def aclose(self) -> None:
        await self._client.close()
        logger.debug("Closed Anthropic client")
