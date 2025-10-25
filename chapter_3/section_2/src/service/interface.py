"""Interface layer for LLM service operations.

This module defines the abstract interface (Bridge pattern) that separates
storage and execution concerns in the LLM system architecture.
"""

from abc import ABC, abstractmethod
from typing import Optional

from src.model.model import CharacterResponse


class ILLMService(ABC):
    """
    Abstract interface for LLM service operations.

    This interface follows the Bridge pattern to decouple the abstraction
    from its implementation, allowing both to vary independently.
    """

    @abstractmethod
    async def generate_character(
        self,
        prompt: list[dict],
        model: str,
        provider: str,
        cache_key: Optional[str] = None,
    ) -> CharacterResponse:
        """
        Generate character using LLM.

        Args:
            prompt: The prompt messages for LLM
            model: The model identifier
            provider: The LLM provider (openai, gemini)
            cache_key: Optional cache key for storage implementations

        Returns:
            CharacterResponse: The generated character
        """
        pass

    @abstractmethod
    async def invalidate_cache(self, cache_key: str) -> bool:
        """
        Invalidate cached data for a specific key.

        Args:
            cache_key: The cache key to invalidate

        Returns:
            bool: True if cache was invalidated, False otherwise
        """
        pass
