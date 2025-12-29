"""Runner Service for Parallel World Article Generation.

This module provides a thin wrapper around the agent-based pipeline implementation.
The actual orchestration logic is handled by ArticlePipelineMediator in the agent layer.
"""

from typing import Literal

from src.agent.extensions.mediators.article_pipeline import run_article_pipeline
from src.client.llm_client import LLMProvider
from src.model.model import CompletedArticle


async def run_parallel_world_article_generation(
    theme: str,
    language: Literal["en", "ja"],
    llm_provider: LLMProvider,
    model: str,
    output_directory: str,
    num_outline_variants: int,
    num_second_half_variants: int,
    auto_select: bool,
) -> CompletedArticle | None:
    """Run the complete parallel world article generation workflow.

    This function delegates to the agent-based pipeline mediator which implements:
    - Parallel World Pattern for generating multiple variants
    - Human-in-the-Loop for outline and article selection
    - LLM-as-a-Judge for article review
    """
    return await run_article_pipeline(
        theme=theme,
        language=language,
        llm_provider=llm_provider,
        model=model,
        output_directory=output_directory,
        num_outline_variants=num_outline_variants,
        num_second_half_variants=num_second_half_variants,
        auto_select=auto_select,
    )
