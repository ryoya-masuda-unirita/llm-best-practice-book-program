"""Service layer for LLM requests using the adapter pattern.

This module provides a unified interface for making LLM requests,
abstracting away the differences between various providers.
"""

from src.client.base import LLMClient
from src.client.factory import LLMClientFactory
from src.client.model import GeminiModel, LLMProvider, OpenAIModel
from src.logger import make_logger
from src.model.model import CharacterResponse
from src.prompt.prompt import make_prompt

logger = make_logger(__name__)


async def request_llm(
    provider: LLMProvider,
    model: OpenAIModel | GeminiModel,
) -> CharacterResponse:
    """Make an LLM request using the factory pattern.

    Args:
        provider: Provider name ('openai', 'anthropic', or 'gemini')
        model: Model identifier

    Returns:
        CharacterResponse object with generated character data

    Raises:
        ValueError: If provider/model combination is invalid
        Exception: Provider-specific API errors

    Example:
        >>> response = await request_llm('openai', 'gpt-4o')
        >>> print(response.first_name, response.last_name)
    """
    # Create client using factory
    client: LLMClient = LLMClientFactory.create_client(provider=provider, model=model)

    logger.info(f"Making LLM request: provider={provider}, model={model}")

    # Get prompt
    prompt = make_prompt()

    # Make request using unified interface
    result = await client.chat(
        messages=prompt,
        response_format=CharacterResponse,
    )

    logger.info(f"Successfully received response from {provider}")

    return result
