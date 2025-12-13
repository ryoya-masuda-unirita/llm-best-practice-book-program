"""Centralized API key management for LLM providers.

This module ensures that API keys are managed in a single location
and are never exposed to client applications.
"""

from typing import Dict

from pydantic import Secret

from src.config import config
from src.logger import make_logger

logger = make_logger(__name__)


class APIKeyManager:
    """Manages API keys for different LLM providers.

    Centralizes API key management so client applications never have direct access
    to keys and key rotation requires only configuration updates.
    """

    def __init__(self):
        self._provider_keys: Dict[str, Secret[str]] = {
            "openai": config.openai_api_key,
            "gemini": config.gemini_api_key,
        }
        logger.info(f"API Key Manager initialized with {len(self._provider_keys)} providers")

    def get_api_key(self, provider: str) -> str:
        """Get the API key for a specific provider. Raises ValueError if unsupported."""
        provider_lower = provider.lower()

        if provider_lower not in self._provider_keys:
            logger.error(f"Attempted to access unsupported provider: {provider}")
            raise ValueError(f"Unsupported LLM provider: {provider}")

        logger.debug(f"Retrieved API key for provider: {provider}")
        return self._provider_keys[provider_lower]

    def is_provider_supported(self, provider: str) -> bool:
        """Check if a provider is supported."""
        return provider.lower() in self._provider_keys

    def list_supported_providers(self) -> list[str]:
        """Get a list of all supported providers."""
        return list(self._provider_keys.keys())


# Global API key manager instance
api_key_manager = APIKeyManager()
