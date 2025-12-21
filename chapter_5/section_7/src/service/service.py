"""
Learning AI Agent Service - Training Plan Generator.

This module implements a learning AI agent that:
1. Generates personalized 1-week training plans
2. Learns from past interactions to improve future recommendations
3. Injects learned patterns into prompts for better personalization

Architecture:
    User Profile -> Memory Load -> Pattern Analysis -> Plan Generation -> Memory Save
                         ^                                    |
                         |                                    v
                         +--------- Feedback Loop <-----------+
"""

import time
from datetime import datetime
from pathlib import Path
from typing import TypeVar
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from src.client.llm_client import OpenAIModel
from src.config import config as global_config
from src.logger import make_logger
from src.model.model import (
    ContentType,
    DailyPlan,
    DailyTask,
    LearnedPattern,
    LearnedPatternResponse,
    PatternAnalysisResponse,
    SkillLevel,
    TrainingPlan,
    TrainingPlanResponse,
    UserMemory,
    UserProfile,
    WeeklyAssessment,
)
from src.prompt.prompt import (
    format_feedback_for_analysis,
    format_learned_context,
    format_training_plan_markdown,
    make_pattern_analyzer_system_prompt,
    make_pattern_analyzer_user_prompt,
    make_training_plan_system_prompt,
    make_training_plan_user_prompt,
)
from src.service.memory_service import (
    create_new_memory,
    load_memory,
    save_memory,
)

T = TypeVar("T", bound=BaseModel)

logger = make_logger(__name__)

# =============================================================================
# Constants
# =============================================================================

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
MIN_FEEDBACK_FOR_LEARNING = 2


# =============================================================================
# LLM Utility Functions
# =============================================================================


def _create_chat_model(model: str = OpenAIModel.GPT_4O) -> ChatOpenAI:
    """Create a ChatOpenAI model instance."""
    return ChatOpenAI(model=model, openai_api_key=global_config.openai_api_key)


def _build_messages(system_prompt: str, user_prompt: str) -> list:
    """Build message list for LLM invocation."""
    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]


def invoke_with_structured_output(
    model: ChatOpenAI,
    messages: list,
    response_model: type[T],
    agent_name: str,
) -> T:
    """Invoke LLM with structured output and retry logic."""
    last_error = None
    structured_model = model.with_structured_output(response_model)

    for attempt in range(MAX_RETRIES):
        try:
            response = structured_model.invoke(messages)
            if response is not None:
                return response
            logger.warning(f"{agent_name}: Empty response on attempt {attempt + 1}")
        except Exception as e:
            last_error = e
            logger.warning(f"{agent_name}: Error on attempt {attempt + 1}: {e}")

        if attempt < MAX_RETRIES - 1:
            logger.info(f"{agent_name}: Retrying in {RETRY_DELAY_SECONDS} seconds...")
            time.sleep(RETRY_DELAY_SECONDS)

    raise ValueError(f"{agent_name} failed after {MAX_RETRIES} attempts: {last_error}")


# =============================================================================
# Training Plan Generation
# =============================================================================


def _safe_enum_parse(enum_class, value: str, default):
    """Safely parse an enum value with fallback to default."""
    try:
        return enum_class(value)
    except ValueError:
        return default


