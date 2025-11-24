import os
from typing import Literal
from uuid import uuid4

import click
from src.logger import make_logger
from src.model.parallel_world_model import (
    ArticleReview,
    CompletedArticle,
    ParallelSession,
)

logger = make_logger(__name__)


# =============================================================================
# Display Utilities
# =============================================================================


def print_separator() -> None:
    """Print a visual separator for terminal output."""
    click.echo("\n" + "=" * 80 + "\n")


def print_article_preview(article_content: str) -> None:
    """
    Print a preview of article content.

    Args:
        article_content: Full article text
    """
    lines = article_content.split("\n")
    click.echo("\n".join(lines))


def display_outlines(outline_sessions: list[ParallelSession]) -> None:
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


def display_reviews(reviewed_sessions: list[ParallelSession]) -> None:
    """
    Display all reviewed articles with their grades to the user.

    Args:
        reviewed_sessions: List of sessions with reviews
    """
    for i, session in enumerate(reviewed_sessions, 1):
        review = session.review
        if review:
            click.echo(f"\n[Article Variant {i}] - Grade: {review.grade}/{ArticleReview.best_grade()}")
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
                print_article_preview(session.second_half)


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
            choice = click.prompt(f"\nSelect an outline (1-{len(outline_sessions)})", type=int)
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
            choice = click.prompt(f"\nSelect final article (1-{len(reviewed_sessions)})", type=int)
            if 1 <= choice <= len(reviewed_sessions):
                return choice - 1
            else:
                click.echo(f"Please enter a number between 1 and {len(reviewed_sessions)}")
        except (ValueError, click.Abort):
            click.echo("Invalid input. Please enter a number.")


def get_human_approval(completed_article: CompletedArticle, auto_select: bool) -> bool:
    """
    Get user's approval (yes/no) for the selected article.

    Args:
        completed_article: The selected complete article
        auto_select: Whether to automatically approve without user interaction

    Returns:
        True if approved, False if rejected (needs revision)
    """
    if auto_select:
        # Auto-approve if grade is 4 or higher
        if completed_article.review and completed_article.review.grade >= 4:
            click.echo("\n🤖 Auto-approved: Article grade is 4 or higher")
            return True
        else:
            click.echo("\n🤖 Auto-rejected: Article grade is below 4")
            return False

    # Show article preview
    click.echo("\n📝 Selected Article Preview:")
    click.echo(f"Title: {completed_article.outline.title}")
    if completed_article.review:
        click.echo(f"Grade: {completed_article.review.grade}/{ArticleReview.best_grade()}")
        click.echo(f"Review: {completed_article.review.reasoning}")

    while True:
        try:
            response = click.prompt("\n✅ Do you approve this article? (yes/no)", type=str).lower().strip()

            if response in ["yes", "y"]:
                return True
            elif response in ["no", "n"]:
                return False
            else:
                click.echo("Please enter 'yes' or 'no'")
        except click.Abort:
            click.echo("\nOperation cancelled. Treating as rejection.")
            return False


def get_rollback_choice(available_phases: list[tuple[int, str]], auto_select: bool) -> int | None:
    """
    Ask user if they want to rollback to a previous phase.

    Args:
        available_phases: List of (phase_number, phase_name) tuples
        auto_select: Whether to auto-select (skip rollback in auto mode)

    Returns:
        Phase number to rollback to, or None to continue without rollback
    """
    if auto_select:
        # In auto mode, never rollback
        return None

    if not available_phases:
        return None

    click.echo("\n🔄 Rollback Option Available")
    click.echo("You can go back to a previous phase if you want to try different choices.")
    click.echo("This will 'forget' all subsequent phases and regenerate them.\n")
    click.echo("Available phases:")
    click.echo("  0. Continue without rollback (keep current progress)")

    for i, (phase_num, phase_name) in enumerate(available_phases, 1):
        click.echo(f"  {i}. Rollback to Phase {phase_num}: {phase_name}")

    while True:
        try:
            choice = click.prompt(
                f"\nSelect phase to rollback to (0-{len(available_phases)}, 0=continue)",
                type=int,
                default=0,
            )

            if choice == 0:
                return None
            elif 1 <= choice <= len(available_phases):
                phase_num, _ = available_phases[choice - 1]
                return phase_num
            else:
                click.echo(f"Please enter a number between 0 and {len(available_phases)}")
        except (ValueError, click.Abort):
            click.echo("Invalid input. Continuing without rollback.")
            return None


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
