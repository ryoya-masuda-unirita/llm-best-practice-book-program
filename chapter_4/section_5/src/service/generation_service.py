import asyncio
from typing import Any, Literal
from uuid import uuid4

from google.genai.types import GenerateContentConfig

from src.client.llm_client import LLMProvider, google_genai_client, openai_client
from src.logger import make_logger
from src.model.parallel_world_model import (
    ArticleHalf,
    ArticleOutline,
    ArticleReview,
    BestArticleSelection,
    ParallelSession,
    ParallelWorldState,
)
from src.prompt.parallel_world_prompt import (
    make_article_review_system_instruction,
    make_choose_best_first_half_system_instruction,
    make_first_half_generation_system_instruction,
    make_outline_generation_system_instruction,
    make_second_half_generation_system_instruction,
    make_second_half_regeneration_system_instruction,
)

logger = make_logger(__name__)


# =============================================================================
# LLM Generation Functions
# =============================================================================


async def _generate_with_openai(
    prompt: list[dict[str, str]],
    response_format: type,
    model: str,
) -> Any:
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
) -> Any:
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
    system_instruction, user_content = make_outline_generation_system_instruction(theme, language)
    try:
        if provider == LLMProvider.OPENAI:
            prompt = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content},
            ]
            return await _generate_with_openai(prompt, ArticleOutline, model)
        else:  # Gemini
            return await _generate_with_gemini(system_instruction, user_content, ArticleOutline, model)
    except Exception as e:
        logger.error(f"Failed to generate outline with {provider.value}: {e}")
        return None


async def generate_first_half(
    outline: ArticleOutline,
    language: Literal["en", "ja"],
    model: str,
    provider: LLMProvider,
) -> ArticleHalf | None:
    """Generate first half of article using specified LLM provider."""
    system_instruction, user_content = make_first_half_generation_system_instruction(outline, language)
    try:
        if provider == LLMProvider.OPENAI:
            prompt = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content},
            ]
            result = await _generate_with_openai(prompt, ArticleHalf, model)
            return result
        else:  # Gemini
            result = await _generate_with_gemini(system_instruction, user_content, ArticleHalf, model)
            return result
    except Exception as e:
        logger.error(f"Failed to generate first half with {provider.value}: {e}")
        return None


async def choose_best_first_half(
    outline: ArticleOutline,
    first_half_candidates: list[ArticleHalf],
    language: Literal["en", "ja"],
    model: str,
    provider: LLMProvider,
) -> ArticleHalf | None:
    """Choose the best first half from candidates using specified LLM provider."""
    first_halves = {uuid4().hex: candidate for candidate in first_half_candidates}
    system_instruction, user_content = make_choose_best_first_half_system_instruction(outline, first_halves, language)
    try:
        if provider == LLMProvider.OPENAI:
            prompt = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content},
            ]
            result = await _generate_with_openai(prompt, BestArticleSelection, model)
            return first_halves[result.selected_id]
        else:  # Gemini
            result = await _generate_with_gemini(system_instruction, user_content, BestArticleSelection, model)
            return first_halves[result.selected_id]
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
    system_instruction, user_content = make_second_half_generation_system_instruction(outline, first_half, language)
    try:
        if provider == LLMProvider.OPENAI:
            prompt = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content},
            ]
            result = await _generate_with_openai(prompt, ArticleHalf, model)
            return result.content
        else:  # Gemini
            result = await _generate_with_gemini(system_instruction, user_content, ArticleHalf, model)
            return result.content
    except Exception as e:
        logger.error(f"Failed to generate second half with {provider.value}: {e}")
        return None


async def review_article(
    theme: str,
    outline: ArticleOutline,
    full_article: str,
    model: str,
    provider: LLMProvider,
) -> ArticleReview | None:
    """Review article using LLM-as-a-Judge with specified provider."""
    system_instruction, user_content = make_article_review_system_instruction(theme, outline, full_article)
    try:
        if provider == LLMProvider.OPENAI:
            prompt = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content},
            ]
            return await _generate_with_openai(prompt, ArticleReview, model)
        else:  # Gemini
            return await _generate_with_gemini(system_instruction, user_content, ArticleReview, model)
    except Exception as e:
        logger.error(f"Failed to review article with {provider.value}: {e}")
        return None


