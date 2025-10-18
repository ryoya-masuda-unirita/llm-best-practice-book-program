import asyncio
import random
from functools import wraps
from typing import Any, Callable

from google.api_core import exceptions as google_exceptions
from google.genai.types import GenerateContentConfig
from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError

from src.client.llm_client import GeminiModel, OpenAIModel, google_genai_client, openai_client
from src.logger import make_logger
from src.model.model import CharacterRequest, CharacterResponse
from src.prompt.prompt import make_prompt
from src.service.llmops_logger import LLMOpsLogger

logger = make_logger(__name__)


# Retry configuration
MAX_RETRIES = 5
MAX_BACKOFF_SECONDS = 60
BASE_BACKOFF_SECONDS = 1
JITTER_MIN = 0.1  # 10% jitter
JITTER_MAX = 0.5  # 50% jitter

# Error codes that should trigger retry
RETRYABLE_STATUS_CODES = {429, 500, 503, 502, 504}


def calculate_backoff_with_jitter(attempt: int, base: float = BASE_BACKOFF_SECONDS) -> float:
    """Calculate exponential backoff time with random jitter."""
    # Exponential backoff: base * 2^attempt
    backoff = min(base * (2**attempt), MAX_BACKOFF_SECONDS)

    # Add random jitter (10-50% of backoff time)
    jitter_range = backoff * (JITTER_MAX - JITTER_MIN)
    jitter = random.uniform(backoff * JITTER_MIN, backoff * JITTER_MIN + jitter_range)

    return backoff + jitter


def should_retry_error(error: Exception) -> tuple[bool, int | None]:
    """
    Determine if an error should be retried and extract retry-after if available.

    Returns:
        tuple: (should_retry: bool, retry_after_seconds: int | None)
    """
    # OpenAI errors
    if isinstance(error, RateLimitError):
        # Check for Retry-After header in rate limit errors
        retry_after = None
        if hasattr(error, "response") and error.response is not None:
            retry_after_header = error.response.headers.get("Retry-After")
            if retry_after_header:
                try:
                    retry_after = int(retry_after_header)
                except ValueError:
                    pass
        return True, retry_after

    if isinstance(error, (APITimeoutError, APIConnectionError)):
        return True, None

    if isinstance(error, APIError):
        if hasattr(error, "status_code") and error.status_code in RETRYABLE_STATUS_CODES:
            return True, None
        return False, None

    # Google Gemini errors
    if isinstance(error, google_exceptions.ResourceExhausted):
        return True, None

    if isinstance(
        error,
        (
            google_exceptions.ServiceUnavailable,
            google_exceptions.InternalServerError,
            google_exceptions.DeadlineExceeded,
        ),
    ):
        return True, None

    # Unknown errors - don't retry
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

                    # Calculate backoff time
                    if retry_after is not None:
                        # Respect Retry-After header
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

            # This should never be reached, but just in case
            raise last_exception

        return wrapper

    return decorator


@retry_with_exponential_backoff()
async def request_openai(
    character_request: CharacterRequest,
    model: OpenAIModel,
    llmops_logger: LLMOpsLogger,
    user_id: str = "default_user",
) -> CharacterResponse:
    """Request character generation from OpenAI with structured logging and retry logic."""
    prompt = make_prompt(character_request)
    temperature = 1.0

    async with llmops_logger.track_llm_request(
        model=model,
        temperature=temperature,
        prompt_content=prompt,
        user_id=user_id,
        metadata={
            "provider": "openai",
            "model": model,
            "response_format": "CharacterResponse",
            "character_request": character_request.model_dump(),
        },
    ) as tracking:
        result = await openai_client.beta.chat.completions.parse(
            model=model,
            messages=prompt,
            response_format=CharacterResponse,
            temperature=temperature,
        )
        parsed_response = result.choices[0].message.parsed
        tracking["response"] = parsed_response.model_dump() if parsed_response else None
        return parsed_response


@retry_with_exponential_backoff()
async def request_gemini(
    character_request: CharacterRequest,
    model: GeminiModel,
    llmops_logger: LLMOpsLogger,
    user_id: str = "default_user",
) -> CharacterResponse:
    """Request character generation from Gemini with structured logging and retry logic."""
    prompt = make_prompt(character_request)
    temperature = 2.0

    async with llmops_logger.track_llm_request(
        model=model,
        temperature=temperature,
        prompt_content=prompt,
        user_id=user_id,
        metadata={
            "provider": "gemini",
            "model": model,
            "response_format": "CharacterResponse",
            "character_request": character_request.model_dump(),
        },
    ) as tracking:
        result = await google_genai_client.aio.models.generate_content(
            model=model,
            contents=prompt[-1]["content"],
            config=GenerateContentConfig(
                system_instruction=prompt[0]["content"],
                response_mime_type="application/json",
                response_schema=CharacterResponse,
                temperature=temperature,
            ),
        )
        logger.info(result)
        tracking["response"] = result.parsed.model_dump() if result.parsed else None
        return result.parsed


async def batch_request_openai(
    character_requests: list[CharacterRequest],
    model: OpenAIModel,
    llmops_logger: LLMOpsLogger,
    user_id: str = "default_user",
    parallelism: int = 5,
) -> list[CharacterResponse]:
    """
    Process multiple character generation requests in batch using OpenAI.

    Args:
        character_requests: List of character generation requests
        model: OpenAI model to use
        llmops_logger: Logger for LLM operations
        user_id: User ID for logging
        parallelism: Maximum number of concurrent requests (default: 5)

    Returns:
        List of generated character responses
    """
    logger.info(
        f"Starting batch processing of {len(character_requests)} requests using OpenAI {model} "
        f"(parallelism: {parallelism})"
    )

    # Create semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(parallelism)

    async def request_with_semaphore(req: CharacterRequest) -> CharacterResponse:
        """Wrapper to execute request with semaphore."""
        async with semaphore:
            return await request_openai(
                character_request=req,
                model=model,
                llmops_logger=llmops_logger,
                user_id=user_id,
            )

    # Process all requests with controlled concurrency
    tasks = [request_with_semaphore(req) for req in character_requests]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Separate successful results from errors
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


async def batch_request_gemini(
    character_requests: list[CharacterRequest],
    model: GeminiModel,
    llmops_logger: LLMOpsLogger,
    user_id: str = "default_user",
    parallelism: int = 5,
) -> list[CharacterResponse]:
    """
    Process multiple character generation requests in batch using Gemini.

    Args:
        character_requests: List of character generation requests
        model: Gemini model to use
        llmops_logger: Logger for LLM operations
        user_id: User ID for logging
        parallelism: Maximum number of concurrent requests (default: 5)

    Returns:
        List of generated character responses
    """
    logger.info(
        f"Starting batch processing of {len(character_requests)} requests using Gemini {model} "
        f"(parallelism: {parallelism})"
    )

    # Create semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(parallelism)

    async def request_with_semaphore(req: CharacterRequest) -> CharacterResponse:
        """Wrapper to execute request with semaphore."""
        async with semaphore:
            return await request_gemini(
                character_request=req,
                model=model,
                llmops_logger=llmops_logger,
                user_id=user_id,
            )

    # Process all requests with controlled concurrency
    tasks = [request_with_semaphore(req) for req in character_requests]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Separate successful results from errors
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
