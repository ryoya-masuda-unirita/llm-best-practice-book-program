"""Profiler metrics models for prompt performance profiling.

Based on the specification in CLAUDE.md, this module provides structured
data models for capturing and analyzing LLM prompt performance metrics.
"""

import json
import statistics
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class MetricStatus(StrEnum):
    """Status of the metric collection."""

    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class ProfilerMetrics(BaseModel):
    """Metrics collected for a single prompt execution.

    This model captures essential performance data for each LLM request:
    - Token usage (input/output)
    - Execution timing
    - API response status
    - Quality scores (if available)
    """

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=False,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    prompt_id: str = Field(..., description="Unique identifier for the prompt")
    request_id: str = Field(..., description="Unique identifier for this specific request")
    prompt_name: Optional[str] = Field(None, description="Human-readable name for the prompt")

    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 formatted timestamp of when the request was made",
    )
    latency_ms: float = Field(..., description="Total execution time in milliseconds", ge=0.0)

    input_tokens: int = Field(..., description="Number of input tokens", ge=0)
    output_tokens: int = Field(..., description="Number of output tokens", ge=0)
    total_tokens: int = Field(..., description="Total tokens (input + output)", ge=0)

    model: str = Field(..., description="Model name used for the request")
    provider: str = Field(..., description="LLM provider (openai, gemini, anthropic)")

    status: MetricStatus = Field(default=MetricStatus.SUCCESS, description="Status of the request")
    status_code: Optional[int] = Field(None, description="API response status code")
    error_message: Optional[str] = Field(None, description="Error message if request failed")

    quality_score: Optional[float] = Field(
        None, description="Quality score from LLM-as-a-Judge (1.0-5.0)", ge=1.0, le=5.0
    )
    quality_details: Optional[dict[str, Any]] = Field(None, description="Detailed quality evaluation results")

    estimated_cost_usd: Optional[float] = Field(None, description="Estimated cost in USD based on token usage", ge=0.0)

    metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    def to_json_string(self) -> str:
        """Convert metrics to JSON string."""
        return json.dumps(self.model_dump(exclude_none=True), ensure_ascii=False)

    def save_to_file(self, file_path: str) -> None:
        """Save metrics to a JSON file."""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(exclude_none=True), f, indent=2, ensure_ascii=False)