async def regenerate_second_half(
    outline: ArticleOutline,
    first_half: str,
    language: Literal["en", "ja"],
    model: str,
    provider: LLMProvider,
    previous_attempts: list[tuple[str, ArticleReview]],
) -> str | None:
    """
    Regenerate second half based on previous feedback.

    Args:
        outline: Article outline
        first_half: First half content
        language: Target language
        model: Model name
        provider: LLM provider
        previous_attempts: List of (second_half_content, review) from rejected attempts

    Returns:
        New second half content or None if failed
    """
    system_instruction, user_content = make_second_half_regeneration_system_instruction(
        outline, first_half, language, previous_attempts
    )
    try:
        if provider == LLMProvider.OPENAI:
            prompt = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content},
            ]
            result = await _generate_with_openai(prompt, ArticleHalf, model)
            return result.content
        else:  # Gemini
            result = await _generate_with_gemini(system_instruction, user_content, ArticleHalf, model)
            return result.content
    except Exception as e:
        logger.error(f"Failed to regenerate second half with {provider.value}: {e}")
        return None


# =============================================================================
# Pipeline Nodes
# =============================================================================


def return_error_state(state: ParallelWorldState, error_msg: str) -> ParallelWorldState:
    """Helper to return state with error message."""
    logger.error(error_msg)
    return {**state, "error": error_msg}


async def generate_multiple_outlines_node(
    state: ParallelWorldState,
) -> ParallelWorldState:
    """
    Generate multiple article outlines in parallel.

    This implements the first parallel world branching point.
    """
    logger.info(f"Generating {state['num_outline_variants']} parallel outline variants for theme: {state['theme']}")

    # Generate multiple outlines in parallel
    tasks = [
        generate_outline(
            state["theme"],
            state["language"],
            state["model"],
            LLMProvider(state["llm_provider"]),
        )
        for _ in range(state["num_outline_variants"])
    ]
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
        return return_error_state(state, "Failed to generate any outlines")

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
        return return_error_state(state, "No outline selected for first half generation")

    # Find the selected session
    selected_session = next((s for s in state["outline_sessions"] if s.session_id == selected_id), None)

    if not selected_session or not selected_session.outline:
        error_msg = "Selected outline session not found or has no outline"
        logger.error(error_msg)
        return {**state, "error": error_msg}

    # Generate first half
    tasks = [
        generate_first_half(
            selected_session.outline,
            state["language"],
            state["model"],
            LLMProvider(state["llm_provider"]),
        )
        for _ in range(state["num_outline_variants"])
    ]
    first_half_contents: list[ArticleHalf] = await asyncio.gather(*tasks)  # type: ignore

    if not first_half_contents:
        return return_error_state(state, "Failed to generate first half candidates")

    best_first_half = await choose_best_first_half(
        selected_session.outline,
        first_half_contents,
        state["language"],
        state["model"],
        LLMProvider(state["llm_provider"]),
    )

    if not best_first_half:
        return return_error_state(state, "Failed to generate first half")

    logger.info(f"Successfully generated first half ({len(best_first_half.content)} characters)")

    # Create new session with first half
    first_half_session = ParallelSession(
        parent_session_id=selected_session.session_id,
        outline=selected_session.outline,
        first_half=best_first_half.content,
        metadata={"phase": "first_half_generated"},
    )

    return {
        **state,
        "first_half_session": first_half_session,
        "error": None,
    }


