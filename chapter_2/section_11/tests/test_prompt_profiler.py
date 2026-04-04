"""Tests for the PromptProfiler collection layer."""

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
    def test_estimate_cost_openai(self):
        cost = estimate_cost(
            provider="openai",
            model="gpt-5.4-mini",
            input_tokens=1000,
            output_tokens=500,
        )
        assert cost is not None
        assert cost > 0

    def test_estimate_cost_gemini(self):
        cost = estimate_cost(
            provider="gemini",
            model="gemini-2.5-flash",
            input_tokens=1000,
            output_tokens=500,
        )
        assert cost is not None
        assert cost > 0

    def test_estimate_cost_anthropic(self):
        cost = estimate_cost(
            provider="anthropic",
            model="claude-sonnet-4-6",
            input_tokens=1000,
            output_tokens=500,
        )
        assert cost is not None
        assert cost > 0

    def test_estimate_cost_unknown_model(self):
        cost = estimate_cost(
            provider="unknown",
            model="unknown-model",
            input_tokens=1000,
            output_tokens=500,
        )
        assert cost is None


class TestMetricsStore:
    @pytest.mark.asyncio
    async def test_add_and_get_metrics(self, sample_profiler_metrics: ProfilerMetrics):
        store = MetricsStore(max_size=100)

        await store.add(sample_profiler_metrics)

        all_metrics = await store.get_all()
        assert len(all_metrics) == 1
        assert all_metrics[0].request_id == sample_profiler_metrics.request_id

    @pytest.mark.asyncio
    async def test_get_by_prompt_id(self, sample_metrics_list: list[ProfilerMetrics]):
        store = MetricsStore(max_size=100)

        for m in sample_metrics_list:
            await store.add(m)

        filtered = await store.get_by_prompt_id("character_generation")
        assert len(filtered) == len(sample_metrics_list)

        filtered = await store.get_by_prompt_id("nonexistent")
        assert len(filtered) == 0

    @pytest.mark.asyncio
    async def test_max_size_eviction(self):
        store = MetricsStore(max_size=5)

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

        all_metrics = await store.get_all()
        assert len(all_metrics) == 5
        assert all_metrics[0].request_id == "request-5"
        assert all_metrics[-1].request_id == "request-9"

    @pytest.mark.asyncio
    async def test_get_recent(self, sample_metrics_list: list[ProfilerMetrics]):
        store = MetricsStore(max_size=100)

        for m in sample_metrics_list:
            await store.add(m)

        recent = await store.get_recent(3)
        assert len(recent) == 3

    @pytest.mark.asyncio
    async def test_clear(self, sample_metrics_list: list[ProfilerMetrics]):
        store = MetricsStore(max_size=100)

        for m in sample_metrics_list:
            await store.add(m)

        await store.clear()
        assert await store.count() == 0


class TestPromptProfiler:
    @pytest.mark.asyncio
    async def test_profile_context_manager(self):
        profiler = PromptProfiler()

        async with profiler.profile(
            prompt_id="test_prompt",
            model="gpt-5.4-mini",
            provider="openai",
            prompt_name="Test Prompt",
        ) as ctx:
            await asyncio.sleep(0.01)
            ctx["input_tokens"] = 100
            ctx["output_tokens"] = 50
            ctx["response"] = "test response"

        await asyncio.sleep(0.1)

        metrics = await profiler.get_metrics(prompt_id="test_prompt")
        assert len(metrics) == 1
        assert metrics[0].input_tokens == 100
        assert metrics[0].output_tokens == 50
        assert metrics[0].latency_ms > 0

    @pytest.mark.asyncio
    async def test_profile_with_error(self):
        profiler = PromptProfiler()

        with pytest.raises(ValueError):
            async with profiler.profile(
                prompt_id="error_prompt",
                model="gpt-5.4-mini",
                provider="openai",
            ):
                raise ValueError("Test error")

        await asyncio.sleep(0.1)

        metrics = await profiler.get_metrics(prompt_id="error_prompt")
        assert len(metrics) == 1
        assert metrics[0].status == MetricStatus.ERROR
        assert "Test error" in metrics[0].error_message

    @pytest.mark.asyncio
    async def test_profile_with_quality_score(self):
        profiler = PromptProfiler()

        async with profiler.profile(
            prompt_id="quality_prompt",
            model="gpt-5.4-mini",
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
        profiler = PromptProfiler()

        metrics = await profiler.record_metrics(
            prompt_id="direct_prompt",
            model="gpt-5.4-mini",
            provider="openai",
            latency_ms=150.0,
            input_tokens=200,
            output_tokens=100,
        )

        assert metrics.prompt_id == "direct_prompt"
        assert metrics.latency_ms == 150.0
        assert metrics.input_tokens == 200

        stored = await profiler.get_metrics(prompt_id="direct_prompt")
        assert len(stored) == 1

    @pytest.mark.asyncio
    async def test_cost_estimation_enabled(self):
        profiler = PromptProfiler(enable_cost_estimation=True)

        async with profiler.profile(
            prompt_id="cost_prompt",
            model="gpt-5.4-mini",
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
        profiler = PromptProfiler(enable_cost_estimation=False)

        async with profiler.profile(
            prompt_id="no_cost_prompt",
            model="gpt-5.4-mini",
            provider="openai",
        ) as ctx:
            ctx["input_tokens"] = 1000
            ctx["output_tokens"] = 500

        await asyncio.sleep(0.1)

        metrics = await profiler.get_metrics(prompt_id="no_cost_prompt")
        assert len(metrics) == 1
        assert metrics[0].estimated_cost_usd is None


class TestDefaultProfiler:
    def test_get_default_profiler(self):
        profiler1 = get_default_profiler()
        profiler2 = get_default_profiler()
        assert profiler1 is profiler2

    def test_set_default_profiler(self):
        custom_profiler = PromptProfiler(enable_cost_estimation=False)
        set_default_profiler(custom_profiler)

        assert get_default_profiler() is custom_profiler
        assert get_default_profiler().enable_cost_estimation is False

        set_default_profiler(PromptProfiler())
