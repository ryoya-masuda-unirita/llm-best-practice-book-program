"""Interactive CLI for parallel world article generation with human-in-the-loop."""

import asyncio
import os
from functools import wraps

import click

from src.client.llm_client import GeminiModel, LLMProvider
from src.logger import make_logger
from src.service.runner_service import run_parallel_world_article_generation

logger = make_logger(__name__)


def async_cmd(func):  # type: ignore
    @wraps(func)
    def wrapper(*args, **kwargs):  # type: ignore
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.command()
@click.option(
    "--theme",
    "-t",
    type=str,
    required=True,
    help="Article theme/topic.",
)
@click.option(
    "--language",
    "-l",
    type=click.Choice(["en", "ja"]),
    required=True,
    help="Article language (en: English, ja: Japanese).",
)
@click.option(
    "--model",
    "-m",
    type=click.Choice(GeminiModel.list_str(), case_sensitive=False),
    required=True,
    help="The model to use (e.g., gemini-2.5-flash, gemini-2.5-pro).",
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
    "--num-outline-variants",
    "-no",
    type=int,
    default=3,
    help="Number of outline variants to generate (default: 3).",
)
@click.option(
    "--num-second-half-variants",
    "-ns",
    type=int,
    default=3,
    help="Number of second half variants to generate (default: 3).",
)
@click.option(
    "--auto-select",
    "-a",
    is_flag=True,
    help="Automatically select best options without human interaction.",
)
@async_cmd
async def main(
    theme: str,
    language: str,
    model: str,
    output_directory: str = "outputs",
    num_outline_variants: int = 3,
    num_second_half_variants: int = 3,
    auto_select: bool = False,
) -> None:
    """
    Generate an article using parallel world pattern with human-in-the-loop.

    This tool implements the parallel world pattern described in CLAUDE.md:
    1. Generate multiple outline variants in parallel
    2. User selects the best outline (human-in-the-loop)
    3. Generate first half based on selected outline
    4. Generate multiple second half variants in parallel
    5. Review all variants using LLM-as-a-Judge
    6. User selects the best complete article (human-in-the-loop)
    """
    llm_provider_enum = LLMProvider.GEMINI

    click.echo(
        f"""
╔════════════════════════════════════════════════════════════════════════════╗
║         Parallel World Article Generation - Human-in-the-Loop             ║
╚════════════════════════════════════════════════════════════════════════════╝

Configuration:
  Theme: {theme}
  Language: {language}
  Model: {model}
  Outline Variants: {num_outline_variants}
  Second Half Variants: {num_second_half_variants}
  Mode: {"Automatic" if auto_select else "Interactive"}
"""
    )

    os.makedirs(output_directory, exist_ok=True)

    await run_parallel_world_article_generation(
        theme=theme,
        language=language,  # type: ignore
        llm_provider=llm_provider_enum,
        model=model.lower(),
        output_directory=output_directory,
        num_outline_variants=num_outline_variants,
        num_second_half_variants=num_second_half_variants,
        auto_select=auto_select,
    )


if __name__ == "__main__":
    main()
