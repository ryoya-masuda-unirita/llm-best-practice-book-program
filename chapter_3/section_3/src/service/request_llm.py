import asyncio
import random
from functools import wraps
from typing import Any, Callable

import anthropic
from src.client.llm_client import AnthropicModel, anthropic_client
from src.logger import make_logger
from src.model.model import CharacterRequest, CharacterResponse
from src.prompt.prompt import make_prompt
from src.service.llmops_logger import LLMOpsLogger

logger = make_logger(__name__)


MAX_RETRIES = 5
MAX_BACKOFF_SECONDS = 60
BASE_BACKOFF_SECONDS = 1
JITTER_MIN = 0.1
JITTER_MAX = 0.5

RETRYABLE_STATUS_CODES = {429, 500, 503, 502, 504}


def calculate_backoff_with_jitter(attempt: int, base: float = BASE_BACKOFF_SECONDS) -> float:
    """Calculate exponential backoff time with random jitter."""
    backoff = min(base * (2**attempt), MAX_BACKOFF_SECONDS)
    jitter_range = backoff * (JITTER_MAX - JITTER_MIN)
    jitter = random.uniform(backoff * JITTER_MIN, backoff * JITTER_MIN + jitter_range)
    return backoff + jitter


def should_retry_error(error: Exception) -> tuple[bool, int | None]:
    """
    Determine if an error should be retried and extract retry-after if available.

    Returns:
        tuple: (should_retry: bool, retry_after_seconds: int | None)
    """
    if isinstance(error, anthropic.RateLimitError):
        retry_after = error.response.headers.get("retry-after")
        return True, int(float(retry_after)) if retry_after else None

    if isinstance(error, anthropic.APIStatusError) and error.status_code in RETRYABLE_STATUS_CODES:
        return True, None

    if isinstance(error, anthropic.APIConnectionError):
        return True, None

    return False, None


def retry_with_exponential_backoff(max_retries: int = MAX_RETRIES):
    """
    Decorator that implements exponential backoff retry logic with jitter.

    Args:
        max_retries: Maximum number of retry attempts
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    should_retry, retry_after = should_retry_error(e)

                    if not should_retry or attempt == max_retries:
                        logger.error(
                            f"Request failed after {attempt + 1} attempts. Error: {type(e).__name__}: {str(e)}"
                        )
                        raise

                    if retry_after is not None:
                        backoff_time = retry_after
                        logger.warning(
                            f"Rate limit hit (attempt {attempt + 1}/{max_retries + 1}). "
                            f"Retry-After: {retry_after}s. Waiting..."
                        )
                    else:
                        backoff_time = calculate_backoff_with_jitter(attempt)
                        logger.warning(
                            f"Request failed (attempt {attempt + 1}/{max_retries + 1}). "
                            f"Error: {type(e).__name__}: {str(e)}. "
                            f"Retrying in {backoff_time:.2f}s..."
                        )

                    await asyncio.sleep(backoff_time)

            raise last_exception

        return wrapper

    return decorator


@retry_with_exponential_backoff()
async def request_anthropic(
    character_request: CharacterRequest,
    model: AnthropicModel,
    llmops_logger: LLMOpsLogger,
    user_id: str = "default_user",
) -> CharacterResponse:
    """Request character generation from Anthropic with structured logging and retry logic."""
    prompt = make_prompt(character_request)
    temperature = 1.0  # Claudeの既定値。ログ記録用（messages.parseはtemperature指定を受け付けない）

    async with llmops_logger.track_llm_request(
        model=model,
        temperature=temperature,
        prompt_content=prompt,
        user_id=user_id,
        metadata={
            "provider": "anthropic",
            "model": model,
            "response_format": "CharacterResponse",
            "character_request": character_request.model_dump(),
        },
    ) as tracking:
        result = await anthropic_client.messages.parse(
            model=model,
            max_tokens=4096,
            system=prompt[0]["content"],
            messages=[{"role": "user", "content": prompt[-1]["content"]}],
            output_format=CharacterResponse,
        )
        logger.info(result)
        tracking["response"] = result.parsed_output.model_dump() if result.parsed_output else None
        return result.parsed_output


async def batch_request_anthropic(
    character_requests: list[CharacterRequest],
    model: AnthropicModel,
    llmops_logger: LLMOpsLogger,
    user_id: str = "default_user",
    parallelism: int = 5,
) -> list[CharacterResponse]:
    """
    Process multiple character generation requests in batch using Anthropic.

    Args:
        character_requests: List of character generation requests
        model: Anthropic model to use
        llmops_logger: Logger for LLM operations
        user_id: User ID for logging
        parallelism: Maximum number of concurrent requests (default: 5)

    Returns:
        List of generated character responses
    """
    logger.info(
        f"Starting batch processing of {len(character_requests)} requests using Anthropic {model} "
        f"(parallelism: {parallelism})"
    )

    semaphore = asyncio.Semaphore(parallelism)

    async def request_with_semaphore(req: CharacterRequest) -> CharacterResponse:
        async with semaphore:
            return await request_anthropic(
                character_request=req,
                model=model,
                llmops_logger=llmops_logger,
                user_id=user_id,
            )

    tasks = [request_with_semaphore(req) for req in character_requests]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    successful_results = []
    failed_requests = []

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Request {i + 1} failed: {type(result).__name__}: {str(result)}")
            failed_requests.append(i)
        else:
            successful_results.append(result)

    logger.info(f"Batch processing completed. Successful: {len(successful_results)}, Failed: {len(failed_requests)}")

    if failed_requests:
        logger.warning(f"Failed request indices: {failed_requests}")

    return successful_results
