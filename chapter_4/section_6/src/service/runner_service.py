"""
Runner Service for Parallel World Article Generation.

This module orchestrates the AI agent pipeline with human-in-the-loop interactions.
It handles:
- User interface and interactions (display, input)
- Pipeline orchestration and phase management
- File output and saving

For the core AI agent pipeline logic, see parallel_world_service.py
"""

import os
from typing import Literal
from uuid import uuid4

import click

from src.client.llm_client import LLMProvider
from src.logger import make_logger
from src.model.parallel_world_model import CompletedArticle, ParallelSession, ParallelWorldState
from src.service.parallel_world_service import (
    generate_first_half_node,
    generate_multiple_outlines_node,
    generate_multiple_second_halves_node,
    review_all_articles_node,
)

logger = make_logger(__name__)


# =============================================================================
# Display Utilities
# =============================================================================


def print_separator():
    """Print a visual separator for terminal output."""
    click.echo("\n" + "=" * 80 + "\n")


def print_article_preview(article_content: str, max_lines: int = 10):
    """
    Print a preview of article content.

    Args:
        article_content: Full article text
        max_lines: Maximum number of lines to display
    """
    lines = article_content.split("\n")
    preview_lines = lines[:max_lines]
    click.echo("\n".join(preview_lines))
    if len(lines) > max_lines:
        click.echo(f"\n... ({len(lines) - max_lines} more lines)")


def display_outlines(outline_sessions: list[ParallelSession]):
    """
    Display all outline variants to the user.

    Args:
        outline_sessions: List of sessions containing outlines
    """
    for i, session in enumerate(outline_sessions, 1):
        outline = session.outline
        if outline:
            click.echo(f"\n[Variant {i}]")
            click.echo(f"Reason: {outline.reason}")
            click.echo(f"Title: {outline.title}")
            click.echo(f"Summary: {outline.summary}")
            click.echo("Structure:")
            for j, section in enumerate(outline.structure, 1):
                click.echo(f"  {j}. {section}")


def display_reviews(reviewed_sessions: list[ParallelSession]):
    """
    Display all reviewed articles with their grades to the user.

    Args:
        reviewed_sessions: List of sessions with reviews
    """
    for i, session in enumerate(reviewed_sessions, 1):
        review = session.review
        if review:
            click.echo(f"\n[Article Variant {i}] - Grade: {review.grade}/5")
            click.echo(f"Reasoning: {review.reasoning}")
            click.echo("Strengths:")
            for strength in review.strengths:
                click.echo(f"  ✓ {strength}")
            if review.weaknesses:
                click.echo("Weaknesses:")
                for weakness in review.weaknesses:
                    click.echo(f"  ✗ {weakness}")

            # Show preview of second half
            if session.second_half:
                click.echo("\nSecond Half Preview:")
                print_article_preview(session.second_half, max_lines=5)


# =============================================================================
# User Input Utilities
# =============================================================================


def get_outline_selection(outline_sessions: list[ParallelSession], auto_select: bool) -> int:
    """
    Get user's outline selection or auto-select the first one.

    Args:
        outline_sessions: Available outline sessions
        auto_select: Whether to automatically select without user input

    Returns:
        Index of selected outline (0-based)
    """
    if auto_select:
        selected_idx = 0
        click.echo("\n🤖 Auto-selected: Variant 1")
        return selected_idx

    while True:
        try:
            choice = click.prompt(
                f"\nSelect an outline (1-{len(outline_sessions)})",
                type=int,
            )
            if 1 <= choice <= len(outline_sessions):
                return choice - 1
            else:
                click.echo(f"Please enter a number between 1 and {len(outline_sessions)}")
        except (ValueError, click.Abort):
            click.echo("Invalid input. Please enter a number.")


def get_final_article_selection(reviewed_sessions: list[ParallelSession], auto_select: bool) -> int:
    """
    Get user's final article selection or auto-select the highest graded one.

    Args:
        reviewed_sessions: Available reviewed sessions
        auto_select: Whether to automatically select without user input

    Returns:
        Index of selected article (0-based)
    """
    if auto_select:
        # Select highest graded article
        best_idx = max(
            range(len(reviewed_sessions)),
            key=lambda i: reviewed_sessions[i].review.grade if reviewed_sessions[i].review else 0,
        )
        click.echo(f"\n🤖 Auto-selected: Variant {best_idx + 1} (highest grade)")
        return best_idx

    while True:
        try:
            choice = click.prompt(
                f"\nSelect final article (1-{len(reviewed_sessions)})",
                type=int,
            )
            if 1 <= choice <= len(reviewed_sessions):
                return choice - 1
            else:
                click.echo(f"Please enter a number between 1 and {len(reviewed_sessions)}")
        except (ValueError, click.Abort):
            click.echo("Invalid input. Please enter a number.")


# =============================================================================
# File Output Utilities
# =============================================================================


