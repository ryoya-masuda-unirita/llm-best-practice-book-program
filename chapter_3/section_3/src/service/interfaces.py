"""Service interfaces for LLM functionality following Interface Segregation Principle."""

from abc import ABC, abstractmethod

from anthropic import AsyncAnthropic

from src.client.llm_client import AnthropicModel
from src.model.model import CharacterResponse, ClassificationResult, UserPlan


def get_available_models(user_plan: UserPlan) -> list[str]:
    if user_plan == UserPlan.FREE:
        return AnthropicModel.free_plan_models()
    return AnthropicModel.standard_plan_models()


class ITextGenerationService(ABC):
    """Interface for text generation services."""

    def __init__(self, client: AsyncAnthropic):
        self.client = client

    @abstractmethod
    async def generate_character(
        self,
        gender: str,
        age: int,
        additional_instructions: str | None,
        model: str,
        user_plan: UserPlan,
    ) -> CharacterResponse:
        """Generate a character based on the given parameters."""
        pass


class ITextClassificationService(ABC):
    """Interface for text classification services."""

    def __init__(self, client: AsyncAnthropic):
        self.client = client

    @abstractmethod
    async def classify(
        self,
        text: str,
        categories: list[str],
        model: str,
        user_plan: UserPlan,
    ) -> ClassificationResult:
        """Classify text into one of the provided categories."""
        pass
