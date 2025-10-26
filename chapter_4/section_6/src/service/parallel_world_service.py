"""
Parallel World AI Agent Pipeline Service.

This module contains the core AI agent pipeline logic using LangGraph.
It handles:
- LLM API calls (OpenAI and Gemini)
- Pipeline nodes and state transitions
- Graph construction and execution

For user interaction and orchestration, see runner_service.py
"""

from typing import Literal

from langgraph.graph import END, START, StateGraph

from src.logger import make_logger
from src.model.parallel_world_model import (
    ParallelWorldState,
)
from src.service.generation_service import (
    generate_first_half_node,
    generate_multiple_outlines_node,
    generate_multiple_second_halves_node,
    regenerate_second_halves_after_rejection_node,
    review_all_articles_node,
)

logger = make_logger(__name__)

# =============================================================================
# Graph Routing Functions
# =============================================================================


def _has_error(state: ParallelWorldState) -> bool:
    """Check if state has an error."""
    error = state.get("error")
    if error:
        logger.error(f"Error detected: {error}")
    return bool(error)


def route_after_outline_generation(state: ParallelWorldState) -> Literal["wait_for_outline_selection", "end"]:
    """Route after outline generation."""
    if _has_error(state) or not state.get("outline_sessions"):
        return "end"
    return "wait_for_outline_selection"


def route_after_outline_selection(state: ParallelWorldState) -> Literal["generate_first_half", "end"]:
    """Route after outline selection."""
    if _has_error(state) or not state.get("selected_outline_session_id"):
        return "end"
    return "generate_first_half"


def route_after_first_half(state: ParallelWorldState) -> Literal["generate_second_halves", "end"]:
    """Route after first half generation."""
    if _has_error(state) or not state.get("first_half_session"):
        return "end"
    return "generate_second_halves"


def route_after_second_halves(state: ParallelWorldState) -> Literal["review_articles", "end"]:
    """Route after second halves generation."""
    if _has_error(state) or not state.get("second_half_sessions"):
        return "end"
    return "review_articles"


def route_after_reviews(state: ParallelWorldState) -> Literal["wait_for_final_selection", "end"]:
    """Route after article reviews."""
    if _has_error(state) or not state.get("reviewed_sessions"):
        return "end"
    return "wait_for_final_selection"


def route_after_final_selection(state: ParallelWorldState) -> Literal["wait_for_human_approval", "end"]:
    """Route after final article selection."""
    if _has_error(state) or not state.get("final_selected_session_id"):
        return "end"
    return "wait_for_human_approval"


def route_after_human_approval(state: ParallelWorldState) -> Literal["regenerate_second_halves", "end"]:
    """
    Route after human approval decision.

    - If approved (human_approved == True): go to END
    - If rejected (human_approved == False): regenerate second halves
    - If error or no decision: go to END
    """
    if _has_error(state):
        return "end"

    human_approved = state.get("human_approved")

    if human_approved is None:
        logger.warning("No human approval decision found")
        return "end"

    if human_approved:
        logger.info("Article approved by human - ending workflow")
        return "end"
    else:
        logger.info("Article rejected by human - regenerating with feedback")
        return "regenerate_second_halves"


# =============================================================================
# Placeholder Nodes for Human-in-the-Loop (implemented in runner_service)
# =============================================================================


async def wait_for_outline_selection_node(state: ParallelWorldState) -> ParallelWorldState:
    """
    Placeholder node for outline selection.

    In the actual implementation (runner_service), this waits for user input.
    For the graph, it just passes through the state.
    """
    logger.info("Outline selection point (handled by runner)")
    return state


async def wait_for_final_selection_node(state: ParallelWorldState) -> ParallelWorldState:
    """
    Placeholder node for final article selection.

    In the actual implementation (runner_service), this waits for user input.
    For the graph, it just passes through the state.
    """
    logger.info("Final selection point (handled by runner)")
    return state


async def wait_for_human_approval_node(state: ParallelWorldState) -> ParallelWorldState:
    """
    Placeholder node for human approval (yes/no decision).

    In the actual implementation (runner_service), this waits for user input.
    For the graph, it just passes through the state.
    """
    logger.info("Human approval point (handled by runner)")
    return state


# =============================================================================
# Graph Construction
# =============================================================================


def create_parallel_world_graph() -> StateGraph:
    """
    Create the parallel world article generation LangGraph pipeline with review loop.

    Pipeline flow:
    1. Generate multiple outlines in parallel (Parallel World 1)
    2. Wait for user to select outline (Human-in-the-loop 1)
    3. Generate first half based on selected outline
    4. Generate multiple second halves in parallel (Parallel World 2)
    5. Review all complete articles using LLM-as-a-Judge
    6. Wait for user to select final article (Human-in-the-loop 2)
    7. Wait for human approval (yes/no) (Human-in-the-loop 3)
    8. If rejected: regenerate second halves with feedback, go back to step 5
       If approved: end workflow

    Returns:
        Compiled StateGraph for parallel world article generation
    """
    graph = StateGraph(ParallelWorldState)

    # Add nodes
    graph.add_node("generate_outlines", generate_multiple_outlines_node)
    graph.add_node("wait_for_outline_selection", wait_for_outline_selection_node)
    graph.add_node("generate_first_half", generate_first_half_node)
    graph.add_node("generate_second_halves", generate_multiple_second_halves_node)
    graph.add_node("review_articles", review_all_articles_node)
    graph.add_node("wait_for_final_selection", wait_for_final_selection_node)
    graph.add_node("wait_for_human_approval", wait_for_human_approval_node)
    graph.add_node("regenerate_second_halves", regenerate_second_halves_after_rejection_node)

    # Add edges
    graph.add_edge(START, "generate_outlines")

    graph.add_conditional_edges(
        "generate_outlines",
        route_after_outline_generation,
        {
            "wait_for_outline_selection": "wait_for_outline_selection",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "wait_for_outline_selection",
        route_after_outline_selection,
        {
            "generate_first_half": "generate_first_half",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "generate_first_half",
        route_after_first_half,
        {
            "generate_second_halves": "generate_second_halves",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "generate_second_halves",
        route_after_second_halves,
        {
            "review_articles": "review_articles",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "review_articles",
        route_after_reviews,
        {
            "wait_for_final_selection": "wait_for_final_selection",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "wait_for_final_selection",
        route_after_final_selection,
        {
            "wait_for_human_approval": "wait_for_human_approval",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "wait_for_human_approval",
        route_after_human_approval,
        {
            "regenerate_second_halves": "regenerate_second_halves",
            "end": END,
        },
    )

    # After regeneration, review again (creates the loop)
    graph.add_edge("regenerate_second_halves", "review_articles")

    return graph.compile()
