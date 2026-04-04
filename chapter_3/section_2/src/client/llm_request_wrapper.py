"""LLM request wrapper with timeout and fallback handling."""

from typing import Optional

from google.genai.types import GenerateContentConfig
from src.client.llm_client import GeminiModel, LLMProvider, OpenAIModel, google_genai_client, openai_client
from src.logger import make_logger
from src.model.model import CharacterResponse
from src.service.fallback_coordinator import FallbackCoordinator, FallbackStrategy

logger = make_logger(__name__)


class LLMRequestWrapper:
    """Wrapper for LLM requests with timeout and fallback handling."""

    def __init__(self, fallback_coordinator: FallbackCoordinator):
        self.fallback_coordinator = fallback_coordinator

    async def request_openai(
        self,
        prompt: str | list[dict],
        model: OpenAIModel = OpenAIModel.GPT_5_4_MINI,
        alternative_model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH,
        with_fallback: bool = True,
    ) -> tuple[CharacterResponse, Optional[FallbackStrategy], Optional[str]]:
        """Request character generation from OpenAI with optional fallback to Gemini."""
        return await self._make_request(
            primary_provider=LLMProvider.OPENAI,
            primary_func=lambda: self._request_openai_internal(prompt, model),
            alternative_func=lambda: self._request_gemini_internal(prompt, alternative_model),
            prompt=prompt,
            model=model,
            with_fallback=with_fallback,
        )

    async def request_gemini(
        self,
        prompt: str | list[dict],
        model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH,
        alternative_model: OpenAIModel = OpenAIModel.GPT_5_4_MINI,
        with_fallback: bool = True,
    ) -> tuple[CharacterResponse, Optional[FallbackStrategy], Optional[str]]:
        """Request character generation from Gemini with optional fallback to OpenAI."""
        return await self._make_request(
            primary_provider=LLMProvider.GEMINI,
            primary_func=lambda: self._request_gemini_internal(prompt, model),
            alternative_func=lambda: self._request_openai_internal(prompt, alternative_model),
            prompt=prompt,
            model=model,
            with_fallback=with_fallback,
        )

    async def _make_request(
        self,
        primary_provider: LLMProvider,
        primary_func,
        alternative_func,
        prompt: str | list[dict],
        model: str,
        with_fallback: bool,
    ) -> tuple[CharacterResponse, Optional[FallbackStrategy], Optional[str]]:
        """Make an LLM request with optional fallback handling."""
        if with_fallback:
            return await self.fallback_coordinator.request_with_fallback(
                primary_provider=primary_provider,
                primary_request_func=primary_func,
                alternative_request_func=alternative_func,
                prompt=prompt,
                model=model,
            )
        else:
            response = await primary_func()
            return response, None, None

    async def _request_gemini_internal(
        self, prompt: str | list[dict], model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH
    ) -> CharacterResponse:
        """Internal method for Gemini API requests."""
        result = await google_genai_client.aio.models.generate_content(
            model=model,
            contents=prompt[-1]["content"],
            config=GenerateContentConfig(
                system_instruction=prompt[0]["content"],
                response_mime_type="application/json",
                response_schema=CharacterResponse,
            ),
        )
        return result.parsed

    async def _request_openai_internal(
        self, prompt: str | list[dict], model: OpenAIModel = OpenAIModel.GPT_5_4_MINI
    ) -> CharacterResponse:
        """Internal method for OpenAI API requests."""
        result = await openai_client.responses.parse(
            model=model,
            input=prompt,
            text_format=CharacterResponse,
        )
        return result.output_parsed
