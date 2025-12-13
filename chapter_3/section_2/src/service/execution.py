"""Execution layer for LLM service operations.

This module implements the execution layer that handles actual LLM API calls.
It's separated from storage concerns following the Bridge pattern.
"""

from src.client.llm_client import LLMProvider, openai_client
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
        cache_key: str | None = None,
    ) -> CharacterResponse:
        """Generate character by calling OpenAI API directly."""
        if provider != LLMProvider.OPENAI:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        logger.info(f"Executing LLM request: model={model}")
        result = await openai_client.responses.parse(
            model=model,
            input=prompt,
            text_format=CharacterResponse,
        )
        logger.info(f"OpenAI API call successful: {model}")
        return result.output_parsed

    async def invalidate_cache(self, cache_key: str) -> bool:
        """No-op for execution layer as it doesn't handle caching."""
        return False
