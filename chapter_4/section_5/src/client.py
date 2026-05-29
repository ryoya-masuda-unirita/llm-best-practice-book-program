"""Gemini LLM client and executor factory."""

from enum import StrEnum
from typing import Any

from google import genai
from google.genai.types import GenerateContentConfig
from pydantic import BaseModel
from src.config import config


class GeminiModel(StrEnum):
    """Available Gemini models."""

    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"
    GEMINI_3_5_FLASH = "gemini-3.5-flash"
    GEMINI_3_1_FLASH_LITE = "gemini-3.1-flash-lite"


google_genai_client = genai.Client(api_key=config.gemini_api_key)


def create_executor(
    model: str = GeminiModel.GEMINI_2_5_FLASH,
    system_instruction: str | None = None,
    response_schema: type[BaseModel] | None = None,
    **kwargs,
):
    """Create a Gemini LLM executor function for use with PromptNode."""

    async def executor(prompt: str | list[dict], context: Any) -> dict[str, Any]:
        if isinstance(prompt, list):
            sys_inst = system_instruction
            content_parts = []
            for msg in prompt:
                if msg.get("role") == "system":
                    sys_inst = sys_inst or msg.get("content", "")
                else:
                    content_parts.append(msg.get("content", ""))
            content = "\n".join(content_parts)
        else:
            content = str(prompt)
            sys_inst = system_instruction

        config_params = {**kwargs}
        if sys_inst:
            config_params["system_instruction"] = sys_inst
        if response_schema:
            config_params["response_mime_type"] = "application/json"
            config_params["response_schema"] = response_schema

        gen_config = GenerateContentConfig(**config_params)

        result = await google_genai_client.aio.models.generate_content(
            model=model,
            contents=content,
            config=gen_config,
        )

        if response_schema:
            return result.parsed

        return {
            "content": result.text,
            "model": model,
            "usage": {
                "prompt_tokens": result.usage_metadata.prompt_token_count if result.usage_metadata else None,
                "completion_tokens": result.usage_metadata.candidates_token_count if result.usage_metadata else None,
                "total_tokens": result.usage_metadata.total_token_count if result.usage_metadata else None,
            },
            "finish_reason": result.candidates[0].finish_reason.name if result.candidates else None,
        }

    return executor
