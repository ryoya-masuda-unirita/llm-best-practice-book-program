"""Profiler Reporter - Visualization layer for prompt performance profiling.

This module implements the third layer of the prompt performance profiling system
as described in CLAUDE.md. It provides reporting and visualization capabilities:
- Text-based reports for terminal output
- JSON reports for programmatic consumption
- HTML reports for visual dashboards
- Comparison reports for A/B testing
- Trend analysis reports

Note: For production use with Grafana/Kibana, the metrics can be exported
using the to_json_string() methods and ingested into those systems.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.logger import make_logger
from src.model.profiler_metrics import Alert, ProfilerMetrics
from src.service.metrics_analyzer import MetricsAnalyzer

logger = make_logger(__name__)


class ProfilerReporter:
    """Reporter for generating profiler reports and visualizations.

    This class provides various report formats:
    - Terminal-friendly text reports
    - JSON reports for API consumption
    - HTML reports for browser viewing
    - Comparison reports for prompt A/B testing
    """

    def __init__(self, analyzer: Optional[MetricsAnalyzer] = None):
        """Initialize the reporter.

        Args:
            analyzer: MetricsAnalyzer instance for data processing
        """
        self.analyzer = analyzer or MetricsAnalyzer()

    def generate_summary_report(
        self,
        metrics: list[ProfilerMetrics],
        title: str = "Prompt Performance Summary",
    ) -> str:
        """Generate a text summary report.

        Args:
            metrics: List of metrics to summarize
            title: Report title

        Returns:
            Formatted text report
        """
        if not metrics:
            return f"{title}\n{'=' * len(title)}\n\nNo metrics available.\n"

        aggregated = self.analyzer.aggregate_metrics(metrics)

        lines = [
            title,
            "=" * len(title),
            "",
            f"Report Generated: {datetime.now(timezone.utc).isoformat()}",
            f"Sample Count: {aggregated.sample_count}",
            f"Time Range: {aggregated.start_time} to {aggregated.end_time}",
            "",
            "LATENCY",
            "-" * 40,
            f"  Mean:    {aggregated.latency_mean_ms:,.2f} ms",
            f"  Median:  {aggregated.latency_median_ms:,.2f} ms",
            f"  P95:     {aggregated.latency_p95_ms:,.2f} ms",
            f"  P99:     {aggregated.latency_p99_ms:,.2f} ms",
            f"  Min:     {aggregated.latency_min_ms:,.2f} ms",
            f"  Max:     {aggregated.latency_max_ms:,.2f} ms",
            f"  Std Dev: {aggregated.latency_std_ms:,.2f} ms",
            "",
            "TOKEN USAGE",
            "-" * 40,
            f"  Total Input:   {aggregated.total_input_tokens:,}",
            f"  Total Output:  {aggregated.total_output_tokens:,}",
            f"  Total:         {aggregated.total_tokens:,}",
            f"  Avg Input:     {aggregated.avg_input_tokens:,.1f}",
            f"  Avg Output:    {aggregated.avg_output_tokens:,.1f}",
            "",
            "SUCCESS RATE",
            "-" * 40,
            f"  Successful:  {aggregated.success_count}",
            f"  Failed:      {aggregated.error_count}",
            f"  Rate:        {aggregated.success_rate:.1%}",
        ]

        if aggregated.avg_quality_score is not None:
            lines.extend(
                [
                    "",
                    "QUALITY SCORES",
                    "-" * 40,
                    f"  Average: {aggregated.avg_quality_score:.2f} / 5.0",
                    f"  Min:     {aggregated.min_quality_score:.2f} / 5.0",
                    f"  Max:     {aggregated.max_quality_score:.2f} / 5.0",
                ]
            )

        if aggregated.total_estimated_cost_usd is not None:
            lines.extend(
                [
                    "",
                    "COST ESTIMATE",
                    "-" * 40,
                    f"  Total: ${aggregated.total_estimated_cost_usd:,.4f}",
                    f"  Avg:   ${aggregated.total_estimated_cost_usd / aggregated.sample_count:,.4f} per request",
                ]
            )

        lines.append("")
        return "\n".join(lines)

    def generate_prompt_comparison_report(
        self,
        metrics: list[ProfilerMetrics],
        prompt_ids: list[str],
        title: str = "Prompt Comparison Report",
    ) -> str:
        """Generate a comparison report for multiple prompts.

        Args:
            metrics: List of metrics to analyze
            prompt_ids: List of prompt IDs to compare
            title: Report title

        Returns:
            Formatted text report
        """
        comparison = self.analyzer.compare_prompts(metrics, prompt_ids)

        if not comparison:
            return f"{title}\n{'=' * len(title)}\n\nNo data available for comparison.\n"

        lines = [
            title,
            "=" * len(title),
            "",
            f"Report Generated: {datetime.now(timezone.utc).isoformat()}",
            "",
        ]

        col_width = 20
        headers = ["Metric", *list(comparison.keys())]
        header_row = " | ".join(h[:col_width].ljust(col_width) for h in headers)
        lines.append(header_row)
        lines.append("-" * len(header_row))

        metric_labels = [
            ("sample_count", "Samples"),
            ("latency_mean_ms", "Avg Latency (ms)"),
            ("latency_p95_ms", "P95 Latency (ms)"),
            ("avg_tokens", "Avg Tokens"),
            ("success_rate", "Success Rate"),
            ("avg_quality", "Avg Quality"),
            ("total_cost", "Total Cost ($)"),
        ]

        for metric_key, label in metric_labels:
            row_values = [label]
            for prompt_id in comparison:
                value = comparison[prompt_id].get(metric_key, 0)
                if metric_key == "success_rate":
                    row_values.append(f"{value:.1%}")
                elif metric_key in ["latency_mean_ms", "latency_p95_ms", "avg_quality"]:
                    row_values.append(f"{value:.2f}")
                elif metric_key == "total_cost":
                    row_values.append(f"${value:.4f}")
                else:
                    row_values.append(f"{value:,.0f}")

            row = " | ".join(str(v)[:col_width].ljust(col_width) for v in row_values)
            lines.append(row)

        lines.append("")
        return "\n".join(lines)

    def generate_trend_report(
        self,
        metrics: list[ProfilerMetrics],
        bucket_minutes: int = 60,
        title: str = "Performance Trend Report",
    ) -> str:
        """Generate a trend analysis report.

        Args:
            metrics: List of metrics to analyze
            bucket_minutes: Time bucket size in minutes
            title: Report title

        Returns:
            Formatted text report
        """
        time_series = self.analyzer.aggregate_by_time_bucket(metrics, bucket_minutes)

        if not time_series:
            return f"{title}\n{'=' * len(title)}\n\nNo data available for trend analysis.\n"

        latency_trend = self.analyzer.detect_trend(time_series, "latency_mean_ms")
        token_trend = self.analyzer.detect_trend(time_series, "avg_input_tokens")

        lines = [
            title,
            "=" * len(title),
            "",
            f"Report Generated: {datetime.now(timezone.utc).isoformat()}",
            f"Bucket Size: {bucket_minutes} minutes",
            f"Total Buckets: {len(time_series)}",
            "",
            "LATENCY TREND",
            "-" * 40,
            f"  First: {latency_trend.get('first_value', 0):,.2f} ms",
            f"  Last:  {latency_trend.get('last_value', 0):,.2f} ms",
            f"  Change: {latency_trend.get('change_percent', 0):+.1f}%",
            f"  Trend:  {'Increasing' if latency_trend.get('trend', 0) > 0 else 'Decreasing' if latency_trend.get('trend', 0) < 0 else 'Stable'}",
            "",
            "TOKEN USAGE TREND",
            "-" * 40,
            f"  First: {token_trend.get('first_value', 0):,.1f} tokens",
            f"  Last:  {token_trend.get('last_value', 0):,.1f} tokens",
            f"  Change: {token_trend.get('change_percent', 0):+.1f}%",
            "",
            "TIME SERIES DATA",
            "-" * 40,
        ]

        for bucket_time, agg in sorted(time_series.items()):
            lines.append(
                f"  {bucket_time[:19]}: "
                f"n={agg.sample_count:3d}, "
                f"lat={agg.latency_mean_ms:7.1f}ms, "
                f"tokens={agg.avg_input_tokens + agg.avg_output_tokens:6.0f}, "
                f"success={agg.success_rate:.0%}"
            )

        lines.append("")
        return "\n".join(lines)

    def generate_alert_report(
        self,
        alerts: list[Alert],
        title: str = "Performance Alerts",
    ) -> str:
        """Generate a report of alerts.

        Args:
            alerts: List of alerts to report
            title: Report title

        Returns:
            Formatted text report
        """
        lines = [
            title,
            "=" * len(title),
            "",
            f"Report Generated: {datetime.now(timezone.utc).isoformat()}",
            f"Total Alerts: {len(alerts)}",
            "",
        ]

        if not alerts:
            lines.append("No alerts to report.")
            lines.append("")
            return "\n".join(lines)

        critical_alerts = [a for a in alerts if a.severity == "critical"]
        warning_alerts = [a for a in alerts if a.severity == "warning"]

        if critical_alerts:
            lines.extend(
                [
                    "CRITICAL ALERTS",
                    "-" * 40,
                ]
            )
            for alert in critical_alerts:
                lines.append(f"  [{alert.timestamp[:19]}] {alert.message}")
            lines.append("")

        if warning_alerts:
            lines.extend(
                [
                    "WARNING ALERTS",
                    "-" * 40,
                ]
            )
            for alert in warning_alerts:
                lines.append(f"  [{alert.timestamp[:19]}] {alert.message}")
            lines.append("")

        return "\n".join(lines)

    def generate_json_report(
        self,
        metrics: list[ProfilerMetrics],
        include_raw_metrics: bool = False,
    ) -> dict:
        """Generate a JSON report.

        Args:
            metrics: List of metrics to analyze
            include_raw_metrics: Whether to include raw metrics data

        Returns:
            Dictionary containing the report data
        """
        if not metrics:
            return {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "sample_count": 0,
                "summary": None,
                "by_prompt": {},
                "by_model": {},
                "by_provider": {},
            }

        aggregated = self.analyzer.aggregate_metrics(metrics)
        by_prompt = self.analyzer.aggregate_by_prompt(metrics)
        by_model = self.analyzer.aggregate_by_model(metrics)
        by_provider = self.analyzer.aggregate_by_provider(metrics)
        cost_summary = self.analyzer.calculate_cost_summary(metrics)
        error_summary = self.analyzer.get_error_summary(metrics)

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sample_count": aggregated.sample_count,
            "time_range": {
                "start": aggregated.start_time,
                "end": aggregated.end_time,
            },
            "summary": aggregated.model_dump(exclude_none=True),
            "by_prompt": {pid: agg.model_dump(exclude_none=True) for pid, agg in by_prompt.items()},
            "by_model": {model: agg.model_dump(exclude_none=True) for model, agg in by_model.items()},
            "by_provider": {provider: agg.model_dump(exclude_none=True) for provider, agg in by_provider.items()},
            "cost_summary": cost_summary,
            "error_summary": error_summary,
        }

        if include_raw_metrics:
            report["raw_metrics"] = [m.model_dump(exclude_none=True) for m in metrics]

        return report

    def generate_html_report(
        self,
        metrics: list[ProfilerMetrics],
        title: str = "Prompt Performance Dashboard",
    ) -> str:
        """Generate an HTML report.

        Args:
            metrics: List of metrics to analyze
            title: Report title

        Returns:
            HTML string
        """
        json_data = self.generate_json_report(metrics)
        summary = json_data.get("summary", {})

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .card {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin: 15px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .metric {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
        }}
        .metric-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
        .status-success {{ color: #28a745; }}
        .status-warning {{ color: #ffc107; }}
        .status-error {{ color: #dc3545; }}
        .timestamp {{
            color: #999;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p class="timestamp">Generated: {json_data.get("generated_at", "N/A")}</p>

    <div class="card">
        <h2>Summary</h2>
        <div class="metric-grid">
            <div class="metric">
                <div class="metric-value">{summary.get("sample_count", 0):,}</div>
                <div class="metric-label">Total Requests</div>
            </div>
            <div class="metric">
                <div class="metric-value">{summary.get("latency_mean_ms", 0):,.1f}ms</div>
                <div class="metric-label">Avg Latency</div>
            </div>
            <div class="metric">
                <div class="metric-value">{summary.get("latency_p95_ms", 0):,.1f}ms</div>
                <div class="metric-label">P95 Latency</div>
            </div>
            <div class="metric">
                <div class="metric-value">{summary.get("success_rate", 0) * 100:.1f}%</div>
                <div class="metric-label">Success Rate</div>
            </div>
            <div class="metric">
                <div class="metric-value">{summary.get("total_tokens", 0):,}</div>
                <div class="metric-label">Total Tokens</div>
            </div>
            <div class="metric">
                <div class="metric-value">${json_data.get("cost_summary", {}).get("total_cost_usd", 0):,.4f}</div>
                <div class="metric-label">Total Cost</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>By Prompt</h2>
        <table>
            <tr>
                <th>Prompt ID</th>
                <th>Requests</th>
                <th>Avg Latency</th>
                <th>P95 Latency</th>
                <th>Success Rate</th>
                <th>Avg Quality</th>
            </tr>
"""
        for pid, pdata in json_data.get("by_prompt", {}).items():
            success_class = (
                "status-success"
                if pdata.get("success_rate", 0) >= 0.95
                else "status-warning"
                if pdata.get("success_rate", 0) >= 0.9
                else "status-error"
            )
            quality = pdata.get("avg_quality_score")
            quality_str = f"{quality:.2f}" if quality else "N/A"
            html += f"""            <tr>
                <td>{pid}</td>
                <td>{pdata.get("sample_count", 0):,}</td>
                <td>{pdata.get("latency_mean_ms", 0):,.1f}ms</td>
                <td>{pdata.get("latency_p95_ms", 0):,.1f}ms</td>
                <td class="{success_class}">{pdata.get("success_rate", 0) * 100:.1f}%</td>
                <td>{quality_str}</td>
            </tr>
"""

        html += """        </table>
    </div>

    <div class="card">
        <h2>By Model</h2>
        <table>
            <tr>
                <th>Model</th>
                <th>Requests</th>
                <th>Avg Latency</th>
                <th>Avg Input Tokens</th>
                <th>Avg Output Tokens</th>
            </tr>
"""
        for model, mdata in json_data.get("by_model", {}).items():
            html += f"""            <tr>
                <td>{model}</td>
                <td>{mdata.get("sample_count", 0):,}</td>
                <td>{mdata.get("latency_mean_ms", 0):,.1f}ms</td>
                <td>{mdata.get("avg_input_tokens", 0):,.0f}</td>
                <td>{mdata.get("avg_output_tokens", 0):,.0f}</td>
            </tr>
"""

        html += """        </table>
    </div>

    <div class="card">
        <h2>By Provider</h2>
        <table>
            <tr>
                <th>Provider</th>
                <th>Requests</th>
                <th>Avg Latency</th>
                <th>Success Rate</th>
                <th>Total Cost</th>
            </tr>
"""
        for provider, pdata in json_data.get("by_provider", {}).items():
            html += f"""            <tr>
                <td>{provider}</td>
                <td>{pdata.get("sample_count", 0):,}</td>
                <td>{pdata.get("latency_mean_ms", 0):,.1f}ms</td>
                <td>{pdata.get("success_rate", 0) * 100:.1f}%</td>
                <td>${pdata.get("total_estimated_cost_usd", 0):,.4f}</td>
            </tr>
"""

        html += """        </table>
    </div>

</body>
</html>
"""
        return html

    def save_report(
        self,
        metrics: list[ProfilerMetrics],
        output_path: Path,
        format: str = "json",
        title: str = "Performance Report",
    ) -> None:
        """Save a report to file.

        Args:
            metrics: List of metrics to analyze
            output_path: Path to save the report
            format: Report format ('json', 'html', 'txt')
            title: Report title
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            report = self.generate_json_report(metrics)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

        elif format == "html":
            report = self.generate_html_report(metrics, title)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)

        elif format == "txt":
            report = self.generate_summary_report(metrics, title)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)

        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info(f"Report saved to: {output_path}")

    def print_summary(self, metrics: list[ProfilerMetrics]) -> None:
        """Print a summary report to stdout.

        Args:
            metrics: List of metrics to summarize
        """
        print(self.generate_summary_report(metrics))

    def print_alerts(self, alerts: list[Alert]) -> None:
        """Print alerts to stdout.

        Args:
            alerts: List of alerts to print
        """
        print(self.generate_alert_report(alerts))
