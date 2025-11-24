"""
Runner Service for Parallel World Article Generation.

This module orchestrates the AI agent pipeline with human-in-the-loop interactions.
It handles:
- User interface and interactions (display, input)
- Pipeline orchestration and phase management
- File output and saving

For the core AI agent pipeline logic, see parallel_world_service.py
"""

from typing import Literal

import click
from src.client.llm_client import LLMProvider
from src.logger import make_logger
from src.model.parallel_world_model import (
    CompletedArticle,
    ParallelWorldState,
)
from src.service.generation_service import (
    generate_first_half_node,
    generate_multiple_outlines_node,
    generate_multiple_second_halves_node,
    regenerate_second_halves_after_rejection_node,
    review_all_articles_node,
)
from src.service.helper import (
    display_outlines,
    display_reviews,
    get_final_article_selection,
    get_human_approval,
    get_outline_selection,
    print_article_preview,
    print_separator,
    save_article_files,
)

logger = make_logger(__name__)


# =============================================================================
# Phase Functions
# =============================================================================


async def generate_outlines(state: ParallelWorldState) -> ParallelWorldState:
    """
    Phase 1: Generate multiple outline variants in parallel.

    Args:
        state: Current pipeline state

    Returns:
        Updated state with outline_sessions populated
    """
    print_separator()
    click.echo("🌍 PHASE 1: Generating Multiple Outline Variants (Parallel World Branching)")
    click.echo(f"Creating {state['num_outline_variants']} different article outlines in parallel...")

    state = await generate_multiple_outlines_node(state)

    if state.get("error"):
        click.echo(f"❌ Error: {state['error']}", err=True)
        return state

    outline_sessions = state["outline_sessions"]
    click.echo(f"✅ Generated {len(outline_sessions)} outline variants")
    return state


async def select_outline(state: ParallelWorldState, auto_select: bool) -> ParallelWorldState:
    """
    Phase 2: Human selects preferred outline.

    Args:
        state: Current pipeline state
        auto_select: Whether to auto-select without user input

    Returns:
        Updated state with selected_outline_session_id set
    """
    print_separator()
    click.echo("👤 PHASE 2: Human-in-the-Loop - Select Your Preferred Outline")

    outline_sessions = state["outline_sessions"]
    display_outlines(outline_sessions)
    selected_idx = get_outline_selection(outline_sessions, auto_select)

    selected_outline_session = outline_sessions[selected_idx]
    state["selected_outline_session_id"] = selected_outline_session.session_id
    click.echo(f"✅ Selected: {selected_outline_session.outline.title}")  # type: ignore

    return state


async def generate_first_half(state: ParallelWorldState) -> ParallelWorldState:
    """
    Phase 3: Generate first half of article based on selected outline.

    Args:
        state: Current pipeline state

    Returns:
        Updated state with first_half_session populated
    """
    print_separator()
    click.echo("📝 PHASE 3: Generating First Half of Article")

    state = await generate_first_half_node(state)

    if state.get("error"):
        click.echo(f"❌ Error: {state['error']}", err=True)
        return state

    first_half_session = state["first_half_session"]
    if first_half_session and first_half_session.first_half:
        click.echo(f"✅ Generated first half ({len(first_half_session.first_half)} characters)")
        click.echo("\nPreview:")
        print_article_preview(first_half_session.first_half)

    return state


async def generate_second_halves(state: ParallelWorldState) -> ParallelWorldState:
    """
    Phase 4: Generate multiple second half variants in parallel.

    Args:
        state: Current pipeline state

    Returns:
        Updated state with second_half_sessions populated
    """
    print_separator()
    click.echo("🌍 PHASE 4: Generating Multiple Second Half Variants (Parallel World Branching)")
    click.echo(f"Creating {state['num_second_half_variants']} different endings in parallel...")

    state = await generate_multiple_second_halves_node(state)

    if state.get("error"):
        click.echo(f"❌ Error: {state['error']}", err=True)
        return state

    second_half_sessions = state["second_half_sessions"]
    click.echo(f"✅ Generated {len(second_half_sessions)} second half variants")

    return state


async def review_articles(state: ParallelWorldState) -> ParallelWorldState:
    """
    Phase 5: Review all complete articles with LLM-as-a-Judge.

    Args:
        state: Current pipeline state

    Returns:
        Updated state with reviewed_sessions populated
    """
    print_separator()
    click.echo("⚖️  PHASE 5: Reviewing All Articles with LLM-as-a-Judge")

    state = await review_all_articles_node(state)

    if state.get("error"):
        click.echo(f"❌ Error: {state['error']}", err=True)
        return state

    reviewed_sessions = state["reviewed_sessions"]
    click.echo(f"✅ Reviewed {len(reviewed_sessions)} complete articles")

    return state


