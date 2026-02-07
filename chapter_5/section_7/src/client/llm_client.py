"""
LLM client configuration and model definitions.

This module provides OpenAI model definitions used by the learning platform.
"""

from enum import StrEnum


class OpenAIModel(StrEnum):
    """Available OpenAI models for the learning platform."""

    GPT_5_2 = "gpt-5.2"
    GPT_5 = "gpt-5"
    GPT_5_MINI = "gpt-5-mini"
    GPT_5_NANO = "gpt-5-nano"

    @staticmethod
    def list_str() -> list[str]:
        """Return list of all available model names."""
        return list(OpenAIModel)
