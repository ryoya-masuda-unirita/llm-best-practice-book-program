"""Fallback coordinator for managing LLM request fallback strategies."""

import asyncio
from enum import StrEnum
from typing import Callable, Optional

from src.client.llm_client import LLMProvider
from src.config import config
from src.logger import make_logger
from src.model.model import CharacterResponse
from src.service.cache_manager import CacheManager, SemanticCacheManager

logger = make_logger(__name__)


class FallbackStrategy(StrEnum):
    """Enum for fallback strategies."""

    PRIMARY = "primary"
    PARAMETER_CACHE = "parameter_cache"
    SEMANTIC_CACHE = "semantic_cache"
    ALTERNATIVE_PROVIDER = "alternative_provider"


class FallbackCoordinator:
    """
    Coordinates fallback strategies when LLM requests fail or timeout.

    Implements a multi-tier fallback approach:
    1. Try primary LLM provider with timeout
    2. Use configured fallback strategy (parameter cache, semantic cache, or alternative provider)
    3. Raise exception if all strategies fail
    """

    def __init__(
        self,
        fallback_strategy: FallbackStrategy = FallbackStrategy.ALTERNATIVE_PROVIDER,
        cache_manager: Optional[CacheManager] = None,
        semantic_cache_manager: Optional[SemanticCacheManager] = None,
        timeout: Optional[float] = None,
    ):
        """
        Initialize the fallback coordinator.

        Args:
            fallback_strategy: Strategy to use for fallback
            cache_manager: CacheManager instance for parameter cache (creates new if None)
            semantic_cache_manager: SemanticCacheManager instance for semantic cache (optional)
            timeout: Request timeout in seconds (uses config default if None)
        """
        self.fallback_strategy = fallback_strategy
        self.cache_manager = cache_manager if cache_manager is not None else CacheManager()
        self.semantic_cache_manager = semantic_cache_manager
        self.timeout = timeout if timeout is not None else config.llm_request_timeout

        # Statistics for monitoring
        self.stats = {
            "total_requests": 0,
            "primary_success": 0,
            "parameter_cache_hits": 0,
            "semantic_cache_hits": 0,
            "alternative_provider_success": 0,
            "timeout_count": 0,
            "error_count": 0,
            "fallback_failures": 0,
        }

    async def request_with_fallback(
        self,
        primary_provider: LLMProvider,
        primary_request_func: Callable,
        alternative_request_func: Optional[Callable] = None,
        prompt: Optional[list] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> tuple[CharacterResponse, FallbackStrategy, Optional[str]]:
        """
        Execute LLM request with comprehensive fallback handling.

        Args:
            primary_provider: Primary LLM provider to use
            primary_request_func: Async function for primary request
            alternative_request_func: Optional async function for alternative provider
            prompt: The prompt (for cache lookup)
            model: Model name (for cache lookup)
            temperature: Temperature parameter (for cache lookup)

        Returns:
            Tuple of (response, strategy_used, error_reason)
            - response: CharacterResponse object
            - strategy_used: Which fallback strategy was used
            - error_reason: Optional error reason if fallback was triggered
        """
        self.stats["total_requests"] += 1
        error_reason = None

        # Step 1: Try primary provider with timeout
        try:
            logger.info(f"Attempting primary request with {primary_provider} (timeout: {self.timeout}s)")
            response = await asyncio.wait_for(primary_request_func(), timeout=self.timeout)
            self.stats["primary_success"] += 1
            logger.info(f"Primary request succeeded with {primary_provider}")

            # Cache the successful response in both caches
            if prompt and model and temperature:
                try:
                    if self.cache_manager:
                        self.cache_manager.set(prompt, model, temperature, response)
                    if self.semantic_cache_manager:
                        await self.semantic_cache_manager.set(prompt, model, temperature, response)
                except Exception as e:
                    logger.warning(f"Failed to cache response: {e}")

            return response, FallbackStrategy.PRIMARY, None

        except asyncio.TimeoutError:
            self.stats["timeout_count"] += 1
            error_reason = "timeout"
            logger.warning(
                f"Primary request timed out after {self.timeout}s. Initiating fallback strategy: {self.fallback_strategy}"
            )

        except Exception as e:
            self.stats["error_count"] += 1
            error_reason = "error"
            logger.error(
                f"Primary request failed with error: {e}. Initiating fallback strategy: {self.fallback_strategy}"
            )

        # Step 2: Execute configured fallback strategy
        if self.fallback_strategy == FallbackStrategy.PARAMETER_CACHE:
            # Try parameter-based cache
            if prompt and model and temperature:
                try:
                    cached_response = self.cache_manager.get(prompt, model, temperature)
                    if cached_response:
                        self.stats["parameter_cache_hits"] += 1
                        logger.info("Fallback: Using parameter cache response (exact match)")
                        return cached_response, FallbackStrategy.PARAMETER_CACHE, error_reason
                    else:
                        logger.info("Fallback: No exact parameter match in cache")
                except Exception as e:
                    logger.warning(f"Parameter cache lookup failed: {e}")

        elif self.fallback_strategy == FallbackStrategy.SEMANTIC_CACHE:
            # Try semantic cache with embeddings
            if self.semantic_cache_manager and prompt and model and temperature:
                try:
                    cached_response = await self.semantic_cache_manager.get(prompt, model, temperature)
                    if cached_response:
                        self.stats["semantic_cache_hits"] += 1
                        logger.info("Fallback: Using semantic cache response (similar prompt)")
                        return cached_response, FallbackStrategy.SEMANTIC_CACHE, error_reason
                    else:
                        logger.info("Fallback: No similar prompt found in semantic cache")
                except Exception as e:
                    logger.warning(f"Semantic cache lookup failed: {e}")
            else:
                logger.warning("Semantic cache not configured")

        elif self.fallback_strategy == FallbackStrategy.ALTERNATIVE_PROVIDER:
            # Try alternative provider
            if alternative_request_func:
                try:
                    logger.info(f"Fallback: Attempting alternative provider (timeout: {self.timeout}s)")
                    response = await asyncio.wait_for(alternative_request_func(), timeout=self.timeout)
                    self.stats["alternative_provider_success"] += 1
                    logger.info("Fallback: Alternative provider succeeded")

                    # Cache the successful response from alternative provider
                    if prompt and model and temperature:
                        try:
                            self.cache_manager.set(prompt, model, temperature, response)
                            if self.semantic_cache_manager:
                                await self.semantic_cache_manager.set(prompt, model, temperature, response)
                        except Exception as e:
                            logger.warning(f"Failed to cache alternative response: {e}")

                    return response, FallbackStrategy.ALTERNATIVE_PROVIDER, error_reason

                except asyncio.TimeoutError:
                    self.stats["timeout_count"] += 1
                    logger.warning(f"Alternative provider timed out after {self.timeout}s")
                except Exception as e:
                    self.stats["error_count"] += 1
                    logger.error(f"Alternative provider failed with error: {e}")
            else:
                logger.warning("No alternative provider configured")

        # Step 3: All strategies failed - raise exception
        self.stats["fallback_failures"] += 1
        logger.error("Fallback: All strategies exhausted. Request failed.")
        raise RuntimeError(
            f"All fallback strategies failed. Primary error: {error_reason}. "
            f"Fallback strategy '{self.fallback_strategy}' also failed."
        )

    def get_stats(self) -> dict:
        """
        Get statistics about fallback usage.

        Returns:
            Dictionary with fallback statistics
        """
        stats = self.stats.copy()

        # Calculate success rates
        if stats["total_requests"] > 0:
            stats["primary_success_rate"] = stats["primary_success"] / stats["total_requests"] * 100
            stats["parameter_cache_hit_rate"] = stats["parameter_cache_hits"] / stats["total_requests"] * 100
            stats["semantic_cache_hit_rate"] = stats["semantic_cache_hits"] / stats["total_requests"] * 100
            stats["total_cache_hit_rate"] = (
                (stats["parameter_cache_hits"] + stats["semantic_cache_hits"]) / stats["total_requests"] * 100
            )
            stats["fallback_rate"] = (
                (stats["parameter_cache_hits"] + stats["semantic_cache_hits"] + stats["alternative_provider_success"])
                / stats["total_requests"]
                * 100
            )
            stats["failure_rate"] = stats["fallback_failures"] / stats["total_requests"] * 100
        else:
            stats["primary_success_rate"] = 0.0
            stats["parameter_cache_hit_rate"] = 0.0
            stats["semantic_cache_hit_rate"] = 0.0
            stats["total_cache_hit_rate"] = 0.0
            stats["fallback_rate"] = 0.0
            stats["failure_rate"] = 0.0

        return stats

    def log_stats(self):
        """Log current fallback statistics."""
        stats = self.get_stats()
        logger.info("=== Fallback Statistics ===")
        logger.info(f"Total Requests: {stats['total_requests']}")
        logger.info(f"Primary Success: {stats['primary_success']} ({stats['primary_success_rate']:.1f}%)")
        logger.info(f"Parameter Cache Hits: {stats['parameter_cache_hits']} ({stats['parameter_cache_hit_rate']:.1f}%)")
        logger.info(f"Semantic Cache Hits: {stats['semantic_cache_hits']} ({stats['semantic_cache_hit_rate']:.1f}%)")
        logger.info(f"Total Cache Hit Rate: {stats['total_cache_hit_rate']:.1f}%")
        logger.info(f"Alternative Provider: {stats['alternative_provider_success']}")
        logger.info(f"Fallback Failures: {stats['fallback_failures']} ({stats['failure_rate']:.1f}%)")
        logger.info(f"Timeouts: {stats['timeout_count']}")
        logger.info(f"Errors: {stats['error_count']}")
        logger.info(f"Fallback Rate: {stats['fallback_rate']:.1f}%")
        logger.info("===========================")

    def reset_stats(self):
        """Reset statistics counters."""
        for key in self.stats:
            self.stats[key] = 0
        logger.info("Fallback statistics reset")
