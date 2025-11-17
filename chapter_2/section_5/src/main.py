import asyncio
import os
from functools import wraps
from uuid import uuid4

import click

from src.client.llm_client import GeminiModel, LLMProvider, google_genai_client
from src.logger import make_logger
from src.service import request_gemini

logger = make_logger(__name__)


def async_cmd(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.command()
@click.option(
    "--model",
    "-m",
    type=click.Choice(GeminiModel.list_str()),
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
    model: str,
    output_directory: str = "outputs",
):
    logger.info(f"""Model: {model}
Output directory: {output_directory}""")

    if model not in GeminiModel.list_str():
        raise ValueError(f"Invalid model '{model}' for provider '{LLMProvider.GEMINI}'.")
    os.makedirs(output_directory, exist_ok=True)

    results = request_gemini(model=model)
    for result in results:
        file_name = f"{LLMProvider.GEMINI}_{uuid4().hex}.json"
        file_path = os.path.join(output_directory, file_name)
        result.save_as_json(file_path)
        logger.info(f"""File saved to {file_path}""")

    await google_genai_client.aio.aclose()


if __name__ == "__main__":
    main()
