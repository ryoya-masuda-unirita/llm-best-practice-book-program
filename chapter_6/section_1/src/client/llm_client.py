from enum import StrEnum

from google import genai
from openai import AsyncOpenAI
from src.config import config


class LLMProvider(StrEnum):
    OPENAI = "openai"
    GEMINI = "gemini"


class OpenAIModel(StrEnum):
    GPT_5_2 = "gpt-5.2"
    GPT_5 = "gpt-5"
    GPT_5_MINI = "gpt-5-mini"
    GPT_5_NANO = "gpt-5-nano"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in OpenAIModel]


class GeminiModel(StrEnum):
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in GeminiModel]


google_genai_client = genai.Client(api_key=config.gemini_api_key)

openai_client = AsyncOpenAI(api_key=config.openai_api_key)
