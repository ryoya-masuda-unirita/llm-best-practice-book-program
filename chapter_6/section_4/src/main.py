"""Interactive CLI for article generation with state-based rollback (forget the past pattern)."""

import asyncio
import os
from functools import wraps

import click
from src.client.llm_client import GeminiModel, LLMProvider, google_genai_client
from src.logger import make_logger
from src.service.runner_service import run_forget_past_article_generation

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
    help="The model to use (e.g., gemini-2.5-flash).",
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
    auto_select: bool = False,
) -> None:
    """Generate an article using state-based rollback pattern (forget the past)."""
    click.echo(
        f"""
╔════════════════════════════════════════════════════════════════════════════╗
║       Article Generation with State-Based Rollback (Forget the Past)      ║
╚════════════════════════════════════════════════════════════════════════════╝

Configuration:
  Theme: {theme}
  Language: {language}
  LLM Provider: {LLMProvider.GEMINI.value}
  Model: {model}
  Mode: {"Automatic" if auto_select else "Interactive"}
"""
    )

    if model.lower() not in GeminiModel.list_str():
        raise ValueError(f"Invalid model '{model}' for provider '{LLMProvider.GEMINI.value}'.")

    os.makedirs(output_directory, exist_ok=True)

    await run_forget_past_article_generation(
        theme=theme,
        language=language,  # type: ignore
        llm_provider=LLMProvider.GEMINI,
        model=model.lower(),
        output_directory=output_directory,
        auto_select=auto_select,
    )

    await google_genai_client.aio.aclose()


if __name__ == "__main__":
    main()
