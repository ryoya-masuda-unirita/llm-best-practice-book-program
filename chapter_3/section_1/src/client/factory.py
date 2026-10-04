"""Factory for creating LLM client adapters."""

from src.client.adapters import AnthropicAdapter, OpenAIAdapter  # , GeminiAdapter
from src.client.base import LLMClient
from src.client.model import AnthropicModel, LLMProvider, OpenAIModel  # , GeminiModel
from src.logger import make_logger

logger = make_logger(__name__)


class LLMClientFactory:
    """Factory for creating LLM client adapters."""

    PROVIDER_MODELS = {
        LLMProvider.OPENAI: OpenAIModel.list_str(),
        # LLMProvider.GEMINI: GeminiModel.list_str(),
        LLMProvider.ANTHROPIC: AnthropicModel.list_str(),
    }

    @staticmethod
    def create_client(
        provider: LLMProvider,
        model: OpenAIModel | AnthropicModel,
    ) -> LLMClient:
        provider_lower = provider.lower()

        if provider_lower not in LLMClientFactory.PROVIDER_MODELS:
            raise ValueError(
                f"Unknown provider: {provider}. Supported: {list(LLMClientFactory.PROVIDER_MODELS.keys())}"
            )

        if model not in LLMClientFactory.PROVIDER_MODELS[provider_lower]:
            raise ValueError(
                f"Invalid model '{model}' for '{provider}'. Supported: {LLMClientFactory.PROVIDER_MODELS[provider_lower]}"
            )

        logger.info(f"Creating client: provider={provider}, model={model}")

        if provider_lower == LLMProvider.OPENAI:
            return OpenAIAdapter(model=model)
        # elif provider_lower == LLMProvider.GEMINI:
        #     return GeminiAdapter(model=model)
        elif provider_lower == LLMProvider.ANTHROPIC:
            return AnthropicAdapter(model=model)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    @staticmethod
    def get_supported_providers() -> list[str]:
        return list(LLMClientFactory.PROVIDER_MODELS.keys())

    @staticmethod
    def get_supported_models(provider: str) -> list[str]:
        provider_lower = provider.lower()
        if provider_lower not in LLMClientFactory.PROVIDER_MODELS:
            raise ValueError(f"Unknown provider: {provider}")
        return LLMClientFactory.PROVIDER_MODELS[provider_lower]

    @staticmethod
    def is_valid_combination(provider: str, model: str) -> bool:
        provider_lower = provider.lower()
        if provider_lower not in LLMClientFactory.PROVIDER_MODELS:
            return False
        return model in LLMClientFactory.PROVIDER_MODELS[provider_lower]
