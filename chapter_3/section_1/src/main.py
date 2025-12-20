"""CLI for character generation using multiple LLM providers."""

import asyncio
import os
from functools import wraps
from uuid import uuid4

import click
from src.client import AnthropicModel, GeminiModel, LLMProvider, OpenAIModel
from src.client.base import LLMClient
from src.client.factory import LLMClientFactory
from src.logger import make_logger
from src.service import request_llm

logger = make_logger(__name__)


def async_cmd(func):
    """Run async click commands."""

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
    type=click.Choice(OpenAIModel.list_str() + GeminiModel.list_str() + AnthropicModel.list_str()),
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
    logger.info(
        f"""LLM provider: {llm_provider.value}
Model: {model}
Output directory: {output_directory}"""
    )

    client: LLMClient = LLMClientFactory.create_client(provider=llm_provider, model=model)

    result = await request_llm(
        client=client,
        model=model,
    )

    os.makedirs(output_directory, exist_ok=True)

    file_name = f"{llm_provider.value}_{model.replace('.', '_')}_{uuid4().hex[:8]}.json"
    file_path = os.path.join(output_directory, file_name)
    result.save_as_json(file_path)

    logger.info("Character generated successfully!")
    logger.info(f"File saved to: {file_path}")
    logger.info(f"Character: {result.first_name} {result.last_name}, {result.age} years old")

    await client.aclose()


if __name__ == "__main__":
    main()
