"""Runner Service for Article Generation with Forget, Replay, Speculate."""

from typing import Literal

from src.agent.extensions.mediators.article_pipeline import run_article_pipeline
from src.client.llm_client import LLMProvider
from src.model.model import CompletedArticle


async def run_forget_replay_speculate_article_generation(
    theme: str,
    language: Literal["en", "ja"],
    llm_provider: LLMProvider,
    model: str,
    output_directory: str,
    auto_select: bool,
    num_outlines: int = 1,
) -> CompletedArticle | None:
    """Run the complete article generation workflow with Forget + Replay + Speculate.

    - Forget: Roll back to any previous phase, discarding contaminated context
    - Replay: Automatically re-send valid user prompts after rollback
    - Speculate: Fork parallel worlds at branch points (e.g., multiple outlines)
    """
    return await run_article_pipeline(
        theme=theme,
        language=language,
        llm_provider=llm_provider,
        model=model,
        output_directory=output_directory,
        auto_select=auto_select,
        num_outlines=num_outlines,
    )
