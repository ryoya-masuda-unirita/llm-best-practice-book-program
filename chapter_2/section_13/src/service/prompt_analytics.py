"""Analytics and reporting for prompt performance."""

from collections import defaultdict
from datetime import datetime

from src.logger import make_logger
from src.model.prompt_log import EvaluationStatus, PromptCategory
from src.service.prompt_storage import PromptStorage

logger = make_logger(__name__)


class PromptAnalytics:
    """
    Analytics service for prompt performance reporting.

    Provides insights into prompt usage, success rates, and trends.
    """

    def __init__(self, storage: PromptStorage):
        """
        Initialize analytics service.

        Args:
            storage: PromptStorage instance
        """
        self.storage = storage
        logger.info("Initialized PromptAnalytics")

    def get_success_rate_by_category(self) -> dict[str, float]:
        """
        Calculate success rates grouped by category.

        Returns:
            Dictionary mapping category to success rate
        """
        results = {}

        for category in PromptCategory:
            logs = self.storage.get_logs_by_category(category, limit=1000)
            if not logs:
                continue

            success_count = sum(1 for log in logs if log.evaluation_status == EvaluationStatus.SUCCESS)
            results[category.value] = success_count / len(logs) if logs else 0.0

        return results

    def get_model_performance(self) -> dict[str, dict]:
        """
        Analyze performance by model.

        Returns:
            Dictionary with model performance statistics
        """
        model_stats = defaultdict(lambda: {"total": 0, "success": 0, "scores": [], "avg_time": []})

        # Collect data from logs
        for category in PromptCategory:
            logs = self.storage.get_logs_by_category(category, limit=1000)
            for log in logs:
                model = log.metadata.model_name
                model_stats[model]["total"] += 1

                if log.evaluation_status == EvaluationStatus.SUCCESS:
                    model_stats[model]["success"] += 1

                score = log.get_overall_score()
                if score is not None:
                    model_stats[model]["scores"].append(score)

                if log.metadata.execution_time_ms:
                    model_stats[model]["avg_time"].append(log.metadata.execution_time_ms)

        # Calculate statistics
        results = {}
        for model, stats in model_stats.items():
            avg_score = sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else None
            avg_time = sum(stats["avg_time"]) / len(stats["avg_time"]) if stats["avg_time"] else None

            results[model] = {
                "total_uses": stats["total"],
                "success_count": stats["success"],
                "success_rate": stats["success"] / stats["total"] if stats["total"] > 0 else 0.0,
                "average_score": avg_score,
                "average_execution_time_ms": avg_time,
            }

        return results

    def get_template_usage_report(self) -> list[dict]:
        """
        Generate a report of template usage and performance.

        Returns:
            List of template statistics
        """
        templates = self.storage.list_templates()
        report = []

        for template in templates:
            total_uses = template.success_count + template.failure_count
            report.append(
                {
                    "template_name": template.name,
                    "template_id": template.template_id,
                    "category": template.category.value,
                    "total_uses": total_uses,
                    "success_count": template.success_count,
                    "failure_count": template.failure_count,
                    "success_rate": template.get_success_rate(),
                    "average_score": template.average_score,
                    "tags": template.tags,
                }
            )

        # Sort by usage
        report.sort(key=lambda x: x["total_uses"], reverse=True)
        return report

    def get_antipattern_report(self) -> list[dict]:
        """
        Generate a report of anti-patterns.

        Returns:
            List of anti-pattern statistics
        """
        antipatterns = self.storage.list_antipatterns()
        report = []

        for pattern in antipatterns:
            report.append(
                {
                    "pattern_name": pattern.name,
                    "pattern_id": pattern.pattern_id,
                    "category": pattern.category.value,
                    "severity": pattern.severity,
                    "occurrence_count": pattern.occurrence_count,
                    "failure_reason": pattern.failure_reason,
                    "recommended_fix": pattern.recommended_fix,
                    "tags": pattern.tags,
                }
            )

        # Sort by severity and occurrence
        severity_order = {"high": 3, "medium": 2, "low": 1}
        report.sort(
            key=lambda x: (severity_order.get(x["severity"], 0), x["occurrence_count"]),
            reverse=True,
        )
        return report

    def get_cost_analysis(self) -> dict:
        """
        Analyze API costs based on token usage.

        Returns:
            Dictionary with cost statistics
        """
        total_cost = 0.0
        total_input_tokens = 0
        total_output_tokens = 0
        cost_by_category = defaultdict(float)

        for category in PromptCategory:
            logs = self.storage.get_logs_by_category(category, limit=1000)
            for log in logs:
                if log.metadata.cost_usd:
                    total_cost += log.metadata.cost_usd
                    cost_by_category[category.value] += log.metadata.cost_usd

                if log.metadata.token_count_input:
                    total_input_tokens += log.metadata.token_count_input
                if log.metadata.token_count_output:
                    total_output_tokens += log.metadata.token_count_output

        return {
            "total_cost_usd": total_cost,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "cost_by_category": dict(cost_by_category),
        }

    def get_improvement_suggestions(self) -> list[dict]:
        """
        Generate suggestions for improving prompt performance.

        Returns:
            List of improvement suggestions
        """
        suggestions = []

        # Check for low-performing templates
        templates = self.storage.list_templates()
        for template in templates:
            if template.get_success_rate() < 0.5 and (template.success_count + template.failure_count) >= 5:
                suggestions.append(
                    {
                        "type": "low_performing_template",
                        "severity": "medium",
                        "template_name": template.name,
                        "template_id": template.template_id,
                        "success_rate": template.get_success_rate(),
                        "suggestion": f"Template '{template.name}' has a low success rate ({template.get_success_rate():.1%}). "
                        "Consider reviewing and updating the template or marking it as an anti-pattern.",
                    }
                )

        # Check for high-occurrence anti-patterns
        antipatterns = self.storage.list_antipatterns()
        for pattern in antipatterns:
            if pattern.occurrence_count >= 5:
                suggestions.append(
                    {
                        "type": "frequent_antipattern",
                        "severity": pattern.severity,
                        "pattern_name": pattern.name,
                        "pattern_id": pattern.pattern_id,
                        "occurrence_count": pattern.occurrence_count,
                        "suggestion": f"Anti-pattern '{pattern.name}' has occurred {pattern.occurrence_count} times. "
                        f"Recommended fix: {pattern.recommended_fix or 'Review and address the underlying issue.'}",
                    }
                )

        # Check for unused templates
        for template in templates:
            total_uses = template.success_count + template.failure_count
            if total_uses == 0:
                suggestions.append(
                    {
                        "type": "unused_template",
                        "severity": "low",
                        "template_name": template.name,
                        "template_id": template.template_id,
                        "suggestion": f"Template '{template.name}' has never been used. "
                        "Consider promoting it or removing it if no longer needed.",
                    }
                )

        return suggestions

    def generate_summary_report(self) -> dict:
        """
        Generate a comprehensive summary report.

        Returns:
            Dictionary with summary statistics
        """
        storage_stats = self.storage.get_statistics()
        success_rates = self.get_success_rate_by_category()
        model_performance = self.get_model_performance()
        cost_analysis = self.get_cost_analysis()
        template_report = self.get_template_usage_report()
        antipattern_report = self.get_antipattern_report()
        suggestions = self.get_improvement_suggestions()

        return {
            "storage_statistics": storage_stats,
            "success_rates_by_category": success_rates,
            "model_performance": model_performance,
            "cost_analysis": cost_analysis,
            "top_templates": template_report[:10],
            "critical_antipatterns": antipattern_report[:10],
            "improvement_suggestions": suggestions,
            "generated_at": datetime.now().isoformat(),
        }