def select_final_article(
    state: ParallelWorldState,
    auto_select: bool,
    iteration: int,
) -> tuple[ParallelWorldState, CompletedArticle | None]:
    """
    Phase 6: Human selects their preferred final article from reviewed sessions.

    Args:
        state: Current pipeline state
        auto_select: Whether to auto-select without user input
        iteration: Current iteration number

    Returns:
        Tuple of (updated_state, completed_article or None if failed)
    """
    print_separator()
    click.echo(f"👤 PHASE 6: Human-in-the-Loop - Select Your Preferred Article (Iteration {iteration})")

    reviewed_sessions = state["reviewed_sessions"]
    display_reviews(reviewed_sessions)
    best_idx = get_final_article_selection(reviewed_sessions, auto_select)

    final_session = reviewed_sessions[best_idx]
    state["final_selected_session_id"] = final_session.session_id

    # Create completed article for approval
    completed_article = final_session.to_completed_article(state["language"])

    if not completed_article:
        click.echo("❌ Failed to create completed article", err=True)
        return state, None

    return state, completed_article


def approve_article(
    state: ParallelWorldState,
    completed_article: CompletedArticle,
    auto_select: bool,
) -> tuple[ParallelWorldState, bool]:
    """
    Phase 7: Get human approval or rejection for selected article.

    Args:
        state: Current pipeline state
        completed_article: The article to approve or reject
        auto_select: Whether to auto-approve based on grade

    Returns:
        Tuple of (updated_state, approval_status)
    """
    print_separator()
    click.echo("✅ PHASE 7: Human-in-the-Loop - Approve or Reject Article")

    human_approved = get_human_approval(completed_article, auto_select)
    state["human_approved"] = human_approved

    if human_approved:
        click.echo("\n✅ Article approved! Proceeding to save...")
    else:
        click.echo("\n❌ Article rejected. Regenerating second half with feedback...")

    return state, human_approved


async def regenerate_and_review(
    state: ParallelWorldState,
    iteration: int,
) -> ParallelWorldState:
    """
    Phase 8: Regenerate second halves with feedback and re-review all articles.

    Args:
        state: Current pipeline state
        iteration: Current iteration number

    Returns:
        Updated state with regenerated and re-reviewed sessions
    """
    # Track rejected session
    if "rejected_session_ids" not in state:
        state["rejected_session_ids"] = []

    final_session_id = state.get("final_selected_session_id")
    if final_session_id:
        state["rejected_session_ids"].append(final_session_id)

    state["review_loop_iteration"] = iteration

    # Regenerate second halves with feedback
    print_separator()
    click.echo(f"🔄 PHASE 8: Regenerating Second Half Variants (Iteration {iteration})")
    click.echo(f"Using feedback from {len(state['rejected_session_ids'])} rejected attempt(s)...")

    state = await regenerate_second_halves_after_rejection_node(state)

    if state.get("error"):
        click.echo(f"❌ Error during regeneration: {state['error']}", err=True)
        return state

    second_half_sessions = state["second_half_sessions"]
    click.echo(f"✅ Regenerated {len(second_half_sessions)} second half variants")

    # Review regenerated articles
    print_separator()
    click.echo("⚖️  Re-reviewing Articles with LLM-as-a-Judge")

    state = await review_all_articles_node(state)

    if state.get("error"):
        click.echo(f"❌ Error during review: {state['error']}", err=True)
        return state

    reviewed_sessions = state["reviewed_sessions"]
    click.echo(f"✅ Re-reviewed {len(reviewed_sessions)} article variants")

    return state


async def review_loop(
    state: ParallelWorldState,
    auto_select: bool,
    max_iterations: int = 5,
) -> tuple[ParallelWorldState, CompletedArticle | None, bool, int]:
    """
    Phase 6-8: Review loop - select article, get approval, regenerate if rejected.

    This phase combines:
    - Phase 6: Human selects final article
    - Phase 7: Human approves/rejects article
    - Phase 8: Regenerate second halves if rejected

    Args:
        state: Current pipeline state
        auto_select: Whether to auto-select without user input
        max_iterations: Maximum number of review iterations

    Returns:
        Tuple of (updated_state, final_article, human_approved, iteration_count)
    """
    iteration = 0
    human_approved = False
    final_completed_article = None

    while not human_approved and iteration < max_iterations:
        iteration += 1

        # Phase 6: Select final article
        state, completed_article = select_final_article(state, auto_select, iteration)

        if not completed_article:
            return state, None, False, iteration

        # Phase 7: Get human approval
        state, human_approved = approve_article(state, completed_article, auto_select)

        if human_approved:
            final_completed_article = completed_article
            break

        # Phase 8: Regenerate and re-review if rejected
        state = await regenerate_and_review(state, iteration)

        if state.get("error"):
            return state, None, False, iteration

    # Handle max iterations reached
    if not human_approved:
        click.echo(f"\n⚠️  Maximum iterations ({max_iterations}) reached without approval")
        click.echo("Saving the last selected article...")
        if not final_completed_article:
            final_completed_article = completed_article

    return state, final_completed_article, human_approved, iteration


