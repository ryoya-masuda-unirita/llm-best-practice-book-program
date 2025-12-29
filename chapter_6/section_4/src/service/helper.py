import os
from typing import Literal
from uuid import uuid4

import click
from src.logger import make_logger
from src.model.model import (
    ArticleReview,
    CompletedArticle,
)

logger = make_logger(__name__)


def print_separator() -> None:
    click.echo("\n" + "=" * 80 + "\n")


def print_article_preview(article_content: str) -> None:
    lines = article_content.split("\n")
    click.echo("\n".join(lines))


def get_human_approval(completed_article: CompletedArticle, auto_select: bool) -> bool:
    if auto_select:
        if completed_article.review and completed_article.review.grade >= 4:
            click.echo("\n🤖 Auto-approved: Article grade is 4 or higher")
            return True
        else:
            click.echo("\n🤖 Auto-rejected: Article grade is below 4")
            return False

    click.echo("\n📝 Article Preview:")
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
    if auto_select:
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


def save_article_files(
    completed_article: CompletedArticle,
    language: Literal["en", "ja"],
    output_directory: str,
) -> tuple[str, str]:
    base_name = f"article_{uuid4().hex}"
    output_dir = os.path.join(output_directory, base_name)
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, f"{base_name}.json")
    md_path = os.path.join(output_dir, f"{base_name}.md")

    completed_article.save_as_json(json_path)
    completed_article.save_as_markdown(md_path)

    return json_path, md_path
