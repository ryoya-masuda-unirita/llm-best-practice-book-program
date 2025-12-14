"""Service layer for unified LLM requests."""

from src.client.base import LLMClient
from src.client.model import AnthropicModel, GeminiModel, OpenAIModel
from src.logger import make_logger
from src.model.model import CharacterResponse
from src.prompt import make_prompt

logger = make_logger(__name__)


async def request_llm(
    client: LLMClient,
    model: OpenAIModel | GeminiModel | AnthropicModel,
) -> CharacterResponse:
    """Make LLM request and return character data."""
    logger.info(f"Making LLM request: provider={client.get_provider_name()}, model={model}")

    provider = client.get_provider_name()
    prompt = make_prompt(provider)

    result = await client.chat(
        messages=prompt,
        response_format=CharacterResponse,
    )

    logger.info(f"Successfully received response from {provider}")

    return result
