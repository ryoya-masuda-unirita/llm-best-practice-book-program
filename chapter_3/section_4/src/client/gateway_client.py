"""Client for communicating with the LLM API Gateway.

This client encapsulates all communication with the gateway server,
allowing services to request LLM completions without managing API keys directly.
"""

from typing import Any, Optional

import httpx

from src.config import config
from src.logger import make_logger

logger = make_logger(__name__)


class GatewayClient:
    """Client for making requests to the LLM API Gateway."""

    def __init__(self, gateway_url: Optional[str] = None):
        """Initialize the gateway client.

        Args:
            gateway_url: Base URL of the gateway server (defaults to config value)
        """
        self.gateway_url = gateway_url or config.gateway_url
        self.client = httpx.AsyncClient(timeout=60.0)
        logger.info(f"Gateway client initialized with URL: {self.gateway_url}")

    async def generate(
        self,
        provider: str,
        model: str,
        prompt: list[dict],
        temperature: float = 1.0,
        response_format: Optional[dict] = None,
        client_id: Optional[str] = None,
    ) -> tuple[Any, float, str]:
        """Generate content via the gateway.

        Args:
            provider: LLM provider name (openai or gemini)
            model: Model name to use
            prompt: Prompt messages
            temperature: Temperature for generation
            response_format: Response format schema
            client_id: Client identifier for tracking

        Returns:
            Tuple of (content, processing_time_ms, request_id)

        Raises:
            httpx.HTTPError: If the request fails
            Exception: If the gateway returns an error
        """
        request_data = {
            "provider": provider,
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "response_format": response_format,
            "client_id": client_id,
        }

        logger.debug(f"Sending request to gateway: provider={provider}, model={model}")

        try:
            response = await self.client.post(
                f"{self.gateway_url}/v1/generate",
                json=request_data,
            )
            response.raise_for_status()

            result = response.json()
            logger.info(
                f"Gateway response received: request_id={result.get('request_id')}, "
                f"time={result.get('processing_time_ms', 0):.2f}ms"
            )

            return (
                result["content"],
                result["processing_time_ms"],
                result["request_id"],
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"Gateway request failed with status {e.response.status_code}: {e.response.text}")
            raise Exception(f"Gateway error: {e.response.text}")
        except httpx.HTTPError as e:
            logger.error(f"Gateway request failed: {type(e).__name__}: {str(e)}")
            raise Exception(f"Failed to connect to gateway: {str(e)}")

    async def health_check(self) -> dict:
        """Check the health of the gateway.

        Returns:
            Gateway health response

        Raises:
            Exception: If health check fails
        """
        try:
            response = await self.client.get(f"{self.gateway_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Gateway health check failed: {str(e)}")
            raise Exception(f"Gateway health check failed: {str(e)}")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global gateway client instance
gateway_client = GatewayClient()
