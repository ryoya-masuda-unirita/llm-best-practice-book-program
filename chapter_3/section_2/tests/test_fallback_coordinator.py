"""Tests for fallback_coordinator module."""

import asyncio

import pytest
from src.client.llm_client import LLMProvider
from src.service.fallback_coordinator import (
    FallbackCoordinator,
    FallbackStrategy,
)


@pytest.mark.asyncio
class TestFallbackCoordinator:
    """Test suite for FallbackCoordinator class."""

    async def test_init_default_values(self, temp_cache_dir):
        """Test FallbackCoordinator initialization with default values."""
        coordinator = FallbackCoordinator()

        assert coordinator.cache_manager is not None
        assert coordinator.timeout == 10.0  # Default from config
        assert coordinator.stats["total_requests"] == 0

    async def test_init_with_custom_timeout(self, temp_cache_dir):
        """Test initialization with custom timeout."""
        coordinator = FallbackCoordinator(timeout=5.0)

        assert coordinator.timeout == 5.0

    async def test_init_stats_structure(self):
        """Test that stats dictionary has correct structure."""
        coordinator = FallbackCoordinator()

        assert "total_requests" in coordinator.stats
        assert "primary_success" in coordinator.stats
        assert "parameter_cache_hits" in coordinator.stats
        assert "semantic_cache_hits" in coordinator.stats
        assert "alternative_provider_success" in coordinator.stats
        assert "fallback_failures" in coordinator.stats
        assert "timeout_count" in coordinator.stats
        assert "error_count" in coordinator.stats

    async def test_primary_request_success(self, temp_cache_dir, sample_character_response, sample_prompt):
        """Test successful primary request without fallback."""
        from src.service.cache_manager import CacheManager

        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        coordinator = FallbackCoordinator(cache_manager=cache_manager, timeout=10.0)

        async def mock_primary_request():
            return sample_character_response

        response, strategy, error_reason = await coordinator.request_with_fallback(
            primary_provider=LLMProvider.OPENAI,
            primary_request_func=mock_primary_request,
            prompt=sample_prompt,
            model="gpt-5.4",
        )

        assert response == sample_character_response
        assert strategy == FallbackStrategy.PRIMARY
        assert error_reason is None
        assert coordinator.stats["total_requests"] == 1
        assert coordinator.stats["primary_success"] == 1
        assert coordinator.stats["timeout_count"] == 0
        assert coordinator.stats["error_count"] == 0

    async def test_primary_request_timeout_with_cache_hit(
        self, temp_cache_dir, sample_character_response, sample_prompt
    ):
        """Test primary request timeout falling back to parameter cache."""
        from src.service.cache_manager import CacheManager

        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        # Pre-populate cache
        cache_manager.set(sample_prompt, "gpt-5.4", sample_character_response)

        coordinator = FallbackCoordinator(
            fallback_strategy=FallbackStrategy.PARAMETER_CACHE, cache_manager=cache_manager, timeout=0.1
        )

        async def slow_primary_request():
            await asyncio.sleep(1.0)  # Longer than timeout
            return sample_character_response

        response, strategy, error_reason = await coordinator.request_with_fallback(
            primary_provider=LLMProvider.OPENAI,
            primary_request_func=slow_primary_request,
            prompt=sample_prompt,
            model="gpt-5.4",
        )

        assert response.first_name == sample_character_response.first_name
        assert strategy == FallbackStrategy.PARAMETER_CACHE
        assert error_reason == "timeout"
        assert coordinator.stats["timeout_count"] == 1
        assert coordinator.stats["parameter_cache_hits"] == 1

    async def test_primary_request_timeout_with_alternative_provider(
        self, temp_cache_dir, sample_character_response, sample_prompt
    ):
        """Test primary request timeout falling back to alternative provider."""
        from src.service.cache_manager import CacheManager

        # Use isolated cache to avoid cache hits from other tests
        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        coordinator = FallbackCoordinator(
            fallback_strategy=FallbackStrategy.ALTERNATIVE_PROVIDER, cache_manager=cache_manager, timeout=0.1
        )

        async def slow_primary_request():
            await asyncio.sleep(1.0)
            return sample_character_response

        async def fast_alternative_request():
            return sample_character_response

        response, strategy, error_reason = await coordinator.request_with_fallback(
            primary_provider=LLMProvider.OPENAI,
            primary_request_func=slow_primary_request,
            alternative_request_func=fast_alternative_request,
            prompt=sample_prompt,
            model="gpt-5.4-unique",  # Use unique model name to avoid cache
        )

        assert response == sample_character_response
        assert strategy == FallbackStrategy.ALTERNATIVE_PROVIDER
        assert error_reason == "timeout"
        assert coordinator.stats["timeout_count"] == 1
        assert coordinator.stats["alternative_provider_success"] == 1

    async def test_all_strategies_fail_raises_exception(self, temp_cache_dir, sample_prompt):
        """Test that exception is raised when all strategies fail."""
        from src.service.cache_manager import CacheManager

        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        coordinator = FallbackCoordinator(
            fallback_strategy=FallbackStrategy.ALTERNATIVE_PROVIDER, cache_manager=cache_manager, timeout=0.1
        )

        async def failing_request():
            await asyncio.sleep(1.0)  # Timeout
            raise Exception("Should not reach here")

        with pytest.raises(RuntimeError, match="All fallback strategies failed"):
            await coordinator.request_with_fallback(
                primary_provider=LLMProvider.OPENAI,
                primary_request_func=failing_request,
                alternative_request_func=failing_request,
                prompt=sample_prompt,
                model="unique-model-template",  # Unique model to avoid cache
            )

        assert coordinator.stats["fallback_failures"] == 1
        assert coordinator.stats["timeout_count"] >= 1

    async def test_primary_request_error_with_alternative(
        self, temp_cache_dir, sample_character_response, sample_prompt
    ):
        """Test primary request error falling back to alternative provider."""
        from src.service.cache_manager import CacheManager

        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        coordinator = FallbackCoordinator(
            fallback_strategy=FallbackStrategy.ALTERNATIVE_PROVIDER, cache_manager=cache_manager
        )

        async def failing_primary_request():
            raise ValueError("Primary request failed")

        async def successful_alternative_request():
            return sample_character_response

        response, strategy, error_reason = await coordinator.request_with_fallback(
            primary_provider=LLMProvider.OPENAI,
            primary_request_func=failing_primary_request,
            alternative_request_func=successful_alternative_request,
            prompt=sample_prompt,
            model="error-test-model",  # Unique model to avoid cache
        )

        assert response == sample_character_response
        assert strategy == FallbackStrategy.ALTERNATIVE_PROVIDER
        assert error_reason == "error"
        assert coordinator.stats["error_count"] == 1
        assert coordinator.stats["alternative_provider_success"] == 1

    @pytest.mark.parametrize(
        "timeout,request_duration,should_timeout",
        [
            (1.0, 0.5, False),  # Fast request
            (2.0, 1.5, False),  # Request just under timeout
        ],
    )
    async def test_timeout_behavior(
        self, temp_cache_dir, sample_character_response, sample_prompt, timeout, request_duration, should_timeout
    ):
        """Test timeout behavior with different durations."""
        from src.service.cache_manager import CacheManager

        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        coordinator = FallbackCoordinator(cache_manager=cache_manager, timeout=timeout)

        async def timed_request():
            await asyncio.sleep(request_duration)
            return sample_character_response

        # Use unique model/temp per test to avoid cache
        response, strategy, error_reason = await coordinator.request_with_fallback(
            primary_provider=LLMProvider.OPENAI,
            primary_request_func=timed_request,
            prompt=sample_prompt,
            model=f"test-model-{timeout}-{request_duration}",
        )

        assert coordinator.stats["primary_success"] == 1
        assert error_reason is None

    async def test_timeout_raises_exception_when_no_fallback(
        self, temp_cache_dir, sample_character_response, sample_prompt
    ):
        """Test that timeout raises exception when fallback fails."""
        from src.service.cache_manager import CacheManager

        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        coordinator = FallbackCoordinator(
            fallback_strategy=FallbackStrategy.PARAMETER_CACHE, cache_manager=cache_manager, timeout=0.5
        )

        async def slow_request():
            await asyncio.sleep(1.0)
            return sample_character_response

        # Use unique model/temp to avoid cache hit
        with pytest.raises(RuntimeError, match="All fallback strategies failed"):
            await coordinator.request_with_fallback(
                primary_provider=LLMProvider.OPENAI,
                primary_request_func=slow_request,
                prompt=sample_prompt,
                model="timeout-test-unique",
            )

        assert coordinator.stats["timeout_count"] == 1
        assert coordinator.stats["fallback_failures"] == 1

    async def test_cache_is_populated_on_success(self, temp_cache_dir, sample_character_response, sample_prompt):
        """Test that successful responses are cached."""
        from src.service.cache_manager import CacheManager

        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        coordinator = FallbackCoordinator(cache_manager=cache_manager)

        async def successful_request():
            return sample_character_response

        await coordinator.request_with_fallback(
            primary_provider=LLMProvider.OPENAI,
            primary_request_func=successful_request,
            prompt=sample_prompt,
            model="gpt-5.4",
        )

        # Verify cache was populated
        cached = cache_manager.get(sample_prompt, "gpt-5.4")
        assert cached is not None
        assert cached.first_name == sample_character_response.first_name

    async def test_alternative_response_is_cached(self, temp_cache_dir, sample_character_response, sample_prompt):
        """Test that alternative provider responses are cached."""
        from src.service.cache_manager import CacheManager

        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        coordinator = FallbackCoordinator(cache_manager=cache_manager, timeout=0.1)

        async def failing_primary():
            await asyncio.sleep(1.0)

        async def successful_alternative():
            return sample_character_response

        await coordinator.request_with_fallback(
            primary_provider=LLMProvider.OPENAI,
            primary_request_func=failing_primary,
            alternative_request_func=successful_alternative,
            prompt=sample_prompt,
            model="alt-cache-test",
        )

        # Verify cache was populated
        cached = cache_manager.get(sample_prompt, "alt-cache-test")
        assert cached is not None

    async def test_get_stats(self, temp_cache_dir, sample_character_response, sample_prompt):
        """Test get_stats returns correct statistics."""
        from src.service.cache_manager import CacheManager

        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        coordinator = FallbackCoordinator(cache_manager=cache_manager, timeout=0.1)

        # Make some requests
        async def success():
            return sample_character_response

        # Successful request
        await coordinator.request_with_fallback(LLMProvider.OPENAI, success, prompt=sample_prompt, model="stats-test-1")

        stats = coordinator.get_stats()

        assert stats["total_requests"] == 1
        assert stats["primary_success"] == 1
        assert stats["primary_success_rate"] == 100.0
        assert stats["fallback_failures"] == 0
        assert stats["failure_rate"] == 0.0

    async def test_get_stats_zero_requests(self):
        """Test get_stats with zero requests."""
        coordinator = FallbackCoordinator()

        stats = coordinator.get_stats()

        assert stats["total_requests"] == 0
        assert stats["primary_success_rate"] == 0.0
        assert stats["parameter_cache_hit_rate"] == 0.0
        assert stats["semantic_cache_hit_rate"] == 0.0
        assert stats["total_cache_hit_rate"] == 0.0
        assert stats["fallback_rate"] == 0.0
        assert stats["failure_rate"] == 0.0

    async def test_reset_stats(self, temp_cache_dir, sample_character_response, sample_prompt):
        """Test resetting statistics."""
        from src.service.cache_manager import CacheManager

        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        coordinator = FallbackCoordinator(cache_manager=cache_manager)

        async def success():
            return sample_character_response

        # Make a request
        await coordinator.request_with_fallback(LLMProvider.OPENAI, success, prompt=sample_prompt, model="reset-test")

        assert coordinator.stats["total_requests"] == 1

        # Reset stats
        coordinator.reset_stats()

        assert coordinator.stats["total_requests"] == 0
        assert coordinator.stats["primary_success"] == 0

    async def test_log_stats(self, mocker, temp_cache_dir, sample_character_response, sample_prompt):
        """Test that log_stats logs correctly."""
        from src.service.cache_manager import CacheManager

        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        coordinator = FallbackCoordinator(cache_manager=cache_manager)
        mock_logger = mocker.patch("src.service.fallback_coordinator.logger")

        async def success():
            return sample_character_response

        await coordinator.request_with_fallback(LLMProvider.OPENAI, success, prompt=sample_prompt, model="log-test")

        coordinator.log_stats()

        # Verify logger was called multiple times
        assert mock_logger.info.call_count > 5

    async def test_without_prompt_model_temperature(self, temp_cache_dir, sample_character_response):
        """Test request without cache parameters."""
        from src.service.cache_manager import CacheManager

        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        coordinator = FallbackCoordinator(cache_manager=cache_manager)

        async def success():
            return sample_character_response

        response, strategy, error_reason = await coordinator.request_with_fallback(
            primary_provider=LLMProvider.OPENAI, primary_request_func=success
        )

        assert response == sample_character_response
        assert strategy == FallbackStrategy.PRIMARY
        assert error_reason is None

    async def test_cache_lookup_failure_raises_exception(
        self, temp_cache_dir, sample_character_response, sample_prompt, mocker
    ):
        """Test that cache lookup failures result in exception when no other fallback."""
        from src.service.cache_manager import CacheManager

        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        coordinator = FallbackCoordinator(
            fallback_strategy=FallbackStrategy.PARAMETER_CACHE, cache_manager=cache_manager, timeout=0.1
        )

        # Mock cache.get to raise an exception
        mocker.patch.object(cache_manager, "get", side_effect=Exception("Cache error"))

        async def failing_primary():
            await asyncio.sleep(1.0)

        # Should raise exception when cache fails and it's the only fallback
        with pytest.raises(RuntimeError, match="All fallback strategies failed"):
            await coordinator.request_with_fallback(
                primary_provider=LLMProvider.OPENAI,
                primary_request_func=failing_primary,
                prompt=sample_prompt,
                model="cache-error-test",
            )

        assert coordinator.stats["fallback_failures"] == 1

    async def test_semantic_cache_fallback(self, temp_cache_dir, sample_character_response, sample_prompt):
        """Test semantic cache fallback strategy."""
        from src.client.llm_client import get_openai_embedding
        from src.service.cache_manager import CacheManager, SemanticCacheManager

        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        semantic_cache_manager = SemanticCacheManager(
            cache_dir=f"{temp_cache_dir}_semantic", similarity_threshold=0.9, embedding_func=get_openai_embedding
        )

        # Pre-populate semantic cache
        await semantic_cache_manager.set(sample_prompt, "gpt-5.4", sample_character_response)

        coordinator = FallbackCoordinator(
            fallback_strategy=FallbackStrategy.SEMANTIC_CACHE,
            cache_manager=cache_manager,
            semantic_cache_manager=semantic_cache_manager,
            timeout=0.1,
        )

        async def slow_primary_request():
            await asyncio.sleep(1.0)  # Longer than timeout
            return sample_character_response

        response, strategy, error_reason = await coordinator.request_with_fallback(
            primary_provider=LLMProvider.OPENAI,
            primary_request_func=slow_primary_request,
            prompt=sample_prompt,
            model="gpt-5.4",
        )

        assert response.first_name == sample_character_response.first_name
        assert strategy == FallbackStrategy.SEMANTIC_CACHE
        assert error_reason == "timeout"
        assert coordinator.stats["timeout_count"] == 1
        assert coordinator.stats["semantic_cache_hits"] == 1

    @pytest.mark.parametrize("provider", [LLMProvider.OPENAI, LLMProvider.GEMINI])
    async def test_different_providers(self, temp_cache_dir, provider, sample_character_response, sample_prompt):
        """Test fallback coordinator with different providers."""
        from src.service.cache_manager import CacheManager

        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        coordinator = FallbackCoordinator(cache_manager=cache_manager)

        async def success():
            return sample_character_response

        response, strategy, error_reason = await coordinator.request_with_fallback(
            primary_provider=provider, primary_request_func=success, prompt=sample_prompt, model=f"{provider}-test"
        )

        assert response == sample_character_response
        assert coordinator.stats["primary_success"] == 1
