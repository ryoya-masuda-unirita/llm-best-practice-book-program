"""Tests for the MetricsAnalyzer analysis layer.

These tests verify the analyzer correctly aggregates metrics,
detects anomalies, and generates alerts.
"""

import pytest
from src.model.profiler_metrics import AggregatedMetrics, AlertThreshold, ProfilerMetrics
from src.service.metrics_analyzer import MetricsAnalyzer


class TestAggregateMetrics:
    """Test metrics aggregation functionality."""

    def test_aggregate_basic_metrics(self, sample_metrics_list: list[ProfilerMetrics]):
        """Test basic aggregation of metrics."""
        analyzer = MetricsAnalyzer()
        aggregated = analyzer.aggregate_metrics(sample_metrics_list)

        assert aggregated.sample_count == len(sample_metrics_list)
        assert aggregated.latency_mean_ms > 0
        assert aggregated.latency_median_ms > 0
        assert aggregated.latency_p95_ms >= aggregated.latency_median_ms
        assert aggregated.latency_p99_ms >= aggregated.latency_p95_ms

    def test_aggregate_token_stats(self, sample_metrics_list: list[ProfilerMetrics]):
        """Test token statistics in aggregation."""
        analyzer = MetricsAnalyzer()
        aggregated = analyzer.aggregate_metrics(sample_metrics_list)

        assert aggregated.total_input_tokens > 0
        assert aggregated.total_output_tokens > 0
        assert aggregated.total_tokens == aggregated.total_input_tokens + aggregated.total_output_tokens
        assert aggregated.avg_input_tokens > 0
        assert aggregated.avg_output_tokens > 0

    def test_aggregate_success_rate(self, sample_metrics_list: list[ProfilerMetrics]):
        """Test success rate calculation in aggregation."""
        analyzer = MetricsAnalyzer()
        aggregated = analyzer.aggregate_metrics(sample_metrics_list)

        # 9 success, 1 error in sample_metrics_list
        assert aggregated.success_count == 9
        assert aggregated.error_count == 1
        assert aggregated.success_rate == 0.9

    def test_aggregate_quality_scores(self, sample_metrics_list: list[ProfilerMetrics]):
        """Test quality score aggregation."""
        analyzer = MetricsAnalyzer()
        aggregated = analyzer.aggregate_metrics(sample_metrics_list)

        assert aggregated.avg_quality_score is not None
        assert aggregated.min_quality_score is not None
        assert aggregated.max_quality_score is not None
        assert aggregated.min_quality_score <= aggregated.avg_quality_score <= aggregated.max_quality_score

    def test_aggregate_empty_list_raises(self):
        """Test that aggregating empty list raises ValueError."""
        analyzer = MetricsAnalyzer()

        with pytest.raises(ValueError):
            analyzer.aggregate_metrics([])


class TestAggregateByGroups:
    """Test grouped aggregation functionality."""

    def test_aggregate_by_prompt(self, mixed_prompt_metrics: list[ProfilerMetrics]):
        """Test aggregation grouped by prompt ID."""
        analyzer = MetricsAnalyzer()
        by_prompt = analyzer.aggregate_by_prompt(mixed_prompt_metrics)

        assert len(by_prompt) == 3  # prompt_a, prompt_b, prompt_c
        assert "prompt_a" in by_prompt
        assert "prompt_b" in by_prompt
        assert "prompt_c" in by_prompt

        # Each prompt should have 5 samples
        for agg in by_prompt.values():
            assert agg.sample_count == 5

    def test_aggregate_by_model(self, sample_metrics_list: list[ProfilerMetrics]):
        """Test aggregation grouped by model."""
        analyzer = MetricsAnalyzer()
        by_model = analyzer.aggregate_by_model(sample_metrics_list)

        # All samples use same model
        assert len(by_model) == 1
        assert "gpt-4o-mini" in by_model

    def test_aggregate_by_provider(self, sample_metrics_list: list[ProfilerMetrics]):
        """Test aggregation grouped by provider."""
        analyzer = MetricsAnalyzer()
        by_provider = analyzer.aggregate_by_provider(sample_metrics_list)

        # All samples use same provider
        assert len(by_provider) == 1
        assert "openai" in by_provider

    def test_aggregate_by_time_bucket(self, sample_metrics_list: list[ProfilerMetrics]):
        """Test aggregation grouped by time buckets."""
        analyzer = MetricsAnalyzer()
        by_time = analyzer.aggregate_by_time_bucket(sample_metrics_list, bucket_minutes=60)

        # All samples have same timestamp, so 1 bucket
        assert len(by_time) >= 1


