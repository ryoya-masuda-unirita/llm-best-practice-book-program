import os
from typing import Literal
from uuid import uuid4

import click

from src.logger import make_logger
from src.model.model import (
    ArticleReview,
    CompletedArticle,
    ParallelSession,
)

logger = make_logger(__name__)


def print_separator() -> None:
    """Print a visual separator for terminal output."""
    click.echo("\n" + "=" * 80 + "\n")


def print_article_preview(article_content: str) -> None:
    """Print a preview of article content."""
    lines = article_content.split("\n")
    click.echo("\n".join(lines))


def display_outlines(outline_sessions: list[ParallelSession]) -> None:
    """Display all outline variants to the user."""
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
    """Display all reviewed articles with their grades to the user."""
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

            if session.second_half:
                click.echo("\nSecond Half Preview:")
                print_article_preview(session.second_half)


def get_outline_selection(outline_sessions: list[ParallelSession], auto_select: bool) -> int:
    """Get user's outline selection or auto-select the first one."""
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
    """Get user's final article selection or auto-select the highest graded one."""
    if auto_select:
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
    """Get user's approval (yes/no) for the selected article."""
    if auto_select:
        if completed_article.review and completed_article.review.grade >= 4:
            click.echo("\n🤖 Auto-approved: Article grade is 4 or higher")
            return True
        else:
            click.echo("\n🤖 Auto-rejected: Article grade is below 4")
            return False

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


def save_article_files(
    completed_article: CompletedArticle,
    reviewed_sessions: list[ParallelSession],
    language: Literal["en", "ja"],
    output_directory: str,
) -> tuple[str, str, str]:
    """Save article files to disk."""
    base_name = f"parallel_world_article_{uuid4().hex}"
    output_dir = os.path.join(output_directory, base_name)
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, f"{base_name}.json")
    md_path = os.path.join(output_dir, f"{base_name}.md")

    completed_article.save_as_json(json_path)
    completed_article.save_as_markdown(md_path)

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
