"""Storage layer for prompt logs, templates, and anti-patterns."""

import json
from pathlib import Path
from typing import Optional

from src.logger import make_logger
from src.model.prompt_log import EvaluationStatus, PromptCategory, PromptLog
from src.model.prompt_template import AntiPattern, PromptTemplate

logger = make_logger(__name__)


class PromptStorage:
    """
    File-based storage system for prompt logs, templates, and anti-patterns.

    This implementation uses JSON files for simplicity, but can be easily
    replaced with a database backend (SQLite, PostgreSQL, etc.) by implementing
    the same interface.
    """

    def __init__(self, storage_dir: str | Path = "prompt_storage"):
        """
        Initialize the storage system.

        Args:
            storage_dir: Directory for storing prompt data
        """
        self.storage_dir = Path(storage_dir)
        self.logs_dir = self.storage_dir / "logs"
        self.templates_dir = self.storage_dir / "templates"
        self.antipatterns_dir = self.storage_dir / "antipatterns"

        # Create directories if they don't exist
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.antipatterns_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized PromptStorage at {self.storage_dir}")

    # === Prompt Log Operations ===

    def save_log(self, log: PromptLog) -> str:
        """
        Save a prompt log entry.

        Args:
            log: PromptLog to save

        Returns:
            The log_id of the saved log
        """
        # Create subdirectory by date for organization
        date_dir = self.logs_dir / log.metadata.timestamp.strftime("%Y-%m-%d")
        date_dir.mkdir(exist_ok=True)

        log_file = date_dir / f"{log.log_id}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log.to_dict(), f, indent=2, ensure_ascii=False, default=str)

        logger.debug(f"Saved prompt log: {log.log_id}")
        return log.log_id

    def get_log(self, log_id: str) -> Optional[PromptLog]:
        """
        Retrieve a prompt log by ID.

        Args:
            log_id: Log ID to retrieve

        Returns:
            PromptLog if found, None otherwise
        """
        # Search in date directories
        for date_dir in sorted(self.logs_dir.iterdir(), reverse=True):
            if not date_dir.is_dir():
                continue

            log_file = date_dir / f"{log_id}.json"
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return PromptLog(**data)

        return None

    def get_logs_by_status(self, status: EvaluationStatus, limit: int = 100) -> list[PromptLog]:
        """
        Get logs filtered by evaluation status.

        Args:
            status: EvaluationStatus to filter by
            limit: Maximum number of logs to return

        Returns:
            List of PromptLog entries
        """
        logs = []
        for date_dir in sorted(self.logs_dir.iterdir(), reverse=True):
            if not date_dir.is_dir():
                continue

            for log_file in sorted(date_dir.glob("*.json"), reverse=True):
                if len(logs) >= limit:
                    return logs

                with open(log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    log = PromptLog(**data)
                    if log.evaluation_status == status:
                        logs.append(log)

        return logs

    def get_logs_by_category(self, category: PromptCategory, limit: int = 100) -> list[PromptLog]:
        """
        Get logs filtered by category.

        Args:
            category: PromptCategory to filter by
            limit: Maximum number of logs to return

        Returns:
            List of PromptLog entries
        """
        logs = []
        for date_dir in sorted(self.logs_dir.iterdir(), reverse=True):
            if not date_dir.is_dir():
                continue

            for log_file in sorted(date_dir.glob("*.json"), reverse=True):
                if len(logs) >= limit:
                    return logs

                with open(log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    log = PromptLog(**data)
                    if log.metadata.category == category:
                        logs.append(log)

        return logs

    # === Template Operations ===

    def save_template(self, template: PromptTemplate) -> str:
        """
        Save a prompt template.

        Args:
            template: PromptTemplate to save

        Returns:
            The template_id of the saved template
        """
        template_file = self.templates_dir / f"{template.template_id}.json"
        with open(template_file, "w", encoding="utf-8") as f:
            json.dump(template.to_dict(), f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Saved template: {template.name} (ID: {template.template_id})")
        return template.template_id

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """
        Retrieve a template by ID.

        Args:
            template_id: Template ID to retrieve

        Returns:
            PromptTemplate if found, None otherwise
        """
        template_file = self.templates_dir / f"{template_id}.json"
        if template_file.exists():
            with open(template_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return PromptTemplate(**data)
        return None

    def get_template_by_name(self, name: str) -> Optional[PromptTemplate]:
        """
        Retrieve a template by name (returns latest version).

        Args:
            name: Template name

        Returns:
            PromptTemplate if found, None otherwise
        """
        for template_file in self.templates_dir.glob("*.json"):
            with open(template_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("name") == name:
                    return PromptTemplate(**data)
        return None

    def list_templates(
        self,
        category: Optional[PromptCategory] = None,
        tags: Optional[list[str]] = None,
        min_success_rate: Optional[float] = None,
    ) -> list[PromptTemplate]:
        """
        List templates with optional filters.

        Args:
            category: Filter by category
            tags: Filter by tags (must have all tags)
            min_success_rate: Minimum success rate filter

        Returns:
            List of PromptTemplate entries
        """
        templates = []
        for template_file in self.templates_dir.glob("*.json"):
            with open(template_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                template = PromptTemplate(**data)

                # Apply filters
                if category and template.category != category:
                    continue
                if tags and not all(tag in template.tags for tag in tags):
                    continue
                if min_success_rate is not None and template.get_success_rate() < min_success_rate:
                    continue

                templates.append(template)

        # Sort by success rate and score
        templates.sort(
            key=lambda t: (
                t.get_success_rate(),
                t.average_score or 0.0,
            ),
            reverse=True,
        )
        return templates

    # === Anti-Pattern Operations ===

    def save_antipattern(self, antipattern: AntiPattern) -> str:
        """
        Save an anti-pattern.

        Args:
            antipattern: AntiPattern to save

        Returns:
            The pattern_id of the saved anti-pattern
        """
        pattern_file = self.antipatterns_dir / f"{antipattern.pattern_id}.json"
        with open(pattern_file, "w", encoding="utf-8") as f:
            json.dump(antipattern.to_dict(), f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Saved anti-pattern: {antipattern.name} (ID: {antipattern.pattern_id})")
        return antipattern.pattern_id

    def get_antipattern(self, pattern_id: str) -> Optional[AntiPattern]:
        """
        Retrieve an anti-pattern by ID.

        Args:
            pattern_id: Pattern ID to retrieve

        Returns:
            AntiPattern if found, None otherwise
        """
        pattern_file = self.antipatterns_dir / f"{pattern_id}.json"
        if pattern_file.exists():
            with open(pattern_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AntiPattern(**data)
        return None

    def list_antipatterns(
        self,
        category: Optional[PromptCategory] = None,
        tags: Optional[list[str]] = None,
        severity: Optional[str] = None,
    ) -> list[AntiPattern]:
        """
        List anti-patterns with optional filters.

        Args:
            category: Filter by category
            tags: Filter by tags
            severity: Filter by severity

        Returns:
            List of AntiPattern entries
        """
        antipatterns = []
        for pattern_file in self.antipatterns_dir.glob("*.json"):
            with open(pattern_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                pattern = AntiPattern(**data)

                # Apply filters
                if category and pattern.category != category:
                    continue
                if tags and not any(tag in pattern.tags for tag in tags):
                    continue
                if severity and pattern.severity != severity:
                    continue

                antipatterns.append(pattern)

        # Sort by occurrence count and severity
        severity_order = {"high": 3, "medium": 2, "low": 1}
        antipatterns.sort(
            key=lambda p: (severity_order.get(p.severity, 0), p.occurrence_count),
            reverse=True,
        )
        return antipatterns

    # === Statistics ===

    def get_statistics(self) -> dict:
        """
        Get overall statistics about the prompt storage.

        Returns:
            Dictionary with statistics
        """
        total_logs = sum(1 for _ in self.logs_dir.rglob("*.json"))
        total_templates = sum(1 for _ in self.templates_dir.glob("*.json"))
        total_antipatterns = sum(1 for _ in self.antipatterns_dir.glob("*.json"))

        return {
            "total_logs": total_logs,
            "total_templates": total_templates,
            "total_antipatterns": total_antipatterns,
            "storage_dir": str(self.storage_dir),
        }
