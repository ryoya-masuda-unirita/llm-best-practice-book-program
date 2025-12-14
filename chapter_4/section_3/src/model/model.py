import json
import time
from enum import StrEnum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class UserPlan(StrEnum):
    """User subscription plan types."""

    FREE = "free"
    STANDARD = "standard"


class Gender(StrEnum):
    FEMALE = "female"
    MALE = "male"


class CharacterRequest(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    gender: Gender = Field(..., description="The gender of the character.")
    age: int = Field(..., description="The age of the character.", ge=0, le=100)
    additional_instructions: Optional[str] = Field(
        None, description="Additional instructions for character generation."
    )


class CharacterPersonality(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    short_personality: str = Field(..., description="A short description of the character's personality.")
    description: str = Field(..., description="A description of the character's personality traits and behaviors.")


class CharacterResponse(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    first_name: str = Field(..., description="The first name of the character.")
    last_name: str = Field(..., description="The last name of the character.")
    gender: Gender = Field(Gender.MALE, description="The gender of the character.")
    age: int = Field(..., description="The age of the character.", ge=0, le=100)
    personalities: list[CharacterPersonality] = Field(
        ..., description="The three most important personality traits of the character."
    )

    @staticmethod
    def detailed_model() -> dict:
        params = {}
        for k, v in CharacterResponse.model_fields.items():
            if k in ["first_name", "last_name"]:
                params[k] = f"string; {v.description}"
            elif k == "gender":
                params[k] = f"enum; {v.description}; {[g.value for g in Gender]}"
            elif k == "age":
                params[k] = f"number; {v.description}; 0-100"
            elif k == "personalities":
                params[k] = [
                    {
                        "short_personality": f"string; {v.description} (personality {i + 1})",
                        "description": f"string; {v.description} (detailed description for personality {i + 1})",
                    }
                    for i in range(3)
                ]
        return params

    def save_as_json(self, file_path: str) -> None:
        """Save the character response as a JSON file."""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=4, ensure_ascii=False)


class LLMRequest(BaseModel):
    """Request model for character generation API."""

    model: str = Field(..., description="The model name to use for generation")
    character_request: CharacterRequest = Field(..., description="Character generation request parameters")
    user_plan: UserPlan = Field(default=UserPlan.FREE, description="User's subscription plan")


class LLMResponse(BaseModel):
    """Response model for character generation API."""

    character: CharacterResponse = Field(..., description="Generated character information")
    model: str = Field(..., description="Model used")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["healthy"] = "healthy"
    timestamp: float = Field(default_factory=time.time)


class TextClassificationRequest(BaseModel):
    """Request model for text classification."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    text: str = Field(..., description="The text to classify")
    categories: list[str] = Field(..., description="List of possible categories", min_length=2)
    model: str = Field(..., description="The model to use for classification")
    user_plan: UserPlan = Field(default=UserPlan.FREE, description="User's subscription plan")


class ClassificationResult(BaseModel):
    """Classification result from LLM - structured output model."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    reasoning: str = Field(None, description="Brief explanation for the classification")
    category: str = Field(..., description="The predicted category from the provided list")
    confidence: Optional[str] = Field(None, description="Optional confidence level: high, medium, or low")


class TextClassificationResponse(BaseModel):
    """Response model for text classification API."""

    category: str = Field(..., description="The predicted category")
    model: str = Field(..., description="Model used")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    classification_result: ClassificationResult = Field(..., description="Detailed classification result")
