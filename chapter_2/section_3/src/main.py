import asyncio
from functools import wraps
from uuid import uuid4

import click
from openai import AsyncOpenAI
from src.llms import LLMClientWithFallback, google_genai_client, openai_client
from src.logger import make_logger
from src.model import CharacterResponse, FailedResponse, LLMProvider
from src.prompt import make_prompt

logger = make_logger(__name__)


def async_cmd(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.command()
@click.option(
    "--timeout",
    "-t",
    type=int,
    default=10,
    help="Timeout for the LLM request in seconds.",
)
@async_cmd
async def main(
    timeout: int,
):
    logger.info(f"Starting LLM request with timeout: {timeout} seconds")
    prompt = make_prompt()

    # Create a client with fallback
    client_with_fallback = LLMClientWithFallback(
        primary_client=openai_client,
        fallback_client=google_genai_client,
    )

    # Use the client with fallback
    logger.info("Attempting to use LLM with fallback")
    response = await client_with_fallback.request_with_fallback(
        prompt=prompt,
        result_type=CharacterResponse,
        timeout_second=timeout,
    )

    # Handle the response
    if isinstance(response, FailedResponse):
        logger.error(f"All LLM requests failed: {response.error}")
        return

    # Determine which provider was used based on the client type
    provider = (
        LLMProvider.OPENAI if isinstance(client_with_fallback.primary_client, AsyncOpenAI) else LLMProvider.GEMINI
    )
    logger.info(f"Successfully received response: {response}")
    response.save_as_json(f"{provider.value}_{uuid4().hex}.json")


if __name__ == "__main__":
    main()
