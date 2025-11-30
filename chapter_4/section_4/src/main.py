import asyncio
import json
import os
from functools import wraps
from uuid import uuid4

import click

from src.client.llm_client import OpenAIModel
from src.logger import make_logger
from src.model.llm_pipeline_model import ContentType, LearnerProfile
from src.service.llm_pipeline_service import run_personalized_learning

logger = make_logger(__name__)


def async_cmd(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.command()
@click.option(
    "--model",
    "-m",
    type=click.Choice(OpenAIModel.list_str()),
    required=False,
    default=OpenAIModel.GPT_4O,
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
    # Load or create learner profile
    if profile_file:
        logger.info(f"Loading learner profile from: {profile_file}")
        with open(profile_file, "r", encoding="utf-8") as f:
            profile_data = json.load(f)

        # Parse content types if present
        preferred_types = []
        if "preferred_content_types" in profile_data:
            for ct in profile_data["preferred_content_types"]:
                preferred_types.append(ContentType(ct))

        learner_profile = LearnerProfile(
            learner_id=profile_data.get("learner_id", f"learner_{uuid4().hex[:8]}"),
            learning_goal=profile_data["learning_goal"],
            current_knowledge=profile_data.get("current_knowledge", []),
            available_hours_per_week=profile_data.get("available_hours_per_week", 10),
            preferred_content_types=preferred_types,
            target_duration_weeks=profile_data.get("target_duration_weeks", 12),
        )
    elif goal:
        logger.info("Creating learner profile from command-line options")
        knowledge_list = [k.strip() for k in current_knowledge.split(",") if k.strip()]

        learner_profile = LearnerProfile(
            learner_id=f"learner_{uuid4().hex[:8]}",
            learning_goal=goal,
            current_knowledge=knowledge_list,
            available_hours_per_week=hours_per_week,
            preferred_content_types=[],
            target_duration_weeks=duration_weeks,
        )
    else:
        raise click.UsageError("Either --profile-file or --goal must be provided.")

    logger.info(f"""Personalized Learning Platform
Model: {model}
Learning Goal: {learner_profile.learning_goal}
Hours/Week: {learner_profile.available_hours_per_week}
Duration: {learner_profile.target_duration_weeks} weeks
Output directory: {output_directory}
""")

    os.makedirs(output_directory, exist_ok=True)

    # Run the hierarchical learning platform
    plan = await run_personalized_learning(
        learner_profile=learner_profile,
        model=model,
    )

    if plan is None:
        raise ValueError("Learning platform failed. Check logs for details.")

    # Save the plan
    base_name = f"learning_plan_{uuid4().hex}"
    md_file_path = os.path.join(output_directory, f"{base_name}.md")

    with open(md_file_path, "w", encoding="utf-8") as f:
        f.write(plan.to_markdown())

    logger.info(f"Plan saved: {md_file_path}")

    # Print summary to console
    click.echo("\n" + "=" * 60)
    click.echo("PERSONALIZED LEARNING PLAN CREATED")
    click.echo("=" * 60)
    click.echo(f"\nLearning Domain: {plan.strategy.learning_domain}")
    click.echo(f"Current Level: {plan.strategy.roadmap.current_level.value}")
    click.echo(f"Target Level: {plan.strategy.roadmap.target_level.value}")
    click.echo(f"Duration: {plan.strategy.roadmap.total_duration_weeks} weeks")
    click.echo(f"Modules: {len(plan.strategy.roadmap.modules)}")
    click.echo(f"First Week Sessions: {len(plan.first_week_sessions)}")
    click.echo(f"\nPlan saved to: {md_file_path}")
    click.echo("\n" + "=" * 60)


if __name__ == "__main__":
    main()
