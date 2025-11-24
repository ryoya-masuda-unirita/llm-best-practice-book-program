"""Catalog service for searching and managing prompt templates."""

from typing import Optional

from src.logger import make_logger
from src.model.prompt_log import PromptCategory
from src.model.prompt_template import AntiPattern, PromptTemplate
from src.service.prompt_storage import PromptStorage

logger = make_logger(__name__)


class PromptCatalog:
    """
    Catalog service for searching and retrieving prompt templates.

    This service provides a high-level interface for discovering and
    managing reusable prompt templates and anti-patterns.
    """

    def __init__(self, storage: PromptStorage):
        """
        Initialize the catalog.

        Args:
            storage: PromptStorage instance
        """
        self.storage = storage
        logger.info("Initialized PromptCatalog")

    def search_templates(
        self,
        query: Optional[str] = None,
        category: Optional[PromptCategory] = None,
        tags: Optional[list[str]] = None,
        min_success_rate: float = 0.0,
        min_score: Optional[float] = None,
    ) -> list[PromptTemplate]:
        """
        Search for templates with filters.

        Args:
            query: Text search in name/description (simple substring match)
            category: Filter by category
            tags: Filter by tags (must have at least one)
            min_success_rate: Minimum success rate (0.0-1.0)
            min_score: Minimum average score

        Returns:
            List of matching PromptTemplate entries
        """
        templates = self.storage.list_templates(category=category, tags=tags, min_success_rate=min_success_rate)

        # Apply additional filters
        results = []
        for template in templates:
            # Text search
            if query:
                query_lower = query.lower()
                if query_lower not in template.name.lower() and query_lower not in template.description.lower():
                    continue

            # Minimum score filter
            if min_score is not None and template.average_score is not None and template.average_score < min_score:
                continue

            results.append(template)

        logger.info(f"Search found {len(results)} templates")
        return results

    def get_top_templates(
        self,
        category: Optional[PromptCategory] = None,
        limit: int = 10,
    ) -> list[PromptTemplate]:
        """
        Get top-performing templates.

        Args:
            category: Filter by category
            limit: Maximum number of templates to return

        Returns:
            List of top PromptTemplate entries
        """
        templates = self.storage.list_templates(category=category)

        # Already sorted by success rate and score in storage
        return templates[:limit]

    def get_template_recommendations(
        self,
        category: PromptCategory,
        tags: Optional[list[str]] = None,
        limit: int = 5,
    ) -> list[PromptTemplate]:
        """
        Get template recommendations based on category and tags.

        Args:
            category: Category to filter by
            tags: Optional tags to match
            limit: Maximum number of recommendations

        Returns:
            List of recommended PromptTemplate entries
        """
        templates = self.storage.list_templates(category=category, tags=tags, min_success_rate=0.5)

        # Prioritize templates with higher usage and scores
        templates.sort(
            key=lambda t: (
                t.success_count + t.failure_count,  # Total usage
                t.get_success_rate(),
                t.average_score or 0.0,
            ),
            reverse=True,
        )

        return templates[:limit]

    def search_antipatterns(
        self,
        query: Optional[str] = None,
        category: Optional[PromptCategory] = None,
        tags: Optional[list[str]] = None,
        severity: Optional[str] = None,
        min_occurrence: int = 1,
    ) -> list[AntiPattern]:
        """
        Search for anti-patterns with filters.

        Args:
            query: Text search in name/description
            category: Filter by category
            tags: Filter by tags
            severity: Filter by severity (low, medium, high)
            min_occurrence: Minimum occurrence count

        Returns:
            List of matching AntiPattern entries
        """
        antipatterns = self.storage.list_antipatterns(category=category, tags=tags, severity=severity)

        # Apply additional filters
        results = []
        for pattern in antipatterns:
            # Text search
            if query:
                query_lower = query.lower()
                if query_lower not in pattern.name.lower() and query_lower not in pattern.description.lower():
                    continue

            # Minimum occurrence filter
            if pattern.occurrence_count < min_occurrence:
                continue

            results.append(pattern)

        logger.info(f"Search found {len(results)} anti-patterns")
        return results

    def get_critical_antipatterns(
        self,
        category: Optional[PromptCategory] = None,
        limit: int = 10,
    ) -> list[AntiPattern]:
        """
        Get most critical anti-patterns (high severity and occurrence).

        Args:
            category: Filter by category
            limit: Maximum number to return

        Returns:
            List of critical AntiPattern entries
        """
        antipatterns = self.storage.list_antipatterns(category=category)

        # Already sorted by severity and occurrence in storage
        return antipatterns[:limit]

    def get_catalog_summary(self) -> dict:
        """
        Get a summary of the catalog contents.

        Returns:
            Dictionary with catalog statistics
        """
        all_templates = self.storage.list_templates()
        all_antipatterns = self.storage.list_antipatterns()

        # Group by category
        templates_by_category = {}
        for template in all_templates:
            cat = template.category.value
            if cat not in templates_by_category:
                templates_by_category[cat] = []
            templates_by_category[cat].append(template)

        antipatterns_by_category = {}
        for pattern in all_antipatterns:
            cat = pattern.category.value
            if cat not in antipatterns_by_category:
                antipatterns_by_category[cat] = []
            antipatterns_by_category[cat].append(pattern)

        # Calculate statistics
        total_template_uses = sum(t.success_count + t.failure_count for t in all_templates)
        avg_success_rate = (
            sum(t.get_success_rate() for t in all_templates) / len(all_templates) if all_templates else 0.0
        )

        return {
            "total_templates": len(all_templates),
            "total_antipatterns": len(all_antipatterns),
            "templates_by_category": {k: len(v) for k, v in templates_by_category.items()},
            "antipatterns_by_category": {k: len(v) for k, v in antipatterns_by_category.items()},
            "total_template_uses": total_template_uses,
            "average_success_rate": avg_success_rate,
        }

    def export_template(self, template_id: str) -> Optional[dict]:
        """
        Export a template in a shareable format.

        Args:
            template_id: Template ID to export

        Returns:
            Template as dictionary or None if not found
        """
        template = self.storage.get_template(template_id)
        if not template:
            return None

        return {
            "name": template.name,
            "version": template.version,
            "description": template.description,
            "category": template.category.value,
            "tags": template.tags,
            "system_prompt": template.system_prompt,
            "user_prompt": template.user_prompt,
            "required_variables": template.required_variables,
            "optional_variables": template.optional_variables,
            "recommended_models": template.recommended_models,
            "recommended_temperature": template.recommended_temperature,
            "success_rate": template.get_success_rate(),
            "average_score": template.average_score,
            "use_case_examples": template.use_case_examples,
        }
