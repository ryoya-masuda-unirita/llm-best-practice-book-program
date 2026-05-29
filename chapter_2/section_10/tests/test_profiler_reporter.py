"""Tests for the ProfilerReporter visualization layer."""

import json
import tempfile
from pathlib import Path

import pytest
from src.model.profiler_metrics import Alert, ProfilerMetrics
from src.service.profiler_reporter import ProfilerReporter


class TestSummaryReport:
    def test_generate_summary_report(self, sample_metrics_list: list[ProfilerMetrics]):
        reporter = ProfilerReporter()
        report = reporter.generate_summary_report(sample_metrics_list)

        assert "Prompt Performance Summary" in report
        assert "LATENCY" in report
        assert "TOKEN USAGE" in report
        assert "SUCCESS RATE" in report
        assert "Mean:" in report
        assert "Median:" in report
        assert "P95:" in report

    def test_generate_summary_report_with_title(self, sample_metrics_list: list[ProfilerMetrics]):
        reporter = ProfilerReporter()
        report = reporter.generate_summary_report(sample_metrics_list, title="Custom Title")

        assert "Custom Title" in report

    def test_generate_summary_report_empty(self):
        reporter = ProfilerReporter()
        report = reporter.generate_summary_report([])

        assert "No metrics available" in report

    def test_generate_summary_with_quality_scores(self, sample_metrics_list: list[ProfilerMetrics]):
        reporter = ProfilerReporter()
        report = reporter.generate_summary_report(sample_metrics_list)

        assert "QUALITY SCORES" in report
        assert "Average:" in report

    def test_generate_summary_with_costs(self, sample_metrics_list: list[ProfilerMetrics]):
        reporter = ProfilerReporter()
        report = reporter.generate_summary_report(sample_metrics_list)

        assert "COST ESTIMATE" in report
        assert "Total:" in report


class TestComparisonReport:
    def test_generate_comparison_report(self, mixed_prompt_metrics: list[ProfilerMetrics]):
        reporter = ProfilerReporter()
        report = reporter.generate_prompt_comparison_report(
            mixed_prompt_metrics,
            prompt_ids=["prompt_a", "prompt_b", "prompt_c"],
        )

        assert "Prompt Comparison Report" in report
        assert "prompt_a" in report
        assert "prompt_b" in report
        assert "prompt_c" in report
        assert "Avg Latency" in report
        assert "Success Rate" in report

    def test_generate_comparison_report_empty(self):
        reporter = ProfilerReporter()
        report = reporter.generate_prompt_comparison_report(
            [],
            prompt_ids=["nonexistent"],
        )

        assert "No data available" in report


class TestTrendReport:
    def test_generate_trend_report(self, sample_metrics_list: list[ProfilerMetrics]):
        reporter = ProfilerReporter()
        report = reporter.generate_trend_report(sample_metrics_list)

        assert "Performance Trend Report" in report
        assert "LATENCY TREND" in report
        assert "TOKEN USAGE TREND" in report
        assert "TIME SERIES DATA" in report

    def test_generate_trend_report_empty(self):
        reporter = ProfilerReporter()
        report = reporter.generate_trend_report([])

        assert "No data available" in report


class TestAlertReport:
    def test_generate_alert_report(self):
        reporter = ProfilerReporter()

        alerts = [
            Alert(
                prompt_id="test",
                severity="critical",
                metric_name="latency_ms",
                metric_value=10000.0,
                threshold_value=5000.0,
                message="Critical latency detected",
            ),
            Alert(
                prompt_id="test",
                severity="warning",
                metric_name="quality_score",
                metric_value=2.5,
                threshold_value=3.0,
                message="Low quality warning",
            ),
        ]

        report = reporter.generate_alert_report(alerts)

        assert "Performance Alerts" in report
        assert "CRITICAL ALERTS" in report
        assert "WARNING ALERTS" in report
        assert "Critical latency detected" in report
        assert "Low quality warning" in report

    def test_generate_alert_report_empty(self):
        reporter = ProfilerReporter()
        report = reporter.generate_alert_report([])

        assert "No alerts to report" in report


