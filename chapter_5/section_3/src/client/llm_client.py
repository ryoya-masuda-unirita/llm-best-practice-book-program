from enum import StrEnum


class LLMProvider(StrEnum):
    GEMINI = "gemini"


class GeminiModel(StrEnum):
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"
    GEMINI_3_5_FLASH = "gemini-3.5-flash"
    GEMINI_3_1_FLASH_LITE = "gemini-3.1-flash-lite"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in GeminiModel]
