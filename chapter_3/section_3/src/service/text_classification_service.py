from anthropic import AsyncAnthropic

from src.logger import make_logger
from src.model.model import ClassificationResult, UserPlan
from src.prompt.prompt import make_classification_prompt
from src.service.interfaces import ITextClassificationService, get_available_models

logger = make_logger(__name__)

STRUCTURED_OUTPUT_BETA = "structured-outputs-2025-11-13"


class TextClassificationService(ITextClassificationService):
    """Service for classifying text into predefined categories."""

    def __init__(self, client: AsyncAnthropic):
        super().__init__(client=client)

    async def classify(
        self,
        text: str,
        categories: list[str],
        model: str,
        user_plan: UserPlan,
    ) -> ClassificationResult:
        """Classify text into one of the provided categories."""
        available_models = get_available_models(user_plan)
        if model not in available_models:
            raise ValueError(
                f"Model '{model}' is not available for {user_plan.value} plan. "
                f"Available models: {', '.join(available_models)}"
            )

        prompt = make_classification_prompt(text=text, categories=categories)

        logger.info(f"Classifying text using Anthropic model: {model}")
        result = await self.client.beta.messages.parse(
            model=model,
            max_tokens=1024,
            betas=[STRUCTURED_OUTPUT_BETA],
            messages=prompt,
            output_format=ClassificationResult,
        )
        logger.info(result)
        classification = result.parsed_output

        if classification.category not in categories:
            logger.warning(
                f"LLM returned category '{classification.category}' not in {categories}. Defaulting to first category."
            )
            return categories[0]

        logger.info(
            f"Classification result: {classification.category}"
            + (f" (confidence: {classification.confidence})" if classification.confidence else "")
            + (f" - {classification.reasoning}" if classification.reasoning else "")
        )

        return classification
