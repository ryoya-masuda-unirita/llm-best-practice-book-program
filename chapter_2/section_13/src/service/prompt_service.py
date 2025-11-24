"""
Integrated prompt management service.

This module provides a unified API for logging, analyzing, and reusing prompts.
It implements the best practice of systematically collecting and analyzing
prompt executions to build a reusable knowledge base.
"""

from pathlib import Path
from typing import Any, Optional

from src.logger import make_logger
from src.model.prompt_log import (
    EvaluationCriteria,
    EvaluationStatus,
    PromptCategory,
    PromptLog,
    PromptMetadata,
)
from src.model.prompt_template import AntiPattern, PromptTemplate
from src.service.prompt_analytics import PromptAnalytics
from src.service.prompt_analyzer import PromptAnalyzer
from src.service.prompt_catalog import PromptCatalog
from src.service.prompt_storage import PromptStorage

logger = make_logger(__name__)


class PromptManagementService:
    """
    Unified service for prompt logging, analysis, and reuse.

    This service implements the complete workflow:
    1. Log all prompts and responses with metadata
    2. Evaluate results based on predefined metrics
    3. Create reusable templates from successful prompts
    4. Track anti-patterns from failed prompts
    5. Provide analytics and recommendations
    """

    def __init__(self, storage_dir: str | Path = "prompt_storage"):
        """
        Initialize the prompt management service.

        Args:
            storage_dir: Directory for storing prompt data
        """
        self.storage = PromptStorage(storage_dir)
        self.analyzer = PromptAnalyzer(self.storage)
        self.catalog = PromptCatalog(self.storage)
        self.analytics = PromptAnalytics(self.storage)

        logger.info("Initialized PromptManagementService")

    # === Logging Methods ===

    def log_prompt_execution(
        self,
        prompt_text: str,
        messages: list[dict[str, str]],
        response_text: str,
        metadata: PromptMetadata,
        parsed_response: Optional[dict[str, Any]] = None,
        template_name: Optional[str] = None,
        template_version: Optional[str] = None,
    ) -> str:
        """
        Log a prompt execution.

        Args:
            prompt_text: The prompt sent to LLM
            messages: Full message list sent to API
            response_text: Raw response from LLM
            metadata: Execution metadata
            parsed_response: Parsed/structured response if applicable
            template_name: Template name if used
            template_version: Template version if used

        Returns:
            Log ID
        """
        log = PromptLog(
            template_name=template_name,
            template_version=template_version,
            prompt_text=prompt_text,
            messages=messages,
            response_text=response_text,
            parsed_response=parsed_response,
            metadata=metadata,
        )

        log_id = self.storage.save_log(log)
        logger.info(f"Logged prompt execution: {log_id}")
        return log_id

    def evaluate_prompt(
        self,
        log_id: str,
        evaluation: EvaluationCriteria,
        status: EvaluationStatus,
        failure_reason: Optional[str] = None,
    ) -> Optional[PromptLog]:
        """
        Evaluate a logged prompt.

        Args:
            log_id: Log ID to evaluate
            evaluation: Evaluation criteria with scores
            status: Overall evaluation status
            failure_reason: Reason for failure if applicable

        Returns:
            Updated PromptLog or None if not found
        """
        log = self.storage.get_log(log_id)
        if not log:
            logger.warning(f"Log {log_id} not found")
            return None

        return self.analyzer.evaluate_log(log, evaluation, status, failure_reason)

    # === Template Management ===

    def create_template_from_success(
        self,
        log_id: str,
        template_name: str,
        description: str,
        required_variables: list[str],
        optional_variables: Optional[list[str]] = None,
    ) -> Optional[PromptTemplate]:
        """
        Create a reusable template from a successful prompt.

        Args:
            log_id: Log ID to convert to template
            template_name: Name for the template
            description: Template description
            required_variables: Required template variables
            optional_variables: Optional template variables

        Returns:
            Created PromptTemplate or None if log not found
        """
        log = self.storage.get_log(log_id)
        if not log:
            logger.warning(f"Log {log_id} not found")
            return None

        return self.analyzer.create_template_from_log(
            log, template_name, description, required_variables, optional_variables
        )

    def record_template_usage(
        self, template_id: str, success: bool, score: Optional[float] = None
    ) -> Optional[PromptTemplate]:
        """
        Record template usage and update statistics.

        Args:
            template_id: Template ID
            success: Whether the usage was successful
            score: Evaluation score if available

        Returns:
            Updated PromptTemplate or None if not found
        """
        return self.analyzer.update_template_stats(template_id, success, score)

    def search_templates(
        self,
        query: Optional[str] = None,
        category: Optional[PromptCategory] = None,
        tags: Optional[list[str]] = None,
        min_success_rate: float = 0.0,
    ) -> list[PromptTemplate]:
        """
        Search for templates.

        Args:
            query: Text search query
            category: Filter by category
            tags: Filter by tags
            min_success_rate: Minimum success rate

        Returns:
            List of matching templates
        """
        return self.catalog.search_templates(query, category, tags, min_success_rate)

    def get_recommended_templates(
        self,
        category: PromptCategory,
        tags: Optional[list[str]] = None,
        limit: int = 5,
    ) -> list[PromptTemplate]:
        """
        Get recommended templates for a use case.

        Args:
            category: Category to filter by
            tags: Optional tags to match
            limit: Maximum number of recommendations

        Returns:
            List of recommended templates
        """
        return self.catalog.get_template_recommendations(category, tags, limit)

    # === Anti-Pattern Management ===

    def create_antipattern_from_failure(
        self,
        log_id: str,
        pattern_name: str,
        failure_reason: str,
        recommended_fix: Optional[str] = None,
        severity: str = "medium",
    ) -> Optional[AntiPattern]:
        """
        Create an anti-pattern from a failed prompt.

        Args:
            log_id: Failed log ID
            pattern_name: Name for the anti-pattern
            failure_reason: Why this pattern fails
            recommended_fix: How to fix this pattern
            severity: Severity level

        Returns:
            Created AntiPattern or None if log not found
        """
        log = self.storage.get_log(log_id)
        if not log:
            logger.warning(f"Log {log_id} not found")
            return None

        return self.analyzer.create_antipattern_from_log(log, pattern_name, failure_reason, recommended_fix, severity)

    def search_antipatterns(
        self,
        query: Optional[str] = None,
        category: Optional[PromptCategory] = None,
        severity: Optional[str] = None,
    ) -> list[AntiPattern]:
        """
        Search for anti-patterns.

        Args:
            query: Text search query
            category: Filter by category
            severity: Filter by severity

        Returns:
            List of matching anti-patterns
        """
        return self.catalog.search_antipatterns(query, category, None, severity)

    # === Analytics and Reporting ===

    def get_performance_summary(self) -> dict:
        """
        Get overall performance summary.

        Returns:
            Dictionary with performance statistics
        """
        return self.analytics.generate_summary_report()

    def get_success_rates(self) -> dict[str, float]:
        """
        Get success rates by category.

        Returns:
            Dictionary mapping category to success rate
        """
        return self.analytics.get_success_rate_by_category()

    def get_improvement_suggestions(self) -> list[dict]:
        """
        Get suggestions for improving prompt performance.

        Returns:
            List of improvement suggestions
        """
        return self.analytics.get_improvement_suggestions()

    def get_cost_analysis(self) -> dict:
        """
        Get cost analysis based on token usage.

        Returns:
            Dictionary with cost statistics
        """
        return self.analytics.get_cost_analysis()

    # === Utility Methods ===

    def get_catalog_summary(self) -> dict:
        """
        Get a summary of the catalog contents.

        Returns:
            Dictionary with catalog statistics
        """
        return self.catalog.get_catalog_summary()

    def export_template(self, template_id: str) -> Optional[dict]:
        """
        Export a template in shareable format.

        Args:
            template_id: Template ID to export

        Returns:
            Template dictionary or None if not found
        """
        return self.catalog.export_template(template_id)
