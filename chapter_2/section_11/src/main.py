"""Main CLI application for character generation using various LLM providers.

This application demonstrates the Adapter and Factory pattern implementation
for LLM API clients, allowing seamless switching between different providers.
"""

import asyncio
import os
from functools import wraps
from uuid import uuid4

import click

from src.client import GeminiModel, LLMProvider, OpenAIModel
from src.client.factory import LLMClientFactory
from src.logger import make_logger
from src.service import request_llm

logger = make_logger(__name__)


def async_cmd(func):
    """Decorator to run async functions in click commands."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.command()
@click.option(
    "--llm-provider",
    "-lp",
    type=click.Choice(LLMProvider),
    required=True,
    default=LLMProvider.GEMINI,
    help="The LLM provider to use (openai, anthropic, or gemini).",
)
@click.option(
    "--model",
    "-m",
    type=click.Choice(OpenAIModel.list_str() + GeminiModel.list_str()),
    required=True,
    help="The model to use for the request.",
)
@click.option(
    "--output-directory",
    "-od",
    type=click.Path(),
    required=False,
    default="outputs",
    help="The directory to save output files.",
)
@async_cmd
async def main(
    llm_provider: LLMProvider,
    model: str,
    output_directory: str = "outputs",
):
    """Generate a fictional character using the specified LLM provider and model.

    This CLI application uses the Adapter and Factory pattern to support
    multiple LLM providers (OpenAI, Anthropic, Google Gemini) through a
    unified interface.

    Example:
        python -m src.main -lp openai -m gpt-4o

        python -m src.main -lp anthropic -m claude-sonnet-4-5 -t 0.7

        python -m src.main -lp gemini -m gemini-2.5-pro
    """
    logger.info(
        f"""LLM provider: {llm_provider.value}
Model: {model}
Output directory: {output_directory}"""
    )

    # Validate provider-model combination using factory
    if not LLMClientFactory.is_valid_combination(llm_provider.value, model):
        supported_models = LLMClientFactory.get_supported_models(llm_provider.value)
        raise ValueError(
            f"Invalid model '{model}' for provider '{llm_provider.value}'. Supported models: {supported_models}"
        )

    # Create output directory
    os.makedirs(output_directory, exist_ok=True)

    # Make unified LLM request using the adapter pattern
    result = await request_llm(
        provider=llm_provider.value,
        model=model,
    )

    # Save result
    file_name = f"{llm_provider.value}_{model.replace('.', '_')}_{uuid4().hex[:8]}.json"
    file_path = os.path.join(output_directory, file_name)
    result.save_as_json(file_path)

    logger.info("Character generated successfully!")
    logger.info(f"File saved to: {file_path}")
    logger.info(f"Character: {result.first_name} {result.last_name}, {result.age} years old")


if __name__ == "__main__":
    main()
