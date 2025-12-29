"""Runner Service for Article Generation with State-Based Rollback (Forget the Past)."""

from typing import Literal

from src.agent.extensions.mediators.article_pipeline import run_article_pipeline
from src.client.llm_client import LLMProvider
from src.model.model import CompletedArticle


async def run_forget_past_article_generation(
    theme: str,
    language: Literal["en", "ja"],
    llm_provider: LLMProvider,
    model: str,
    output_directory: str,
    auto_select: bool,
) -> CompletedArticle | None:
    """Run the complete article generation workflow with state-based rollback.

    This implements the "forget the past" pattern where rolling back to a previous
    phase clears all state after that phase, causing regeneration from scratch.
    """
    return await run_article_pipeline(
        theme=theme,
        language=language,
        llm_provider=llm_provider,
        model=model,
        output_directory=output_directory,
        auto_select=auto_select,
    )
