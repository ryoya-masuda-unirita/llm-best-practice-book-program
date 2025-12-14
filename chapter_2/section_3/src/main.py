import asyncio
import json
import os
from functools import wraps
from uuid import uuid4

import click
from google.genai.types import File

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
    "--image-path",
    "-i",
    type=click.Path(exists=True),
    required=True,
    help="The path to the input image file.",
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
    image_path: str,
    output_directory: str = "outputs",
):
    logger.info(f"""
Model: {model}
Input image path: {image_path}
Output directory: {output_directory}""")

    if model not in GeminiModel.list_str():
        raise ValueError(f"Invalid model '{model}'.")

    os.makedirs(output_directory, exist_ok=True)

    gemini_path: File = await google_genai_client.aio.files.upload(file=image_path)
    result = await request_gemini(model=model, gemini_path=gemini_path)

    file_name = f"{LLMProvider.GEMINI.value}_{uuid4().hex}.json"
    file_path = os.path.join(output_directory, file_name)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(result.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

    logger.info(f"""File saved to {file_path}""")

    await google_genai_client.aio.aclose()


if __name__ == "__main__":
    main()