def _convert_response_to_training_plan(
    response: TrainingPlanResponse,
    user_id: str,
    week_number: int,
) -> TrainingPlan:
    """Convert LLM response to TrainingPlan model."""
    plan_id = f"plan_{user_id}_{week_number}_{uuid4().hex[:8]}"
    now = datetime.now().isoformat()

    daily_plans = []
    for dp in response.daily_plans:
        tasks = []
        for i, t in enumerate(dp.tasks):
            content_type = _safe_enum_parse(
                ContentType,
                t.content_type,
                ContentType.ARTICLE,
            )
            task = DailyTask(
                task_id=t.task_id or f"task_w{week_number}d{dp.day_number}_{i + 1:02d}",
                title=t.title,
                description=t.description,
                content_type=content_type,
                estimated_minutes=t.estimated_minutes,
                learning_objectives=t.learning_objectives,
                resources=t.resources,
            )
            tasks.append(task)

        total_minutes = dp.total_minutes or sum(t.estimated_minutes for t in tasks)
        daily_plan = DailyPlan(
            day_number=dp.day_number,
            day_name=dp.day_name or f"Day {dp.day_number}",
            theme=dp.theme,
            tasks=tasks,
            total_minutes=total_minutes,
        )
        daily_plans.append(daily_plan)

    weekly_assessment = WeeklyAssessment(
        assessment_type=response.weekly_assessment.assessment_type,
        description=response.weekly_assessment.description,
        topics_covered=response.weekly_assessment.topics_covered,
        passing_criteria=response.weekly_assessment.passing_criteria,
    )

    return TrainingPlan(
        plan_id=plan_id,
        user_id=user_id,
        week_number=week_number,
        created_at=now,
        goal_for_week=response.goal_for_week,
        prerequisite_knowledge=response.prerequisite_knowledge,
        daily_plans=daily_plans,
        weekly_assessment=weekly_assessment,
        expected_outcomes=response.expected_outcomes,
        adaptation_notes=response.adaptation_notes,
    )


def generate_training_plan(
    memory: UserMemory,
    model: str = OpenAIModel.GPT_4O,
) -> TrainingPlan:
    """Generate a personalized 1-week training plan."""
    logger.info("=" * 60)
    logger.info("GENERATING TRAINING PLAN")
    logger.info("=" * 60)

    profile = memory.profile
    week_number = memory.progress.total_weeks_completed + 1

    patterns = memory.get_patterns_for_prompt()
    recent_feedback = memory.get_recent_feedback(limit=3)
    progress_dict = {
        "topics_mastered": memory.progress.topics_mastered,
        "total_weeks_completed": memory.progress.total_weeks_completed,
        "average_completion_rate": memory.progress.average_completion_rate,
    }

    learned_context = format_learned_context(patterns, progress_dict, recent_feedback)

    logger.info(f"User: {profile.user_id}")
    logger.info(f"Week number: {week_number}")
    logger.info(f"Patterns loaded: {len(patterns)}")
    logger.info(f"Recent feedback: {len(recent_feedback)}")

    system_prompt = make_training_plan_system_prompt()
    user_prompt = make_training_plan_user_prompt(
        learning_goal=profile.learning_goal,
        skill_level=profile.skill_level.value,
        current_knowledge=profile.current_knowledge,
        available_hours_per_week=profile.available_hours_per_week,
        preferred_content_types=[ct.value for ct in profile.preferred_content_types],
        learning_pace=profile.learning_pace,
        week_number=week_number,
        learned_context=learned_context,
    )

    messages = _build_messages(system_prompt, user_prompt)

    llm = _create_chat_model(model)
    response = invoke_with_structured_output(llm, messages, TrainingPlanResponse, "Training Plan Generator")

    plan = _convert_response_to_training_plan(response, profile.user_id, week_number)

    logger.info(f"Plan generated: {plan.plan_id}")
    logger.info(f"Goal: {plan.goal_for_week}")
    logger.info(f"Daily plans: {len(plan.daily_plans)}")

    memory.add_training_plan(plan)

    return plan


# =============================================================================
# Pattern Analysis (Learning Agent)
# =============================================================================


def _convert_response_to_learned_pattern(
    response: LearnedPatternResponse,
    feedback_ids: list[str],
) -> LearnedPattern:
    """Convert LLM response to LearnedPattern model."""
    return LearnedPattern(
        pattern_id=f"pattern_{uuid4().hex[:8]}",
        pattern_type=response.pattern_type,
        description=response.description,
        evidence=response.evidence,
        recommendations=response.recommendations,
        confidence_score=min(1.0, max(0.0, response.confidence_score)),
        created_at=datetime.now().isoformat(),
        source_feedback_ids=feedback_ids,
    )


