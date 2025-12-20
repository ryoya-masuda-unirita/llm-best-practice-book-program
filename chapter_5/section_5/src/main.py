"""
CLI entry point for the Personalized Learning Platform with Learning Capabilities.

This module provides a command-line interface for generating personalized
learning plans using a hierarchical AI agent architecture. It supports
experience-based learning through feedback loops.

The system can:
1. Generate personalized learning plans based on learner profiles
2. Load and save experience stores for continuous improvement
3. Run learning cycles to extract patterns from past experiences
4. Inject learned patterns into agent prompts for better output quality
"""

import asyncio
import json
import os
from functools import wraps
from pathlib import Path
from uuid import uuid4

import click
from src.client.llm_client import OpenAIModel
from src.logger import make_logger
from src.model.llm_pipeline_model import (
    ContentType,
    ExperienceStore,
    LearnerProfile,
)
from src.service.llm_pipeline_service import (
    create_new_experience_store,
    run_personalized_learning,
)

logger = make_logger(__name__)


# =============================================================================
# Experience Store Loading/Saving
# =============================================================================


def _load_experience_store(file_path: str) -> ExperienceStore | None:
    """Load an experience store from a JSON file."""
    if not file_path or not os.path.exists(file_path):
        return None

    logger.info(f"Loading experience store from: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    store = ExperienceStore.from_dict(data)
    logger.info(f"Loaded {len(store.experiences)} experiences, {len(store.learned_patterns)} patterns")
    return store


def _save_experience_store(store: ExperienceStore, file_path: str) -> None:
    """Save an experience store to a JSON file."""
    logger.info(f"Saving experience store to: {file_path}")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(store.to_dict(), f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {len(store.experiences)} experiences, {len(store.learned_patterns)} patterns")


# =============================================================================
# Decorators
# =============================================================================


def async_cmd(func):
    """Decorator to run async click commands."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


# =============================================================================
# Profile Loading Helpers
# =============================================================================


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


# =============================================================================
# CLI Command
# =============================================================================


@click.command()
@click.option(
    "--model",
    "-m",
    type=click.Choice(OpenAIModel.list_str()),
    required=False,
    default=OpenAIModel.GPT_5_MINI,
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
@click.option(
    "--experience-store",
    "-e",
    type=click.Path(),
    required=False,
    default=None,
    help="Path to a JSON file containing past experiences for learning.",
)
@click.option(
    "--save-experience-store",
    "-se",
    type=click.Path(),
    required=False,
    default=None,
    help="Path to save the updated experience store after the run.",
)
@click.option(
    "--skip-learning/--with-learning",
    default=False,
    help="Skip the learning cycle even if experiences are available.",
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
    experience_store: str | None,
    save_experience_store: str | None,
    skip_learning: bool,
):
    """
    Personalized Learning Platform - A Learning AI Agent System

    This system creates personalized learning plans using a hierarchical
    multi-agent architecture with learning capabilities. It can learn from
    past experiences and improve its output quality over time.

    \b
    Architecture:
    1. Learning Agent: Analyzes past experiences to extract patterns
    2. Strategy Layer: Creates learning roadmap and sets objectives
    3. Tactics Layer: Designs weekly/daily curriculum
    4. Execution Layer: Generates content and quizzes
    5. Progress Monitoring: Tracks learner progress

    \b
    Learning Features:
    - Load past experiences from JSON file
    - Run learning cycles to extract patterns
    - Inject learned patterns into agent prompts
    - Save updated experience store for future runs

    Examples:

    \b
        # Basic usage with command-line options
        python -m src.main -g "3ヶ月でPythonプログラミングを習得したい" -h 10 -d 12

        # Using a profile file
        python -m src.main -p example/learner_profile.json

        # With experience-based learning
        python -m src.main -p example/learner_profile.json -e example/experience_store.json

        # Save experiences for future learning
        python -m src.main -p example/learner_profile.json -se outputs/experience_store.json
    """
    # Load or create learner profile
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

    # Load or create experience store
    exp_store = None
    if experience_store:
        exp_store = _load_experience_store(experience_store)
    if exp_store is None and save_experience_store:
        # Create a new experience store if we want to save but don't have one
        exp_store = create_new_experience_store()
        logger.info(f"Created new experience store: {exp_store.store_id}")

    # Run the hierarchical learning platform with learning capabilities
    plan, updated_exp_store = await run_personalized_learning(
        learner_profile=learner_profile,
        model=model,
        experience_store=exp_store,
        run_learning_before=not skip_learning,
    )

    if plan is None:
        raise ValueError("Learning platform failed. Check logs for details.")

    # Save the plan
    output_path = Path(output_directory) / f"learning_plan_{uuid4().hex}.md"
    output_path.write_text(plan.to_markdown(), encoding="utf-8")
    logger.info(f"Plan saved: {output_path}")

    # Save the updated experience store if requested
    if save_experience_store and updated_exp_store:
        _save_experience_store(updated_exp_store, save_experience_store)
        logger.info(f"Experience store saved: {save_experience_store}")


if __name__ == "__main__":
    main()
