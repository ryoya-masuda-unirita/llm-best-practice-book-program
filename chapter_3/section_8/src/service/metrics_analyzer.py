"""Metrics Analyzer - Analysis layer for prompt performance profiling."""

import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from src.logger import make_logger
from src.model.profiler_metrics import (
    AggregatedMetrics,
    Alert,
    AlertThreshold,
    MetricStatus,
    ProfilerMetrics,
)

logger = make_logger(__name__)


class MetricsAnalyzer:
    """Analyzer for prompt performance metrics."""

    def __init__(
        self,
        thresholds: Optional[AlertThreshold] = None,
        baseline_window_hours: int = 24,
    ):
        self.thresholds = thresholds or AlertThreshold()
        self.baseline_window_hours = baseline_window_hours
        self._baselines: dict[str, dict[str, float]] = {}

    def aggregate_metrics(
        self,
        metrics: list[ProfilerMetrics],
        prompt_id: Optional[str] = None,
        prompt_name: Optional[str] = None,
    ) -> AggregatedMetrics:
        """Aggregate a list of metrics into summary statistics."""
        return AggregatedMetrics.from_metrics_list(
            metrics,
            prompt_id=prompt_id,
            prompt_name=prompt_name,
        )

    def aggregate_by_prompt(
        self,
        metrics: list[ProfilerMetrics],
    ) -> dict[str, AggregatedMetrics]:
        """Aggregate metrics grouped by prompt ID."""
        grouped: dict[str, list[ProfilerMetrics]] = defaultdict(list)
        for m in metrics:
            grouped[m.prompt_id].append(m)

        result = {}
        for prompt_id, prompt_metrics in grouped.items():
            prompt_name = prompt_metrics[0].prompt_name if prompt_metrics else None
            result[prompt_id] = self.aggregate_metrics(
                prompt_metrics,
                prompt_id=prompt_id,
                prompt_name=prompt_name,
            )
        return result

    def aggregate_by_model(
        self,
        metrics: list[ProfilerMetrics],
    ) -> dict[str, AggregatedMetrics]:
        """Aggregate metrics grouped by model."""
        grouped: dict[str, list[ProfilerMetrics]] = defaultdict(list)
        for m in metrics:
            grouped[m.model].append(m)

        return {model: self.aggregate_metrics(model_metrics) for model, model_metrics in grouped.items()}

    def aggregate_by_provider(
        self,
        metrics: list[ProfilerMetrics],
    ) -> dict[str, AggregatedMetrics]:
        """Aggregate metrics grouped by provider."""
        grouped: dict[str, list[ProfilerMetrics]] = defaultdict(list)
        for m in metrics:
            grouped[m.provider].append(m)

        return {provider: self.aggregate_metrics(provider_metrics) for provider, provider_metrics in grouped.items()}

    def aggregate_by_time_bucket(
        self,
        metrics: list[ProfilerMetrics],
        bucket_minutes: int = 60,
    ) -> dict[str, AggregatedMetrics]:
        """Aggregate metrics grouped by time buckets."""
        grouped: dict[str, list[ProfilerMetrics]] = defaultdict(list)

        for m in metrics:
            # Parse timestamp and bucket it
            ts = datetime.fromisoformat(m.timestamp.replace("Z", "+00:00"))
            bucket_start = ts.replace(
                minute=(ts.minute // bucket_minutes) * bucket_minutes,
                second=0,
                microsecond=0,
            )
            bucket_key = bucket_start.isoformat()
            grouped[bucket_key].append(m)

        result = {}
        for bucket_key, bucket_metrics in sorted(grouped.items()):
            bucket_end = datetime.fromisoformat(bucket_key.replace("Z", "+00:00")) + timedelta(minutes=bucket_minutes)
            result[bucket_key] = AggregatedMetrics.from_metrics_list(
                bucket_metrics,
                start_time=bucket_key,
                end_time=bucket_end.isoformat(),
            )
        return result

    def calculate_baseline(
        self,
        metrics: list[ProfilerMetrics],
        prompt_id: str,
    ) -> dict[str, float]:
        """Calculate baseline metrics for a prompt."""
        prompt_metrics = [m for m in metrics if m.prompt_id == prompt_id]

        if not prompt_metrics:
            return {}

        latencies = [m.latency_ms for m in prompt_metrics]
        input_tokens = [m.input_tokens for m in prompt_metrics]
        output_tokens = [m.output_tokens for m in prompt_metrics]
        quality_scores = [m.quality_score for m in prompt_metrics if m.quality_score]

        baseline = {
            "latency_mean_ms": statistics.mean(latencies),
            "latency_std_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0.0,
            "input_tokens_mean": statistics.mean(input_tokens),
            "output_tokens_mean": statistics.mean(output_tokens),
        }

        if quality_scores:
            baseline["quality_mean"] = statistics.mean(quality_scores)

        self._baselines[prompt_id] = baseline
        return baseline

    def detect_anomalies(
        self,
        metrics: ProfilerMetrics,
        baseline: Optional[dict[str, float]] = None,
    ) -> list[str]:
        """Detect anomalies in a single metrics entry."""
        anomalies = []

        if baseline is None:
            baseline = self._baselines.get(metrics.prompt_id, {})

        if metrics.latency_ms > self.thresholds.latency_critical_ms:
            anomalies.append(
                f"Critical latency: {metrics.latency_ms:.2f}ms (threshold: {self.thresholds.latency_critical_ms}ms)"
            )
        elif metrics.latency_ms > self.thresholds.latency_warning_ms:
            anomalies.append(
                f"High latency: {metrics.latency_ms:.2f}ms (threshold: {self.thresholds.latency_warning_ms}ms)"
            )

        if metrics.total_tokens > self.thresholds.token_critical:
            anomalies.append(
                f"Critical token usage: {metrics.total_tokens} (threshold: {self.thresholds.token_critical})"
            )
        elif metrics.total_tokens > self.thresholds.token_warning:
            anomalies.append(f"High token usage: {metrics.total_tokens} (threshold: {self.thresholds.token_warning})")

        if metrics.quality_score is not None:
            if metrics.quality_score < self.thresholds.quality_critical:
                anomalies.append(
                    f"Critical quality score: {metrics.quality_score:.2f} "
                    f"(threshold: {self.thresholds.quality_critical})"
                )
            elif metrics.quality_score < self.thresholds.quality_warning:
                anomalies.append(
                    f"Low quality score: {metrics.quality_score:.2f} (threshold: {self.thresholds.quality_warning})"
                )

        if metrics.estimated_cost_usd is not None:
            if metrics.estimated_cost_usd > self.thresholds.cost_critical_usd:
                anomalies.append(
                    f"Critical cost: ${metrics.estimated_cost_usd:.4f} "
                    f"(threshold: ${self.thresholds.cost_critical_usd})"
                )
            elif metrics.estimated_cost_usd > self.thresholds.cost_warning_usd:
                anomalies.append(
                    f"High cost: ${metrics.estimated_cost_usd:.4f} (threshold: ${self.thresholds.cost_warning_usd})"
                )

        if baseline:
            baseline_latency = baseline.get("latency_mean_ms")
            if baseline_latency:
                relative_latency = metrics.latency_ms / baseline_latency
                if relative_latency > self.thresholds.latency_relative_critical:
                    anomalies.append(
                        f"Latency {relative_latency:.1f}x baseline "
                        f"(threshold: {self.thresholds.latency_relative_critical}x)"
                    )
                elif relative_latency > self.thresholds.latency_relative_warning:
                    anomalies.append(
                        f"Latency {relative_latency:.1f}x baseline "
                        f"(threshold: {self.thresholds.latency_relative_warning}x)"
                    )

        return anomalies

    def generate_alerts(
        self,
        metrics: ProfilerMetrics,
        baseline: Optional[dict[str, float]] = None,
    ) -> list[Alert]:
        """Generate alerts based on metrics and thresholds."""
        alerts = []

        if baseline is None:
            baseline = self._baselines.get(metrics.prompt_id, {})

        if metrics.latency_ms > self.thresholds.latency_critical_ms:
            alerts.append(
                Alert(
                    prompt_id=metrics.prompt_id,
                    prompt_name=metrics.prompt_name,
                    severity="critical",
                    metric_name="latency_ms",
                    metric_value=metrics.latency_ms,
                    threshold_value=self.thresholds.latency_critical_ms,
                    message=f"Critical latency detected: {metrics.latency_ms:.2f}ms exceeds {self.thresholds.latency_critical_ms}ms threshold",
                )
            )
        elif metrics.latency_ms > self.thresholds.latency_warning_ms:
            alerts.append(
                Alert(
                    prompt_id=metrics.prompt_id,
                    prompt_name=metrics.prompt_name,
                    severity="warning",
                    metric_name="latency_ms",
                    metric_value=metrics.latency_ms,
                    threshold_value=self.thresholds.latency_warning_ms,
                    message=f"High latency warning: {metrics.latency_ms:.2f}ms exceeds {self.thresholds.latency_warning_ms}ms threshold",
                )
            )

        if metrics.total_tokens > self.thresholds.token_critical:
            alerts.append(
                Alert(
                    prompt_id=metrics.prompt_id,
                    prompt_name=metrics.prompt_name,
                    severity="critical",
                    metric_name="total_tokens",
                    metric_value=float(metrics.total_tokens),
                    threshold_value=float(self.thresholds.token_critical),
                    message=f"Critical token usage: {metrics.total_tokens} exceeds {self.thresholds.token_critical} threshold",
                )
            )
        elif metrics.total_tokens > self.thresholds.token_warning:
            alerts.append(
                Alert(
                    prompt_id=metrics.prompt_id,
                    prompt_name=metrics.prompt_name,
                    severity="warning",
                    metric_name="total_tokens",
                    metric_value=float(metrics.total_tokens),
                    threshold_value=float(self.thresholds.token_warning),
                    message=f"High token usage warning: {metrics.total_tokens} exceeds {self.thresholds.token_warning} threshold",
                )
            )

        if metrics.quality_score is not None:
            if metrics.quality_score < self.thresholds.quality_critical:
                alerts.append(
                    Alert(
                        prompt_id=metrics.prompt_id,
                        prompt_name=metrics.prompt_name,
                        severity="critical",
                        metric_name="quality_score",
                        metric_value=metrics.quality_score,
                        threshold_value=self.thresholds.quality_critical,
                        message=f"Critical quality score: {metrics.quality_score:.2f} below {self.thresholds.quality_critical} threshold",
                    )
                )
            elif metrics.quality_score < self.thresholds.quality_warning:
                alerts.append(
                    Alert(
                        prompt_id=metrics.prompt_id,
                        prompt_name=metrics.prompt_name,
                        severity="warning",
                        metric_name="quality_score",
                        metric_value=metrics.quality_score,
                        threshold_value=self.thresholds.quality_warning,
                        message=f"Low quality warning: {metrics.quality_score:.2f} below {self.thresholds.quality_warning} threshold",
                    )
                )

        if metrics.estimated_cost_usd is not None:
            if metrics.estimated_cost_usd > self.thresholds.cost_critical_usd:
                alerts.append(
                    Alert(
                        prompt_id=metrics.prompt_id,
                        prompt_name=metrics.prompt_name,
                        severity="critical",
                        metric_name="estimated_cost_usd",
                        metric_value=metrics.estimated_cost_usd,
                        threshold_value=self.thresholds.cost_critical_usd,
                        message=f"Critical cost: ${metrics.estimated_cost_usd:.4f} exceeds ${self.thresholds.cost_critical_usd} threshold",
                    )
                )
            elif metrics.estimated_cost_usd > self.thresholds.cost_warning_usd:
                alerts.append(
                    Alert(
                        prompt_id=metrics.prompt_id,
                        prompt_name=metrics.prompt_name,
                        severity="warning",
                        metric_name="estimated_cost_usd",
                        metric_value=metrics.estimated_cost_usd,
                        threshold_value=self.thresholds.cost_warning_usd,
                        message=f"High cost warning: ${metrics.estimated_cost_usd:.4f} exceeds ${self.thresholds.cost_warning_usd} threshold",
                    )
                )

        if baseline:
            baseline_latency = baseline.get("latency_mean_ms")
            if baseline_latency and baseline_latency > 0:
                relative_latency = metrics.latency_ms / baseline_latency
                if relative_latency > self.thresholds.latency_relative_critical:
                    alerts.append(
                        Alert(
                            prompt_id=metrics.prompt_id,
                            prompt_name=metrics.prompt_name,
                            severity="critical",
                            metric_name="latency_relative",
                            metric_value=relative_latency,
                            threshold_value=self.thresholds.latency_relative_critical,
                            message=f"Latency regression: {relative_latency:.1f}x baseline ({baseline_latency:.2f}ms)",
                        )
                    )
                elif relative_latency > self.thresholds.latency_relative_warning:
                    alerts.append(
                        Alert(
                            prompt_id=metrics.prompt_id,
                            prompt_name=metrics.prompt_name,
                            severity="warning",
                            metric_name="latency_relative",
                            metric_value=relative_latency,
                            threshold_value=self.thresholds.latency_relative_warning,
                            message=f"Latency increase: {relative_latency:.1f}x baseline ({baseline_latency:.2f}ms)",
                        )
                    )

        return alerts

    def analyze_aggregated_metrics(
        self,
        aggregated: AggregatedMetrics,
    ) -> list[Alert]:
        """Generate alerts based on aggregated metrics."""
        alerts = []

        if aggregated.success_rate < self.thresholds.success_rate_critical:
            alerts.append(
                Alert(
                    prompt_id=aggregated.prompt_id,
                    prompt_name=aggregated.prompt_name,
                    severity="critical",
                    metric_name="success_rate",
                    metric_value=aggregated.success_rate,
                    threshold_value=self.thresholds.success_rate_critical,
                    message=f"Critical success rate: {aggregated.success_rate:.1%} below {self.thresholds.success_rate_critical:.1%} threshold",
                )
            )
        elif aggregated.success_rate < self.thresholds.success_rate_warning:
            alerts.append(
                Alert(
                    prompt_id=aggregated.prompt_id,
                    prompt_name=aggregated.prompt_name,
                    severity="warning",
                    metric_name="success_rate",
                    metric_value=aggregated.success_rate,
                    threshold_value=self.thresholds.success_rate_warning,
                    message=f"Low success rate warning: {aggregated.success_rate:.1%} below {self.thresholds.success_rate_warning:.1%} threshold",
                )
            )

        if aggregated.latency_p95_ms > self.thresholds.latency_critical_ms:
            alerts.append(
                Alert(
                    prompt_id=aggregated.prompt_id,
                    prompt_name=aggregated.prompt_name,
                    severity="critical",
                    metric_name="latency_p95_ms",
                    metric_value=aggregated.latency_p95_ms,
                    threshold_value=self.thresholds.latency_critical_ms,
                    message=f"Critical P95 latency: {aggregated.latency_p95_ms:.2f}ms exceeds {self.thresholds.latency_critical_ms}ms threshold",
                )
            )

        if aggregated.avg_quality_score is not None:
            if aggregated.avg_quality_score < self.thresholds.quality_critical:
                alerts.append(
                    Alert(
                        prompt_id=aggregated.prompt_id,
                        prompt_name=aggregated.prompt_name,
                        severity="critical",
                        metric_name="avg_quality_score",
                        metric_value=aggregated.avg_quality_score,
                        threshold_value=self.thresholds.quality_critical,
                        message=f"Critical average quality: {aggregated.avg_quality_score:.2f} below {self.thresholds.quality_critical} threshold",
                    )
                )
            elif aggregated.avg_quality_score < self.thresholds.quality_warning:
                alerts.append(
                    Alert(
                        prompt_id=aggregated.prompt_id,
                        prompt_name=aggregated.prompt_name,
                        severity="warning",
                        metric_name="avg_quality_score",
                        metric_value=aggregated.avg_quality_score,
                        threshold_value=self.thresholds.quality_warning,
                        message=f"Low average quality warning: {aggregated.avg_quality_score:.2f} below {self.thresholds.quality_warning} threshold",
                    )
                )

        return alerts

    def compare_prompts(
        self,
        metrics: list[ProfilerMetrics],
        prompt_ids: list[str],
    ) -> dict[str, dict[str, float]]:
        """Compare performance across multiple prompts."""
        aggregated = self.aggregate_by_prompt(metrics)

        comparison = {}
        for prompt_id in prompt_ids:
            if prompt_id not in aggregated:
                continue

            agg = aggregated[prompt_id]
            comparison[prompt_id] = {
                "sample_count": agg.sample_count,
                "latency_mean_ms": agg.latency_mean_ms,
                "latency_p95_ms": agg.latency_p95_ms,
                "avg_tokens": agg.avg_input_tokens + agg.avg_output_tokens,
                "success_rate": agg.success_rate,
                "avg_quality": agg.avg_quality_score or 0.0,
                "total_cost": agg.total_estimated_cost_usd or 0.0,
            }

        return comparison

    def detect_trend(
        self,
        time_series: dict[str, AggregatedMetrics],
        metric_name: str = "latency_mean_ms",
    ) -> dict[str, float]:
        """Detect trends in time-series metrics."""
        if len(time_series) < 2:
            return {"trend": 0.0, "change_percent": 0.0}

        sorted_buckets = sorted(time_series.items())
        values = []

        for _, agg in sorted_buckets:
            value = getattr(agg, metric_name, None)
            if value is not None:
                values.append(value)

        if len(values) < 2:
            return {"trend": 0.0, "change_percent": 0.0}

        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator != 0 else 0

        first_value = values[0]
        last_value = values[-1]
        change_percent = ((last_value - first_value) / first_value * 100) if first_value != 0 else 0

        return {
            "trend": slope,
            "change_percent": change_percent,
            "first_value": first_value,
            "last_value": last_value,
            "sample_count": n,
        }

    def calculate_cost_summary(
        self,
        metrics: list[ProfilerMetrics],
    ) -> dict[str, float]:
        """Calculate cost summary for a set of metrics."""
        costs = [m.estimated_cost_usd for m in metrics if m.estimated_cost_usd is not None]

        if not costs:
            return {
                "total_cost_usd": 0.0,
                "avg_cost_usd": 0.0,
                "max_cost_usd": 0.0,
                "min_cost_usd": 0.0,
            }

        return {
            "total_cost_usd": sum(costs),
            "avg_cost_usd": statistics.mean(costs),
            "max_cost_usd": max(costs),
            "min_cost_usd": min(costs),
            "request_count": len(costs),
        }

    def get_error_summary(
        self,
        metrics: list[ProfilerMetrics],
    ) -> dict[str, int]:
        """Get summary of errors by type."""
        error_counts: dict[str, int] = defaultdict(int)

        for m in metrics:
            if m.status != MetricStatus.SUCCESS:
                error_type = m.error_message or str(m.status)
                error_counts[error_type] += 1

        return dict(error_counts)
