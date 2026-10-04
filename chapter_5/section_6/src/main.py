"""
CLI entry point for the Learning AI Agent - Training Plan Generator.

This module provides a command-line interface for:
1. Generating personalized 1-week training plans
2. Managing user memory (profile, history, feedback)
3. Submitting feedback on completed training plans
4. Listing existing users and their training history

The system learns from user feedback to continuously improve
the quality and personalization of generated training plans.
"""

import asyncio
import json
import os
from datetime import datetime
from functools import wraps
from pathlib import Path
from uuid import uuid4

import click
from src.client.llm_client import OpenAIModel
from src.logger import make_logger
from src.model.model import (
    ContentType,
    DifficultyRating,
    FeedbackRating,
    SkillLevel,
    TaskCompletion,
    TrainingFeedback,
    UserProfile,
)
from src.service import (
    add_feedback_to_memory,
    create_user_profile,
    get_training_plan_markdown,
    list_user_memories,
    load_memory,
    load_memory_from_file,
    run_training_plan_generation,
)

logger = make_logger(__name__)

OUTPUT_DIR = Path("outputs")


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


def _load_profile_from_file(profile_file: str) -> UserProfile:
    """Load user profile from a JSON file."""
    logger.info(f"Loading profile from: {profile_file}")
    with open(profile_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    content_types = []
    for ct in data.get("preferred_content_types", []):
        try:
            content_types.append(ContentType(ct))
        except ValueError:
            pass

    return UserProfile(
        user_id=data.get("user_id", f"user_{uuid4().hex[:8]}"),
        learning_goal=data["learning_goal"],
        current_knowledge=data.get("current_knowledge", []),
        skill_level=SkillLevel(data.get("skill_level", "beginner")),
        available_hours_per_week=data.get("available_hours_per_week", 10),
        preferred_content_types=content_types,
        learning_pace=data.get("learning_pace", "moderate"),
    )


# =============================================================================
# CLI Commands
# =============================================================================


@click.group()
def cli():
    """
    Learning AI Agent - Training Plan Generator

    A learning AI agent that generates personalized 1-week training plans
    and improves based on user feedback.

    \b
    Commands:
      generate  Generate a new training plan
      feedback  Submit feedback on a training plan
      list      List users and their training history
      show      Show details of a user's memory

    \b
    Examples:
      # Generate a training plan for a new user
      python -m src.main generate -g "Learn Python programming" -h 10

      # Generate a plan using a profile file
      python -m src.main generate -p profile.json

      # Generate a plan for an existing user (uses memory)
      python -m src.main generate -u user_abc123

      # Submit feedback on a training plan
      python -m src.main feedback -u user_abc123 -f feedback.json

      # List all users
      python -m src.main list
    """
    pass


@cli.command()
@click.option(
    "--model",
    "-m",
    type=click.Choice(OpenAIModel.list_str()),
    default=OpenAIModel.GPT_5_4,
    help="OpenAI model to use.",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default="outputs",
    help="Directory to save output files.",
)
@click.option(
    "--profile-file",
    "-p",
    type=click.Path(exists=True),
    default=None,
    help="Path to a JSON file containing user profile.",
)
@click.option(
    "--user-id",
    "-u",
    type=str,
    default=None,
    help="User ID to load existing memory.",
)
@click.option(
    "--goal",
    "-g",
    type=str,
    default=None,
    help="Learning goal (e.g., 'Learn Python programming').",
)
@click.option(
    "--hours-per-week",
    "-h",
    type=int,
    default=10,
    help="Available study hours per week.",
)
@click.option(
    "--skill-level",
    "-s",
    type=click.Choice(["beginner", "elementary", "intermediate", "upper_intermediate", "advanced"]),
    default="beginner",
    help="Current skill level.",
)
@click.option(
    "--current-knowledge",
    "-k",
    type=str,
    default="",
    help="Current knowledge/skills (comma-separated).",
)
@click.option(
    "--learning-pace",
    "-lp",
    type=click.Choice(["slow", "moderate", "fast"]),
    default="moderate",
    help="Preferred learning pace.",
)
@click.option(
    "--skip-analysis/--with-analysis",
    default=False,
    help="Skip pattern analysis even if feedback exists.",
)
@async_cmd
async def generate(
    model: str,
    output_dir: str,
    profile_file: str | None,
    user_id: str | None,
    goal: str | None,
    hours_per_week: int,
    skill_level: str,
    current_knowledge: str,
    learning_pace: str,
    skip_analysis: bool,
):
    """
    Generate a personalized 1-week training plan.

    You can either:
    1. Provide a profile file with user details
    2. Provide a user-id to load existing memory
    3. Provide learning goal and options to create a new user

    \b
    Examples:
      # New user with command-line options
      python -m src.main generate -g "Learn Python" -h 10 -s beginner

      # Load from profile file
      python -m src.main generate -p example/profile.json

      # Existing user (loads memory automatically)
      python -m src.main generate -u user_abc123
    """
    profile: UserProfile | None = None
    effective_user_id: str | None = user_id

    if profile_file:
        profile = _load_profile_from_file(profile_file)
        if effective_user_id is None:
            effective_user_id = profile.user_id

    if user_id:
        memory = load_memory(user_id)
        if memory is not None:
            if profile is None:
                profile = memory.profile
            else:
                profile = UserProfile(
                    user_id=user_id,
                    learning_goal=profile.learning_goal,
                    current_knowledge=profile.current_knowledge,
                    skill_level=profile.skill_level,
                    available_hours_per_week=profile.available_hours_per_week,
                    preferred_content_types=profile.preferred_content_types,
                    learning_pace=profile.learning_pace,
                )

    if goal:
        knowledge_list = [k.strip() for k in current_knowledge.split(",") if k.strip()]
        if profile is None:
            profile = create_user_profile(
                user_id=effective_user_id,
                learning_goal=goal,
                current_knowledge=knowledge_list,
                skill_level=skill_level,
                available_hours_per_week=hours_per_week,
                learning_pace=learning_pace,
            )
        else:
            profile = UserProfile(
                user_id=effective_user_id or profile.user_id,
                learning_goal=goal,
                current_knowledge=knowledge_list if current_knowledge else profile.current_knowledge,
                skill_level=SkillLevel(skill_level),
                available_hours_per_week=hours_per_week,
                preferred_content_types=profile.preferred_content_types,
                learning_pace=learning_pace,
            )

    if profile is None:
        raise click.UsageError("Either --profile-file, --user-id with existing memory, or --goal must be provided.")

    effective_user_id = profile.user_id if profile else user_id
    logger.info(f"Generating training plan for user: {effective_user_id}")
    logger.info(f"Model: {model}")

    os.makedirs(output_dir, exist_ok=True)

    plan, memory, memory_path = await run_training_plan_generation(
        user_id=profile.user_id,
        profile=profile,
        model=model,
        analyze_patterns=not skip_analysis,
    )

    markdown = get_training_plan_markdown(plan)
    output_path = Path(output_dir) / f"training_plan_{plan.plan_id}.md"
    output_path.write_text(markdown, encoding="utf-8")

    logger.info("\n" + "=" * 60)
    logger.info("TRAINING PLAN GENERATED SUCCESSFULLY")
    logger.info("=" * 60)
    logger.info(f"Plan ID: {plan.plan_id}")
    logger.info(f"User ID: {plan.user_id}")
    logger.info(f"Week: {plan.week_number}")
    logger.info(f"Goal: {plan.goal_for_week}")
    logger.info(f"Daily plans: {len(plan.daily_plans)}")
    logger.info(f"Plan saved: {output_path}")
    logger.info(f"Memory saved: {memory_path}")
    logger.info("=" * 60)


@cli.command()
@click.option(
    "--user-id",
    "-u",
    type=str,
    required=True,
    help="User ID to add feedback for.",
)
@click.option(
    "--plan-id",
    "-pid",
    type=str,
    default=None,
    help="Plan ID to add feedback for (uses latest if not specified).",
)
@click.option(
    "--rating",
    "-r",
    type=click.Choice(["excellent", "good", "neutral", "poor", "very_poor"]),
    required=True,
    help="Overall rating.",
)
@click.option(
    "--difficulty",
    "-d",
    type=click.Choice(["too_easy", "easy", "just_right", "challenging", "too_hard"]),
    required=True,
    help="Difficulty rating.",
)
@click.option(
    "--improvement-suggestions",
    "-is",
    type=str,
    default="",
    help="Comma-separated improvement suggestions.",
)
@click.option(
    "--free-text",
    "-ft",
    type=str,
    default="",
    help="Free text feedback.",
)
def feedback(
    user_id: str,
    plan_id: str | None,
    rating: str,
    difficulty: str,
    improvement_suggestions: str,
    free_text: str,
):
    """
    Submit feedback on a completed training plan.

    Feedback is used by the learning agent to improve future
    training plan generation for this user.

    \b
    Examples:
      python -m src.main feedback -u user_abc123 -r good -d just_right
      python -m src.main feedback -u user_abc123 -r excellent -d challenging -ft "Great content!"
    """
    memory = load_memory(user_id)
    if memory is None:
        raise click.UsageError(f"No memory found for user: {user_id}")

    if plan_id is None:
        latest = memory.get_latest_plan()
        if latest is None:
            raise click.UsageError("No training plans found for this user.")
        plan_id = latest.plan_id
        logger.info(f"Using latest plan: {plan_id}")

    plan = next((r.plan for r in memory.training_history if r.plan.plan_id == plan_id), None)
    if plan is None:
        raise click.UsageError(f"Plan not found: {plan_id}")

    task_completions = []
    for day_plan in plan.daily_plans:
        for task in day_plan.tasks:
            task_completions.append(
                TaskCompletion(
                    task_id=task.task_id,
                    completed=True,
                    actual_minutes=0,
                    notes="",
                )
            )

    fb = TrainingFeedback(
        feedback_id=f"fb_{uuid4().hex[:8]}",
        plan_id=plan_id,
        user_id=user_id,
        submitted_at=datetime.now().isoformat(),
        task_completions=task_completions,
        overall_rating=FeedbackRating(rating),
        difficulty_rating=DifficultyRating(difficulty),
        helpful_aspects=[],
        improvement_suggestions=[s.strip() for s in improvement_suggestions.split(",") if s.strip()],
        topics_mastered=[],
        topics_needing_review=[],
        free_text_feedback=free_text,
    )

    _, memory_path = add_feedback_to_memory(fb, user_id=user_id)

    logger.info("\n" + "=" * 60)
    logger.info("FEEDBACK SUBMITTED SUCCESSFULLY")
    logger.info("=" * 60)
    logger.info(f"Feedback ID: {fb.feedback_id}")
    logger.info(f"Plan ID: {fb.plan_id}")
    logger.info(f"Rating: {fb.overall_rating.value}")
    logger.info(f"Difficulty: {fb.difficulty_rating.value}")
    logger.info(f"Memory saved: {memory_path}")
    logger.info("=" * 60)


@cli.command("list")
def list_users():
    """
    List all users and their training history.

    Shows user IDs and the number of training plans
    in their memory.
    """
    users = list_user_memories()

    if not users:
        logger.info("No users found in memory.")
        return

    logger.info("\n" + "=" * 60)
    logger.info("USERS")
    logger.info("=" * 60)

    for user_id, files in users.items():
        latest = files[0] if files else None
        memory = None
        if latest:
            try:
                memory = load_memory_from_file(latest)
            except Exception:
                pass

        plans = len(memory.training_history) if memory else 0
        patterns = len(memory.learned_patterns) if memory else 0
        weeks = memory.progress.total_weeks_completed if memory else 0

        logger.info(f"\nUser: {user_id}")
        logger.info(f"  Training plans: {plans}")
        logger.info(f"  Learned patterns: {patterns}")
        logger.info(f"  Weeks completed: {weeks}")
        logger.info(f"  Memory files: {len(files)}")

    logger.info("=" * 60)


@cli.command()
@click.option(
    "--user-id",
    "-u",
    type=str,
    required=True,
    help="User ID to show details for.",
)
@click.option(
    "--show-plans/--hide-plans",
    default=False,
    help="Show training plan details.",
)
@click.option(
    "--show-patterns/--hide-patterns",
    default=False,
    help="Show learned patterns.",
)
def show(user_id: str, show_plans: bool, show_patterns: bool):
    """
    Show details of a user's memory.

    Displays profile, progress, and optionally
    training plans and learned patterns.
    """
    memory = load_memory(user_id)
    if memory is None:
        raise click.UsageError(f"No memory found for user: {user_id}")

    logger.info("\n" + "=" * 60)
    logger.info(f"USER: {user_id}")
    logger.info("=" * 60)

    logger.info("\n--- Profile ---")
    logger.info(f"Learning Goal: {memory.profile.learning_goal}")
    logger.info(f"Skill Level: {memory.profile.skill_level.value}")
    logger.info(f"Hours/Week: {memory.profile.available_hours_per_week}")
    logger.info(f"Learning Pace: {memory.profile.learning_pace}")
    if memory.profile.current_knowledge:
        logger.info(f"Current Knowledge: {', '.join(memory.profile.current_knowledge)}")

    logger.info("\n--- Progress ---")
    logger.info(f"Weeks Completed: {memory.progress.total_weeks_completed}")
    logger.info(f"Tasks Completed: {memory.progress.total_tasks_completed}")
    logger.info(f"Hours Spent: {memory.progress.total_hours_spent}")
    logger.info(f"Completion Rate: {memory.progress.average_completion_rate * 100:.1f}%")
    logger.info(f"Streak: {memory.progress.streak_weeks} weeks")
    if memory.progress.topics_mastered:
        logger.info(f"Topics Mastered: {', '.join(memory.progress.topics_mastered)}")

    if show_plans and memory.training_history:
        logger.info("\n--- Training Plans ---")
        for i, record in enumerate(memory.training_history, 1):
            plan = record.plan
            has_feedback = "Yes" if record.feedback else "No"
            logger.info(f"\n{i}. {plan.plan_id}")
            logger.info(f"   Week: {plan.week_number}")
            logger.info(f"   Goal: {plan.goal_for_week}")
            logger.info(f"   Created: {plan.created_at}")
            logger.info(f"   Feedback: {has_feedback}")

    if show_patterns and memory.learned_patterns:
        logger.info("\n--- Learned Patterns ---")
        for i, pattern in enumerate(memory.learned_patterns, 1):
            logger.info(f"\n{i}. {pattern.pattern_type}: {pattern.description}")
            logger.info(f"   Confidence: {pattern.confidence_score:.2f}")
            if pattern.recommendations:
                logger.info(f"   Recommendations: {', '.join(pattern.recommendations[:3])}")

    logger.info("\n" + "=" * 60)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
