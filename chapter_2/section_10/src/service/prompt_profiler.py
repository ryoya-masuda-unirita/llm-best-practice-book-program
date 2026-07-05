"""Prompt Profiler - Collection layer for LLM performance monitoring."""

import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Optional
from uuid import uuid4

from src.logger import make_logger
from src.model.profiler_metrics import MetricStatus, ProfilerMetrics

logger = make_logger(__name__)


TOKEN_PRICING = {
    "openai": {
        "gpt-5.4": {"input": 0.0025, "output": 0.01},
        "gpt-5.4-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-5.4-nano": {"input": 0.0001, "output": 0.0004},
        "gpt-5.2": {"input": 0.002, "output": 0.008},
        "gpt-5.1": {"input": 0.0004, "output": 0.0016},
        "gpt-5": {"input": 0.005, "output": 0.02},
        "gpt-5-mini": {"input": 0.001, "output": 0.004},
        "gpt-5-nano": {"input": 0.0002, "output": 0.0008},
    },
    "gemini": {
        "gemini-2.5-pro": {"input": 0.00125, "output": 0.005},
        "gemini-2.5-flash": {"input": 0.000075, "output": 0.0003},
        "gemini-2.5-flash-lite": {"input": 0.00005, "output": 0.0002},
    },
    "anthropic": {
        "claude-sonnet-4-6": {"input": 0.003, "output": 0.015},
        "claude-opus-4-7": {"input": 0.015, "output": 0.075},
        "claude-sonnet-5": {"input": 0.003, "output": 0.015},
        "claude-opus-4-8": {"input": 0.015, "output": 0.075},
    },
}


def estimate_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> Optional[float]:
    """Estimate the cost of an API call based on token usage."""
    provider_pricing = TOKEN_PRICING.get(provider.lower(), {})
    model_pricing = provider_pricing.get(model.lower())

    if not model_pricing:
        # Try to find partial match for model name
        for model_key, pricing in provider_pricing.items():
            if model_key in model.lower() or model.lower() in model_key:
                model_pricing = pricing
                break

    if not model_pricing:
        return None

    input_cost = (input_tokens / 1000) * model_pricing["input"]
    output_cost = (output_tokens / 1000) * model_pricing["output"]
    return input_cost + output_cost


class MetricsStore:
    """In-memory store for profiler metrics with async-safe operations."""

    def __init__(self, max_size: int = 10000, storage_path: Optional[Path] = None):
        self._metrics: list[ProfilerMetrics] = []
        self._max_size = max_size
        self._storage_path = storage_path
        self._lock = asyncio.Lock()

        if storage_path:
            storage_path.mkdir(parents=True, exist_ok=True)

    async def add(self, metrics: ProfilerMetrics) -> None:
        async with self._lock:
            self._metrics.append(metrics)

            if len(self._metrics) > self._max_size:
                self._metrics = self._metrics[-self._max_size :]

            if self._storage_path:
                await self._persist_metrics(metrics)

    async def _persist_metrics(self, metrics: ProfilerMetrics) -> None:
        if not self._storage_path:
            return

        timestamp = metrics.timestamp.replace(":", "-").replace("+", "_")
        filename = f"{metrics.prompt_id}_{metrics.request_id}_{timestamp}.json"
        file_path = self._storage_path / filename

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, metrics.save_to_file, str(file_path))

    async def get_all(self) -> list[ProfilerMetrics]:
        async with self._lock:
            return list(self._metrics)

    async def get_by_prompt_id(self, prompt_id: str) -> list[ProfilerMetrics]:
        async with self._lock:
            return [m for m in self._metrics if m.prompt_id == prompt_id]

    async def get_by_time_range(
        self,
        start_time: str,
        end_time: str,
    ) -> list[ProfilerMetrics]:
        async with self._lock:
            return [m for m in self._metrics if start_time <= m.timestamp <= end_time]

    async def get_recent(self, count: int = 100) -> list[ProfilerMetrics]:
        async with self._lock:
            return list(self._metrics[-count:])

    async def clear(self) -> None:
        async with self._lock:
            self._metrics.clear()

    async def count(self) -> int:
        async with self._lock:
            return len(self._metrics)


