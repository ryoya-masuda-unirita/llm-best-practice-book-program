from enum import StrEnum

from google import genai

from src.config import config


class LLMProvider(StrEnum):
    """Enum for LLM providers."""

    GEMINI = "gemini"


class GeminiModel(StrEnum):
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in GeminiModel]


google_genai_client = genai.Client(api_key=config.gemini_api_key)
