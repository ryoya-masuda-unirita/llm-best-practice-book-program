"""Factory for creating LLM client instances.

This module implements the Factory pattern to encapsulate the logic for
creating appropriate LLM client adapters based on provider and model specifications.
"""

from src.client.adapters import GeminiAdapter, OpenAIAdapter
from src.client.base import LLMClient
from src.client.model import GeminiModel, LLMProvider, OpenAIModel
from src.logger import make_logger

logger = make_logger(__name__)


class LLMClientFactory:
    """Factory class for creating LLM client instances.

    This factory encapsulates the creation logic for different LLM providers,
    managing API keys and configuration internally. It provides a unified
    interface for obtaining properly configured client adapters.
    """

    # Mapping of provider names to their supported models
    PROVIDER_MODELS = {
        LLMProvider.OPENAI: OpenAIModel.list_str(),
        LLMProvider.GEMINI: GeminiModel.list_str(),
    }

    @staticmethod
    def create_client(
        provider: LLMProvider,
        model: OpenAIModel | GeminiModel,
    ) -> LLMClient:
        """Create and return an LLM client adapter for the specified provider.

        Args:
            provider: Provider name ('openai', 'anthropic', or 'gemini')
            model: Model identifier to use

        Returns:
            Configured LLMClient adapter instance

        Raises:
            ValueError: If provider is unknown or model is invalid for the provider

        Example:
            >>> factory = LLMClientFactory()
            >>> client = factory.create_client('openai', 'gpt-4o')
            >>> response = await client.chat(messages, CharacterResponse)
        """
        provider_lower = provider.lower()

        # Validate provider
        if provider_lower not in LLMClientFactory.PROVIDER_MODELS:
            raise ValueError(
                f"Unknown provider: {provider}. Supported providers: {list(LLMClientFactory.PROVIDER_MODELS.keys())}"
            )

        # Validate model for provider
        if model not in LLMClientFactory.PROVIDER_MODELS[provider_lower]:
            raise ValueError(
                f"Invalid model '{model}' for provider '{provider}'. "
                f"Supported models: {LLMClientFactory.PROVIDER_MODELS[provider_lower]}"
            )

        logger.info(f"Creating LLM client: provider={provider}, model={model}")

        # Create appropriate adapter based on provider
        if provider_lower == LLMProvider.OPENAI:
            return OpenAIAdapter(model=model)

        elif provider_lower == LLMProvider.GEMINI:
            return GeminiAdapter(model=model)

        else:
            # This should never happen due to earlier validation
            raise ValueError(f"Unsupported provider: {provider}")

    @staticmethod
    def get_supported_providers() -> list[str]:
        """Return list of supported provider names.

        Returns:
            List of provider identifiers
        """
        return list(LLMClientFactory.PROVIDER_MODELS.keys())

    @staticmethod
    def get_supported_models(provider: str) -> list[str]:
        """Return list of supported models for a given provider.

        Args:
            provider: Provider name

        Returns:
            List of model identifiers

        Raises:
            ValueError: If provider is unknown
        """
        provider_lower = provider.lower()
        if provider_lower not in LLMClientFactory.PROVIDER_MODELS:
            raise ValueError(f"Unknown provider: {provider}")

        return LLMClientFactory.PROVIDER_MODELS[provider_lower]

    @staticmethod
    def is_valid_combination(provider: str, model: str) -> bool:
        """Check if a provider-model combination is valid.

        Args:
            provider: Provider name
            model: Model identifier

        Returns:
            True if combination is valid, False otherwise
        """
        provider_lower = provider.lower()
        if provider_lower not in LLMClientFactory.PROVIDER_MODELS:
            return False

        return model in LLMClientFactory.PROVIDER_MODELS[provider_lower]