class PromptProfiler:
    """Profiler for collecting LLM prompt performance metrics."""

    def __init__(
        self,
        metrics_store: Optional[MetricsStore] = None,
        enable_cost_estimation: bool = True,
        default_prompt_name: Optional[str] = None,
    ):
        self.metrics_store = metrics_store or MetricsStore()
        self.enable_cost_estimation = enable_cost_estimation
        self.default_prompt_name = default_prompt_name
        self._active_profiles: dict[str, dict[str, Any]] = {}

    @asynccontextmanager
    async def profile(
        self,
        prompt_id: str,
        model: str,
        provider: str,
        prompt_name: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Context manager to profile an LLM request."""
        request_id = request_id or str(uuid4())
        prompt_name = prompt_name or self.default_prompt_name

        context: dict[str, Any] = {
            "request_id": request_id,
            "prompt_id": prompt_id,
            "input_tokens": 0,
            "output_tokens": 0,
            "response": None,
            "quality_score": None,
            "quality_details": None,
            "error": None,
        }

        start_time = time.perf_counter()
        status = MetricStatus.SUCCESS
        status_code: Optional[int] = None
        error_message: Optional[str] = None

        try:
            yield context
            status_code = 200
        except TimeoutError as e:
            status = MetricStatus.TIMEOUT
            status_code = 408
            error_message = str(e)
            context["error"] = e
            raise
        except Exception as e:
            status = MetricStatus.ERROR
            status_code = 500
            error_message = str(e)
            context["error"] = e
            raise
        finally:
            latency_ms = (time.perf_counter() - start_time) * 1000

            input_tokens = context.get("input_tokens", 0)
            output_tokens = context.get("output_tokens", 0)
            total_tokens = input_tokens + output_tokens

            estimated_cost: Optional[float] = None
            if self.enable_cost_estimation:
                estimated_cost = estimate_cost(
                    provider=provider,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

            metrics = ProfilerMetrics(
                prompt_id=prompt_id,
                request_id=request_id,
                prompt_name=prompt_name,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                model=model,
                provider=provider,
                status=status,
                status_code=status_code,
                error_message=error_message,
                quality_score=context.get("quality_score"),
                quality_details=context.get("quality_details"),
                estimated_cost_usd=estimated_cost,
                metadata=metadata,
            )

            asyncio.create_task(self._store_metrics(metrics))

            logger.info(
                f"Profiled request {request_id}: "
                f"prompt={prompt_id}, model={model}, "
                f"latency={latency_ms:.2f}ms, "
                f"tokens={total_tokens} (in={input_tokens}, out={output_tokens}), "
                f"status={status}"
            )

    async def _store_metrics(self, metrics: ProfilerMetrics) -> None:
        try:
            await self.metrics_store.add(metrics)
        except Exception as e:
            logger.error(f"Failed to store metrics: {e}")

    async def record_metrics(
        self,
        prompt_id: str,
        model: str,
        provider: str,
        latency_ms: float,
        input_tokens: int,
        output_tokens: int,
        prompt_name: Optional[str] = None,
        request_id: Optional[str] = None,
        status: MetricStatus = MetricStatus.SUCCESS,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
        quality_score: Optional[float] = None,
        quality_details: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ProfilerMetrics:
        """Directly record metrics without using context manager."""
        request_id = request_id or str(uuid4())

        estimated_cost: Optional[float] = None
        if self.enable_cost_estimation:
            estimated_cost = estimate_cost(
                provider=provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        metrics = ProfilerMetrics(
            prompt_id=prompt_id,
            request_id=request_id,
            prompt_name=prompt_name or self.default_prompt_name,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            model=model,
            provider=provider,
            status=status,
            status_code=status_code,
            error_message=error_message,
            quality_score=quality_score,
            quality_details=quality_details,
            estimated_cost_usd=estimated_cost,
            metadata=metadata,
        )

        await self.metrics_store.add(metrics)
        return metrics

    async def get_metrics(
        self,
        prompt_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[ProfilerMetrics]:
        """Get collected metrics."""
        if prompt_id:
            metrics = await self.metrics_store.get_by_prompt_id(prompt_id)
        else:
            metrics = await self.metrics_store.get_all()

        if limit:
            metrics = metrics[-limit:]

        return metrics


_default_profiler: Optional[PromptProfiler] = None


def get_default_profiler() -> PromptProfiler:
    global _default_profiler
    if _default_profiler is None:
        _default_profiler = PromptProfiler()
    return _default_profiler


def set_default_profiler(profiler: PromptProfiler) -> None:
    global _default_profiler
    _default_profiler = profiler
