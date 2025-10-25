"""Service interfaces for LLM functionality following Interface Segregation Principle."""

from abc import ABC, abstractmethod

from src.client.llm_client import GeminiModel, LLMClient, LLMProvider, OpenAIModel
from src.model.model import CharacterResponse, ClassificationResult, UserPlan


def get_available_models(provider: LLMProvider, user_plan: UserPlan) -> list[str]:
    if provider == LLMProvider.OPENAI:
        if user_plan == UserPlan.FREE:
            return OpenAIModel.free_plan_models()
        else:  # STANDARD
            return OpenAIModel.standard_plan_models()
    elif provider == LLMProvider.GEMINI:
        if user_plan == UserPlan.FREE:
            return GeminiModel.free_plan_models()
        else:  # STANDARD
            return GeminiModel.standard_plan_models()
    else:
        raise ValueError(f"Unsupported provider: {provider}")


class ITextGenerationService(ABC):
    """Interface for text generation services (character generation)."""

    def __init__(self, llm_client: LLMClient, provider: LLMProvider):
        self.llm_client = llm_client
        self.provider = provider

    @abstractmethod
    async def generate_character(
        self,
        gender: str,
        age: int,
        additional_instructions: str | None,
        model: str,
        user_plan: UserPlan,
    ) -> CharacterResponse:
        """Generate a character based on the given parameters.

        Args:
            gender: The gender of the character
            age: The age of the character
            additional_instructions: Additional instructions for generation
            model: The model to use for generation
            user_plan: The user's subscription plan

        Returns:
            CharacterResponse: The generated character

        Raises:
            ValueError: If the model is not available for the user's plan
        """
        pass


class ITextClassificationService(ABC):
    """Interface for text classification services."""

    def __init__(self, llm_client: LLMClient, provider: LLMProvider):
        self.llm_client = llm_client
        self.provider = provider

    @abstractmethod
    async def classify(self, text: str, categories: list[str], model: str, user_plan: UserPlan) -> ClassificationResult:
        """Classify text into one of the provided categories.

        Args:
            text: The text to classify
            categories: List of possible categories
            model: The model to use for classification
            user_plan: The user's subscription plan

        Returns:
            str: The predicted category

        Raises:
            ValueError: If the model is not available for the user's plan
        """
        pass
