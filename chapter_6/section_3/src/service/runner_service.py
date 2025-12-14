"""Runner Service for Parallel World Article Generation."""

from typing import Literal

import click
from src.client.llm_client import LLMProvider
from src.logger import make_logger
from src.model.model import (
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
    get_rollback_choice,
    print_article_preview,
    print_separator,
    save_article_files,
)

logger = make_logger(__name__)


def get_current_phase(state: ParallelWorldState) -> int:
    """Determine the current phase based on which state variables are populated."""
    if state.get("human_approved") is not None:
        return 7
    elif state.get("final_selected_session_id") is not None:
        return 6
    elif state.get("reviewed_sessions"):
        return 5
    elif state.get("second_half_sessions"):
        return 4
    elif state.get("first_half_session") is not None:
        return 3
    elif state.get("selected_outline_session_id") is not None:
        return 2
    elif state.get("outline_sessions"):
        return 1
    else:
        return 0


def get_phase_name(phase: int) -> str:
    """Get human-readable phase name."""
    phase_names = {
        0: "Initial State",
        1: "Outline Generation Complete",
        2: "Outline Selected",
        3: "First Half Complete",
        4: "Second Half Variants Generated",
        5: "All Articles Reviewed",
        6: "Article Selected",
        7: "Approval Decision Made",
    }
    return phase_names.get(phase, "Unknown Phase")


def forget_phases_after(state: ParallelWorldState, target_phase: int) -> ParallelWorldState:
    """Remove state variables after target phase to implement rollback."""
    click.echo(f"\n🔄 Rolling back to Phase {target_phase}: {get_phase_name(target_phase)}")
    click.echo("   Forgetting all subsequent phases...\n")

    if target_phase < 7:
        state.pop("human_approved", None)
        state.pop("rejected_session_ids", None)
        state.pop("review_loop_iteration", None)
        logger.info("Forgot Phase 7: Approval decision")

    if target_phase < 6:
        state.pop("final_selected_session_id", None)
        logger.info("Forgot Phase 6: Article selection")

    if target_phase < 5:
        state.pop("reviewed_sessions", None)
        logger.info("Forgot Phase 5: Article reviews")

    if target_phase < 4:
        state.pop("second_half_sessions", None)
        logger.info("Forgot Phase 4: Second half variants")

    if target_phase < 3:
        state.pop("first_half_session", None)
        logger.info("Forgot Phase 3: First half")

    if target_phase < 2:
        state.pop("selected_outline_session_id", None)
        logger.info("Forgot Phase 2: Outline selection")

    if target_phase < 1:
        state.pop("outline_sessions", None)
        logger.info("Forgot Phase 1: Outlines")

    state.pop("error", None)

    click.echo(f"✅ Rolled back to Phase {target_phase}. Forgotten phases will be regenerated.\n")

    return state


def get_available_rollback_phases(state: ParallelWorldState) -> list[tuple[int, str]]:
    """Get list of available phases to rollback to."""
    current_phase = get_current_phase(state)
    available = []

    for phase in range(current_phase):
        available.append((phase, get_phase_name(phase)))

    return available


async def generate_outlines(state: ParallelWorldState) -> ParallelWorldState:
    """Phase 1: Generate multiple outline variants in parallel."""
    print_separator()
    click.echo("🌍 PHASE 1: Generating Multiple Outline Variants (Parallel World Branching)")
    click.echo(f"Creating {state['num_outline_variants']} different article outlines in parallel...")

    state = await generate_multiple_outlines_node(state)

    if state.get("error"):
        click.echo(f"❌ Error: {state['error']}", err=True)
        return state

    outline_sessions = state.get("outline_sessions", [])
    click.echo(f"✅ Generated {len(outline_sessions)} outline variants")
    return state


async def select_outline(state: ParallelWorldState, auto_select: bool) -> ParallelWorldState:
    """Phase 2: Human selects preferred outline."""
    print_separator()
    click.echo("👤 PHASE 2: Human-in-the-Loop - Select Your Preferred Outline")

    outline_sessions = state.get("outline_sessions", [])
    if not outline_sessions:
        state["error"] = "No outline sessions available"
        return state

    display_outlines(outline_sessions)
    selected_idx = get_outline_selection(outline_sessions, auto_select)

    selected_outline_session = outline_sessions[selected_idx]
    state["selected_outline_session_id"] = selected_outline_session.session_id
    click.echo(f"✅ Selected: {selected_outline_session.outline.title}")  # type: ignore

    return state


async def generate_first_half(state: ParallelWorldState) -> ParallelWorldState:
    """Phase 3: Generate first half of article based on selected outline."""
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
    """Phase 4: Generate multiple second half variants in parallel."""
    print_separator()
    click.echo("🌍 PHASE 4: Generating Multiple Second Half Variants (Parallel World Branching)")
    click.echo(f"Creating {state['num_second_half_variants']} different endings in parallel...")

    state = await generate_multiple_second_halves_node(state)

    if state.get("error"):
        click.echo(f"❌ Error: {state['error']}", err=True)
        return state

    second_half_sessions = state.get("second_half_sessions", [])
    click.echo(f"✅ Generated {len(second_half_sessions)} second half variants")

    return state


async def review_articles(state: ParallelWorldState) -> ParallelWorldState:
    """Phase 5: Review all complete articles with LLM-as-a-Judge."""
    print_separator()
    click.echo("⚖️  PHASE 5: Reviewing All Articles with LLM-as-a-Judge")

    state = await review_all_articles_node(state)

    if state.get("error"):
        click.echo(f"❌ Error: {state['error']}", err=True)
        return state

    reviewed_sessions = state.get("reviewed_sessions", [])
    click.echo(f"✅ Reviewed {len(reviewed_sessions)} complete articles")

    return state


