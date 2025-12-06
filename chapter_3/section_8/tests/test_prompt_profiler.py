"""Tests for the PromptProfiler collection layer.

These tests verify the profiler correctly collects metrics for LLM requests
including latency, token counts, and quality scores.
"""

import asyncio

import pytest
from src.model.profiler_metrics import MetricStatus, ProfilerMetrics
from src.service.prompt_profiler import (
    MetricsStore,
    PromptProfiler,
    estimate_cost,
    get_default_profiler,
    set_default_profiler,
)


class TestEstimateCost:
    """Test cost estimation functionality."""

    def test_estimate_cost_openai(self):
        """Test cost estimation for OpenAI models."""
        cost = estimate_cost(
            provider="openai",
            model="gpt-4o-mini",
            input_tokens=1000,
            output_tokens=500,
        )
        assert cost is not None
        assert cost > 0

    def test_estimate_cost_gemini(self):
        """Test cost estimation for Gemini models."""
        cost = estimate_cost(
            provider="gemini",
            model="gemini-2.5-flash",
            input_tokens=1000,
            output_tokens=500,
        )
        assert cost is not None
        assert cost > 0

    def test_estimate_cost_anthropic(self):
        """Test cost estimation for Anthropic models."""
        cost = estimate_cost(
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=500,
        )
        assert cost is not None
        assert cost > 0

    def test_estimate_cost_unknown_model(self):
        """Test cost estimation for unknown model returns None."""
        cost = estimate_cost(
            provider="unknown",
            model="unknown-model",
            input_tokens=1000,
            output_tokens=500,
        )
        assert cost is None


class TestMetricsStore:
    """Test the MetricsStore class."""

    @pytest.mark.asyncio
    async def test_add_and_get_metrics(self, sample_profiler_metrics: ProfilerMetrics):
        """Test adding and retrieving metrics."""
        store = MetricsStore(max_size=100)

        await store.add(sample_profiler_metrics)

        all_metrics = await store.get_all()
        assert len(all_metrics) == 1
        assert all_metrics[0].request_id == sample_profiler_metrics.request_id

    @pytest.mark.asyncio
    async def test_get_by_prompt_id(self, sample_metrics_list: list[ProfilerMetrics]):
        """Test filtering metrics by prompt ID."""
        store = MetricsStore(max_size=100)

        for m in sample_metrics_list:
            await store.add(m)

        # All metrics have the same prompt_id
        filtered = await store.get_by_prompt_id("character_generation")
        assert len(filtered) == len(sample_metrics_list)

        # Non-existent prompt_id
        filtered = await store.get_by_prompt_id("nonexistent")
        assert len(filtered) == 0

    @pytest.mark.asyncio
    async def test_max_size_eviction(self):
        """Test that store evicts old entries when max size is exceeded."""
        store = MetricsStore(max_size=5)

        # Add 10 metrics
        for i in range(10):
            metrics = ProfilerMetrics(
                prompt_id="test",
                request_id=f"request-{i}",
                latency_ms=100.0,
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                model="test-model",
                provider="test",
            )
            await store.add(metrics)

        # Should only have 5 (the last 5)
        all_metrics = await store.get_all()
        assert len(all_metrics) == 5
        assert all_metrics[0].request_id == "request-5"
        assert all_metrics[-1].request_id == "request-9"

    @pytest.mark.asyncio
    async def test_get_recent(self, sample_metrics_list: list[ProfilerMetrics]):
        """Test getting recent metrics."""
        store = MetricsStore(max_size=100)

        for m in sample_metrics_list:
            await store.add(m)

        recent = await store.get_recent(3)
        assert len(recent) == 3

    @pytest.mark.asyncio
    async def test_clear(self, sample_metrics_list: list[ProfilerMetrics]):
        """Test clearing all metrics."""
        store = MetricsStore(max_size=100)

        for m in sample_metrics_list:
            await store.add(m)

        await store.clear()
        assert await store.count() == 0


