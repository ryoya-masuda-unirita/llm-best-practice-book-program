"""Analyzer for evaluating prompts and extracting reusable patterns."""

from datetime import datetime
from typing import Optional

from src.logger import make_logger
from src.model.prompt_log import EvaluationCriteria, EvaluationStatus, PromptLog
from src.model.prompt_template import AntiPattern, PromptTemplate
from src.service.prompt_storage import PromptStorage

logger = make_logger(__name__)


class PromptAnalyzer:
    """
    Analyzer for evaluating prompt effectiveness and creating templates.

    This class implements the core logic for analyzing prompt success/failure
    and converting successful prompts into reusable templates.
    """

    def __init__(self, storage: PromptStorage):
        """
        Initialize the analyzer.

        Args:
            storage: PromptStorage instance for data persistence
        """
        self.storage = storage
        logger.info("Initialized PromptAnalyzer")

    def evaluate_log(
        self,
        log: PromptLog,
        evaluation: EvaluationCriteria,
        status: EvaluationStatus,
        failure_reason: Optional[str] = None,
    ) -> PromptLog:
        """
        Evaluate a prompt log and update its status.

        Args:
            log: PromptLog to evaluate
            evaluation: EvaluationCriteria with scores
            status: Overall evaluation status
            failure_reason: Reason for failure if applicable

        Returns:
            Updated PromptLog
        """
        updated_data = log.to_dict()
        updated_data["evaluation"] = evaluation.model_dump()
        updated_data["evaluation_status"] = status
        if failure_reason:
            updated_data["failure_reason"] = failure_reason

        updated_log = PromptLog(**updated_data)

        self.storage.save_log(updated_log)

        logger.info(f"Evaluated log {log.log_id}: {status} (score: {updated_log.get_overall_score()})")
        return updated_log

    def create_template_from_log(
        self,
        log: PromptLog,
        template_name: str,
        description: str,
        required_variables: list[str],
        optional_variables: Optional[list[str]] = None,
    ) -> PromptTemplate:
        """
        Create a reusable template from a successful prompt log.

        Args:
            log: PromptLog to convert to template
            template_name: Name for the template
            description: Description of the template
            required_variables: List of required template variables
            optional_variables: List of optional template variables

        Returns:
            Created PromptTemplate
        """
        if log.evaluation_status != EvaluationStatus.SUCCESS:
            logger.warning(f"Creating template from non-successful log {log.log_id} (status: {log.evaluation_status})")

        system_prompt = ""
        user_prompt = ""
        for message in log.messages:
            if message.get("role") == "system":
                system_prompt = message.get("content", "")
            elif message.get("role") == "user":
                user_prompt = message.get("content", "")

        template = PromptTemplate(
            name=template_name,
            description=description,
            category=log.metadata.category,
            tags=log.metadata.tags,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            required_variables=required_variables,
            optional_variables=optional_variables or [],
            recommended_models=[log.metadata.model_name],
            recommended_temperature=log.metadata.temperature,
            success_count=1,
            failure_count=0,
            average_score=log.get_overall_score(),
            created_by=log.metadata.user_id,
            use_case_examples=[log.metadata.use_case],
            notes=f"Created from log {log.log_id}",
        )

        template_id = self.storage.save_template(template)
        logger.info(f"Created template '{template_name}' of {template_id} from log {log.log_id}")

        return template

    def update_template_stats(
        self,
        template_id: str,
        success: bool,
        score: Optional[float] = None,
    ) -> Optional[PromptTemplate]:
        """
        Update template statistics based on usage.

        Args:
            template_id: Template ID to update
            success: Whether the usage was successful
            score: Evaluation score if available

        Returns:
            Updated PromptTemplate or None if not found
        """
        template = self.storage.get_template(template_id)
        if not template:
            logger.warning(f"Template {template_id} not found")
            return None

        new_success_count = template.success_count + 1 if success else template.success_count
        new_failure_count = template.failure_count if success else template.failure_count + 1

        new_average_score = template.average_score
        if score is not None:
            if template.average_score is None:
                new_average_score = score
            else:
                total_uses = template.success_count + template.failure_count
                new_average_score = (template.average_score * total_uses + score) / (total_uses + 1)

        updated_data = template.to_dict()
        updated_data["success_count"] = new_success_count
        updated_data["failure_count"] = new_failure_count
        updated_data["average_score"] = new_average_score
        updated_data["updated_at"] = datetime.now()

        updated_template = PromptTemplate(**updated_data)
        self.storage.save_template(updated_template)

        logger.info(f"Updated template {template_id}: success_rate={updated_template.get_success_rate():.2%}")
        return updated_template

    def create_antipattern_from_log(
        self,
        log: PromptLog,
        pattern_name: str,
        failure_reason: str,
        recommended_fix: Optional[str] = None,
        severity: str = "medium",
    ) -> AntiPattern:
        """
        Create an anti-pattern from a failed prompt log.

        Args:
            log: Failed PromptLog
            pattern_name: Name for the anti-pattern
            failure_reason: Why this pattern fails
            recommended_fix: How to fix this pattern
            severity: Severity level (low, medium, high)

        Returns:
            Created AntiPattern
        """
        if log.evaluation_status == EvaluationStatus.SUCCESS:
            logger.warning(f"Creating anti-pattern from successful log {log.log_id}")

        user_prompt = ""
        for message in log.messages:
            if message.get("role") == "user":
                user_prompt = message.get("content", "")
                break

        antipattern = AntiPattern(
            name=pattern_name,
            description=f"Anti-pattern identified from log {log.log_id}",
            category=log.metadata.category,
            tags=log.metadata.tags,
            prompt_pattern=user_prompt,
            failure_reason=failure_reason,
            occurrence_count=1,
            recommended_fix=recommended_fix,
            severity=severity,
            examples=[log.prompt_text],
            notes=log.failure_reason or "",
        )

        pattern_id = self.storage.save_antipattern(antipattern)
        logger.info(f"Created anti-pattern '{pattern_name}' of {pattern_id} from failed log {log.log_id}")

        return antipattern

    def update_antipattern_occurrence(
        self,
        pattern_id: str,
    ) -> Optional[AntiPattern]:
        """
        Increment occurrence count for an anti-pattern.

        Args:
            pattern_id: Anti-pattern ID to update

        Returns:
            Updated AntiPattern or None if not found
        """
        antipattern = self.storage.get_antipattern(pattern_id)
        if not antipattern:
            logger.warning(f"Anti-pattern {pattern_id} not found")
            return None

        updated_data = antipattern.to_dict()
        updated_data["occurrence_count"] = antipattern.occurrence_count + 1
        updated_data["updated_at"] = datetime.now()

        updated_pattern = AntiPattern(**updated_data)
        self.storage.save_antipattern(updated_pattern)

        logger.info(f"Updated anti-pattern {pattern_id}: occurrences={updated_pattern.occurrence_count}")
        return updated_pattern

    def analyze_prompt_effectiveness(self, category: Optional[str] = None, limit: int = 100) -> dict:
        """
        Analyze prompt effectiveness across logs.

        Args:
            category: Filter by category
            limit: Maximum number of logs to analyze

        Returns:
            Dictionary with analysis results
        """
        if category:
            from src.model.prompt_log import PromptCategory

            logs = self.storage.get_logs_by_category(PromptCategory(category), limit=limit)
        else:
            success_logs = self.storage.get_logs_by_status(EvaluationStatus.SUCCESS, limit=limit // 2)
            failure_logs = self.storage.get_logs_by_status(EvaluationStatus.FAILURE, limit=limit // 2)
            logs = success_logs + failure_logs

        if not logs:
            return {
                "total_logs": 0,
                "success_count": 0,
                "failure_count": 0,
                "success_rate": 0.0,
                "average_score": None,
            }

        success_count = sum(1 for log in logs if log.evaluation_status == EvaluationStatus.SUCCESS)
        failure_count = sum(1 for log in logs if log.evaluation_status == EvaluationStatus.FAILURE)
        scores = [log.get_overall_score() for log in logs if log.get_overall_score()]
        average_score = sum(scores) / len(scores) if scores else None

        return {
            "total_logs": len(logs),
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": success_count / len(logs) if logs else 0.0,
            "average_score": average_score,
            "logs_analyzed": len(logs),
        }

    def find_similar_templates(self, log: PromptLog, min_similarity: float = 0.7) -> list[PromptTemplate]:
        """
        Find similar templates based on category and tags.

        This is a simple implementation. For production, you might want to use
        embedding-based similarity or more sophisticated matching.

        Args:
            log: PromptLog to find similar templates for
            min_similarity: Minimum similarity threshold (0.0-1.0)

        Returns:
            List of similar PromptTemplate entries
        """
        templates = self.storage.list_templates(category=log.metadata.category)

        similar = []
        for template in templates:
            if not log.metadata.tags:
                continue

            tag_overlap = len(set(template.tags).intersection(set(log.metadata.tags)))
            similarity = tag_overlap / len(log.metadata.tags) if log.metadata.tags else 0.0

            if similarity >= min_similarity:
                similar.append(template)

        return similar