def save_article(
    state: ParallelWorldState,
    final_completed_article: CompletedArticle,
    output_directory: str,
    iteration_count: int,
) -> tuple[str, str, str]:
    """
    Phase 9: Save final article and all variants to disk.

    Args:
        state: Current pipeline state
        final_completed_article: The selected complete article
        output_directory: Directory to save files
        iteration_count: Number of review loop iterations

    Returns:
        Tuple of (json_path, md_path, variants_dir)
    """
    print_separator()
    click.echo("💾 Saving Final Article")

    # Save files
    json_path, md_path, variants_dir = save_article_files(
        final_completed_article,
        state["reviewed_sessions"],
        state["language"],
        output_directory,
    )

    # Display summary
    click.echo(
        f"""
✅ Article Generation Complete!

Selected Article Details:
  Title: {final_completed_article.outline.title}
  Grade: {final_completed_article.review.grade if final_completed_article.review else "N/A"}/5
  Total Length: {len(final_completed_article.get_full_content())} characters
  Review Loop Iterations: {iteration_count}

Files saved:
  📄 JSON: {json_path}
  📝 Markdown: {md_path}

Session Metadata:
  Session ID: {final_completed_article.session_id}
  Created: {final_completed_article.created_at}
  Outline variants generated: {len(state["outline_sessions"])}
  Second half variants generated: {len(state["second_half_sessions"])}
"""
    )

    click.echo(f"📁 All variants saved to: {variants_dir}")

    print_separator()
    click.echo("🎉 Parallel World Article Generation Complete!")

    return json_path, md_path, variants_dir


# =============================================================================
# Main Runner Function
# =============================================================================


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
    """
    Run the complete parallel world article generation workflow with human-in-the-loop and review loop.

    This orchestrates the entire pipeline with user interactions at decision points.

    Workflow:
    1. Generate multiple outlines in parallel (AI Agent)
    2. User selects preferred outline (Human-in-the-Loop #1)
    3. Generate first half based on selection (AI Agent)
    4. Generate multiple second half variants in parallel (AI Agent)
    5. Review all complete articles with LLM-as-a-Judge (AI Agent)
    6. User selects final article (Human-in-the-Loop #2)
    7. User approves or rejects article (Human-in-the-Loop #3)
    8. If rejected: Regenerate second halves with feedback, go back to step 5
       If approved: Save selected article and all variants

    Args:
        theme: Article theme/topic
        language: Target language ("en" or "ja")
        llm_provider: LLM provider to use
        model: Model name
        output_directory: Directory to save output files
        num_outline_variants: Number of outline variants to generate
        num_second_half_variants: Number of second half variants to generate
        auto_select: Whether to auto-select options without user interaction

    Returns:
        CompletedArticle if successful, None otherwise
    """

    # Initialize pipeline state
    state: ParallelWorldState = {
        "theme": theme,
        "language": language,
        "outline_sessions": [],
        "selected_outline_session_id": None,
        "first_half_session": None,
        "second_half_sessions": [],
        "reviewed_sessions": [],
        "final_selected_session_id": None,
        "human_approved": None,
        "rejected_session_ids": [],
        "review_loop_iteration": 0,
        "llm_provider": llm_provider.value,
        "model": model,
        "error": None,
        "num_outline_variants": num_outline_variants,
        "num_second_half_variants": num_second_half_variants,
    }

    # Phase 1: Generate Multiple Outlines
    state = await generate_outlines(state)
    if state.get("error"):
        return None

    # Phase 2: Human Selects Outline
    state = await select_outline(state, auto_select)
    if state.get("error"):
        return None

    # Phase 3: Generate First Half
    state = await generate_first_half(state)
    if state.get("error"):
        return None

    # Phase 4: Generate Multiple Second Halves
    state = await generate_second_halves(state)
    if state.get("error"):
        return None

    # Phase 5: Review All Articles
    state = await review_articles(state)
    if state.get("error"):
        return None

    # Phase 6-8: Review Loop (select, approve/reject, regenerate)
    state, final_completed_article, human_approved, iteration = await review_loop(state, auto_select, max_iterations=5)

    if not final_completed_article:
        return None

    # Phase 9: Save Final Article and All Variants
    save_article(state, final_completed_article, output_directory, iteration)

    return final_completed_article
