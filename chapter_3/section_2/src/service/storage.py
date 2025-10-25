"""Storage layer for LLM service operations.

This module implements the storage layer that handles caching of LLM responses.
It supports both in-memory and Redis-based caching strategies.
"""

import hashlib
from typing import Optional

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
        """
        Initialize cached service with execution service.

        Args:
            execution_service: The execution layer service for actual LLM calls
        """
        self._execution_service = execution_service
        self._cache_backend = config.cache_backend
        self._cache_enabled = config.cache_enabled

        # Initialize appropriate cache backend
        if self._cache_backend == CacheBackend.MEMORY:
            self._cache = InMemoryCache()
            logger.info("Using in-memory cache backend")
        else:
            self._cache = redis_client
            logger.info("Using Redis cache backend")

        # Metrics tracking
        self._cache_hits = 0
        self._cache_misses = 0

    def _generate_cache_key(
        self,
        prompt: list[dict],
        model: str,
        provider: str,
        custom_key: Optional[str] = None,
    ) -> str:
        """
        Generate a unique cache key based on request parameters.

        Args:
            prompt: The prompt messages
            model: The model identifier
            provider: The LLM provider
            custom_key: Optional custom cache key

        Returns:
            str: SHA256 hash of the parameters
        """
        if custom_key:
            return custom_key

        # Create a deterministic string from parameters
        key_data = f"{provider}:{model}:{str(prompt)}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    async def generate_character(
        self,
        prompt: list[dict],
        model: str,
        provider: str,
        cache_key: Optional[str] = None,
    ) -> CharacterResponse:
        """
        Generate character with caching support.

        This method first checks the cache. On cache miss, it delegates to
        the execution service and stores the result in cache.

        Args:
            prompt: The prompt messages for LLM
            model: The model identifier
            provider: The LLM provider (openai, gemini)
            cache_key: Optional custom cache key

        Returns:
            CharacterResponse: The generated character (from cache or execution)
        """
        key = self._generate_cache_key(prompt, model, provider, cache_key)

        # Try to get from cache if enabled
        if self._cache_enabled:
            cached_data = await self._cache.get(key)
            if cached_data:
                self._cache_hits += 1
                logger.info(
                    f"Cache hit for {provider}/{model} (hits: {self._cache_hits}, "
                    f"misses: {self._cache_misses}, "
                    f"hit_rate: {self.get_cache_hit_rate():.2%})"
                )
                return CharacterResponse(**cached_data)

            self._cache_misses += 1
            logger.info(
                f"Cache miss for {provider}/{model} (hits: {self._cache_hits}, "
                f"misses: {self._cache_misses}, "
                f"hit_rate: {self.get_cache_hit_rate():.2%})"
            )

        # Cache miss or caching disabled - execute LLM request
        character = await self._execution_service.generate_character(prompt, model, provider, cache_key)

        # Store in cache if enabled
        if self._cache_enabled:
            cached_successfully = await self._cache.set(key, character.model_dump())
            if cached_successfully:
                logger.debug(f"Cached response for key: {key}")

        return character

    async def invalidate_cache(self, cache_key: str) -> bool:
        """
        Invalidate specific cache entry.

        Args:
            cache_key: The cache key to invalidate

        Returns:
            bool: True if cache was invalidated, False otherwise
        """
        if not self._cache_enabled:
            logger.debug("Cache is disabled, invalidation skipped")
            return False

        result = await self._cache.delete(cache_key)
        if result:
            logger.info(f"Cache invalidated for key: {cache_key}")
        return result

    def get_cache_hit_rate(self) -> float:
        """
        Calculate cache hit rate.

        Returns:
            float: Cache hit rate as a decimal (0.0 to 1.0)
        """
        total_requests = self._cache_hits + self._cache_misses
        if total_requests == 0:
            return 0.0
        return self._cache_hits / total_requests

    def get_cache_metrics(self) -> dict:
        """
        Get cache performance metrics.

        Returns:
            dict: Cache metrics including hits, misses, and hit rate
        """
        return {
            "cache_enabled": self._cache_enabled,
            "cache_backend": self._cache_backend,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": self.get_cache_hit_rate(),
            "total_requests": self._cache_hits + self._cache_misses,
        }
