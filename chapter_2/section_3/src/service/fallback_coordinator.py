"""Fallback coordinator for managing LLM request fallback strategies."""

import asyncio
from dataclasses import dataclass
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


@dataclass
class RequestContext:
    """Context for LLM request execution."""

    prompt: Optional[list]
    model: Optional[str]


@dataclass
class FallbackResult:
    """Result of a fallback request."""

    response: CharacterResponse
    strategy: FallbackStrategy
    error_reason: Optional[str]


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
        self.fallback_strategy = fallback_strategy
        self.cache_manager = cache_manager or CacheManager()
        self.semantic_cache_manager = semantic_cache_manager
        self.timeout = timeout or config.llm_request_timeout
        self.stats = self._init_stats()

    def _init_stats(self) -> dict:
        """Initialize statistics dictionary."""
        return {
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
    ) -> tuple[CharacterResponse, FallbackStrategy, Optional[str]]:
        """Execute LLM request with comprehensive fallback handling."""
        self.stats["total_requests"] += 1
        context = RequestContext(prompt=prompt, model=model)

        result = await self._try_primary_request(primary_provider, primary_request_func, context)
        if result:
            return result.response, result.strategy, result.error_reason

        error_reason = "timeout" if self.stats["timeout_count"] > 0 else "error"
        result = await self._execute_fallback_strategy(alternative_request_func, context, error_reason)
        if result:
            return result.response, result.strategy, result.error_reason

        self._handle_fallback_failure(error_reason)

    async def _try_primary_request(
        self, provider: LLMProvider, request_func: Callable, context: RequestContext
    ) -> Optional[FallbackResult]:
        """Try primary request with timeout."""
        try:
            logger.info(f"Attempting primary request with {provider} (timeout: {self.timeout}s)")
            response = await asyncio.wait_for(request_func(), timeout=self.timeout)
            self.stats["primary_success"] += 1
            logger.info(f"Primary request succeeded with {provider}")

            await self._cache_response(response, context)
            return FallbackResult(response=response, strategy=FallbackStrategy.PRIMARY, error_reason=None)

        except asyncio.TimeoutError:
            self.stats["timeout_count"] += 1
            logger.warning(
                f"Primary request timed out after {self.timeout}s. Initiating fallback strategy: {self.fallback_strategy}"
            )
            return None

        except Exception as e:
            self.stats["error_count"] += 1
            logger.error(
                f"Primary request failed with error: {e}. Initiating fallback strategy: {self.fallback_strategy}"
            )
            return None

    async def _execute_fallback_strategy(
        self, alternative_func: Optional[Callable], context: RequestContext, error_reason: str
    ) -> Optional[FallbackResult]:
        """Execute the configured fallback strategy."""
        strategy_handlers = {
            FallbackStrategy.PARAMETER_CACHE: self._try_parameter_cache,
            FallbackStrategy.SEMANTIC_CACHE: self._try_semantic_cache,
            FallbackStrategy.ALTERNATIVE_PROVIDER: lambda ctx, err: self._try_alternative_provider(
                alternative_func, ctx, err
            ),
        }

        handler = strategy_handlers.get(self.fallback_strategy)
        if handler:
            return await handler(context, error_reason)
        return None

    async def _try_parameter_cache(self, context: RequestContext, error_reason: str) -> Optional[FallbackResult]:
        """Try parameter-based cache lookup."""
        if not (context.prompt and context.model):
            return None

        try:
            cached_response = self.cache_manager.get(context.prompt, context.model)
            if cached_response:
                self.stats["parameter_cache_hits"] += 1
                logger.info("Fallback: Using parameter cache response (exact match)")
                return FallbackResult(
                    response=cached_response, strategy=FallbackStrategy.PARAMETER_CACHE, error_reason=error_reason
                )
            logger.info("Fallback: No exact parameter match in cache")
        except Exception as e:
            logger.warning(f"Parameter cache lookup failed: {e}")

        return None

    async def _try_semantic_cache(self, context: RequestContext, error_reason: str) -> Optional[FallbackResult]:
        """Try semantic cache lookup."""
        if not self.semantic_cache_manager:
            logger.warning("Semantic cache not configured")
            return None

        if not (context.prompt and context.model):
            return None

        try:
            cached_response = await self.semantic_cache_manager.get(context.prompt, context.model)
            if cached_response:
                self.stats["semantic_cache_hits"] += 1
                logger.info("Fallback: Using semantic cache response (similar prompt)")
                return FallbackResult(
                    response=cached_response, strategy=FallbackStrategy.SEMANTIC_CACHE, error_reason=error_reason
                )
            logger.info("Fallback: No similar prompt found in semantic cache")
        except Exception as e:
            logger.warning(f"Semantic cache lookup failed: {e}")

        return None

    async def _try_alternative_provider(
        self, alternative_func: Optional[Callable], context: RequestContext, error_reason: str
    ) -> Optional[FallbackResult]:
        """Try alternative LLM provider."""
        if not alternative_func:
            logger.warning("No alternative provider configured")
            return None

        try:
            logger.info(f"Fallback: Attempting alternative provider (timeout: {self.timeout}s)")
            response = await asyncio.wait_for(alternative_func(), timeout=self.timeout)
            self.stats["alternative_provider_success"] += 1
            logger.info("Fallback: Alternative provider succeeded")

            await self._cache_response(response, context)
            return FallbackResult(
                response=response, strategy=FallbackStrategy.ALTERNATIVE_PROVIDER, error_reason=error_reason
            )

        except asyncio.TimeoutError:
            self.stats["timeout_count"] += 1
            logger.warning(f"Alternative provider timed out after {self.timeout}s")
        except Exception as e:
            self.stats["error_count"] += 1
            logger.error(f"Alternative provider failed with error: {e}")

        return None

    async def _cache_response(self, response: CharacterResponse, context: RequestContext) -> None:
        """Cache a successful response."""
        if not (context.prompt and context.model):
            return

        try:
            self.cache_manager.set(context.prompt, context.model, response)
            if self.semantic_cache_manager:
                await self.semantic_cache_manager.set(context.prompt, context.model, response)
        except Exception as e:
            logger.warning(f"Failed to cache response: {e}")

    def _handle_fallback_failure(self, error_reason: str) -> None:
        """Handle complete fallback failure."""
        self.stats["fallback_failures"] += 1
        logger.error("Fallback: All strategies exhausted. Request failed.")
        raise RuntimeError(
            f"All fallback strategies failed. Primary error: {error_reason}. "
            f"Fallback strategy '{self.fallback_strategy}' also failed."
        )

    def get_stats(self) -> dict:
        """Get statistics about fallback usage with calculated rates."""
        stats = self.stats.copy()
        total = stats["total_requests"]

        if total > 0:
            stats.update(self._calculate_rates(stats, total))
        else:
            stats.update(self._zero_rates())

        return stats

    def _calculate_rates(self, stats: dict, total: int) -> dict:
        """Calculate success rates from raw statistics."""
        cache_hits = stats["parameter_cache_hits"] + stats["semantic_cache_hits"]
        fallback_successes = cache_hits + stats["alternative_provider_success"]

        return {
            "primary_success_rate": stats["primary_success"] / total * 100,
            "parameter_cache_hit_rate": stats["parameter_cache_hits"] / total * 100,
            "semantic_cache_hit_rate": stats["semantic_cache_hits"] / total * 100,
            "total_cache_hit_rate": cache_hits / total * 100,
            "fallback_rate": fallback_successes / total * 100,
            "failure_rate": stats["fallback_failures"] / total * 100,
        }

    def _zero_rates(self) -> dict:
        """Return zero values for all rate statistics."""
        return {
            "primary_success_rate": 0.0,
            "parameter_cache_hit_rate": 0.0,
            "semantic_cache_hit_rate": 0.0,
            "total_cache_hit_rate": 0.0,
            "fallback_rate": 0.0,
            "failure_rate": 0.0,
        }

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
        self.stats = self._init_stats()
        logger.info("Fallback statistics reset")