class TestJsonReport:
    def test_generate_json_report(self, sample_metrics_list: list[ProfilerMetrics]):
        reporter = ProfilerReporter()
        report = reporter.generate_json_report(sample_metrics_list)

        assert "generated_at" in report
        assert "sample_count" in report
        assert "summary" in report
        assert "by_prompt" in report
        assert "by_model" in report
        assert "by_provider" in report
        assert "cost_summary" in report
        assert "error_summary" in report

    def test_generate_json_report_with_raw_metrics(self, sample_metrics_list: list[ProfilerMetrics]):
        reporter = ProfilerReporter()
        report = reporter.generate_json_report(sample_metrics_list, include_raw_metrics=True)

        assert "raw_metrics" in report
        assert len(report["raw_metrics"]) == len(sample_metrics_list)

    def test_generate_json_report_empty(self):
        reporter = ProfilerReporter()
        report = reporter.generate_json_report([])

        assert report["sample_count"] == 0
        assert report["summary"] is None

    def test_json_report_is_valid_json(self, sample_metrics_list: list[ProfilerMetrics]):
        reporter = ProfilerReporter()
        report = reporter.generate_json_report(sample_metrics_list)

        json_str = json.dumps(report)
        assert json_str is not None

        parsed = json.loads(json_str)
        assert parsed["sample_count"] == report["sample_count"]


class TestHtmlReport:
    def test_generate_html_report(self, sample_metrics_list: list[ProfilerMetrics]):
        reporter = ProfilerReporter()
        html = reporter.generate_html_report(sample_metrics_list)

        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "Prompt Performance Dashboard" in html
        assert "Summary" in html
        assert "Total Requests" in html
        assert "Avg Latency" in html

    def test_generate_html_report_with_title(self, sample_metrics_list: list[ProfilerMetrics]):
        reporter = ProfilerReporter()
        html = reporter.generate_html_report(sample_metrics_list, title="Custom Dashboard")

        assert "Custom Dashboard" in html

    def test_html_report_includes_tables(self, sample_metrics_list: list[ProfilerMetrics]):
        reporter = ProfilerReporter()
        html = reporter.generate_html_report(sample_metrics_list)

        assert "<table>" in html
        assert "By Prompt" in html
        assert "By Model" in html
        assert "By Provider" in html


class TestSaveReport:
    def test_save_json_report(self, sample_metrics_list: list[ProfilerMetrics]):
        reporter = ProfilerReporter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.json"
            reporter.save_report(sample_metrics_list, output_path, format="json")

            assert output_path.exists()

            with open(output_path) as f:
                data = json.load(f)
                assert "sample_count" in data

    def test_save_html_report(self, sample_metrics_list: list[ProfilerMetrics]):
        reporter = ProfilerReporter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            reporter.save_report(sample_metrics_list, output_path, format="html")

            assert output_path.exists()

            with open(output_path) as f:
                content = f.read()
                assert "<!DOCTYPE html>" in content

    def test_save_txt_report(self, sample_metrics_list: list[ProfilerMetrics]):
        reporter = ProfilerReporter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.txt"
            reporter.save_report(sample_metrics_list, output_path, format="txt")

            assert output_path.exists()

            with open(output_path) as f:
                content = f.read()
                assert "LATENCY" in content

    def test_save_report_creates_directories(self, sample_metrics_list: list[ProfilerMetrics]):
        reporter = ProfilerReporter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dirs" / "report.json"
            reporter.save_report(sample_metrics_list, output_path, format="json")

            assert output_path.exists()

    def test_save_report_invalid_format(self, sample_metrics_list: list[ProfilerMetrics]):
        reporter = ProfilerReporter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.xyz"

            with pytest.raises(ValueError, match="Unsupported format"):
                reporter.save_report(sample_metrics_list, output_path, format="xyz")
