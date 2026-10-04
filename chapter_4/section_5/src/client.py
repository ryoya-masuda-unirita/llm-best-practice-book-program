"""Anthropic LLM client and executor factory."""

from enum import StrEnum
from typing import Any

from anthropic import AsyncAnthropicBedrock
from pydantic import BaseModel
from src.config import config


class AnthropicModel(StrEnum):
    """Available Anthropic models."""

    CLAUDE_SONNET_4_6 = "global.anthropic.claude-sonnet-4-6"
    CLAUDE_HAIKU_4_5 = "global.anthropic.claude-haiku-4-5-20251001-v1:0"


anthropic_client = AsyncAnthropicBedrock(aws_region=config.aws_region)


def create_executor(
    model: str = AnthropicModel.CLAUDE_HAIKU_4_5,
    system_instruction: str | None = None,
    response_schema: type[BaseModel] | None = None,
    **kwargs,
):
    """Create a Anthropic LLM executor function for use with PromptNode."""

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

        request_params = {**kwargs}
        request_params.setdefault("max_tokens", 4096)
        if sys_inst:
            request_params["system"] = sys_inst
        messages = [{"role": "user", "content": content}]

        if response_schema:
            result = await anthropic_client.messages.parse(
                model=model,
                messages=messages,
                output_format=response_schema,
                **request_params,
            )
            return result.parsed_output

        result = await anthropic_client.messages.create(
            model=model,
            messages=messages,
            **request_params,
        )

        return {
            "content": next((block.text for block in result.content if block.type == "text"), ""),
            "model": model,
            "usage": {
                "prompt_tokens": result.usage.input_tokens,
                "completion_tokens": result.usage.output_tokens,
                "total_tokens": result.usage.input_tokens + result.usage.output_tokens,
            },
            "finish_reason": result.stop_reason,
        }

    return executor
