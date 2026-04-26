"""Models for article generation with Forget, Replay, Speculate pattern."""

import json
from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ArticleOutline(BaseModel):
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
        structure_md = "\n".join(f"{i + 1}. {section}" for i, section in enumerate(self.structure))
        return f"""# {self.title}

## Summary
{self.summary}

## Structure
{structure_md}
"""


class ArticleHalf(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    reason: str = Field(..., description="Reason for the content")
    content: str = Field(..., description="Article content in markdown format")


class BestArticleSelection(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    reason: str = Field(..., description="Reason for selecting this article (2-3 sentences)")
    selected_id: str = Field(..., description="ID of the selected best article")


class ArticleReview(BaseModel):
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
        return self.grade >= 4

    def to_markdown(self) -> str:
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
        return f"""{self.first_half}

{self.second_half}"""

    def to_markdown(self) -> str:
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
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=4, ensure_ascii=False)

    def save_as_markdown(self, file_path: str) -> None:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())
