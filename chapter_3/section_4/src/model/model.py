import json
import time
from enum import StrEnum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


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
    additional_instructions: Optional[str] = Field(..., description="Additional instructions for character generation.")


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
                params[k] = []
                for i in range(3):
                    params[k].append(
                        {
                            "short_personality": f"string; {v.description} (personality {i + 1})",
                            "description": f"string; {v.description} (detailed description for personality {i + 1})",
                        }
                    )
        return params

    def save_as_json(self, file_path: str) -> None:
        """Save the character response as a JSON file."""

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=4, ensure_ascii=False)


class LLMRequest(BaseModel):
    """Request model for LLM API."""

    model: str = Field(..., description="The Gemini model name to use for generation")
    character_request: CharacterRequest = Field(..., description="Character generation request parameters")


class LLMResponse(BaseModel):
    """Response model for LLM API."""

    character: CharacterResponse = Field(..., description="Generated character information")
    provider: str = Field(..., description="LLM provider used")
    model: str = Field(..., description="Model used")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["healthy"] = "healthy"
    timestamp: float = Field(default_factory=time.time)