class TestPromptProfiler:
    """Test the PromptProfiler class."""

    @pytest.mark.asyncio
    async def test_profile_context_manager(self):
        """Test profiling with context manager."""
        profiler = PromptProfiler()

        async with profiler.profile(
            prompt_id="test_prompt",
            model="gpt-4o-mini",
            provider="openai",
            prompt_name="Test Prompt",
        ) as ctx:
            # Simulate some work
            await asyncio.sleep(0.01)
            ctx["input_tokens"] = 100
            ctx["output_tokens"] = 50
            ctx["response"] = "test response"

        # Give async task time to complete
        await asyncio.sleep(0.1)

        # Check metrics were collected
        metrics = await profiler.get_metrics(prompt_id="test_prompt")
        assert len(metrics) == 1
        assert metrics[0].input_tokens == 100
        assert metrics[0].output_tokens == 50
        assert metrics[0].latency_ms > 0

    @pytest.mark.asyncio
    async def test_profile_with_error(self):
        """Test profiling when an error occurs."""
        profiler = PromptProfiler()

        with pytest.raises(ValueError):
            async with profiler.profile(
                prompt_id="error_prompt",
                model="gpt-4o-mini",
                provider="openai",
            ):
                raise ValueError("Test error")

        # Give async task time to complete
        await asyncio.sleep(0.1)

        metrics = await profiler.get_metrics(prompt_id="error_prompt")
        assert len(metrics) == 1
        assert metrics[0].status == MetricStatus.ERROR
        assert "Test error" in metrics[0].error_message

    @pytest.mark.asyncio
    async def test_profile_with_quality_score(self):
        """Test profiling with quality score."""
        profiler = PromptProfiler()

        async with profiler.profile(
            prompt_id="quality_prompt",
            model="gpt-4o-mini",
            provider="openai",
        ) as ctx:
            ctx["input_tokens"] = 100
            ctx["output_tokens"] = 50
            ctx["quality_score"] = 4.5
            ctx["quality_details"] = {"summary": "Good quality"}

        await asyncio.sleep(0.1)

        metrics = await profiler.get_metrics(prompt_id="quality_prompt")
        assert len(metrics) == 1
        assert metrics[0].quality_score == 4.5
        assert metrics[0].quality_details == {"summary": "Good quality"}

    @pytest.mark.asyncio
    async def test_record_metrics_directly(self):
        """Test recording metrics directly without context manager."""
        profiler = PromptProfiler()

        metrics = await profiler.record_metrics(
            prompt_id="direct_prompt",
            model="gpt-4o-mini",
            provider="openai",
            latency_ms=150.0,
            input_tokens=200,
            output_tokens=100,
        )

        assert metrics.prompt_id == "direct_prompt"
        assert metrics.latency_ms == 150.0
        assert metrics.input_tokens == 200

        # Verify it was stored
        stored = await profiler.get_metrics(prompt_id="direct_prompt")
        assert len(stored) == 1

    @pytest.mark.asyncio
    async def test_cost_estimation_enabled(self):
        """Test that cost estimation works when enabled."""
        profiler = PromptProfiler(enable_cost_estimation=True)

        async with profiler.profile(
            prompt_id="cost_prompt",
            model="gpt-4o-mini",
            provider="openai",
        ) as ctx:
            ctx["input_tokens"] = 1000
            ctx["output_tokens"] = 500

        await asyncio.sleep(0.1)

        metrics = await profiler.get_metrics(prompt_id="cost_prompt")
        assert len(metrics) == 1
        assert metrics[0].estimated_cost_usd is not None
        assert metrics[0].estimated_cost_usd > 0

    @pytest.mark.asyncio
    async def test_cost_estimation_disabled(self):
        """Test that cost estimation can be disabled."""
        profiler = PromptProfiler(enable_cost_estimation=False)

        async with profiler.profile(
            prompt_id="no_cost_prompt",
            model="gpt-4o-mini",
            provider="openai",
        ) as ctx:
            ctx["input_tokens"] = 1000
            ctx["output_tokens"] = 500

        await asyncio.sleep(0.1)

        metrics = await profiler.get_metrics(prompt_id="no_cost_prompt")
        assert len(metrics) == 1
        assert metrics[0].estimated_cost_usd is None


class TestDefaultProfiler:
    """Test the default profiler singleton."""

    def test_get_default_profiler(self):
        """Test getting the default profiler."""
        profiler1 = get_default_profiler()
        profiler2 = get_default_profiler()
        assert profiler1 is profiler2

    def test_set_default_profiler(self):
        """Test setting a custom default profiler."""
        custom_profiler = PromptProfiler(enable_cost_estimation=False)
        set_default_profiler(custom_profiler)

        assert get_default_profiler() is custom_profiler
        assert get_default_profiler().enable_cost_estimation is False

        # Reset to a new instance for other tests
        set_default_profiler(PromptProfiler())
