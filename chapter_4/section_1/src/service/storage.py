"""Storage layer for LLM service operations.

This module implements the storage layer that handles caching of LLM responses.
It supports both in-memory and Redis-based caching strategies.
"""

import hashlib

from src.client.cache_client import InMemoryCache, redis_client
from src.config import CacheBackend, config
from src.logger import make_logger
from src.model.model import CharacterResponse
from src.service.interface import ILLMService

logger = make_logger(__name__)


class CachedLLMService(ILLMService):
    """
    Storage layer implementation with caching support.

    This class implements the Bridge pattern, delegating actual LLM execution
    to the execution layer while handling caching concerns independently.
    """

    def __init__(self, execution_service: ILLMService):
        self._execution_service = execution_service
        self._cache_backend = config.cache_backend
        self._cache_enabled = config.cache_enabled
        self._cache_hits = 0
        self._cache_misses = 0

        if self._cache_backend == CacheBackend.MEMORY:
            self._cache = InMemoryCache()
            logger.info("Using in-memory cache backend")
        else:
            self._cache = redis_client
            logger.info("Using Redis cache backend")

    def _generate_cache_key(
        self,
        prompt: list[dict],
        model: str,
        provider: str,
        custom_key: str | None = None,
    ) -> str:
        """Generate a unique cache key based on request parameters."""
        if custom_key:
            return custom_key
        key_data = f"{provider}:{model}:{str(prompt)}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def _log_cache_stats(self, event: str, provider: str, model: str) -> None:
        """Log cache statistics."""
        logger.info(
            f"Cache {event} for {provider}/{model} "
            f"(hits: {self._cache_hits}, misses: {self._cache_misses}, "
            f"hit_rate: {self.get_cache_hit_rate():.2%})"
        )

    async def generate_character(
        self,
        prompt: list[dict],
        model: str,
        provider: str,
        cache_key: str | None = None,
    ) -> CharacterResponse:
        """Generate character with caching support."""
        key = self._generate_cache_key(prompt, model, provider, cache_key)

        if self._cache_enabled:
            cached_data = await self._cache.get(key)
            if cached_data:
                self._cache_hits += 1
                self._log_cache_stats("hit", provider, model)
                return CharacterResponse(**cached_data)

            self._cache_misses += 1
            self._log_cache_stats("miss", provider, model)

        character = await self._execution_service.generate_character(prompt, model, provider, cache_key)

        if self._cache_enabled:
            await self._cache.set(key, character.model_dump())

        return character

    async def invalidate_cache(self, cache_key: str) -> bool:
        """Invalidate specific cache entry."""
        if not self._cache_enabled:
            return False

        result = await self._cache.delete(cache_key)
        if result:
            logger.info(f"Cache invalidated for key: {cache_key}")
        return result

    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self._cache_hits + self._cache_misses
        return self._cache_hits / total if total > 0 else 0.0

    def get_cache_metrics(self) -> dict:
        """Get cache performance metrics."""
        return {
            "cache_enabled": self._cache_enabled,
            "cache_backend": self._cache_backend,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": self.get_cache_hit_rate(),
            "total_requests": self._cache_hits + self._cache_misses,
        }
