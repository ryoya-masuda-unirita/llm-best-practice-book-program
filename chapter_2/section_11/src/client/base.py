"""Base interface for LLM clients."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class LLMClient(ABC):
    """Abstract interface for LLM providers (OpenAI, Anthropic, Gemini)."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        response_format: type,
        **kwargs: Any,
    ) -> BaseModel:
        raise NotImplementedError

    @abstractmethod
    def get_provider_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_model_name(self) -> str:
        raise NotImplementedError

    async def aclose(self) -> None:
        """Close client and clean up resources."""
        pass
