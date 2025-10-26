"""Models for parallel world pattern article generation."""

import json
from datetime import datetime
from typing import Literal, TypedDict
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ArticleOutline(BaseModel):
    """Article outline model."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    reason: str = Field(..., description="Reason for choosing this outline (2-3 sentences)")
    title: str = Field(..., description="Article title")
    summary: str = Field(..., description="Article summary (2-3 sentences)")
    structure: list[str] = Field(
        ...,
        description="Article structure with section headers",
        min_length=3,
        max_length=10,
    )

    def to_markdown(self) -> str:
        """Convert outline to markdown format."""
        structure_md = "\n".join(f"{i + 1}. {section}" for i, section in enumerate(self.structure))
        return f"""# {self.title}

## Summary
{self.summary}

## Structure
{structure_md}
"""


class ArticleHalf(BaseModel):
    """Half of an article (first half or second half)."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    reason: str = Field(..., description="Reason for the content")
    content: str = Field(..., description="Article content in markdown format")


class BestArticleSelection(BaseModel):
    """Selection of the best article among multiple variants."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    reason: str = Field(..., description="Reason for selecting this article (2-3 sentences)")
    selected_id: str = Field(..., description="ID of the selected best article")


class ArticleReview(BaseModel):
    """Review of an article using LLM-as-a-Judge."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    reasoning: str = Field(
        ...,
        description="Detailed reasoning for the grade (3-5 sentences)",
    )
    grade: int = Field(
        ...,
        description="Grade from 1 (very poor) to 5 (excellent)",
        ge=1,
        le=5,
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="Specific strengths of the article (2-4 items)",
    )
    weaknesses: list[str] = Field(
        default_factory=list,
        description="Specific weaknesses of the article (2-4 items if any)",
    )

    @staticmethod
    def worst_grade() -> int:
        return 1

    @staticmethod
    def best_grade() -> int:
        return 5

    def is_acceptable(self) -> bool:
        """Check if the article quality is acceptable (grade >= 4)."""
        return self.grade >= 4

    def to_markdown(self) -> str:
        """Convert review to markdown format."""
        strengths_md = "\n".join(f"- {s}" for s in self.strengths)
        weaknesses_md = "\n".join(f"- {w}" for w in self.weaknesses)

        return f"""## Review Grade: {self.grade}/5

### Reasoning
{self.reasoning}

### Strengths
{strengths_md}

### Weaknesses
{weaknesses_md if self.weaknesses else "No significant weaknesses identified."}
"""


class CompletedArticle(BaseModel):
    """Complete article with both halves."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=False,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    session_id: str = Field(default_factory=lambda: uuid4().hex, description="Unique session ID")
    outline: ArticleOutline = Field(..., description="Article outline")
    first_half: str = Field(..., description="First half of the article")
    second_half: str = Field(..., description="Second half of the article")
    review: ArticleReview | None = Field(None, description="Article review (optional)")
    language: Literal["en", "ja"] = Field(..., description="Article language")
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Creation timestamp",
    )

    def get_full_content(self) -> str:
        """Get the complete article content."""
        return f"""{self.first_half}

{self.second_half}"""

    def to_markdown(self) -> str:
        """Convert complete article to markdown format."""
        full_article = self.get_full_content()

        if self.review:
            review_section = f"""
---

# Article Review

{self.review.to_markdown()}
"""
        else:
            review_section = ""

        return f"""# {self.outline.title}

{full_article}
{review_section}
"""

    def save_as_json(self, file_path: str) -> None:
        """Save the complete article as a JSON file."""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=4, ensure_ascii=False)

    def save_as_markdown(self, file_path: str) -> None:
        """Save the complete article as a markdown file."""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())


class ParallelSession(BaseModel):
    """Represents a single parallel world session."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=False,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    session_id: str = Field(default_factory=lambda: uuid4().hex, description="Unique session ID")
    parent_session_id: str | None = Field(None, description="Parent session ID (if forked)")
    outline: ArticleOutline | None = Field(None, description="Article outline")
    first_half: str | None = Field(None, description="First half of the article")
    second_half: str | None = Field(None, description="Second half of the article")
    review: ArticleReview | None = Field(None, description="Article review")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Creation timestamp",
    )

    def is_completed(self) -> bool:
        """Check if this session has all parts completed."""
        return (
            self.outline is not None
            and self.first_half is not None
            and self.second_half is not None
            and self.review is not None
        )

    def to_completed_article(self, language: Literal["en", "ja"]) -> CompletedArticle | None:
        """Convert to CompletedArticle if all parts are present."""
        if not self.is_completed():
            return None

        return CompletedArticle(
            session_id=self.session_id,
            outline=self.outline,  # type: ignore
            first_half=self.first_half,  # type: ignore
            second_half=self.second_half,  # type: ignore
            review=self.review,
            language=language,
            created_at=self.created_at,
        )


class ParallelWorldState(TypedDict, total=False):
    """
    State for parallel world article generation pipeline.

    The state itself serves as the memory of which phases have been completed.
    Phases are determined by which fields are populated:

    Phase 0: Initial state (only theme, language, metadata)
    Phase 1: outline_sessions populated
    Phase 2: selected_outline_session_id populated
    Phase 3: first_half_session populated
    Phase 4: second_half_sessions populated
    Phase 5: reviewed_sessions populated
    Phase 6-7: final_selected_session_id and human_approved populated

    To "forget the past" and rollback to a phase, simply remove the state
    variables that come after that phase.
    """

    # Required: Pipeline configuration (always present)
    theme: str
    language: Literal["en", "ja"]
    llm_provider: str
    model: str
    num_outline_variants: int
    num_second_half_variants: int

    # Optional: Phase-specific state (presence indicates phase completion)
    # Phase 1: Multiple outlines generated in parallel
    outline_sessions: list[ParallelSession]
    # Phase 2: User selects one outline
    selected_outline_session_id: str | None
    # Phase 3: First half generated based on selected outline
    first_half_session: ParallelSession | None
    # Phase 4: Multiple second halves generated in parallel
    second_half_sessions: list[ParallelSession]
    # Phase 5: Reviews generated for each complete article
    reviewed_sessions: list[ParallelSession]
    # Phase 6: User selects best article
    final_selected_session_id: str | None
    # Phase 7: Human review (yes/no) and feedback loop
    human_approved: bool | None  # True if approved, False if needs revision
    rejected_session_ids: list[str]  # Track rejected sessions to avoid re-showing
    review_loop_iteration: int  # Track how many times we've looped

    # Error tracking
    error: str | None
