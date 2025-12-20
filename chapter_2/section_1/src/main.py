import asyncio
import os
from functools import wraps
from uuid import uuid4

import click
from src.client.llm_client import AnthropicModel, GeminiModel, LLMProvider, OpenAIModel, google_genai_client
from src.logger import make_logger
from src.service import request_anthropic, request_gemini, request_openai

logger = make_logger(__name__)


def async_cmd(func):
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
    help="The LLM provider to use.",
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
    logger.info(f"""LLM provider: {llm_provider.value}
Model: {model}
Output directory: {output_directory}""")

    if llm_provider == LLMProvider.OPENAI and model not in OpenAIModel.list_str():
        raise ValueError(f"Invalid model '{model}' for provider '{llm_provider.value}'.")
    if llm_provider == LLMProvider.GEMINI and model not in GeminiModel.list_str():
        raise ValueError(f"Invalid model '{model}' for provider '{llm_provider.value}'.")
    if llm_provider == LLMProvider.ANTHROPIC and model not in AnthropicModel.list_str():
        raise ValueError(f"Invalid model '{model}' for provider '{llm_provider.value}'.")

    os.makedirs(output_directory, exist_ok=True)

    if llm_provider == LLMProvider.OPENAI:
        result = await request_openai(model=model)
    elif llm_provider == LLMProvider.GEMINI:
        result = await request_gemini(model=model)
    elif llm_provider == LLMProvider.ANTHROPIC:
        result = await request_anthropic(model=model)
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_provider.value}")

    file_name = f"{llm_provider.value}_{uuid4().hex}.json"
    file_path = os.path.join(output_directory, file_name)
    result.save_as_json(file_path)
    logger.info(f"""File saved to {file_path}""")

    if llm_provider == LLMProvider.GEMINI:
        await google_genai_client.aio.aclose()


if __name__ == "__main__":
    main()
