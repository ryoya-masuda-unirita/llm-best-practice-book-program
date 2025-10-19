"""Concrete adapter implementations for different LLM providers.

This module contains adapter classes that implement the LLMClient interface
for OpenAI, Anthropic, and Google Gemini APIs. Each adapter translates
the common interface to provider-specific API calls.
"""

from typing import Any

from google import genai
from google.genai.types import GenerateContentConfig
from openai import AsyncOpenAI
from pydantic import BaseModel

from src.client.base import LLMClient
from src.client.model import LLMProvider
from src.config import config
from src.logger import make_logger

logger = make_logger(__name__)


class OpenAIAdapter(LLMClient):
    """Adapter for OpenAI API.

    Translates the common LLMClient interface to OpenAI's chat completion API
    with structured output using response_format.
    """

    def __init__(self, model: str):
        """Initialize OpenAI adapter.

        Args:
            model: Model identifier (e.g., 'gpt-4o', 'gpt-4o-mini')
        """
        self._client = AsyncOpenAI(api_key=config.openai_api_key)
        self._model = model
        logger.info(f"Initialized OpenAI adapter with model: {model}")

    async def chat(
        self,
        messages: list[dict[str, str]],
        response_format: type,
        **kwargs: Any,
    ) -> BaseModel:
        """Generate chat completion using OpenAI API.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            response_format: Pydantic model for structured output
            temperature: Sampling temperature
            **kwargs: Additional OpenAI-specific parameters

        Returns:
            Parsed response matching response_format
        """
        logger.debug(f"OpenAI request: model={self._model}")

        result = await self._client.beta.chat.completions.parse(
            model=self._model,
            messages=messages,
            response_format=response_format,
            **kwargs,
        )

        return result.choices[0].message.parsed

    def get_provider_name(self) -> str:
        """Return provider name."""
        return LLMProvider.OPENAI

    def get_model_name(self) -> str:
        """Return model identifier."""
        return self._model


class GeminiAdapter(LLMClient):
    """Adapter for Google Gemini API.

    Translates the common LLMClient interface to Google's Gemini API
    with response schema-based structured output.
    """

    def __init__(self, model: str):
        """Initialize Gemini adapter.

        Args:
            model: Model identifier (e.g., 'gemini-2.5-pro', 'gemini-2.5-flash')
        """
        self._client = genai.Client(api_key=config.gemini_api_key)
        self._model = model
        logger.info(f"Initialized Gemini adapter with model: {model}")

    async def chat(
        self,
        messages: list[dict[str, str]],
        response_format: type,
        **kwargs: Any,
    ) -> BaseModel:
        """Generate chat completion using Gemini API.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            response_format: Pydantic model for structured output
            **kwargs: Additional Gemini-specific parameters

        Returns:
            Parsed response matching response_format
        """
        logger.debug(f"Gemini request: model={self._model}")

        # Separate system instruction from user messages
        system_instruction = None
        user_content = None

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                user_content = msg["content"]

        # Build config
        config = GenerateContentConfig(
            response_mime_type="application/json",
        )

        if system_instruction:
            config.system_instruction = system_instruction

        if response_format:
            config.response_schema = response_format

        result = await self._client.aio.models.generate_content(
            model=self._model,
            contents=user_content,
            config=config,
        )

        return result.parsed

    def get_provider_name(self) -> str:
        """Return provider name."""
        return LLMProvider.GEMINI

    def get_model_name(self) -> str:
        """Return model identifier."""
        return self._model
