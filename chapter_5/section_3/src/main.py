"""CLI entry point for the Personalized Learning Platform."""

import asyncio
import json
import os
from functools import wraps
from pathlib import Path
from uuid import uuid4

import click
from src.client.llm_client import OpenAIModel
from src.logger import make_logger
from src.model.model import ContentType, LearnerProfile
from src.service.service import run_personalized_learning

logger = make_logger(__name__)


def async_cmd(func):
    """Decorator to run async click commands."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


def _generate_learner_id() -> str:
    """Generate a unique learner ID."""
    return f"learner_{uuid4().hex[:8]}"


def _parse_content_types(content_types: list[str]) -> list[ContentType]:
    """Parse content type strings to ContentType enum values."""
    return [ContentType(ct) for ct in content_types]


def _load_profile_from_file(profile_file: str) -> LearnerProfile:
    """Load learner profile from a JSON file."""
    logger.info(f"Loading learner profile from: {profile_file}")
    with open(profile_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    preferred_types = _parse_content_types(data.get("preferred_content_types", []))

    return LearnerProfile(
        learner_id=data.get("learner_id", _generate_learner_id()),
        learning_goal=data["learning_goal"],
        current_knowledge=data.get("current_knowledge", []),
        available_hours_per_week=data.get("available_hours_per_week", 10),
        preferred_content_types=preferred_types,
        target_duration_weeks=data.get("target_duration_weeks", 12),
    )


def _create_profile_from_options(
    goal: str,
    hours_per_week: int,
    duration_weeks: int,
    current_knowledge: str,
) -> LearnerProfile:
    """Create learner profile from command-line options."""
    logger.info("Creating learner profile from command-line options")
    knowledge_list = [k.strip() for k in current_knowledge.split(",") if k.strip()]

    return LearnerProfile(
        learner_id=_generate_learner_id(),
        learning_goal=goal,
        current_knowledge=knowledge_list,
        available_hours_per_week=hours_per_week,
        preferred_content_types=[],
        target_duration_weeks=duration_weeks,
    )


def _log_startup_info(
    model: str,
    learner_profile: LearnerProfile,
    output_directory: str,
) -> None:
    """Log startup information."""
    logger.info(
        f"Personalized Learning Platform\n"
        f"Model: {model}\n"
        f"Learning Goal: {learner_profile.learning_goal}\n"
        f"Hours/Week: {learner_profile.available_hours_per_week}\n"
        f"Duration: {learner_profile.target_duration_weeks} weeks\n"
        f"Output directory: {output_directory}"
    )


@click.command()
@click.option(
    "--model",
    "-m",
    type=click.Choice(OpenAIModel.list_str()),
    required=False,
    default=OpenAIModel.GPT_5_4,
    help="The model to use for the request.",
)
@click.option(
    "--output-directory",
    "-od",
    type=click.Path(),
    required=False,
    default="outputs",
    help="The directory to save output files.",
)
@click.option(
    "--profile-file",
    "-p",
    type=click.Path(exists=True),
    required=False,
    default=None,
    help="Path to a JSON file containing the learner profile.",
)
@click.option(
    "--goal",
    "-g",
    type=str,
    required=False,
    default=None,
    help="Learning goal (e.g., '3ヶ月でデータ分析ができるようになりたい').",
)
@click.option(
    "--hours-per-week",
    "-h",
    type=int,
    required=False,
    default=10,
    help="Available study hours per week.",
)
@click.option(
    "--duration-weeks",
    "-d",
    type=int,
    required=False,
    default=12,
    help="Target duration in weeks.",
)
@click.option(
    "--current-knowledge",
    "-k",
    type=str,
    required=False,
    default="",
    help="Current knowledge/skills (comma-separated).",
)
@async_cmd
async def main(
    model: str,
    output_directory: str,
    profile_file: str | None,
    goal: str | None,
    hours_per_week: int,
    duration_weeks: int,
    current_knowledge: str,
):
    """
    Personalized Learning Platform - A Hierarchical AI Agent System

    This system creates personalized learning plans using a hierarchical
    multi-agent architecture with three layers:

    \b
    1. Strategy Layer: Creates learning roadmap and sets objectives
    2. Tactics Layer: Designs weekly/daily curriculum
    3. Execution Layer: Generates content and quizzes

    You can provide a learner profile via JSON file or command-line options.

    Examples:

    \b
        # Using command-line options
        python -m src.main -g "3ヶ月でPythonプログラミングを習得したい" -h 10 -d 12

        # Using a profile file
        python -m src.main -p example/learner_profile.json

        # With current knowledge
        python -m src.main -g "データ分析を学びたい" -k "Excel基礎,統計基礎"
    """
    if profile_file:
        learner_profile = _load_profile_from_file(profile_file)
    elif goal:
        learner_profile = _create_profile_from_options(
            goal=goal,
            hours_per_week=hours_per_week,
            duration_weeks=duration_weeks,
            current_knowledge=current_knowledge,
        )
    else:
        raise click.UsageError("Either --profile-file or --goal must be provided.")

    _log_startup_info(model, learner_profile, output_directory)

    os.makedirs(output_directory, exist_ok=True)

    plan = await run_personalized_learning(
        learner_profile=learner_profile,
        model=model,
    )

    if plan is None:
        raise ValueError("Learning platform failed. Check logs for details.")

    output_path = Path(output_directory) / f"learning_plan_{uuid4().hex}.md"
    output_path.write_text(plan.to_markdown(), encoding="utf-8")
    logger.info(f"Plan saved: {output_path}")


if __name__ == "__main__":
    main()
