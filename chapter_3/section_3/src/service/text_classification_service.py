"""Concrete implementation of text classification service."""

from google.genai.types import GenerateContentConfig

from src.client.llm_client import GeminiModel, LLMClient, LLMProvider, OpenAIModel
from src.logger import make_logger
from src.model.model import ClassificationResult, UserPlan
from src.prompt.prompt import make_classification_prompt
from src.service.interfaces import ITextClassificationService, get_available_models

logger = make_logger(__name__)


class TextClassificationService(ITextClassificationService):
    """Service for classifying text into predefined categories."""

    def __init__(self, llm_client: LLMClient, provider: LLMProvider):
        super().__init__(llm_client=llm_client, provider=provider)

    async def request_openai(self, model: OpenAIModel, prompt: list[dict]) -> ClassificationResult:
        """Request classification from OpenAI with structured output.

        Args:
            model: The OpenAI model to use
            prompt: The prompt messages

        Returns:
            ClassificationResult: The parsed classification result
        """
        result = await self.llm_client.openai_client.beta.chat.completions.parse(
            model=model,
            messages=prompt,
            response_format=ClassificationResult,
        )
        return result.choices[0].message.parsed

    async def request_gemini(self, model: GeminiModel, prompt: list[dict]) -> ClassificationResult:
        """Request classification from Gemini with structured output.

        Args:
            model: The Gemini model to use
            prompt: The prompt messages

        Returns:
            ClassificationResult: The parsed classification result
        """
        result = await self.llm_client.google_genai_client.aio.models.generate_content(
            model=model,
            contents=prompt[-1]["content"],
            config=GenerateContentConfig(
                system_instruction=prompt[0]["content"],
                response_mime_type="application/json",
                response_schema=ClassificationResult,
            ),
        )
        logger.info(result)
        return result.parsed

    async def classify(self, text: str, categories: list[str], model: str, user_plan: UserPlan) -> ClassificationResult:
        """Classify text into one of the provided categories."""
        # Validate model availability for user plan
        available_models = get_available_models(self.provider, user_plan)
        if model not in available_models:
            raise ValueError(
                f"Model '{model}' is not available for {user_plan.value} plan. "
                f"Available models: {', '.join(available_models)}"
            )

        # Generate classification prompt
        prompt = make_classification_prompt(text=text, categories=categories)

        # Request LLM based on provider with structured output
        if self.provider == LLMProvider.OPENAI:
            logger.info(f"Classifying text using OpenAI model: {model}")
            result = await self.request_openai(model=model, prompt=prompt)
        elif self.provider == LLMProvider.GEMINI:
            logger.info(f"Classifying text using Gemini model: {model}")
            result = await self.request_gemini(model=model, prompt=prompt)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        # Validate the result category is in the provided categories
        if result.category not in categories:
            logger.warning(
                f"LLM returned category '{result.category}' which is not in {categories}. Defaulting to first category."
            )
            return categories[0]

        logger.info(
            f"Classification result: {result.category}"
            + (f" (confidence: {result.confidence})" if result.confidence else "")
            + (f" - {result.reasoning}" if result.reasoning else "")
        )

        return result
