import json

from pydantic import BaseModel, ConfigDict, Field


class EvaluationCriterion(BaseModel):
    """Individual evaluation criterion result."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    reasoning: str = Field(..., description="The reasoning behind the score.")
    criterion_name: str = Field(..., description="The name of the evaluation criterion.")
    score: int = Field(..., description="The evaluation score from 1 to 5.", ge=1, le=5)


class JudgeRequest(BaseModel):
    """Request model for LLM-as-a-Judge evaluation."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    question: str = Field(..., description="The original question or prompt.")
    response: str = Field(..., description="The response to be evaluated.")
    context: str | None = Field(None, description="Optional context or source material for evaluation.")
    request_parameters: str | None = Field(None, description="Optional request parameters to evaluate against.")


class JudgeResponse(BaseModel):
    """Response model for LLM-as-a-Judge evaluation."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    evaluations: list[EvaluationCriterion] = Field(..., description="List of evaluation results for each criterion.")
    overall_score: float = Field(..., description="The overall average score across all criteria.", ge=1.0, le=5.0)
    summary: str = Field(..., description="A brief summary of the overall evaluation.")

    @staticmethod
    def detailed_model() -> dict:
        """Generate a detailed model structure for prompt generation."""
        return {
            "evaluations": [
                {
                    "criterion_name": "string; The name of the evaluation criterion (e.g., 'accuracy', 'comprehensiveness', 'clarity')",
                    "score": "number; The evaluation score from 1 to 5 (1: completely inappropriate, 2: poor, 3: acceptable, 4: good, 5: perfect)",
                    "reasoning": "string; The reasoning behind the score",
                }
            ],
            "overall_score": "number; The overall average score across all criteria (1.0-5.0)",
            "summary": "string; A brief summary of the overall evaluation",
        }

    def save_as_json(self, file_path: str) -> None:
        """Save the evaluation response as a JSON file."""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=4, ensure_ascii=False)

    def is_passing(self, threshold: float = 3.0) -> bool:
        """Check if the evaluation passes a minimum threshold."""
        return self.overall_score >= threshold