def analyze_feedback_patterns(
    memory: UserMemory,
    model: str = OpenAIModel.GPT_4O,
) -> list[LearnedPattern]:
    """Analyze user feedback and extract patterns for improving future plan generation."""
    feedback_list = memory.get_recent_feedback(limit=10)

    if len(feedback_list) < MIN_FEEDBACK_FOR_LEARNING:
        logger.info(f"Not enough feedback for pattern analysis ({len(feedback_list)} < {MIN_FEEDBACK_FOR_LEARNING})")
        return []

    logger.info("=" * 60)
    logger.info("ANALYZING FEEDBACK PATTERNS")
    logger.info("=" * 60)
    logger.info(f"Feedback entries: {len(feedback_list)}")

    feedback_history_str = format_feedback_for_analysis(feedback_list)
    feedback_ids = [f.feedback_id for f in feedback_list]

    system_prompt = make_pattern_analyzer_system_prompt()
    user_prompt = make_pattern_analyzer_user_prompt(
        feedback_history=feedback_history_str,
        total_weeks_completed=memory.progress.total_weeks_completed,
        total_tasks_completed=memory.progress.total_tasks_completed,
        average_completion_rate=memory.progress.average_completion_rate,
        topics_mastered=memory.progress.topics_mastered,
    )

    messages = _build_messages(system_prompt, user_prompt)

    llm = _create_chat_model(model)
    response = invoke_with_structured_output(llm, messages, PatternAnalysisResponse, "Pattern Analyzer")

    patterns = [_convert_response_to_learned_pattern(p, feedback_ids) for p in response.patterns]

    logger.info(f"Patterns extracted: {len(patterns)}")

    for pattern in patterns:
        memory.add_learned_pattern(pattern)

    return patterns


# =============================================================================
# Main Entry Points
# =============================================================================


async def run_training_plan_generation(
    user_id: str,
    profile: UserProfile | None = None,
    model: str = OpenAIModel.GPT_4O,
    analyze_patterns: bool = True,
) -> tuple[TrainingPlan, UserMemory, Path]:
    """Run the complete training plan generation workflow."""
    logger.info("=" * 80)
    logger.info("LEARNING AI AGENT - TRAINING PLAN GENERATION")
    logger.info("=" * 80)

    memory = load_memory(user_id)

    if memory is not None:
        logger.info(f"Loaded latest memory for user: {user_id}")
        if profile is not None:
            memory.profile = profile
            logger.info("Updated profile in memory")
    else:
        if profile is None:
            raise ValueError(f"No memory found for user '{user_id}' and no profile provided")
        memory = create_new_memory(profile)
        logger.info(f"Created new memory for user: {user_id}")

    logger.info(f"Training history: {len(memory.training_history)} plans")
    logger.info(f"Learned patterns: {len(memory.learned_patterns)}")
    logger.info(f"Weeks completed: {memory.progress.total_weeks_completed}")

    if analyze_patterns:
        patterns = analyze_feedback_patterns(memory, model)
        if patterns:
            logger.info(f"New patterns learned: {len(patterns)}")

    plan = generate_training_plan(memory, model)

    memory_path = save_memory(memory)

    logger.info("=" * 80)
    logger.info("TRAINING PLAN GENERATION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Plan ID: {plan.plan_id}")
    logger.info(f"Memory saved: {memory_path}")

    return plan, memory, memory_path


def get_training_plan_markdown(plan: TrainingPlan) -> str:
    """Get training plan as markdown."""
    return format_training_plan_markdown(plan)


# =============================================================================
# Profile Creation Helper
# =============================================================================


def create_user_profile(
    user_id: str | None = None,
    learning_goal: str = "",
    current_knowledge: list[str] | None = None,
    skill_level: str = "beginner",
    available_hours_per_week: int = 10,
    preferred_content_types: list[str] | None = None,
    learning_pace: str = "moderate",
) -> UserProfile:
    """Create a user profile."""
    if user_id is None:
        user_id = f"user_{uuid4().hex[:8]}"

    content_types = []
    if preferred_content_types:
        content_types = [_safe_enum_parse(ContentType, ct, ContentType.ARTICLE) for ct in preferred_content_types]

    return UserProfile(
        user_id=user_id,
        learning_goal=learning_goal,
        current_knowledge=current_knowledge or [],
        skill_level=_safe_enum_parse(SkillLevel, skill_level, SkillLevel.BEGINNER),
        available_hours_per_week=available_hours_per_week,
        preferred_content_types=content_types,
        learning_pace=learning_pace,
    )