def select_final_article(
    state: ParallelWorldState,
    auto_select: bool,
    iteration: int,
) -> tuple[ParallelWorldState, CompletedArticle | None]:
    """Phase 6: Human selects their preferred final article from reviewed sessions."""
    print_separator()
    click.echo(f"👤 PHASE 6: Human-in-the-Loop - Select Your Preferred Article (Iteration {iteration})")

    reviewed_sessions = state.get("reviewed_sessions", [])
    if not reviewed_sessions:
        state["error"] = "No reviewed sessions available"
        return state, None

    display_reviews(reviewed_sessions)
    best_idx = get_final_article_selection(reviewed_sessions, auto_select)

    final_session = reviewed_sessions[best_idx]
    state["final_selected_session_id"] = final_session.session_id

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
    """Phase 7: Get human approval or rejection for selected article."""
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
    """Phase 8: Regenerate second halves with feedback and re-review all articles."""
    rejected_session_ids = state.get("rejected_session_ids", [])

    final_session_id = state.get("final_selected_session_id")
    if final_session_id and final_session_id not in rejected_session_ids:
        rejected_session_ids.append(final_session_id)
        state["rejected_session_ids"] = rejected_session_ids

    state["review_loop_iteration"] = iteration

    print_separator()
    click.echo(f"🔄 PHASE 8: Regenerating Second Half Variants (Iteration {iteration})")
    click.echo(f"Using feedback from {len(rejected_session_ids)} rejected attempt(s)...")

    state = await regenerate_second_halves_after_rejection_node(state)

    if state.get("error"):
        click.echo(f"❌ Error during regeneration: {state['error']}", err=True)
        return state

    second_half_sessions = state.get("second_half_sessions", [])
    click.echo(f"✅ Regenerated {len(second_half_sessions)} second half variants")

    print_separator()
    click.echo("⚖️  Re-reviewing Articles with LLM-as-a-Judge")

    state = await review_all_articles_node(state)

    if state.get("error"):
        click.echo(f"❌ Error during review: {state['error']}", err=True)
        return state

    reviewed_sessions = state.get("reviewed_sessions", [])
    click.echo(f"✅ Re-reviewed {len(reviewed_sessions)} article variants")

    return state


async def review_loop(
    state: ParallelWorldState,
    auto_select: bool,
    max_iterations: int = 5,
) -> tuple[ParallelWorldState, CompletedArticle | None, bool, int]:
    """Phase 6-8: Review loop - select article, get approval, regenerate if rejected."""
    iteration = state.get("review_loop_iteration", 0)
    human_approved = False
    final_completed_article = None

    while not human_approved and iteration < max_iterations:
        iteration += 1

        state, completed_article = select_final_article(state, auto_select, iteration)

        if not completed_article:
            return state, None, False, iteration

        state, human_approved = approve_article(state, completed_article, auto_select)

        if human_approved:
            final_completed_article = completed_article
            break

        state = await regenerate_and_review(state, iteration)

        if state.get("error"):
            return state, None, False, iteration

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
    """Phase 9: Save final article and all variants to disk."""
    print_separator()
    click.echo("💾 Saving Final Article")

    json_path, md_path, variants_dir = save_article_files(
        final_completed_article,
        state["reviewed_sessions"],
        state["language"],
        output_directory,
    )

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
    """Run the complete parallel world article generation workflow."""
    state: ParallelWorldState = {
        "theme": theme,
        "language": language,
        "llm_provider": llm_provider.value,
        "model": model,
        "num_outline_variants": num_outline_variants,
        "num_second_half_variants": num_second_half_variants,
    }

    while True:
        current_phase = get_current_phase(state)
        click.echo(f"\n📍 Current phase: {current_phase} - {get_phase_name(current_phase)}")

        if current_phase < 1:
            state = await generate_outlines(state)
            if state.get("error"):
                return None

        if current_phase < 2:
            state = await select_outline(state, auto_select)
            if state.get("error"):
                return None

        if current_phase < 3:
            state = await generate_first_half(state)
            if state.get("error"):
                return None

            available_phases = get_available_rollback_phases(state)
            rollback_phase = get_rollback_choice(available_phases, auto_select)
            if rollback_phase is not None:
                state = forget_phases_after(state, rollback_phase)
                continue

        if current_phase < 4:
            state = await generate_second_halves(state)
            if state.get("error"):
                return None

        if current_phase < 5:
            state = await review_articles(state)
            if state.get("error"):
                return None

        if current_phase < 7 or not state.get("human_approved"):
            state, final_completed_article, human_approved, iteration = await review_loop(
                state, auto_select, max_iterations=5
            )

            if not final_completed_article:
                return None

            available_phases = get_available_rollback_phases(state)
            rollback_phase = get_rollback_choice(available_phases, auto_select)
            if rollback_phase is not None:
                state = forget_phases_after(state, rollback_phase)
                continue

            if human_approved:
                break
        else:
            reviewed_sessions = state.get("reviewed_sessions", [])
            final_session_id = state.get("final_selected_session_id")

            final_session = next(
                (s for s in reviewed_sessions if s.session_id == final_session_id),
                reviewed_sessions[0] if reviewed_sessions else None,
            )

            if final_session:
                final_completed_article = final_session.to_completed_article(state["language"])
                iteration = state.get("review_loop_iteration", 0)
                break
            else:
                click.echo("❌ Could not find final article in state", err=True)
                return None

    save_article(state, final_completed_article, output_directory, iteration)

    return final_completed_article
