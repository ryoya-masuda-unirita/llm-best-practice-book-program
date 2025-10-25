"""Execution layer for LLM service operations.

This module implements the execution layer that handles actual LLM API calls.
It's separated from storage concerns following the Bridge pattern.
"""

from typing import Optional

from google.genai.types import GenerateContentConfig

from src.client.llm_client import LLMProvider, google_genai_client, openai_client
from src.logger import make_logger
from src.model.model import CharacterResponse
from src.service.interface import ILLMService

logger = make_logger(__name__)


class ExecutionLLMService(ILLMService):
    """
    Execution layer implementation that performs actual LLM API calls.

    This class is responsible only for executing LLM requests and does not
    handle any caching or storage logic.
    """

    async def generate_character(
        self,
        prompt: list[dict],
        model: str,
        provider: str,
        cache_key: Optional[str] = None,
    ) -> CharacterResponse:
        """
        Generate character by calling LLM API directly.

        Args:
            prompt: The prompt messages for LLM
            model: The model identifier
            provider: The LLM provider (openai, gemini)
            cache_key: Not used in execution layer (for interface compatibility)

        Returns:
            CharacterResponse: The generated character

        Raises:
            ValueError: If provider is not supported
        """
        logger.info(f"Executing LLM request: provider={provider}, model={model}")

        if provider == LLMProvider.OPENAI:
            return await self._request_openai(model, prompt)
        elif provider == LLMProvider.GEMINI:
            return await self._request_gemini(model, prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    async def _request_openai(self, model: str, prompt: list[dict]) -> CharacterResponse:
        """Request OpenAI API for character generation."""
        logger.debug(f"Calling OpenAI API with model: {model}")
        result = await openai_client.beta.chat.completions.parse(
            model=model,
            messages=prompt,
            response_format=CharacterResponse,
            temperature=1.0,
        )
        logger.info(f"OpenAI API call successful: {model}")
        return result.choices[0].message.parsed

    async def _request_gemini(self, model: str, prompt: list[dict]) -> CharacterResponse:
        """Request Gemini API for character generation."""
        logger.debug(f"Calling Gemini API with model: {model}")
        result = await google_genai_client.aio.models.generate_content(
            model=model,
            contents=prompt[-1]["content"],
            config=GenerateContentConfig(
                system_instruction=prompt[0]["content"],
                response_mime_type="application/json",
                response_schema=CharacterResponse,
                temperature=2.0,
            ),
        )
        logger.info(f"Gemini API call successful: {model}")
        return result.parsed

    async def invalidate_cache(self, cache_key: str) -> bool:
        """
        No-op for execution layer as it doesn't handle caching.

        Args:
            cache_key: The cache key (not used)

        Returns:
            bool: Always False as execution layer has no cache
        """
        logger.debug(f"invalidate_cache called on ExecutionLLMService (no-op): {cache_key}")
        return False