async def generate_multiple_second_halves_node(
    state: ParallelWorldState,
) -> ParallelWorldState:
    """
    Generate multiple second half variants in parallel.

    This implements the second parallel world branching point.
    """
    logger.info(f"Generating {state['num_second_half_variants']} parallel second half variants...")

    first_half_session = state.get("first_half_session")
    if not first_half_session or not first_half_session.outline or not first_half_session.first_half:
        return return_error_state(state, "No first half session available for second half generation")

    # Generate multiple second halves in parallel
    tasks = [
        generate_second_half(
            first_half_session.outline,
            first_half_session.first_half,
            state["language"],
            state["model"],
            LLMProvider(state["llm_provider"]),
        )
        for _ in range(state["num_second_half_variants"])
    ]
    second_halves = await asyncio.gather(*tasks)

    # Create parallel sessions for each second half
    second_half_sessions = []
    for i, second_half in enumerate(second_halves):
        if second_half:
            session = ParallelSession(
                parent_session_id=first_half_session.session_id,
                outline=first_half_session.outline,
                first_half=first_half_session.first_half,
                second_half=second_half,
                metadata={"variant_number": i + 1, "phase": "second_half_generated"},
            )
            second_half_sessions.append(session)
            logger.info(f"Generated second half variant {i + 1} ({len(second_half)} characters)")
        else:
            logger.warning(f"Failed to generate second half variant {i + 1}")

    if not second_half_sessions:
        return return_error_state(state, "Failed to generate any second half variants")

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
        return return_error_state(state, "No second half sessions available for review")

    # Review all articles in parallel
    tasks = []
    sessions_to_review = []

    for session in second_half_sessions:
        if session.outline and session.first_half and session.second_half:
            full_article = f"{session.first_half}\n\n{session.second_half}"
            task = review_article(
                state["theme"],
                session.outline,
                full_article,
                state["model"],
                LLMProvider(state["llm_provider"]),
            )
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
        return return_error_state(state, "Failed to review any articles")

    logger.info(f"Successfully reviewed {len(reviewed_sessions)} article variants")

    return {
        **state,
        "reviewed_sessions": reviewed_sessions,
        "error": None,
    }


async def regenerate_second_halves_after_rejection_node(
    state: ParallelWorldState,
) -> ParallelWorldState:
    """
    Regenerate multiple second half variants after human rejection.

    This uses feedback from rejected sessions to generate improved versions.
    """
    logger.info("Regenerating second half variants based on previous feedback...")

    first_half_session = state.get("first_half_session")
    if not first_half_session or not first_half_session.outline or not first_half_session.first_half:
        return return_error_state(state, "No first half session available for regeneration")

    # Collect previous rejected attempts for feedback
    rejected_ids = state.get("rejected_session_ids", [])
    reviewed_sessions = state.get("reviewed_sessions", [])

    previous_attempts: list[tuple[str, ArticleReview]] = []
    for session in reviewed_sessions:
        if session.session_id in rejected_ids and session.second_half and session.review:
            previous_attempts.append((session.second_half, session.review))

    logger.info(f"Using feedback from {len(previous_attempts)} previous attempt(s)")

    # Generate multiple new second halves in parallel, all with feedback
    tasks = [
        regenerate_second_half(
            first_half_session.outline,
            first_half_session.first_half,
            state["language"],
            state["model"],
            LLMProvider(state["llm_provider"]),
            previous_attempts,
        )
        for _ in range(state["num_second_half_variants"])
    ]
    second_halves = await asyncio.gather(*tasks)

    # Create parallel sessions for each regenerated second half
    new_second_half_sessions = []
    for i, second_half in enumerate(second_halves):
        if second_half:
            session = ParallelSession(
                parent_session_id=first_half_session.session_id,
                outline=first_half_session.outline,
                first_half=first_half_session.first_half,
                second_half=second_half,
                metadata={
                    "variant_number": i + 1,
                    "phase": "second_half_regenerated",
                    "iteration": state.get("review_loop_iteration", 0),
                },
            )
            new_second_half_sessions.append(session)
            logger.info(f"Regenerated second half variant {i + 1} ({len(second_half)} characters)")
        else:
            logger.warning(f"Failed to regenerate second half variant {i + 1}")

    if not new_second_half_sessions:
        return return_error_state(state, "Failed to regenerate any second half variants")

    logger.info(f"Successfully regenerated {len(new_second_half_sessions)} second half variants")

    return {
        **state,
        "second_half_sessions": new_second_half_sessions,
        "error": None,
    }
