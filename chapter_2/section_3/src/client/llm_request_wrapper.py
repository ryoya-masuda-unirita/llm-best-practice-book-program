"""LLM request wrapper with timeout and fallback handling."""

from typing import Optional

from google.genai.types import GenerateContentConfig

from src.client.llm_client import GeminiModel, LLMProvider, OpenAIModel, google_genai_client, openai_client
from src.logger import make_logger
from src.model.model import CharacterResponse
from src.service.fallback_coordinator import FallbackCoordinator, FallbackStrategy

logger = make_logger(__name__)


class LLMRequestWrapper:
    """
    Wrapper for LLM requests with comprehensive timeout and fallback handling.

    This class encapsulates the logic for making LLM requests with automatic
    fallback strategies including caching, alternative providers, and templates.
    """

    def __init__(
        self,
        fallback_coordinator: FallbackCoordinator,
    ):
        """
        Initialize the LLM request wrapper.

        Args:
            cache_manager: Optional CacheManager instance
            template_generator: Optional TemplateResponseGenerator instance
            timeout: Optional timeout in seconds
        """
        self.fallback_coordinator = fallback_coordinator

    async def request_openai(
        self,
        prompt: str | list[dict],
        model: OpenAIModel = OpenAIModel.GPT_4O_MINI,
        alternative_model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH,
        with_fallback: bool = True,
    ) -> tuple[CharacterResponse, Optional[FallbackStrategy], Optional[str]]:
        """
        Request character generation from OpenAI.

        Args:
            with_fallback: If True, use fallback strategies on failure

        Returns:
            Tuple of (response, strategy_used, error_reason)
        """
        temperature = 1.0

        async def primary_request():
            return await self._request_openai_internal(prompt=prompt, model=model)

        # Use alternative provider (Gemini) as fallback
        async def alternative_request():
            return await self._request_gemini_internal(prompt=prompt, model=alternative_model)

        if with_fallback:
            return await self.fallback_coordinator.request_with_fallback(
                primary_provider=LLMProvider.OPENAI,
                primary_request_func=primary_request,
                alternative_request_func=alternative_request,
                prompt=prompt,
                model=model,
                temperature=temperature,
            )
        else:
            # No fallback - direct request
            response = await primary_request()
            return response, None, None

    async def request_gemini(
        self,
        prompt: str | list[dict],
        model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH,
        alternative_model: OpenAIModel = OpenAIModel.GPT_4O_MINI,
        with_fallback: bool = True,
    ) -> tuple[CharacterResponse, Optional[FallbackStrategy], Optional[str]]:
        """
        Request character generation from Gemini.

        Args:
            with_fallback: If True, use fallback strategies on failure

        Returns:
            Tuple of (response, strategy_used, error_reason)
        """
        temperature = 2.0

        async def primary_request():
            return await self._request_gemini_internal(prompt=prompt, model=model)

        # Use alternative provider (OpenAI) as fallback
        async def alternative_request():
            return self._request_openai_internal(prompt=prompt, model=alternative_model)

        if with_fallback:
            return await self.fallback_coordinator.request_with_fallback(
                primary_provider=LLMProvider.GEMINI,
                primary_request_func=primary_request,
                alternative_request_func=alternative_request,
                prompt=prompt,
                model=model,
                temperature=temperature,
            )
        else:
            # No fallback - direct request
            response = await primary_request()
            return response, None, None

    async def _request_gemini_internal(
        self,
        prompt: str | list[dict],
        model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH,
    ) -> CharacterResponse:
        """Internal method for Gemini requests."""
        result = await google_genai_client.aio.models.generate_content(
            model=model,
            contents=prompt[-1]["content"],
            config=GenerateContentConfig(
                system_instruction=prompt[0]["content"],
                response_mime_type="application/json",
                response_schema=CharacterResponse,
                temperature=2.0,
            ),
        )
        return result.parsed

    async def _request_openai_internal(
        self,
        prompt: str | list[dict],
        model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH,
    ) -> CharacterResponse:
        """Internal method for Gemini requests."""
        result = await openai_client.beta.chat.completions.parse(
            model=model,
            messages=prompt,
            response_format=CharacterResponse,
            temperature=1.0,
        )
        return result.choices[0].message.parsed
