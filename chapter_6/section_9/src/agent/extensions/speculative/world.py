"""World: an isolated execution context for speculative pipeline execution."""

import copy
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class WorldStatus(Enum):
    """Status of a speculative world."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorldSummary:
    """Brief summary of a world's state for user comparison."""

    world_id: str
    candidate_label: str
    status: WorldStatus
    preview: str | None = None
    review_grade: int | None = None
    review_reasoning: str | None = None


@dataclass
class World:
    """An isolated execution context representing one speculative branch.

    Each world holds an independent deep copy of the pipeline state,
    allowing it to be executed without affecting other worlds or the
    main pipeline.
    """

    world_id: str
    branch_point_phase: int
    candidate: Any
    candidate_label: str
    state: Any
    status: WorldStatus = WorldStatus.PENDING
    result: Any | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    def mark_running(self) -> None:
        self.status = WorldStatus.RUNNING

    def mark_completed(self, result: Any) -> None:
        self.status = WorldStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now()

    def mark_failed(self, error: str) -> None:
        self.status = WorldStatus.FAILED
        self.error = error
        self.completed_at = datetime.now()

    def mark_cancelled(self) -> None:
        self.status = WorldStatus.CANCELLED
        self.completed_at = datetime.now()

    def get_summary(self) -> WorldSummary:
        """Create a brief summary for user comparison."""
        preview = None
        review_grade = None
        review_reasoning = None

        if self.result is not None:
            # Extract preview from completed article
            if hasattr(self.result, "article") and self.result.article is not None:
                article = self.result.article
                full_content = article.get_full_content()
                preview = full_content[:200] + "..." if len(full_content) > 200 else full_content
                if article.review is not None:
                    review_grade = article.review.grade
                    review_reasoning = article.review.reasoning

        return WorldSummary(
            world_id=self.world_id,
            candidate_label=self.candidate_label,
            status=self.status,
            preview=preview,
            review_grade=review_grade,
            review_reasoning=review_reasoning,
        )

    @staticmethod
    def create_from_state(
        world_id: str,
        branch_point_phase: int,
        candidate: Any,
        candidate_label: str,
        base_state: Any,
    ) -> "World":
        """Create a new world with a deep copy of the base state."""
        return World(
            world_id=world_id,
            branch_point_phase=branch_point_phase,
            candidate=candidate,
            candidate_label=candidate_label,
            state=copy.deepcopy(base_state),
        )
