from typing import Annotated, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """ReAct agent state for dinner menu advisor."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_request: str
    final_recommendation: str | None


class DinnerRecommendation(BaseModel):
    """Dinner menu recommendation result."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    menu_name: str = Field(..., description="Name of the recommended dinner menu")
    ingredients: list[str] = Field(..., description="List of main ingredients needed")
    cooking_time_minutes: int = Field(..., description="Estimated cooking time in minutes")
    difficulty: str = Field(..., description="Difficulty level: easy, medium, or hard")
    reason: str = Field(..., description="Why this menu is recommended based on user's request")
    recipe_steps: list[str] = Field(..., description="Step-by-step cooking instructions")

    def to_markdown(self) -> str:
        """Convert the recommendation to markdown format."""
        ingredients_md = "\n".join(f"- {ing}" for ing in self.ingredients)
        steps_md = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(self.recipe_steps))

        return f"""# Dinner Recommendation: {self.menu_name}

## Overview
- **Cooking Time**: {self.cooking_time_minutes} minutes
- **Difficulty**: {self.difficulty}

## Why This Menu?
{self.reason}

## Ingredients
{ingredients_md}

## Recipe Steps
{steps_md}
"""
