"""
LLM client configuration and model definitions.

This module provides OpenAI model definitions used by the learning platform.
"""

from enum import StrEnum


class OpenAIModel(StrEnum):
    """Available OpenAI models for the learning platform."""

    GPT_5 = "gpt-5"
    GPT_5_MINI = "gpt-5-mini"
    GPT_5_NANO = "gpt-5-nano"
    GPT_4_1 = "gpt-4.1"
    GPT_4_1_MINI = "gpt-4.1-mini"
    GPT_4_1_NANO = "gpt-4.1-nano"
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"

    @staticmethod
    def list_str() -> list[str]:
        """Return list of all available model names."""
        return list(OpenAIModel)
