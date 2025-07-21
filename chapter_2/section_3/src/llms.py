from google import genai
from google.genai.types import GenerateContentConfig, HttpOptions
from openai import AsyncOpenAI
from pydantic import BaseModel
from src.config import config
from src.logger import make_logger
from src.model import FailedResponse

logger = make_logger(__name__)

google_genai_client = genai.Client(api_key=config.gemini_api_key)

openai_client = AsyncOpenAI(api_key=config.openai_api_key)


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
        timeout_second: int = 10,
    ) -> BaseModel:
        """Helper method to make a request with a specific client."""
        if isinstance(client, AsyncOpenAI):
            return await self.request_structured_openai(
                client=client,
                prompt=prompt,
                result_type=result_type,
                timeout_second=timeout_second,
            )
        elif isinstance(client, genai.Client):
            return await self.request_structured_gemini(
                client=client,
                prompt=prompt,
                result_type=result_type,
                timeout_second=timeout_second,
            )
        else:
            raise ValueError(f"Unsupported client type: {type(client)}")

    async def _try_client_request(
        self,
        client: AsyncOpenAI | genai.Client,
        prompt: list[dict],
        result_type: type[BaseModel],
        timeout_second: int = 10,
    ) -> tuple[BaseModel | None, str | None]:
        """Try to make a request with a client and return the result or error message."""
        try:
            result = await self._request_with_client(
                client=client,
                prompt=prompt,
                result_type=result_type,
                timeout_second=timeout_second,
            )
            return result, None
        except Exception as e:
            error_msg = str(e)
            return None, error_msg

    async def request_with_fallback(
        self,
        prompt: list[dict],
        result_type: type[BaseModel],
        timeout_second: int = 10,
    ) -> BaseModel | FailedResponse:
        # Try primary client
        primary_result, primary_error = await self._try_client_request(
            client=self.primary_client,
            prompt=prompt,
            result_type=result_type,
            timeout_second=timeout_second,
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
            timeout_second=timeout_second,
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
        timeout_second: int = 10,
    ) -> BaseModel:
        result = await client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=prompt,
            response_format=result_type,
            temperature=1.0,
            timeout=timeout_second,
        )
        return result.choices[0].message.parsed

    @staticmethod
    async def request_structured_gemini(
        client: genai.Client,
        prompt: list[dict],
        result_type: type[BaseModel],
        timeout_second: int = 10,
    ) -> BaseModel:
        result = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt[-1]["content"],
            config=GenerateContentConfig(
                system_instruction=prompt[0]["content"],
                response_mime_type="application/json",
                response_schema=result_type,
                temperature=2.0,
                http_options=HttpOptions(
                    timeout=timeout_second * 1000  # Convert seconds to milliseconds
                ),
            ),
        )
        return result.parsed
