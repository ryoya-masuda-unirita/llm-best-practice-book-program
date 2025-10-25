"""Concrete implementation of text generation service."""

from google.genai.types import GenerateContentConfig

from src.client.llm_client import GeminiModel, LLMClient, LLMProvider, OpenAIModel
from src.logger import make_logger
from src.model.model import CharacterRequest, CharacterResponse, UserPlan
from src.prompt.prompt import make_generation_prompt
from src.service.interfaces import ITextGenerationService, get_available_models

logger = make_logger(__name__)


class TextGenerationService(ITextGenerationService):
    """Service for generating text content like character descriptions."""

    def __init__(self, llm_client: LLMClient, provider: LLMProvider):
        super().__init__(llm_client=llm_client, provider=provider)

    async def request_openai(self, model: OpenAIModel, prompt: list[dict]) -> CharacterResponse:
        result = await self.llm_client.openai_client.beta.chat.completions.parse(
            model=model,
            messages=prompt,
            response_format=CharacterResponse,
        )
        return result.choices[0].message.parsed

    async def request_gemini(self, model: GeminiModel, prompt: list[dict]) -> CharacterResponse:
        result = await self.llm_client.google_genai_client.aio.models.generate_content(
            model=model,
            contents=prompt[-1]["content"],
            config=GenerateContentConfig(
                system_instruction=prompt[0]["content"],
                response_mime_type="application/json",
                response_schema=CharacterResponse,
            ),
        )
        logger.info(result)
        return result.parsed

    async def generate_character(
        self,
        gender: str,
        age: int,
        additional_instructions: str | None,
        model: str,
        user_plan: UserPlan,
    ) -> CharacterResponse:
        """Generate a character based on the given parameters."""
        # Validate model availability for user plan
        available_models = get_available_models(self.provider, user_plan)
        if model not in available_models:
            raise ValueError(
                f"Model '{model}' is not available for {user_plan.value} plan. "
                f"Available models: {', '.join(available_models)}"
            )

        # Create character request
        character_request = CharacterRequest(gender=gender, age=age, additional_instructions=additional_instructions)

        # Generate prompt
        prompt = make_generation_prompt(character_request=character_request)

        # Request LLM based on provider
        if self.provider == LLMProvider.OPENAI:
            logger.info(f"Generating character using OpenAI model: {model}")
            return await self.request_openai(model=model, prompt=prompt)
        elif self.provider == LLMProvider.GEMINI:
            logger.info(f"Generating character using Gemini model: {model}")
            return await self.request_gemini(model=model, prompt=prompt)
        raise ValueError(f"Unsupported provider: {self.provider}")
