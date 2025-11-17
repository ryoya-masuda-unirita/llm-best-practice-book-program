import json
from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field


class AnalysisEvaluation(BaseModel):
    """Evaluation result for document analysis."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    grade: Literal[1, 2, 3, 4, 5] = Field(
        ...,
        description="Grade from 1 (very poor) to 5 (very good)",
    )
    reasoning: str = Field(
        ...,
        description="Detailed reasoning for the grade (3-5 sentences)",
    )
    specific_improvements: list[str] = Field(
        default_factory=list,
        description="Specific improvements needed if grade is below 4 (optional)",
    )

    def is_acceptable(self) -> bool:
        """Check if the analysis quality is acceptable (grade >= 4)."""
        return self.grade >= 4


class DocumentAnalysis(BaseModel):
    """Document analysis result model."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    theme: str = Field(..., description="Document main theme (1-2 sentences)")
    value: str = Field(..., description="Document value and importance (2-3 sentences)")
    improvement_requests: list[str] = Field(
        ...,
        description="Document improvement requests list (3-5 items)",
        min_length=3,
        max_length=5,
    )

    def to_markdown(self) -> str:
        """Convert the analysis result to markdown format."""
        improvements_md = "\n".join(f"{i + 1}. {req}" for i, req in enumerate(self.improvement_requests))

        return f"""# Document Analysis Result

## Theme
{self.theme}

## Value
{self.value}

## Improvement Requests
{improvements_md}
"""

    def save_as_json(self, file_path: str) -> None:
        """Save the analysis result as a JSON file."""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=4, ensure_ascii=False)

    def save_as_markdown(self, file_path: str) -> None:
        """Save the analysis result as a markdown file."""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())


class PipelineState(TypedDict):
    """LangGraph pipeline state."""

    document_path: str
    document_content: str
    analysis_result: DocumentAnalysis | None
    evaluation_result: AnalysisEvaluation | None
    retry_count: int
    error: str | None
