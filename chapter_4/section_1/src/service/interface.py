"""Interface layer for LLM service operations.

This module defines the abstract interface (Bridge pattern) that separates
storage and execution concerns in the LLM system architecture.
"""

from abc import ABC, abstractmethod

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
        cache_key: str | None = None,
    ) -> CharacterResponse:
        """Generate character using LLM."""
        pass

    @abstractmethod
    async def invalidate_cache(self, cache_key: str) -> bool:
        """Invalidate cached data for a specific key."""
        pass