class AggregatedMetrics(BaseModel):
    """Aggregated metrics for a collection of prompt executions.

    Used for time-series analysis and reporting.
    """

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=False,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    prompt_id: Optional[str] = Field(None, description="Prompt ID if aggregating for a specific prompt")
    prompt_name: Optional[str] = Field(None, description="Prompt name if aggregating for a specific prompt")
    start_time: str = Field(..., description="Start of aggregation period")
    end_time: str = Field(..., description="End of aggregation period")
    sample_count: int = Field(..., description="Number of samples in this aggregation", ge=0)

    latency_mean_ms: float = Field(..., description="Mean latency in milliseconds")
    latency_median_ms: float = Field(..., description="Median latency in milliseconds")
    latency_p95_ms: float = Field(..., description="95th percentile latency in milliseconds")
    latency_p99_ms: float = Field(..., description="99th percentile latency in milliseconds")
    latency_min_ms: float = Field(..., description="Minimum latency in milliseconds")
    latency_max_ms: float = Field(..., description="Maximum latency in milliseconds")
    latency_std_ms: float = Field(..., description="Standard deviation of latency")

    total_input_tokens: int = Field(..., description="Total input tokens", ge=0)
    total_output_tokens: int = Field(..., description="Total output tokens", ge=0)
    total_tokens: int = Field(..., description="Total tokens (input + output)", ge=0)
    avg_input_tokens: float = Field(..., description="Average input tokens per request")
    avg_output_tokens: float = Field(..., description="Average output tokens per request")

    success_count: int = Field(..., description="Number of successful requests", ge=0)
    error_count: int = Field(..., description="Number of failed requests", ge=0)
    success_rate: float = Field(..., description="Success rate (0.0-1.0)", ge=0.0, le=1.0)

    avg_quality_score: Optional[float] = Field(None, description="Average quality score", ge=1.0, le=5.0)
    min_quality_score: Optional[float] = Field(None, description="Minimum quality score", ge=1.0, le=5.0)
    max_quality_score: Optional[float] = Field(None, description="Maximum quality score", ge=1.0, le=5.0)

    total_estimated_cost_usd: Optional[float] = Field(None, description="Total estimated cost in USD", ge=0.0)

    def to_json_string(self) -> str:
        """Convert aggregated metrics to JSON string."""
        return json.dumps(self.model_dump(exclude_none=True), ensure_ascii=False)

    def save_to_file(self, file_path: str) -> None:
        """Save aggregated metrics to a JSON file."""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(exclude_none=True), f, indent=2, ensure_ascii=False)

    @staticmethod
    def from_metrics_list(
        metrics: list[ProfilerMetrics],
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        prompt_id: Optional[str] = None,
        prompt_name: Optional[str] = None,
    ) -> "AggregatedMetrics":
        """Create aggregated metrics from a list of ProfilerMetrics."""
        if not metrics:
            raise ValueError("Cannot aggregate empty metrics list")

        latencies = [m.latency_ms for m in metrics]
        input_tokens = [m.input_tokens for m in metrics]
        output_tokens = [m.output_tokens for m in metrics]
        quality_scores = [m.quality_score for m in metrics if m.quality_score is not None]
        costs = [m.estimated_cost_usd for m in metrics if m.estimated_cost_usd is not None]

        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        # Calculate percentiles
        p95_idx = int(n * 0.95)
        p99_idx = int(n * 0.99)

        success_count = sum(1 for m in metrics if m.status == MetricStatus.SUCCESS)
        error_count = len(metrics) - success_count

        return AggregatedMetrics(
            prompt_id=prompt_id,
            prompt_name=prompt_name,
            start_time=start_time or min(m.timestamp for m in metrics),
            end_time=end_time or max(m.timestamp for m in metrics),
            sample_count=len(metrics),
            latency_mean_ms=statistics.mean(latencies),
            latency_median_ms=statistics.median(latencies),
            latency_p95_ms=sorted_latencies[min(p95_idx, n - 1)],
            latency_p99_ms=sorted_latencies[min(p99_idx, n - 1)],
            latency_min_ms=min(latencies),
            latency_max_ms=max(latencies),
            latency_std_ms=statistics.stdev(latencies) if len(latencies) > 1 else 0.0,
            total_input_tokens=sum(input_tokens),
            total_output_tokens=sum(output_tokens),
            total_tokens=sum(input_tokens) + sum(output_tokens),
            avg_input_tokens=statistics.mean(input_tokens),
            avg_output_tokens=statistics.mean(output_tokens),
            success_count=success_count,
            error_count=error_count,
            success_rate=success_count / len(metrics) if metrics else 0.0,
            avg_quality_score=statistics.mean(quality_scores) if quality_scores else None,
            min_quality_score=min(quality_scores) if quality_scores else None,
            max_quality_score=max(quality_scores) if quality_scores else None,
            total_estimated_cost_usd=sum(costs) if costs else None,
        )


class AlertThreshold(BaseModel):
    """Threshold configuration for performance alerts."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    latency_warning_ms: float = Field(5000.0, description="Warning threshold for latency (ms)")
    latency_critical_ms: float = Field(10000.0, description="Critical threshold for latency (ms)")

    latency_relative_warning: float = Field(1.5, description="Warning if latency exceeds 150% of baseline")
    latency_relative_critical: float = Field(2.0, description="Critical if latency exceeds 200% of baseline")

    token_warning: int = Field(8000, description="Warning threshold for total tokens")
    token_critical: int = Field(16000, description="Critical threshold for total tokens")

    quality_warning: float = Field(3.0, description="Warning if quality score drops below this")
    quality_critical: float = Field(2.0, description="Critical if quality score drops below this")

    cost_warning_usd: float = Field(0.1, description="Warning threshold for cost per request")
    cost_critical_usd: float = Field(0.5, description="Critical threshold for cost per request")

    success_rate_warning: float = Field(0.95, description="Warning if success rate drops below 95%")
    success_rate_critical: float = Field(0.90, description="Critical if success rate drops below 90%")


class Alert(BaseModel):
    """Performance alert generated when thresholds are exceeded."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="When the alert was generated",
    )
    prompt_id: Optional[str] = Field(None, description="Prompt ID that triggered the alert")
    prompt_name: Optional[str] = Field(None, description="Prompt name that triggered the alert")
    severity: str = Field(..., description="Alert severity: warning or critical")
    metric_name: str = Field(..., description="Name of the metric that triggered the alert")
    metric_value: float = Field(..., description="Current value of the metric")
    threshold_value: float = Field(..., description="Threshold that was exceeded")
    message: str = Field(..., description="Human-readable alert message")

    def to_json_string(self) -> str:
        """Convert alert to JSON string."""
        return json.dumps(self.model_dump(exclude_none=True), ensure_ascii=False)
