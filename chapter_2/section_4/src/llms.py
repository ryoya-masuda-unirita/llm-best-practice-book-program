from google import genai
from google.genai.types import GenerateContentConfig, HttpOptions, HttpRetryOptions
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field
from src.config import config
from src.logger import make_logger
from src.model import FailedResponse

logger = make_logger(__name__)

google_genai_client = genai.Client(api_key=config.gemini_api_key)

openai_client = AsyncOpenAI(api_key=config.openai_api_key)


class LLMRequestRetryOptions(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    timeout_second: int = Field(description="Timeout seconds", default=10)
    max_retries: int = Field(description="Max retries", default=3)
    do_exponential_backoff: bool = Field(description="Do exponential backoff", default=False)
    exponential_backoff_factor: float = Field(description="Exponential backoff factor", default=2.0)
    max_backoff: int = Field(description="Max backoff", default=60)
    jitter: float = Field(description="Jitter", default=1.0)

    def to_google_genai_http_options(self) -> HttpOptions:
        """Convert to Google GenAI HTTP options."""
        return HttpOptions(
            timeout=self.timeout_second * 1000,  # Convert seconds to milliseconds
            retry_options=HttpRetryOptions(
                attempts=self.max_retries,
                exp_base=self.exponential_backoff_factor if self.do_exponential_backoff else 1.0,
                max_delay=self.max_backoff,
                jitter=self.jitter,
            ),
        )


class LLMClientWithFallback:
    def __init__(
        self,
        primary_client: AsyncOpenAI | genai.Client,
        fallback_client: AsyncOpenAI | genai.Client,
    ):
        self.primary_client = primary_client
        self.fallback_client = fallback_client

    async def _request_with_client(
        self,
        client: AsyncOpenAI | genai.Client,
        prompt: list[dict],
        result_type: type[BaseModel],
        retry_options: LLMRequestRetryOptions,
    ) -> BaseModel:
        """Helper method to make a request with a specific client."""
        if isinstance(client, AsyncOpenAI):
            return await self.request_structured_openai(
                client=client,
                prompt=prompt,
                result_type=result_type,
                retry_options=retry_options,
            )
        elif isinstance(client, genai.Client):
            return await self.request_structured_gemini(
                client=client,
                prompt=prompt,
                result_type=result_type,
                retry_options=retry_options,
            )
        else:
            raise ValueError(f"Unsupported client type: {type(client)}")

    async def _try_client_request(
        self,
        client: AsyncOpenAI | genai.Client,
        prompt: list[dict],
        result_type: type[BaseModel],
        retry_options: LLMRequestRetryOptions,
    ) -> tuple[BaseModel | None, str | None]:
        """Try to make a request with a client and return the result or error message."""
        try:
            result = await self._request_with_client(
                client=client,
                prompt=prompt,
                result_type=result_type,
                retry_options=retry_options,
            )
            return result, None
        except Exception as e:
            error_msg = str(e)
            return None, error_msg

    async def request_with_fallback(
        self,
        prompt: list[dict],
        result_type: type[BaseModel],
        retry_options: LLMRequestRetryOptions,
    ) -> BaseModel | FailedResponse:
        # Try primary client
        primary_result, primary_error = await self._try_client_request(
            client=self.primary_client,
            prompt=prompt,
            result_type=result_type,
            retry_options=retry_options,
        )

        # If primary client succeeded, return the result
        if primary_result is not None:
            return primary_result

        # Log primary error and try fallback client
        logger.error(f"Primary client failed with error: {primary_error}. Falling back to secondary client.")

        # Try fallback client
        fallback_result, fallback_error = await self._try_client_request(
            client=self.fallback_client,
            prompt=prompt,
            result_type=result_type,
            retry_options=retry_options,
        )

        # If fallback client succeeded, return the result
        if fallback_result is not None:
            return fallback_result

        # Both clients failed, log fallback error and return FailedResponse
        logger.error(f"Fallback client also failed with error: {fallback_error}")
        error_message = f"Both primary and fallback LLM requests failed. Primary error: {primary_error}. Fallback error: {fallback_error}"
        return FailedResponse(error=error_message)

    @staticmethod
    async def request_structured_openai(
        client: AsyncOpenAI,
        prompt: list[dict],
        result_type: type[BaseModel],
        retry_options: LLMRequestRetryOptions,
    ) -> BaseModel:
        import asyncio
        import random

        from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError

        # If exponential backoff is not enabled, just use the built-in retry mechanism
        if not retry_options.do_exponential_backoff:
            client_with_retries = AsyncOpenAI(
                api_key=client.api_key,
                organization=client.organization,
                max_retries=retry_options.max_retries,
                timeout=retry_options.timeout_second,
            )

            result = await client_with_retries.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=prompt,
                response_format=result_type,
                temperature=1.0,
            )
            return result.choices[0].message.parsed

        # If exponential backoff is enabled, implement custom retry logic
        retries = 0
        last_exception = None

        while retries <= retry_options.max_retries:
            try:
                result = await client.beta.chat.completions.parse(
                    model="gpt-4o-mini",
                    messages=prompt,
                    response_format=result_type,
                    temperature=1.0,
                    timeout=retry_options.timeout_second,
                )
                return result.choices[0].message.parsed
            except (APIError, RateLimitError, APITimeoutError, APIConnectionError) as e:
                last_exception = e
                retries += 1

                if retries > retry_options.max_retries:
                    break

                # Calculate backoff with exponential factor and jitter
                backoff = min(retry_options.max_backoff, (2**retries) * retry_options.exponential_backoff_factor)

                # Apply jitter if configured
                if retry_options.jitter > 0:
                    jitter_factor = 1 - (random.random() * retry_options.jitter * 0.5)
                    backoff = backoff * jitter_factor

                # Log the retry attempt
                logger.warning(
                    f"OpenAI API request failed with {type(e).__name__}: {str(e)}. "
                    f"Retrying in {backoff:.2f} seconds (attempt {retries}/{retry_options.max_retries})."
                )

                # Wait before retrying
                await asyncio.sleep(backoff)

        # If we've exhausted all retries, raise the last exception
        if last_exception:
            raise last_exception

        # This should never happen, but just in case
        raise RuntimeError("Unexpected error in request_structured_openai")

    @staticmethod
    async def request_structured_gemini(
        client: genai.Client,
        prompt: list[dict],
        result_type: type[BaseModel],
        retry_options: LLMRequestRetryOptions,
    ) -> BaseModel:
        result = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt[-1]["content"],
            config=GenerateContentConfig(
                system_instruction=prompt[0]["content"],
                response_mime_type="application/json",
                response_schema=result_type,
                temperature=2.0,
                http_options=retry_options.to_google_genai_http_options(),
            ),
        )
        return result.parsed
