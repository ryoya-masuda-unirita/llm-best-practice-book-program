"""Base abstract interface for LLM clients following the Adapter pattern."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class LLMClient(ABC):
    """Abstract base class defining the common interface for all LLM providers.

    This interface defines the contract that all LLM adapters must implement,
    enabling uniform interaction with different providers (OpenAI, Anthropic, Google Gemini).
    """

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        response_format: type,
        **kwargs: Any,
    ) -> BaseModel:
        """Generate a chat completion with structured output.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            response_format: Pydantic model class for structured output
            **kwargs: Additional provider-specific parameters

        Returns:
            Parsed response matching the response_format type

        Raises:
            Exception: Provider-specific errors during API calls
        """
        raise NotImplementedError("chat method must be implemented by subclasses")

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of the LLM provider.

        Returns:
            Provider name (e.g., 'openai', 'anthropic', 'gemini')
        """
        raise NotImplementedError("get_provider_name must be implemented by subclasses")

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model identifier being used.

        Returns:
            Model identifier (e.g., 'gpt-4o', 'claude-sonnet-4-5')
        """
        raise NotImplementedError("get_model_name must be implemented by subclasses")
