import asyncio
import os
from functools import wraps
from uuid import uuid4

import click

from src.client.llm_client import GeminiModel
from src.logger import make_logger
from src.service.llm_pipeline_service import run_novel_writer

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
    required=False,
    default=GeminiModel.GEMINI_2_5_FLASH,
    help="The Gemini model to use for deep thinking.",
)
@click.option(
    "--output-directory",
    "-od",
    type=click.Path(),
    required=False,
    default="outputs",
    help="The directory to save output files.",
)
@click.option(
    "--request",
    "-r",
    type=str,
    required=True,
    help="Your novel request in natural language.",
)
@async_cmd
async def main(
    model: str,
    output_directory: str,
    request: str,
):
    """
    Deep Think Novel Writer - An AI Agent for Creative Writing

    This agent generates short novels based on your request using deep thinking.
    It uses Gemini's extended thinking capabilities to craft compelling narratives
    with rich characters, engaging plots, and evocative prose.

    REQUEST: Your novel request in natural language.

    Examples:

        python -m src.main -r "Write a story about a lonely lighthouse keeper who discovers a message in a bottle"

        python -m src.main -r "A bittersweet tale of childhood friends reuniting after 20 years"

        python -m src.main -r "孤独な宇宙飛行士が地球を見つめながら人生を振り返る物語"
    """
    logger.info(f"""Deep Think Novel Writer
Model: {model}
Request: {request}
Output directory: {output_directory}
""")

    os.makedirs(output_directory, exist_ok=True)

    # Run the novel writer deep think agent
    result = await run_novel_writer(
        user_request=request,
        model=model,
    )

    if result is None:
        raise ValueError("Novel writer failed. Check logs for details.")

    # Save the novel
    base_name = f"novel_{uuid4().hex}"
    md_file_path = os.path.join(output_directory, f"{base_name}.md")

    with open(md_file_path, "w", encoding="utf-8") as f:
        f.write(result)

    logger.info(f"Novel saved: {md_file_path}")


if __name__ == "__main__":
    main()