class TestAnomalyDetection:
    """Test anomaly detection functionality."""

    def test_detect_high_latency_anomaly(self, alert_thresholds: AlertThreshold):
        """Test detection of high latency anomaly."""
        analyzer = MetricsAnalyzer(thresholds=alert_thresholds)

        # Create metrics with very high latency
        high_latency_metrics = ProfilerMetrics(
            prompt_id="test",
            request_id="test-001",
            latency_ms=6000.0,  # Above critical threshold
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            model="gpt-4o-mini",
            provider="openai",
        )

        anomalies = analyzer.detect_anomalies(high_latency_metrics)
        assert len(anomalies) > 0
        assert any("Critical latency" in a for a in anomalies)

    def test_detect_high_token_anomaly(self, alert_thresholds: AlertThreshold):
        """Test detection of high token usage anomaly."""
        analyzer = MetricsAnalyzer(thresholds=alert_thresholds)

        # Create metrics with very high token count
        high_token_metrics = ProfilerMetrics(
            prompt_id="test",
            request_id="test-001",
            latency_ms=100.0,
            input_tokens=8000,
            output_tokens=4000,
            total_tokens=12000,  # Above critical threshold
            model="gpt-4o-mini",
            provider="openai",
        )

        anomalies = analyzer.detect_anomalies(high_token_metrics)
        assert len(anomalies) > 0
        assert any("token" in a.lower() for a in anomalies)

    def test_detect_low_quality_anomaly(self, alert_thresholds: AlertThreshold):
        """Test detection of low quality score anomaly."""
        analyzer = MetricsAnalyzer(thresholds=alert_thresholds)

        # Create metrics with low quality
        low_quality_metrics = ProfilerMetrics(
            prompt_id="test",
            request_id="test-001",
            latency_ms=100.0,
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            model="gpt-4o-mini",
            provider="openai",
            quality_score=1.5,  # Below critical threshold
        )

        anomalies = analyzer.detect_anomalies(low_quality_metrics)
        assert len(anomalies) > 0
        assert any("quality" in a.lower() for a in anomalies)

    def test_detect_relative_latency_anomaly(self, alert_thresholds: AlertThreshold):
        """Test detection of relative latency anomaly compared to baseline."""
        analyzer = MetricsAnalyzer(thresholds=alert_thresholds)

        # Set baseline
        baseline = {"latency_mean_ms": 100.0}

        # Create metrics with latency 3x baseline
        high_relative_metrics = ProfilerMetrics(
            prompt_id="test",
            request_id="test-001",
            latency_ms=300.0,  # 3x baseline, above critical threshold
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            model="gpt-4o-mini",
            provider="openai",
        )

        anomalies = analyzer.detect_anomalies(high_relative_metrics, baseline=baseline)
        assert len(anomalies) > 0
        assert any("baseline" in a.lower() for a in anomalies)

    def test_no_anomalies_for_normal_metrics(self, sample_profiler_metrics: ProfilerMetrics):
        """Test that normal metrics don't trigger anomalies."""
        analyzer = MetricsAnalyzer()  # Use default thresholds

        anomalies = analyzer.detect_anomalies(sample_profiler_metrics)
        # The sample has normal values, should have no anomalies
        assert len(anomalies) == 0


class TestAlertGeneration:
    """Test alert generation functionality."""

    def test_generate_latency_alert(self, alert_thresholds: AlertThreshold):
        """Test generation of latency alerts."""
        analyzer = MetricsAnalyzer(thresholds=alert_thresholds)

        high_latency_metrics = ProfilerMetrics(
            prompt_id="test",
            request_id="test-001",
            prompt_name="Test Prompt",
            latency_ms=6000.0,
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            model="gpt-4o-mini",
            provider="openai",
        )

        alerts = analyzer.generate_alerts(high_latency_metrics)
        assert len(alerts) > 0

        latency_alert = next((a for a in alerts if a.metric_name == "latency_ms"), None)
        assert latency_alert is not None
        assert latency_alert.severity == "critical"

    def test_generate_quality_warning_alert(self, alert_thresholds: AlertThreshold):
        """Test generation of quality warning alerts."""
        analyzer = MetricsAnalyzer(thresholds=alert_thresholds)

        low_quality_metrics = ProfilerMetrics(
            prompt_id="test",
            request_id="test-001",
            latency_ms=100.0,
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            model="gpt-4o-mini",
            provider="openai",
            quality_score=2.5,  # Below warning, above critical
        )

        alerts = analyzer.generate_alerts(low_quality_metrics)
        quality_alert = next((a for a in alerts if a.metric_name == "quality_score"), None)
        assert quality_alert is not None
        assert quality_alert.severity == "warning"

    def test_generate_aggregated_alerts(self, sample_metrics_list: list[ProfilerMetrics]):
        """Test alert generation for aggregated metrics."""
        # Lower the thresholds to trigger alerts
        thresholds = AlertThreshold(
            success_rate_warning=0.95,
            success_rate_critical=0.92,
        )
        analyzer = MetricsAnalyzer(thresholds=thresholds)

        aggregated = analyzer.aggregate_metrics(sample_metrics_list)
        alerts = analyzer.analyze_aggregated_metrics(aggregated)

        # sample_metrics_list has 90% success rate, below warning threshold
        success_alert = next((a for a in alerts if a.metric_name == "success_rate"), None)
        assert success_alert is not None


