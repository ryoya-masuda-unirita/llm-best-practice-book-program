from enum import StrEnum

from google import genai
from src.config import config


class GeminiModel(StrEnum):
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"
    GEMINI_3_5_FLASH = "gemini-3.5-flash"
    GEMINI_3_1_FLASH_LITE = "gemini-3.1-flash-lite"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in GeminiModel]


class GeminiEmbeddingModel(StrEnum):
    GEMINI_EMBEDDING_001 = "gemini-embedding-001"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in GeminiEmbeddingModel]


google_genai_client = genai.Client(api_key=config.gemini_api_key)
