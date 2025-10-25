"""Example client demonstrating how to use the LLM API Gateway.

This shows how application services can use the gateway instead of
calling LLM APIs directly, benefiting from centralized management
and security.
"""

import asyncio

import httpx

from src.config import config
from src.logger import make_logger

logger = make_logger(__name__)


class GatewayClient:
    """Client for interacting with the LLM API Gateway.

    This client hides the complexity of authentication, retry logic,
    and provider-specific implementations from the application.
    """

    def __init__(self, gateway_url: str, api_token: str):
        """Initialize the gateway client.

        Args:
            gateway_url: URL of the gateway service
            api_token: API token for gateway authentication
        """
        self.gateway_url = gateway_url.rstrip("/")
        self.api_token = api_token
        self.client = httpx.AsyncClient(timeout=60.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def generate(
        self,
        provider: str,
        model: str,
        prompt: list[dict[str, str]],
        temperature: float = 1.0,
        response_format: dict = None,
    ) -> dict:
        """Generate content using LLM through the gateway.

        Args:
            provider: LLM provider (openai or gemini)
            model: Model name
            prompt: Prompt messages
            temperature: Temperature for generation
            response_format: Optional response format schema

        Returns:
            Gateway response with generated content

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "provider": provider,
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "api_token": self.api_token,
        }

        if response_format:
            payload["response_format"] = response_format

        logger.info(f"Sending request to gateway: {provider}/{model}")

        response = await self.client.post(
            f"{self.gateway_url}/v1/generate",
            json=payload,
            headers=headers,
        )

        response.raise_for_status()
        result = response.json()

        logger.info(
            f"Received response from gateway: request_id={result.get('request_id')}, "
            f"cached={result.get('cached')}, "
            f"processing_time={result.get('processing_time_ms')}ms"
        )

        return result

    async def health_check(self) -> dict:
        """Check gateway health status.

        Returns:
            Health status response
        """
        response = await self.client.get(f"{self.gateway_url}/health")
        response.raise_for_status()
        return response.json()


async def example_usage():
    """Example demonstrating gateway client usage."""

    # Initialize gateway client
    # Note: Applications only need the gateway URL and token,
    # NOT the actual LLM API keys!
    gateway_client = GatewayClient(
        gateway_url=config.proxy_url,  # Gateway URL
        api_token=config.gateway_api_token.get_secret_value(),
    )

    try:
        # Check gateway health
        logger.info("Checking gateway health...")
        health = await gateway_client.health_check()
        logger.info(f"Gateway health: {health}")

        # Example 1: Generate content using OpenAI
        logger.info("\n--- Example 1: OpenAI Request ---")
        prompt = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Write a haiku about programming."},
        ]

        response = await gateway_client.generate(
            provider="openai",
            model="gpt-4o-mini",
            prompt=prompt,
            temperature=0.7,
        )

        logger.info(f"OpenAI Response: {response['content']}")
        logger.info(f"Processing time: {response['processing_time_ms']}ms")
        logger.info(f"Cached: {response['cached']}")

        # Example 2: Generate content using Gemini
        logger.info("\n--- Example 2: Gemini Request ---")
        prompt = [
            {"role": "system", "content": "You are a creative writer."},
            {"role": "user", "content": "Write a short story opening about a robot."},
        ]

        response = await gateway_client.generate(
            provider="gemini",
            model="gemini-2.5-flash",
            prompt=prompt,
            temperature=1.0,
        )

        logger.info(f"Gemini Response: {response['content']}")
        logger.info(f"Processing time: {response['processing_time_ms']}ms")
        logger.info(f"Cached: {response['cached']}")

        # Example 3: Retry the same request (should be cached)
        logger.info("\n--- Example 3: Cached Request ---")
        response = await gateway_client.generate(
            provider="gemini",
            model="gemini-2.5-flash",
            prompt=prompt,
            temperature=1.0,
        )

        logger.info(f"Cached: {response['cached']}")
        logger.info(f"Processing time: {response['processing_time_ms']}ms")

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logger.error(f"Error occurred: {type(e).__name__}: {str(e)}")
    finally:
        await gateway_client.close()


if __name__ == "__main__":
    logger.info("=== LLM API Gateway Client Example ===\n")
    asyncio.run(example_usage())