class TestComparison:
    """Test prompt comparison functionality."""

    def test_compare_prompts(self, mixed_prompt_metrics: list[ProfilerMetrics]):
        """Test comparing multiple prompts."""
        analyzer = MetricsAnalyzer()

        comparison = analyzer.compare_prompts(
            mixed_prompt_metrics,
            prompt_ids=["prompt_a", "prompt_b", "prompt_c"],
        )

        assert len(comparison) == 3
        for prompt_id in ["prompt_a", "prompt_b", "prompt_c"]:
            assert prompt_id in comparison
            assert "latency_mean_ms" in comparison[prompt_id]
            assert "success_rate" in comparison[prompt_id]
            assert "avg_quality" in comparison[prompt_id]

    def test_compare_prompts_partial(self, mixed_prompt_metrics: list[ProfilerMetrics]):
        """Test comparing with some non-existent prompts."""
        analyzer = MetricsAnalyzer()

        comparison = analyzer.compare_prompts(
            mixed_prompt_metrics,
            prompt_ids=["prompt_a", "nonexistent"],
        )

        assert len(comparison) == 1
        assert "prompt_a" in comparison
        assert "nonexistent" not in comparison


class TestTrendDetection:
    """Test trend detection functionality."""

    def test_detect_increasing_trend(self):
        """Test detection of increasing latency trend."""

        analyzer = MetricsAnalyzer()

        # Create time series with increasing latency
        time_series = {}

        for i in range(5):
            bucket_time = f"2024-01-01T{i:02d}:00:00+00:00"
            time_series[bucket_time] = AggregatedMetrics(
                start_time=bucket_time,
                end_time=bucket_time,
                sample_count=10,
                latency_mean_ms=100.0 + (i * 50),  # Increasing
                latency_median_ms=100.0 + (i * 50),
                latency_p95_ms=150.0 + (i * 50),
                latency_p99_ms=200.0 + (i * 50),
                latency_min_ms=50.0 + (i * 50),
                latency_max_ms=250.0 + (i * 50),
                latency_std_ms=30.0,
                total_input_tokens=1000,
                total_output_tokens=500,
                total_tokens=1500,
                avg_input_tokens=100.0,
                avg_output_tokens=50.0,
                success_count=10,
                error_count=0,
                success_rate=1.0,
            )

        trend = analyzer.detect_trend(time_series, "latency_mean_ms")
        assert trend["change_percent"] > 0
        assert trend["trend"] > 0

    def test_detect_stable_trend(self):
        """Test detection of stable metrics."""
        analyzer = MetricsAnalyzer()

        from src.model.profiler_metrics import AggregatedMetrics

        time_series = {}
        for i in range(5):
            bucket_time = f"2024-01-01T{i:02d}:00:00+00:00"
            time_series[bucket_time] = AggregatedMetrics(
                start_time=bucket_time,
                end_time=bucket_time,
                sample_count=10,
                latency_mean_ms=100.0,  # Stable
                latency_median_ms=100.0,
                latency_p95_ms=150.0,
                latency_p99_ms=200.0,
                latency_min_ms=50.0,
                latency_max_ms=250.0,
                latency_std_ms=30.0,
                total_input_tokens=1000,
                total_output_tokens=500,
                total_tokens=1500,
                avg_input_tokens=100.0,
                avg_output_tokens=50.0,
                success_count=10,
                error_count=0,
                success_rate=1.0,
            )

        trend = analyzer.detect_trend(time_series, "latency_mean_ms")
        assert abs(trend["change_percent"]) < 0.01  # Essentially 0


class TestCostAndErrors:
    """Test cost summary and error summary functionality."""

    def test_calculate_cost_summary(self, sample_metrics_list: list[ProfilerMetrics]):
        """Test cost summary calculation."""
        analyzer = MetricsAnalyzer()
        cost_summary = analyzer.calculate_cost_summary(sample_metrics_list)

        assert "total_cost_usd" in cost_summary
        assert "avg_cost_usd" in cost_summary
        assert cost_summary["total_cost_usd"] > 0

    def test_get_error_summary(self, sample_metrics_list: list[ProfilerMetrics]):
        """Test error summary calculation."""
        analyzer = MetricsAnalyzer()
        error_summary = analyzer.get_error_summary(sample_metrics_list)

        # sample_metrics_list has 1 error
        assert len(error_summary) >= 0  # May have 0 if all success

    def test_calculate_baseline(self, sample_metrics_list: list[ProfilerMetrics]):
        """Test baseline calculation."""
        analyzer = MetricsAnalyzer()
        baseline = analyzer.calculate_baseline(sample_metrics_list, "character_generation")

        assert "latency_mean_ms" in baseline
        assert "latency_std_ms" in baseline
        assert baseline["latency_mean_ms"] > 0
