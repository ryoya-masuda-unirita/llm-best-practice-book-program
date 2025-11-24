"""Data models for prompt logging and analysis."""

from datetime import datetime
from enum import StrEnum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class EvaluationStatus(StrEnum):
    """Evaluation status for prompt execution results."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    NOT_EVALUATED = "not_evaluated"


class PromptCategory(StrEnum):
    """Categories for prompt classification."""

    CHARACTER_GENERATION = "character_generation"
    TEXT_SUMMARIZATION = "text_summarization"
    CODE_GENERATION = "code_generation"
    DATA_EXTRACTION = "data_extraction"
    CLASSIFICATION = "classification"
    TRANSLATION = "translation"
    OTHER = "other"


class PromptMetadata(BaseModel):
    """Metadata for prompt execution context."""

    model_config = ConfigDict(frozen=True, extra="allow")

    model_name: str = Field(..., description="Name of the LLM model used")
    model_version: Optional[str] = Field(None, description="Version of the model")
    temperature: float = Field(..., description="Temperature parameter used")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens limit")
    use_case: str = Field(..., description="Use case or task description")
    category: PromptCategory = Field(..., description="Prompt category")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    timestamp: datetime = Field(default_factory=datetime.now, description="Execution timestamp")
    execution_time_ms: Optional[float] = Field(None, description="Execution time in milliseconds")
    token_count_input: Optional[int] = Field(None, description="Input token count")
    token_count_output: Optional[int] = Field(None, description="Output token count")
    cost_usd: Optional[float] = Field(None, description="Estimated cost in USD")
    user_id: Optional[str] = Field(None, description="User identifier (anonymized)")
    session_id: Optional[str] = Field(None, description="Session identifier")


class EvaluationCriteria(BaseModel):
    """Evaluation criteria for prompt results."""

    model_config = ConfigDict(frozen=True)

    accuracy: Optional[float] = Field(None, ge=0.0, le=1.0, description="Accuracy score (0.0-1.0)")
    completeness: Optional[float] = Field(None, ge=0.0, le=1.0, description="Completeness score (0.0-1.0)")
    relevance: Optional[float] = Field(None, ge=0.0, le=1.0, description="Relevance score (0.0-1.0)")
    user_feedback: Optional[bool] = Field(None, description="User feedback (thumbs up/down)")
    task_completed: Optional[bool] = Field(None, description="Whether task was completed")
    error_count: int = Field(0, ge=0, description="Number of errors encountered")
    custom_metrics: dict[str, Any] = Field(default_factory=dict, description="Custom evaluation metrics")


class PromptLog(BaseModel):
    """Complete log entry for a prompt execution."""

    model_config = ConfigDict(frozen=True)

    log_id: str = Field(default_factory=lambda: uuid4().hex, description="Unique log ID")
    template_name: Optional[str] = Field(None, description="Template name if used")
    template_version: Optional[str] = Field(None, description="Template version")
    prompt_text: str = Field(..., description="The actual prompt sent to LLM")
    messages: list[dict[str, str]] = Field(..., description="Full message list sent to API")
    response_text: str = Field(..., description="Raw response from LLM")
    parsed_response: Optional[dict[str, Any]] = Field(None, description="Parsed/structured response if applicable")
    metadata: PromptMetadata = Field(..., description="Execution metadata")
    evaluation: Optional[EvaluationCriteria] = Field(None, description="Evaluation results")
    evaluation_status: EvaluationStatus = Field(EvaluationStatus.NOT_EVALUATED, description="Overall evaluation status")
    failure_reason: Optional[str] = Field(None, description="Reason for failure if any")
    notes: Optional[str] = Field(None, description="Additional notes")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return self.model_dump()

    def get_overall_score(self) -> Optional[float]:
        """Calculate overall score from evaluation criteria."""
        if not self.evaluation:
            return None

        scores = []
        if self.evaluation.accuracy is not None:
            scores.append(self.evaluation.accuracy)
        if self.evaluation.completeness is not None:
            scores.append(self.evaluation.completeness)
        if self.evaluation.relevance is not None:
            scores.append(self.evaluation.relevance)

        if not scores:
            return None

        return sum(scores) / len(scores)
