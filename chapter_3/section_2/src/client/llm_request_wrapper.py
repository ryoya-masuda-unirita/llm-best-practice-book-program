"""LLM request wrapper with timeout and fallback handling."""

from typing import Optional

from src.client.llm_client import AnthropicModel, LLMProvider, OpenAIModel, anthropic_client, openai_client
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
        model: OpenAIModel = OpenAIModel.GPT_5_4,
        alternative_model: AnthropicModel = AnthropicModel.CLAUDE_HAIKU_4_5,
        with_fallback: bool = True,
    ) -> tuple[CharacterResponse, Optional[FallbackStrategy], Optional[str]]:
        """Request character generation from OpenAI with optional fallback to Anthropic."""
        return await self._make_request(
            primary_provider=LLMProvider.OPENAI,
            primary_func=lambda: self._request_openai_internal(prompt, model),
            alternative_func=lambda: self._request_anthropic_internal(prompt, alternative_model),
            prompt=prompt,
            model=model,
            with_fallback=with_fallback,
        )

    async def request_anthropic(
        self,
        prompt: str | list[dict],
        model: AnthropicModel = AnthropicModel.CLAUDE_HAIKU_4_5,
        alternative_model: OpenAIModel = OpenAIModel.GPT_5_4,
        with_fallback: bool = True,
    ) -> tuple[CharacterResponse, Optional[FallbackStrategy], Optional[str]]:
        """Request character generation from Anthropic with optional fallback to OpenAI."""
        return await self._make_request(
            primary_provider=LLMProvider.ANTHROPIC,
            primary_func=lambda: self._request_anthropic_internal(prompt, model),
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

    async def _request_anthropic_internal(
        self, prompt: str | list[dict], model: AnthropicModel = AnthropicModel.CLAUDE_HAIKU_4_5
    ) -> CharacterResponse:
        """Internal method for Anthropic API requests."""
        result = await anthropic_client.messages.parse(
            model=model,
            max_tokens=4096,
            system=prompt[0]["content"],
            messages=[{"role": "user", "content": prompt[-1]["content"]}],
            output_format=CharacterResponse,
        )
        return result.parsed_output

    async def _request_openai_internal(
        self, prompt: str | list[dict], model: OpenAIModel = OpenAIModel.GPT_5_4
    ) -> CharacterResponse:
        """Internal method for OpenAI API requests."""
        result = await openai_client.responses.parse(
            model=model,
            input=prompt,
            text_format=CharacterResponse,
        )
        return result.output_parsed
