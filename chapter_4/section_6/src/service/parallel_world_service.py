"""
Parallel World AI Agent Pipeline Service.

This module contains the core AI agent pipeline logic using LangGraph.
It handles:
- LLM API calls (OpenAI and Gemini)
- Pipeline nodes and state transitions
- Graph construction and execution

For user interaction and orchestration, see runner_service.py
"""

import asyncio
from typing import Literal

from google.genai.types import GenerateContentConfig
from langgraph.graph import END, START, StateGraph

from src.client.llm_client import LLMProvider, google_genai_client, openai_client
from src.logger import make_logger
from src.model.parallel_world_model import (
    ArticleHalf,
    ArticleOutline,
    ArticleReview,
    ParallelSession,
    ParallelWorldState,
)
from src.prompt.parallel_world_prompt import (
    make_article_review_prompt,
    make_article_review_system_instruction,
    make_first_half_generation_prompt,
    make_first_half_generation_system_instruction,
    make_outline_generation_prompt,
    make_outline_generation_system_instruction,
    make_second_half_generation_prompt,
    make_second_half_generation_system_instruction,
)

logger = make_logger(__name__)


# =============================================================================
# LLM Generation Functions
# =============================================================================


async def _generate_with_openai(
    prompt: list[dict[str, str]],
    response_format: type,
    model: str,
) -> any:
    """Generic OpenAI generation helper."""
    result = await openai_client.beta.chat.completions.parse(
        model=model,
        messages=prompt,
        response_format=response_format,
    )
    return result.choices[0].message.parsed


async def _generate_with_gemini(
    system_instruction: str,
    user_content: str,
    response_schema: type,
    model: str,
) -> any:
    """Generic Gemini generation helper."""
    result = await google_genai_client.aio.models.generate_content(
        model=model,
        contents=user_content,
        config=GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_schema,
        ),
    )
    return result.parsed


async def generate_outline(
    theme: str,
    language: Literal["en", "ja"],
    model: str,
    provider: LLMProvider,
) -> ArticleOutline | None:
    """Generate article outline using specified LLM provider."""
    try:
        if provider == LLMProvider.OPENAI:
            prompt = make_outline_generation_prompt(theme, language)
            return await _generate_with_openai(
                prompt,
                ArticleOutline,
                model,
            )
        else:  # Gemini
            system_instruction, user_content = make_outline_generation_system_instruction(theme, language)
            return await _generate_with_gemini(
                system_instruction,
                user_content,
                ArticleOutline,
                model,
            )
    except Exception as e:
        logger.error(f"Failed to generate outline with {provider.value}: {e}")
        return None


async def generate_first_half(
    outline: ArticleOutline,
    language: Literal["en", "ja"],
    model: str,
    provider: LLMProvider,
) -> str | None:
    """Generate first half of article using specified LLM provider."""
    try:
        if provider == LLMProvider.OPENAI:
            prompt = make_first_half_generation_prompt(outline, language)
            result = await _generate_with_openai(prompt, ArticleHalf, model)
            return result.content
        else:  # Gemini
            system_instruction, user_content = make_first_half_generation_system_instruction(outline, language)
            result = await _generate_with_gemini(system_instruction, user_content, ArticleHalf, model)
            return result.content
    except Exception as e:
        logger.error(f"Failed to generate first half with {provider.value}: {e}")
        return None


async def generate_second_half(
    outline: ArticleOutline,
    first_half: str,
    language: Literal["en", "ja"],
    model: str,
    provider: LLMProvider,
) -> str | None:
    """Generate second half of article using specified LLM provider."""
    try:
        if provider == LLMProvider.OPENAI:
            prompt = make_second_half_generation_prompt(outline, first_half, language)
            result = await _generate_with_openai(
                prompt,
                ArticleHalf,
                model,
            )
            return result.content
        else:  # Gemini
            system_instruction, user_content = make_second_half_generation_system_instruction(
                outline, first_half, language
            )
            result = await _generate_with_gemini(
                system_instruction,
                user_content,
                ArticleHalf,
                model,
            )
            return result.content
    except Exception as e:
        logger.error(f"Failed to generate second half with {provider.value}: {e}")
        return None


