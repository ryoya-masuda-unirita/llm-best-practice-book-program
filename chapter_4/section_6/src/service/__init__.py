"""
Service layer for parallel world article generation.

- parallel_world_service: Core AI agent pipeline logic (LangGraph)
- runner_service: User interaction and orchestration
"""

from src.service.parallel_world_service import (
    create_parallel_world_graph,
    generate_first_half_node,
    generate_multiple_outlines_node,
    generate_multiple_second_halves_node,
    review_all_articles_node,
)
from src.service.runner_service import run_parallel_world_article_generation

__all__ = [
    # Runner (main entry point for users)
    "run_parallel_world_article_generation",
    # Pipeline nodes (for advanced usage)
    "create_parallel_world_graph",
    "generate_multiple_outlines_node",
    "generate_first_half_node",
    "generate_multiple_second_halves_node",
    "review_all_articles_node",
]
