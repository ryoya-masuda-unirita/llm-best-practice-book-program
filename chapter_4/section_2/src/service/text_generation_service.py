from anthropic import AsyncAnthropicBedrock
from src.logger import make_logger
from src.model.model import CharacterRequest, CharacterResponse, UserPlan
from src.prompt.prompt import make_generation_prompt
from src.service.interfaces import ITextGenerationService, get_available_models

logger = make_logger(__name__)


class TextGenerationService(ITextGenerationService):
    """Service for generating text content like character descriptions."""

    def __init__(self, client: AsyncAnthropicBedrock):
        super().__init__(client=client)

    async def generate_character(
        self,
        gender: str,
        age: int,
        additional_instructions: str | None,
        model: str,
        user_plan: UserPlan,
    ) -> CharacterResponse:
        """Generate a character based on the given parameters."""
        available_models = get_available_models(user_plan)
        if model not in available_models:
            raise ValueError(
                f"Model '{model}' is not available for {user_plan.value} plan. "
                f"Available models: {', '.join(available_models)}"
            )

        character_request = CharacterRequest(
            gender=gender,
            age=age,
            additional_instructions=additional_instructions,
        )
        prompt = make_generation_prompt(character_request=character_request)

        logger.info(f"Generating character using Anthropic model: {model}")
        result = await self.client.messages.parse(
            model=model,
            max_tokens=1024,
            messages=prompt,
            output_format=CharacterResponse,
        )
        logger.info(result)
        return result.parsed_output
