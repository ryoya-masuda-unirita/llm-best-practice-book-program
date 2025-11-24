"""Data models for prompt template management and cataloging."""

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from src.model.prompt_log import PromptCategory


class PromptTemplate(BaseModel):
    """Reusable prompt template with metadata."""

    model_config = ConfigDict(frozen=True)

    template_id: str = Field(default_factory=lambda: uuid4().hex, description="Unique template ID")
    name: str = Field(..., description="Template name")
    version: str = Field("1.0.0", description="Template version")
    description: str = Field(..., description="Template description")
    category: PromptCategory = Field(..., description="Template category")
    tags: list[str] = Field(default_factory=list, description="Tags for search")
    system_prompt: str = Field(..., description="System prompt template")
    user_prompt: str = Field(..., description="User prompt template")
    required_variables: list[str] = Field(default_factory=list, description="Required template variables")
    optional_variables: list[str] = Field(default_factory=list, description="Optional template variables")
    recommended_models: list[str] = Field(default_factory=list, description="Recommended models for this template")
    recommended_temperature: float = Field(1.0, description="Recommended temperature")
    success_count: int = Field(0, ge=0, description="Number of successful uses")
    failure_count: int = Field(0, ge=0, description="Number of failed uses")
    average_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Average evaluation score")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    created_by: Optional[str] = Field(None, description="Creator identifier")
    use_case_examples: list[str] = Field(default_factory=list, description="Example use cases")
    notes: Optional[str] = Field(None, description="Additional notes")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return self.model_dump()

    def get_success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.success_count / total


class AntiPattern(BaseModel):
    """Anti-pattern for failed prompts."""

    model_config = ConfigDict(frozen=True)

    pattern_id: str = Field(default_factory=lambda: uuid4().hex, description="Unique pattern ID")
    name: str = Field(..., description="Anti-pattern name")
    description: str = Field(..., description="Description of the anti-pattern")
    category: PromptCategory = Field(..., description="Category")
    tags: list[str] = Field(default_factory=list, description="Tags for search")
    prompt_pattern: str = Field(..., description="The problematic prompt pattern")
    failure_reason: str = Field(..., description="Why this pattern fails")
    occurrence_count: int = Field(1, ge=1, description="Number of times observed")
    recommended_fix: Optional[str] = Field(None, description="Recommended solution")
    related_template_id: Optional[str] = Field(None, description="ID of template that solves this")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    severity: str = Field("medium", description="Severity: low, medium, high")
    examples: list[str] = Field(default_factory=list, description="Example failures")
    notes: Optional[str] = Field(None, description="Additional notes")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return self.model_dump()
