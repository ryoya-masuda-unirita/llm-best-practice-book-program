import asyncio
import os
from functools import wraps
from uuid import uuid4

import click

from src.client.llm_client import OpenAIModel
from src.logger import make_logger
from src.service import request_openai

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
    type=click.Choice(OpenAIModel.list_str()),
    required=True,
    default=OpenAIModel.GPT_4O,
    help="The OpenAI model to use for the request.",
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

    if model not in OpenAIModel.list_str():
        raise ValueError(f"Invalid model '{model}'. Must be one of {OpenAIModel.list_str()}")

    os.makedirs(output_directory, exist_ok=True)

    result = await request_openai(model=model)

    file_name = f"openai_{uuid4().hex}.json"
    file_path = os.path.join(output_directory, file_name)
    result.save_as_json(file_path)
    logger.info(f"""File saved to {file_path}""")


if __name__ == "__main__":
    main()
