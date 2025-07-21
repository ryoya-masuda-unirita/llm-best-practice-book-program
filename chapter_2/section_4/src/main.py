import asyncio
from functools import wraps
from uuid import uuid4

import click
from openai import AsyncOpenAI
from src.llms import LLMClientWithFallback, LLMRequestRetryOptions, google_genai_client, openai_client
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
    help="Timeout for the LLM request in seconds. Default: 10.",
)
@click.option(
    "--max-retries",
    "-r",
    type=int,
    default=3,
    help="Maximum number of retries for the LLM request. Default: 3.",
)
@click.option(
    "--exponential-backoff",
    "-eb",
    is_flag=True,
    default=False,
    help="Enable exponential backoff for retries. Default: False.",
)
@click.option(
    "--backoff-factor",
    "-bf",
    type=float,
    default=2.0,
    help="Backoff factor for exponential backoff. Default: 2.0.",
)
@click.option(
    "--max-backoff",
    "-mb",
    type=int,
    default=60,
    help="Maximum backoff time in seconds for exponential backoff. Default: 60.",
)
@click.option(
    "--jitter",
    "-j",
    is_flag=True,
    default=False,
    help="Enable jitter for the backoff time. Default: False.",
)
@async_cmd
async def main(
    timeout: int,
    max_retries: int = 3,
    exponential_backoff: bool = False,
    backoff_factor: float = 2.0,
    max_backoff: int = 60,
    jitter: bool = False,
):
    logger.info(f"""Params:
Timeout: {timeout} seconds
Max Retries: {max_retries}
Exponential Backoff: {exponential_backoff}
Backoff Factor: {backoff_factor}
Max Backoff: {max_backoff} seconds
Jitter: {jitter}
""")

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
        retry_options=LLMRequestRetryOptions(
            timeout_second=timeout,
            max_retries=max_retries,
            do_exponential_backoff=exponential_backoff,
            exponential_backoff_factor=backoff_factor,
            max_backoff=max_backoff,
            jitter=jitter,
        ),
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