async def review_article(
    theme: str,
    outline: ArticleOutline,
    full_article: str,
    language: Literal["en", "ja"],
    model: str,
    provider: LLMProvider,
) -> ArticleReview | None:
    """Review article using LLM-as-a-Judge with specified provider."""
    try:
        if provider == LLMProvider.OPENAI:
            prompt = make_article_review_prompt(theme, outline, full_article, language)
            return await _generate_with_openai(
                prompt,
                ArticleReview,
                model,
            )
        else:  # Gemini
            system_instruction, user_content = make_article_review_system_instruction(
                theme, outline, full_article, language
            )
            return await _generate_with_gemini(
                system_instruction,
                user_content,
                ArticleReview,
                model,
            )
    except Exception as e:
        logger.error(f"Failed to review article with {provider.value}: {e}")
        return None


# =============================================================================
# Pipeline Nodes
# =============================================================================


async def generate_multiple_outlines_node(state: ParallelWorldState) -> ParallelWorldState:
    """
    Generate multiple article outlines in parallel.

    This implements the first parallel world branching point.
    """
    logger.info(f"Generating {state['num_outline_variants']} parallel outline variants for theme: {state['theme']}")

    provider = LLMProvider(state["llm_provider"])
    model = state["model"]
    theme = state["theme"]
    language = state["language"]
    num_variants = state["num_outline_variants"]

    # Generate multiple outlines in parallel
    tasks = [generate_outline(theme, language, model, provider) for _ in range(num_variants)]
    outlines = await asyncio.gather(*tasks)

    # Create parallel sessions for each outline
    outline_sessions = []
    for i, outline in enumerate(outlines):
        if outline:
            session = ParallelSession(
                outline=outline,
                metadata={"variant_number": i + 1, "phase": "outline_generation"},
            )
            outline_sessions.append(session)
            logger.info(f"Generated outline variant {i + 1}: {outline.title}")
        else:
            logger.warning(f"Failed to generate outline variant {i + 1}")

    if not outline_sessions:
        error_msg = "Failed to generate any outlines"
        logger.error(error_msg)
        return {**state, "error": error_msg}

    logger.info(f"Successfully generated {len(outline_sessions)} outline variants")

    return {
        **state,
        "outline_sessions": outline_sessions,
        "error": None,
    }


async def generate_first_half_node(state: ParallelWorldState) -> ParallelWorldState:
    """Generate the first half of the article based on selected outline."""
    logger.info("Generating first half of article...")

    selected_id = state.get("selected_outline_session_id")
    if not selected_id:
        error_msg = "No outline selected for first half generation"
        logger.error(error_msg)
        return {**state, "error": error_msg}

    # Find the selected session
    selected_session = next(
        (s for s in state["outline_sessions"] if s.session_id == selected_id),
        None,
    )

    if not selected_session or not selected_session.outline:
        error_msg = "Selected outline session not found or has no outline"
        logger.error(error_msg)
        return {**state, "error": error_msg}

    provider = LLMProvider(state["llm_provider"])
    model = state["model"]
    language = state["language"]
    outline = selected_session.outline

    # Generate first half
    first_half_content = await generate_first_half(outline, language, model, provider)

    if not first_half_content:
        error_msg = "Failed to generate first half"
        logger.error(error_msg)
        return {**state, "error": error_msg}

    logger.info(f"Successfully generated first half ({len(first_half_content)} characters)")

    # Create new session with first half
    first_half_session = ParallelSession(
        parent_session_id=selected_session.session_id,
        outline=outline,
        first_half=first_half_content,
        metadata={"phase": "first_half_generated"},
    )

    return {
        **state,
        "first_half_session": first_half_session,
        "error": None,
    }


