"""Core gateway service for handling LLM API requests.

This service acts as the central point for all LLM API interactions,
providing unified access to multiple LLM providers with centralized API key management.
"""

import time
from typing import Any, Optional

from google import genai
from google.genai.types import GenerateContentConfig
from openai import AsyncOpenAI
from pydantic import BaseModel

from src.api_gateway.api_key_manager import api_key_manager
from src.api_gateway.monitoring import gateway_monitor
from src.logger import make_logger

logger = make_logger(__name__)


class GatewayService:
    """Core gateway service for routing LLM requests to appropriate providers."""

    def __init__(self):
        """Initialize the gateway service."""
        self._openai_client: Optional[AsyncOpenAI] = None
        self._gemini_client: Optional[genai.Client] = None
        logger.info("Gateway service initialized")

    def _get_openai_client(self) -> AsyncOpenAI:
        """Get or create OpenAI client with managed API key.

        Returns:
            Configured OpenAI client
        """
        if self._openai_client is None:
            api_key = api_key_manager.get_api_key("openai")
            self._openai_client = AsyncOpenAI(api_key=api_key)
            logger.info("OpenAI client initialized")
        return self._openai_client

    def _get_gemini_client(self) -> genai.Client:
        """Get or create Gemini client with managed API key.

        Returns:
            Configured Gemini client
        """
        if self._gemini_client is None:
            api_key = api_key_manager.get_api_key("gemini")
            self._gemini_client = genai.Client(api_key=api_key)
            logger.info("Gemini client initialized")
        return self._gemini_client

    async def _call_openai(
        self,
        model: str,
        prompt: list[dict],
        response_format: BaseModel,
    ) -> Any:
        """Call OpenAI API.

        Args:
            model: Model name
            prompt: Prompt messages
            response_format: Response format schema

        Returns:
            Generated content
        """
        client = self._get_openai_client()

        # Structured output mode
        result = await client.beta.chat.completions.parse(
            model=model,
            messages=prompt,
            response_format=response_format,
        )
        return result.choices[0].message.parsed

    async def _call_gemini(
        self,
        model: str,
        prompt: list[dict],
        response_format: BaseModel,
    ) -> Any:
        """Call Gemini API.

        Args:
            model: Model name
            prompt: Prompt messages
            response_format: Response format schema

        Returns:
            Generated content
        """
        client = self._get_gemini_client()

        # Extract system instruction and user message
        system_instruction = prompt[0]["content"] if prompt[0]["role"] == "system" else None
        user_content = prompt[-1]["content"]

        config_params = {}

        if system_instruction:
            config_params["system_instruction"] = system_instruction

        if response_format:
            config_params["response_mime_type"] = "application/json"
            config_params["response_schema"] = response_format

        result = await client.aio.models.generate_content(
            model=model,
            contents=user_content,
            config=GenerateContentConfig(**config_params),
        )

        return result.parsed

    async def process_request(
        self,
        request_id: str,
        provider: str,
        model: str,
        prompt: list[dict],
        response_format: BaseModel,
        client_id: Optional[str] = None,
    ) -> tuple[Any, float]:
        """Process an LLM request through the gateway.

        Args:
            request_id: Unique request identifier
            provider: LLM provider name
            model: Model name
            prompt: Prompt messages
            response_format: Response format schema
            client_id: Client identifier

        Returns:
            Tuple of (content, processing_time_ms)

        Raises:
            ValueError: If provider is not supported
            Exception: If request fails
        """
        # Log the request
        gateway_monitor.log_request(request_id, provider, model, client_id)

        # Validate provider
        if not api_key_manager.is_provider_supported(provider):
            gateway_monitor.log_error(request_id, "UnsupportedProvider", f"Provider '{provider}' is not supported")
            raise ValueError(f"Unsupported provider: {provider}")

        start_time = time.time()

        try:
            # Route to appropriate provider
            if provider.lower() == "openai":
                content = await self._call_openai(
                    model=model,
                    prompt=prompt,
                    response_format=response_format,
                )
            elif provider.lower() == "gemini":
                content = await self._call_gemini(
                    model=model,
                    prompt=prompt,
                    response_format=response_format,
                )
            else:
                raise ValueError(f"Unsupported provider: {provider}")

            processing_time_ms = (time.time() - start_time) * 1000

            # Log successful response
            gateway_monitor.log_response(request_id, provider, model, processing_time_ms, True)

            return content, processing_time_ms

        except Exception as e:
            processing_time_ms = (time.time() - start_time) * 1000
            gateway_monitor.log_error(
                request_id,
                type(e).__name__,
                str(e),
                provider,
                model,
            )
            gateway_monitor.log_response(request_id, provider, model, processing_time_ms, False, error=str(e))
            raise


# Global gateway service instance
gateway_service = GatewayService()
