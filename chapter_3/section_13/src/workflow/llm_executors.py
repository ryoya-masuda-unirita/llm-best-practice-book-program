"""
LLM executor functions for use with PromptNode.

These are optional helper functions that integrate with the existing LLM client infrastructure.
Users can provide their own executor functions or use these as examples.
"""

from typing import Any

from google.genai.types import GenerateContentConfig
from pydantic import BaseModel

from src.client.llm_client import GeminiModel, LLMProvider, OpenAIModel, google_genai_client, openai_client
from src.logger import make_logger
from src.workflow.base import ExecutionContext

logger = make_logger(__name__)


def create_openai_executor(
    model: str = OpenAIModel.GPT_4O_MINI,
    response_format: type[BaseModel] | None = None,
    **kwargs,
):
    """
    Create an OpenAI LLM executor function.

    Args:
        model: OpenAI model to use
        response_format: Optional Pydantic model for structured output
        **kwargs: Additional arguments to pass to the API

    Returns:
        Async executor function

    Example:
        ```python
        # Simple text completion
        executor = create_openai_executor(model=OpenAIModel.GPT_4O)
        builder.add_prompt_node("llm", llm_executor=executor)

        # Structured output
        from pydantic import BaseModel

        class Character(BaseModel):
            name: str
            age: int

        executor = create_openai_executor(
            model=OpenAIModel.GPT_4O,
            response_format=Character
        )
        ```
    """

    async def openai_executor(prompt: str | list[dict], context: ExecutionContext) -> Any:
        """Execute OpenAI API call."""
        logger.info(f"Executing OpenAI request with model: {model}")

        try:
            # Convert prompt to messages format
            if isinstance(prompt, str):
                messages = [{"role": "user", "content": prompt}]
            else:
                messages = prompt

            # Make API call
            if response_format:
                # Structured output using response.parse
                result = await openai_client.responses.parse(
                    model=model,
                    input=messages,
                    text_format=response_format,
                    **kwargs,
                )
                return result.output_parsed
            else:
                # Regular completion
                result = await openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    **kwargs,
                )
                return {
                    "content": result.choices[0].message.content,
                    "model": result.model,
                    "usage": result.usage.model_dump() if result.usage else None,
                    "finish_reason": result.choices[0].finish_reason,
                }

        except Exception as e:
            logger.error(f"OpenAI execution failed: {e}")
            raise

    return openai_executor


def create_gemini_executor(
    model: str = GeminiModel.GEMINI_2_5_FLASH,
    response_schema: type[BaseModel] | None = None,
    system_instruction: str | None = None,
    **kwargs,
):
    """
    Create a Gemini LLM executor function.

    Args:
        model: Gemini model to use
        response_schema: Optional Pydantic model for structured output
        system_instruction: Optional system instruction
        **kwargs: Additional arguments to pass to the API

    Returns:
        Async executor function

    Example:
        ```python
        # Simple text completion
        executor = create_gemini_executor(model=GeminiModel.GEMINI_2_5_PRO)
        builder.add_prompt_node("llm", llm_executor=executor)

        # Structured output
        from pydantic import BaseModel

        class Character(BaseModel):
            name: str
            age: int

        executor = create_gemini_executor(
            model=GeminiModel.GEMINI_2_5_FLASH,
            response_schema=Character,
            system_instruction="You are a character generator."
        )
        ```
    """

    async def gemini_executor(prompt: str | list[dict], context: ExecutionContext) -> Any:
        """Execute Gemini API call."""
        logger.info(f"Executing Gemini request with model: {model}")

        try:
            # Extract content from prompt
            if isinstance(prompt, str):
                content = prompt
                sys_inst = system_instruction
            elif isinstance(prompt, list):
                # Extract system message if present
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

            # Build config
            config_params = {**kwargs}
            if sys_inst:
                config_params["system_instruction"] = sys_inst
            if response_schema:
                config_params["response_mime_type"] = "application/json"
                config_params["response_schema"] = response_schema

            config = GenerateContentConfig(**config_params)

            # Make API call
            result = await google_genai_client.aio.models.generate_content(
                model=model,
                contents=content,
                config=config,
            )

            # Return structured response
            if response_schema:
                return result.parsed
            else:
                return {
                    "content": result.text,
                    "model": model,
                    "usage": {
                        "prompt_tokens": result.usage_metadata.prompt_token_count if result.usage_metadata else None,
                        "completion_tokens": result.usage_metadata.candidates_token_count
                        if result.usage_metadata
                        else None,
                        "total_tokens": result.usage_metadata.total_token_count if result.usage_metadata else None,
                    },
                    "finish_reason": result.candidates[0].finish_reason.name if result.candidates else None,
                }

        except Exception as e:
            logger.error(f"Gemini execution failed: {e}")
            raise

    return gemini_executor


def create_llm_executor(
    provider: LLMProvider = LLMProvider.GEMINI,
    model: str | None = None,
    **kwargs,
):
    """
    Create a generic LLM executor function that supports multiple providers.

    Args:
        provider: LLM provider to use
        model: Model name (provider-specific)
        **kwargs: Additional arguments to pass to the API

    Returns:
        Async executor function

    Example:
        ```python
        # Using Gemini
        executor = create_llm_executor(
            provider=LLMProvider.GEMINI,
            model=GeminiModel.GEMINI_2_5_FLASH
        )

        # Using OpenAI
        executor = create_llm_executor(
            provider=LLMProvider.OPENAI,
            model=OpenAIModel.GPT_4O
        )

        builder.add_prompt_node("llm", llm_executor=executor)
        ```
    """
    if provider == LLMProvider.OPENAI:
        return create_openai_executor(model or OpenAIModel.GPT_4O_MINI, **kwargs)
    elif provider == LLMProvider.GEMINI:
        return create_gemini_executor(model or GeminiModel.GEMINI_2_5_FLASH, **kwargs)
    else:
        raise ValueError(f"Unsupported provider: {provider}")