def save_article_files(
    completed_article: CompletedArticle,
    reviewed_sessions: list[ParallelSession],
    language: Literal["en", "ja"],
    output_directory: str,
) -> tuple[str, str, str]:
    """
    Save article files to disk.

    Args:
        completed_article: The selected complete article
        reviewed_sessions: All reviewed sessions (for variants)
        language: Article language
        output_directory: Directory to save files

    Returns:
        Tuple of (json_path, md_path, variants_dir)
    """
    base_name = f"parallel_world_article_{uuid4().hex}"
    output_dir = os.path.join(output_directory, base_name)
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, f"{base_name}.json")
    md_path = os.path.join(output_dir, f"{base_name}.md")

    # Save selected article
    completed_article.save_as_json(json_path)
    completed_article.save_as_markdown(md_path)

    # Save all variants for comparison
    variants_dir = os.path.join(output_dir, "all_variants")
    os.makedirs(variants_dir, exist_ok=True)

    for i, session in enumerate(reviewed_sessions, 1):
        variant_article = session.to_completed_article(language)
        if variant_article:
            variant_md_path = os.path.join(
                variants_dir,
                f"variant_{i}_grade_{session.review.grade if session.review else 0}.md",
            )
            variant_article.save_as_markdown(variant_md_path)

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
    Run the complete parallel world article generation workflow with human-in-the-loop.

    This orchestrates the entire pipeline with user interactions at decision points.

    Workflow:
    1. Generate multiple outlines in parallel (AI Agent)
    2. User selects preferred outline (Human-in-the-Loop)
    3. Generate first half based on selection (AI Agent)
    4. Generate multiple second half variants in parallel (AI Agent)
    5. Review all complete articles with LLM-as-a-Judge (AI Agent)
    6. User selects final article (Human-in-the-Loop)
    7. Save selected article and all variants

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
        "llm_provider": llm_provider.value,
        "model": model,
        "error": None,
        "num_outline_variants": num_outline_variants,
        "num_second_half_variants": num_second_half_variants,
    }

    # =========================================================================
    # Phase 1: Generate Multiple Outlines (Parallel World Branching #1)
    # =========================================================================

    print_separator()
    click.echo("🌍 PHASE 1: Generating Multiple Outline Variants (Parallel World Branching)")
    click.echo(f"Creating {num_outline_variants} different article outlines in parallel...")

    state = await generate_multiple_outlines_node(state)

    if state.get("error"):
        click.echo(f"❌ Error: {state['error']}", err=True)
        return None

    outline_sessions = state["outline_sessions"]
    click.echo(f"✅ Generated {len(outline_sessions)} outline variants")

    # =========================================================================
    # Phase 2: Human Selects Outline (Human-in-the-Loop #1)
    # =========================================================================

    print_separator()
    click.echo("👤 PHASE 2: Human-in-the-Loop - Select Your Preferred Outline")

    display_outlines(outline_sessions)
    selected_idx = get_outline_selection(outline_sessions, auto_select)

    selected_outline_session = outline_sessions[selected_idx]
    state["selected_outline_session_id"] = selected_outline_session.session_id
    click.echo(f"✅ Selected: {selected_outline_session.outline.title}")  # type: ignore

    # =========================================================================
    # Phase 3: Generate First Half
    # =========================================================================

    print_separator()
    click.echo("📝 PHASE 3: Generating First Half of Article")

    state = await generate_first_half_node(state)

    if state.get("error"):
        click.echo(f"❌ Error: {state['error']}", err=True)
        return None

    first_half_session = state["first_half_session"]
    if first_half_session and first_half_session.first_half:
        click.echo(f"✅ Generated first half ({len(first_half_session.first_half)} characters)")
        click.echo("\nPreview:")
        print_article_preview(first_half_session.first_half)

    # =========================================================================
    # Phase 4: Generate Multiple Second Halves (Parallel World Branching #2)
    # =========================================================================

    print_separator()
    click.echo("🌍 PHASE 4: Generating Multiple Second Half Variants (Parallel World Branching)")
    click.echo(f"Creating {num_second_half_variants} different endings in parallel...")

    state = await generate_multiple_second_halves_node(state)

    if state.get("error"):
        click.echo(f"❌ Error: {state['error']}", err=True)
        return None

    second_half_sessions = state["second_half_sessions"]
    click.echo(f"✅ Generated {len(second_half_sessions)} second half variants")

    # =========================================================================
    # Phase 5: Review All Articles with LLM-as-a-Judge
    # =========================================================================

    print_separator()
    click.echo("⚖️  PHASE 5: Reviewing All Articles with LLM-as-a-Judge")

    state = await review_all_articles_node(state)

    if state.get("error"):
        click.echo(f"❌ Error: {state['error']}", err=True)
        return None

    reviewed_sessions = state["reviewed_sessions"]
    click.echo(f"✅ Reviewed {len(reviewed_sessions)} complete articles")

    # =========================================================================
    # Phase 6: Human Selects Final Article (Human-in-the-Loop #2)
    # =========================================================================

    print_separator()
    click.echo("👤 PHASE 6: Human-in-the-Loop - Select Your Preferred Article")

    display_reviews(reviewed_sessions)
    best_idx = get_final_article_selection(reviewed_sessions, auto_select)

    final_session = reviewed_sessions[best_idx]
    state["final_selected_session_id"] = final_session.session_id

    # =========================================================================
    # Phase 7: Save Final Article and All Variants
    # =========================================================================

    print_separator()
    click.echo("💾 Saving Final Article")

    completed_article = final_session.to_completed_article(language)

    if not completed_article:
        click.echo("❌ Failed to create completed article", err=True)
        return None

    # Save files
    json_path, md_path, variants_dir = save_article_files(
        completed_article,
        reviewed_sessions,
        language,
        output_directory,
    )

    # Display summary
    click.echo(
        f"""
✅ Article Generation Complete!

Selected Article Details:
  Title: {completed_article.outline.title}
  Grade: {completed_article.review.grade}/5
  Total Length: {len(completed_article.get_full_content())} characters

Files saved:
  📄 JSON: {json_path}
  📝 Markdown: {md_path}

Session Metadata:
  Session ID: {completed_article.session_id}
  Created: {completed_article.created_at}
  Outline variants generated: {len(outline_sessions)}
  Second half variants generated: {len(second_half_sessions)}
"""
    )

    click.echo(f"📁 All variants saved to: {variants_dir}")

    print_separator()
    click.echo("🎉 Parallel World Article Generation Complete!")

    return completed_article
