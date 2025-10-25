"""Dependency injection container for LLM services.

This module provides a simple service locator pattern for managing
LLM service instances based on provider and functionality.
"""

from src.client.llm_client import LLMClient, LLMProvider
from src.service.interfaces import ITextClassificationService, ITextGenerationService
from src.service.text_classification_service import TextClassificationService
from src.service.text_generation_service import TextGenerationService


class ServiceContainer:
    """Container for managing LLM service instances.

    This class implements a simple service locator pattern to provide
    centralized access to different LLM service implementations.
    """

    def __init__(self):
        """Initialize the service container."""
        self._text_generation_services: dict[LLMProvider, ITextGenerationService] = {}
        self._text_classification_services: dict[LLMProvider, ITextClassificationService] = {}
        self._llm_client = LLMClient()
        self._initialize_services()

    def _initialize_services(self):
        """Initialize all service instances."""
        # Register text generation services for each provider

        for provider in LLMProvider:
            self._text_generation_services[provider] = TextGenerationService(
                llm_client=self._llm_client, provider=provider
            )
            self._text_classification_services[provider] = TextClassificationService(
                llm_client=self._llm_client, provider=provider
            )

    def get_text_generation_service(self, provider: LLMProvider) -> ITextGenerationService:
        """Get text generation service for the specified provider.

        Args:
            provider: The LLM provider

        Returns:
            ITextGenerationService: The text generation service instance
        """
        return self._text_generation_services[provider]

    def get_text_classification_service(self, provider: LLMProvider) -> ITextClassificationService:
        """Get text classification service for the specified provider.

        Args:
            provider: The LLM provider

        Returns:
            ITextClassificationService: The text classification service instance
        """
        return self._text_classification_services[provider]


# Global service container instance
service_container = ServiceContainer()
