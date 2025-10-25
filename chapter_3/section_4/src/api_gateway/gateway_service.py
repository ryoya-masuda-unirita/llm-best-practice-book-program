"""Core gateway service for handling LLM API requests.

This service acts as the central point for all LLM API interactions,
providing unified access to multiple LLM providers.
"""

import hashlib
import json
import time
from typing import Any, Dict, Optional

from google import genai
from google.genai.types import GenerateContentConfig
from openai import AsyncOpenAI

from src.api_gateway.api_key_manager import api_key_manager
from src.api_gateway.monitoring import gateway_monitor
from src.api_gateway.retry_handler import retry_handler
from src.config import config
from src.logger import make_logger

logger = make_logger(__name__)


class GatewayCache:
    """Simple in-memory cache for LLM responses.

    In production, this would be replaced with Redis or similar distributed cache.
    """

    def __init__(self, enabled: bool = False, ttl: int = 300):
        """Initialize the cache.

        Args:
            enabled: Whether caching is enabled
            ttl: Time-to-live for cache entries in seconds
        """
        self.enabled = enabled
        self.ttl = ttl
        self._cache: Dict[str, tuple[Any, float]] = {}
        logger.info(f"Gateway cache initialized: enabled={enabled}, ttl={ttl}s")

    def _generate_cache_key(self, provider: str, model: str, prompt: list) -> str:
        """Generate a cache key from request parameters.

        Args:
            provider: LLM provider name
            model: Model name
            prompt: Prompt messages

        Returns:
            Cache key string
        """
        cache_data = f"{provider}:{model}:{json.dumps(prompt, sort_keys=True)}"
        return hashlib.sha256(cache_data.encode()).hexdigest()

    def get(self, provider: str, model: str, prompt: list) -> Optional[Any]:
        """Get a cached response if available and not expired.

        Args:
            provider: LLM provider name
            model: Model name
            prompt: Prompt messages

        Returns:
            Cached response or None if not found/expired
        """
        if not self.enabled:
            return None

        cache_key = self._generate_cache_key(provider, model, prompt)
        if cache_key in self._cache:
            content, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self.ttl:
                logger.debug(f"Cache hit for key: {cache_key[:16]}...")
                return content
            else:
                # Remove expired entry
                del self._cache[cache_key]
                logger.debug(f"Cache expired for key: {cache_key[:16]}...")

        return None

    def set(self, provider: str, model: str, prompt: list, content: Any) -> None:
        """Store a response in the cache.

        Args:
            provider: LLM provider name
            model: Model name
            prompt: Prompt messages
            content: Response content to cache
        """
        if not self.enabled:
            return

        cache_key = self._generate_cache_key(provider, model, prompt)
        self._cache[cache_key] = (content, time.time())
        logger.debug(f"Cached response for key: {cache_key[:16]}...")


class GatewayService:
    """Core gateway service for routing LLM requests to appropriate providers."""

    def __init__(self):
        """Initialize the gateway service."""
        self.cache = GatewayCache(enabled=config.gateway_enable_cache, ttl=config.gateway_cache_ttl)
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
        temperature: float,
        response_format: Optional[dict] = None,
    ) -> Any:
        """Call OpenAI API.

        Args:
            model: Model name
            prompt: Prompt messages
            temperature: Temperature for generation
            response_format: Response format schema

        Returns:
            Generated content
        """
        client = self._get_openai_client()

        if response_format:
            # Structured output mode
            result = await client.beta.chat.completions.parse(
                model=model,
                messages=prompt,
                response_format=response_format,
                temperature=temperature,
            )
            return result.choices[0].message.parsed
        else:
            # Standard chat completion
            result = await client.chat.completions.create(
                model=model,
                messages=prompt,
                temperature=temperature,
            )
            return result.choices[0].message.content

    async def _call_gemini(
        self,
        model: str,
        prompt: list[dict],
        temperature: float,
        response_format: Optional[dict] = None,
    ) -> Any:
        """Call Gemini API.

        Args:
            model: Model name
            prompt: Prompt messages
            temperature: Temperature for generation
            response_format: Response format schema

        Returns:
            Generated content
        """
        client = self._get_gemini_client()

        # Extract system instruction and user message
        system_instruction = prompt[0]["content"] if prompt[0]["role"] == "system" else None
        user_content = prompt[-1]["content"]

        config_params = {
            "temperature": temperature,
        }

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

        return result.parsed if response_format else result.text

    async def process_request(
        self,
        request_id: str,
        provider: str,
        model: str,
        prompt: list[dict],
        temperature: float = 1.0,
        response_format: Optional[dict] = None,
        client_id: Optional[str] = None,
    ) -> tuple[Any, float, bool]:
        """Process an LLM request through the gateway.

        Args:
            request_id: Unique request identifier
            provider: LLM provider name
            model: Model name
            prompt: Prompt messages
            temperature: Temperature for generation
            response_format: Response format schema
            client_id: Client identifier

        Returns:
            Tuple of (content, processing_time_ms, cached)

        Raises:
            ValueError: If provider is not supported
            Exception: If request fails after all retries
        """
        # Log the request
        gateway_monitor.log_request(request_id, provider, model, client_id)

        # Check cache
        cached_content = self.cache.get(provider, model, prompt)
        if cached_content is not None:
            gateway_monitor.log_cache_hit(request_id, provider, model)
            gateway_monitor.log_response(request_id, provider, model, 0, True, cached=True)
            return cached_content, 0, True

        gateway_monitor.log_cache_miss(request_id, provider, model)

        # Validate provider
        if not api_key_manager.is_provider_supported(provider):
            gateway_monitor.log_error(request_id, "UnsupportedProvider", f"Provider '{provider}' is not supported")
            raise ValueError(f"Unsupported provider: {provider}")

        start_time = time.time()

        try:
            # Route to appropriate provider with retry logic
            if provider.lower() == "openai":
                content = await retry_handler.execute_with_retry(
                    self._call_openai,
                    model=model,
                    prompt=prompt,
                    temperature=temperature,
                    response_format=response_format,
                )
            elif provider.lower() == "gemini":
                content = await retry_handler.execute_with_retry(
                    self._call_gemini,
                    model=model,
                    prompt=prompt,
                    temperature=temperature,
                    response_format=response_format,
                )
            else:
                raise ValueError(f"Unsupported provider: {provider}")

            processing_time_ms = (time.time() - start_time) * 1000

            # Cache the result
            self.cache.set(provider, model, prompt, content)

            # Log successful response
            gateway_monitor.log_response(request_id, provider, model, processing_time_ms, True, cached=False)

            return content, processing_time_ms, False

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