async def generate_multiple_second_halves_node(state: ParallelWorldState) -> ParallelWorldState:
    """
    Generate multiple second half variants in parallel.

    This implements the second parallel world branching point.
    """
    logger.info(f"Generating {state['num_second_half_variants']} parallel second half variants...")

    first_half_session = state.get("first_half_session")
    if not first_half_session or not first_half_session.outline or not first_half_session.first_half:
        error_msg = "No first half session available"
        logger.error(error_msg)
        return {**state, "error": error_msg}

    provider = LLMProvider(state["llm_provider"])
    model = state["model"]
    language = state["language"]
    outline = first_half_session.outline
    first_half = first_half_session.first_half
    num_variants = state["num_second_half_variants"]

    # Generate multiple second halves in parallel
    tasks = [generate_second_half(outline, first_half, language, model, provider) for _ in range(num_variants)]
    second_halves = await asyncio.gather(*tasks)

    # Create parallel sessions for each second half
    second_half_sessions = []
    for i, second_half in enumerate(second_halves):
        if second_half:
            session = ParallelSession(
                parent_session_id=first_half_session.session_id,
                outline=outline,
                first_half=first_half,
                second_half=second_half,
                metadata={"variant_number": i + 1, "phase": "second_half_generated"},
            )
            second_half_sessions.append(session)
            logger.info(f"Generated second half variant {i + 1} ({len(second_half)} characters)")
        else:
            logger.warning(f"Failed to generate second half variant {i + 1}")

    if not second_half_sessions:
        error_msg = "Failed to generate any second half variants"
        logger.error(error_msg)
        return {**state, "error": error_msg}

    logger.info(f"Successfully generated {len(second_half_sessions)} second half variants")

    return {
        **state,
        "second_half_sessions": second_half_sessions,
        "error": None,
    }


async def review_all_articles_node(state: ParallelWorldState) -> ParallelWorldState:
    """Review all complete articles in parallel using LLM-as-a-Judge."""
    logger.info("Reviewing all article variants...")

    second_half_sessions = state.get("second_half_sessions", [])
    if not second_half_sessions:
        error_msg = "No second half sessions available for review"
        logger.error(error_msg)
        return {**state, "error": error_msg}

    provider = LLMProvider(state["llm_provider"])
    model = state["model"]
    language = state["language"]
    theme = state["theme"]

    # Review all articles in parallel
    tasks = []
    sessions_to_review = []

    for session in second_half_sessions:
        if session.outline and session.first_half and session.second_half:
            full_article = f"{session.first_half}\n\n{session.second_half}"
            task = review_article(theme, session.outline, full_article, language, model, provider)
            tasks.append(task)
            sessions_to_review.append(session)

    reviews = await asyncio.gather(*tasks)

    # Create reviewed sessions
    reviewed_sessions = []
    for session, review in zip(sessions_to_review, reviews):
        if review:
            reviewed_session = ParallelSession(
                session_id=session.session_id,
                parent_session_id=session.parent_session_id,
                outline=session.outline,
                first_half=session.first_half,
                second_half=session.second_half,
                review=review,
                metadata={**session.metadata, "phase": "reviewed"},
                created_at=session.created_at,
            )
            reviewed_sessions.append(reviewed_session)
            logger.info(f"Reviewed variant {session.metadata.get('variant_number', '?')}: Grade {review.grade}/5")
        else:
            logger.warning(f"Failed to review variant {session.metadata.get('variant_number', '?')}")

    if not reviewed_sessions:
        error_msg = "Failed to review any articles"
        logger.error(error_msg)
        return {**state, "error": error_msg}

    logger.info(f"Successfully reviewed {len(reviewed_sessions)} article variants")

    return {
        **state,
        "reviewed_sessions": reviewed_sessions,
        "error": None,
    }


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


# =============================================================================
# Graph Construction
# =============================================================================


def create_parallel_world_graph() -> StateGraph:
    """
    Create the parallel world article generation LangGraph pipeline.

    Pipeline flow:
    1. Generate multiple outlines in parallel (Parallel World 1)
    2. Wait for user to select outline (Human-in-the-loop 1)
    3. Generate first half based on selected outline
    4. Generate multiple second halves in parallel (Parallel World 2)
    5. Review all complete articles using LLM-as-a-Judge
    6. Wait for user to select final article (Human-in-the-loop 2)

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

    graph.add_edge("wait_for_final_selection", END)

    return graph.compile()
