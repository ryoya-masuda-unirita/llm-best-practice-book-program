"""Interactive CLI for article generation with Forget, Replay, Speculate pattern."""

import asyncio
import os
from functools import wraps

import click
from src.client.llm_client import AnthropicModel, LLMProvider, anthropic_client
from src.logger import make_logger
from src.service.runner_service import run_forget_replay_speculate_article_generation

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
    type=click.Choice(AnthropicModel.list_str(), case_sensitive=False),
    required=True,
    help="The model to use (e.g., global.anthropic.claude-haiku-4-5-20251001-v1:0).",
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
@click.option(
    "--num-outlines",
    "-n",
    type=click.IntRange(min=1, max=5),
    required=False,
    default=1,
    help="Number of outline candidates for speculative execution (1=no speculation, max 5).",
)
@async_cmd
async def main(
    theme: str,
    language: str,
    model: str,
    output_directory: str = "outputs",
    auto_select: bool = False,
    num_outlines: int = 1,
) -> None:
    """Generate an article using the Forget, Replay, Speculate pattern."""
    speculation_mode = "Enabled" if num_outlines > 1 else "Disabled"
    click.echo(
        f"""
+============================================================================+
|    Article Generation with Forget, Replay, Speculate                       |
+============================================================================+

Configuration:
  Theme: {theme}
  Language: {language}
  LLM Provider: {LLMProvider.ANTHROPIC.value}
  Model: {model}
  Mode: {"Automatic" if auto_select else "Interactive"}
  Speculation: {speculation_mode} ({num_outlines} outline(s))
"""
    )

    if model.lower() not in AnthropicModel.list_str():
        raise ValueError(f"Invalid model '{model}' for provider '{LLMProvider.ANTHROPIC.value}'.")

    os.makedirs(output_directory, exist_ok=True)

    await run_forget_replay_speculate_article_generation(
        theme=theme,
        language=language,  # type: ignore
        llm_provider=LLMProvider.ANTHROPIC,
        model=model.lower(),
        output_directory=output_directory,
        auto_select=auto_select,
        num_outlines=num_outlines,
    )

    await anthropic_client.close()


if __name__ == "__main__":
    main()
