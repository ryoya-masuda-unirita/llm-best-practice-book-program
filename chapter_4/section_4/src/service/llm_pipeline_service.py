"""
Hierarchical Personalized Learning Platform Service.

This module implements a hierarchical multi-agent system for creating
personalized learning plans using LangGraph.

Architecture:
    Strategy Layer -> Tactics Layer -> Execution Layer -> Progress Monitoring
"""

import json
import re
import time
from typing import Literal
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from src.client.llm_client import OpenAIModel
from src.config import config as global_config
from src.logger import make_logger
from src.model.llm_pipeline_model import (
    ContentType,
    DailyTask,
    HierarchicalAgentState,
    LearnerProfile,
    LearningContent,
    LearningModule,
    LearningModuleCategory,
    LearningRoadmap,
    LearningSession,
    PersonalizedLearningPlan,
    ProgressMetrics,
    ProgressReport,
    QuestionType,
    Quiz,
    QuizQuestion,
    SkillLevel,
    StrategyOutput,
    TacticsOutput,
    WeeklyPlan,
)
from src.prompt.llm_pipeline_prompt import (
    make_content_system_prompt,
    make_content_user_prompt,
    make_progress_system_prompt,
    make_progress_user_prompt,
    make_quiz_system_prompt,
    make_quiz_user_prompt,
    make_strategy_system_prompt,
    make_strategy_user_prompt,
    make_tactics_system_prompt,
    make_tactics_user_prompt,
)

logger = make_logger(__name__)

# =============================================================================
# Constants
# =============================================================================

MAX_SESSIONS_FIRST_WEEK = 5
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2


# =============================================================================
# Helper Functions
# =============================================================================


def _get_model_from_config(config: RunnableConfig) -> str:
    """Extract model name from config with default fallback."""
    return config.get("configurable", {}).get("model", OpenAIModel.GPT_5_MINI)


def _create_chat_model(config: RunnableConfig) -> ChatOpenAI:
    """Create a ChatOpenAI model instance from config."""
    return ChatOpenAI(model=_get_model_from_config(config), openai_api_key=global_config.openai_api_key)


def _build_messages(system_prompt: str, user_prompt: str) -> list:
    """Build message list for LLM invocation."""
    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]


def _log_layer_start(layer_name: str, description: str) -> None:
    """Log the start of a layer's execution."""
    logger.info("=" * 60)
    logger.info(f"{layer_name}: {description}")
    logger.info("=" * 60)


def _safe_enum_parse(enum_class, value: str, default):
    """Safely parse an enum value with fallback to default."""
    try:
        return enum_class(value)
    except ValueError:
        return default


# =============================================================================
# JSON Parsing Utilities
# =============================================================================


def _try_fix_truncated_json(json_str: str) -> str:
    """Try to fix truncated JSON by adding missing closing brackets/braces."""
    open_braces = json_str.count("{")
    close_braces = json_str.count("}")
    open_brackets = json_str.count("[")
    close_brackets = json_str.count("]")

    # Check for unterminated strings
    in_string = False
    escape_next = False

    for char in json_str:
        if escape_next:
            escape_next = False
            continue
        if char == "\\":
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string

    # Close unterminated string and add missing brackets/braces
    if in_string:
        json_str += '"'
    json_str += "]" * (open_brackets - close_brackets)
    json_str += "}" * (open_braces - close_braces)

    return json_str


def _extract_json_string(response: str) -> str:
    """Extract JSON string from LLM response using multiple strategies."""
    stripped = response.strip()

    # Strategy 1: Response starts with '{'
    if stripped.startswith("{"):
        return stripped

    # Strategy 2: Find ```json code block
    json_match = re.search(r"```json\s*([\s\S]*?)```", response)
    if json_match:
        return json_match.group(1).strip()

    # Strategy 3: Find first { and last }
    first_brace = response.find("{")
    last_brace = response.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        return response[first_brace : last_brace + 1]

    # Strategy 4: Use the whole response
    return stripped


def extract_json_from_response(response: str) -> dict:
    """Extract and parse JSON from LLM response."""
    if not response or not response.strip():
        raise ValueError("Empty response from LLM")

    json_str = _extract_json_string(response)
    if not json_str:
        raise ValueError(f"No JSON content found in response: {response[:200]}...")

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        logger.warning("JSON parsing failed, attempting to fix truncated JSON...")
        fixed_json = _try_fix_truncated_json(json_str)
        try:
            return json.loads(fixed_json)
        except json.JSONDecodeError as e:
            logger.error(f"Original JSON (first 500 chars): {json_str[:500]}...")
            logger.error(f"Fixed JSON (last 200 chars): ...{fixed_json[-200:]}")
            raise e


def invoke_with_retry(
    model: ChatOpenAI,
    messages: list,
    config: RunnableConfig,
    agent_name: str,
) -> str:
    """Invoke LLM with retry logic for transient failures."""
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            response = model.invoke(messages, config)
            if response.content and response.content.strip():
                return response.content
            logger.warning(f"{agent_name}: Empty response on attempt {attempt + 1}")
        except Exception as e:
            last_error = e
            logger.warning(f"{agent_name}: Error on attempt {attempt + 1}: {e}")

        if attempt < MAX_RETRIES - 1:
            logger.info(f"{agent_name}: Retrying in {RETRY_DELAY_SECONDS} seconds...")
            time.sleep(RETRY_DELAY_SECONDS)

    raise ValueError(f"{agent_name} failed after {MAX_RETRIES} attempts: {last_error}")


# =============================================================================
# Strategy Layer Agent
# =============================================================================


def _parse_learning_module(data: dict) -> LearningModule:
    """Parse a learning module from JSON data."""
    return LearningModule(
        module_id=data["module_id"],
        name=data["name"],
        category=LearningModuleCategory(data["category"]),
        description=data["description"],
        prerequisites=data.get("prerequisites", []),
        estimated_hours=data["estimated_hours"],
        target_competencies=data["target_competencies"],
    )


def _parse_strategy_output(result: dict) -> StrategyOutput:
    """Parse strategy output from JSON result."""
    roadmap_data = result["roadmap"]
    modules = [_parse_learning_module(m) for m in roadmap_data["modules"]]

    roadmap = LearningRoadmap(
        goal_summary=roadmap_data["goal_summary"],
        target_level=SkillLevel(roadmap_data["target_level"]),
        current_level=SkillLevel(roadmap_data["current_level"]),
        total_duration_weeks=roadmap_data["total_duration_weeks"],
        modules=modules,
        milestones=roadmap_data["milestones"],
        success_criteria=roadmap_data["success_criteria"],
    )

    return StrategyOutput(
        learning_domain=result["learning_domain"],
        roadmap=roadmap,
        recommended_study_hours_per_week=result["recommended_study_hours_per_week"],
        learning_style_notes=result["learning_style_notes"],
    )


def strategy_agent(state: HierarchicalAgentState, config: RunnableConfig) -> dict:
    """Strategy layer agent that creates the learning roadmap."""
    _log_layer_start("STRATEGY LAYER", "Creating learning roadmap")

    learner = state["learner_profile"]
    model = _create_chat_model(config)

    user_prompt = make_strategy_user_prompt(
        learning_goal=learner.learning_goal,
        current_knowledge=learner.current_knowledge,
        available_hours_per_week=learner.available_hours_per_week,
        target_duration_weeks=learner.target_duration_weeks,
        preferred_content_types=[ct.value for ct in learner.preferred_content_types],
    )
    messages = _build_messages(make_strategy_system_prompt(), user_prompt)

    response_content = invoke_with_retry(model, messages, config, "Strategy Agent")
    logger.info("Strategy agent received response from LLM")

    try:
        result = extract_json_from_response(response_content)
        strategy_output = _parse_strategy_output(result)

        logger.info(f"Strategy output: domain={strategy_output.learning_domain}")
        logger.info(f"Strategy output: {len(strategy_output.roadmap.modules)} modules created")
        logger.info(
            f"Strategy output: {strategy_output.roadmap.current_level} -> {strategy_output.roadmap.target_level}"
        )

        return {"strategy_output": strategy_output}

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse strategy response: {e}")
        logger.error(f"Raw response: {response_content[:500] if response_content else 'None'}...")
        raise ValueError(f"Strategy agent failed to produce valid output: {e}")


# =============================================================================
# Tactics Layer Agent
# =============================================================================


def _parse_daily_task(data: dict) -> DailyTask:
    """Parse a daily task from JSON data."""
    return DailyTask(
        task_id=data["task_id"],
        title=data["title"],
        description=data["description"],
        content_type=ContentType(data["content_type"]),
        estimated_minutes=data["estimated_minutes"],
        learning_objectives=data["learning_objectives"],
    )


def _parse_weekly_plan(data: dict) -> WeeklyPlan:
    """Parse a weekly plan from JSON data."""
    daily_tasks = {day_key: [_parse_daily_task(t) for t in tasks] for day_key, tasks in data["daily_tasks"].items()}

    return WeeklyPlan(
        week_number=data["week_number"],
        module_id=data["module_id"],
        theme=data["theme"],
        learning_goals=data["learning_goals"],
        daily_tasks=daily_tasks,
        weekly_assessment=data["weekly_assessment"],
    )


def _parse_tactics_output(result: dict) -> TacticsOutput:
    """Parse tactics output from JSON result."""
    weekly_plans = [_parse_weekly_plan(wp) for wp in result["weekly_plans"]]

    return TacticsOutput(
        curriculum_summary=result["curriculum_summary"],
        weekly_plans=weekly_plans,
        assessment_strategy=result["assessment_strategy"],
        adaptation_notes=result["adaptation_notes"],
    )


def tactics_agent(state: HierarchicalAgentState, config: RunnableConfig) -> dict:
    """Tactics layer agent that creates the detailed curriculum."""
    _log_layer_start("TACTICS LAYER", "Designing curriculum")

    strategy = state["strategy_output"]
    if strategy is None:
        raise ValueError("Tactics agent requires strategy output")

    model = _create_chat_model(config)

    modules_str = "\n".join(
        f"- {m.module_id}: {m.name} ({m.category.value}) - {m.estimated_hours}時間" for m in strategy.roadmap.modules
    )
    milestones_str = "\n".join(f"- {ms}" for ms in strategy.roadmap.milestones)

    user_prompt = make_tactics_user_prompt(
        learning_domain=strategy.learning_domain,
        goal_summary=strategy.roadmap.goal_summary,
        current_level=strategy.roadmap.current_level.value,
        target_level=strategy.roadmap.target_level.value,
        total_duration_weeks=strategy.roadmap.total_duration_weeks,
        modules=modules_str,
        milestones=milestones_str,
        recommended_study_hours_per_week=strategy.recommended_study_hours_per_week,
        learning_style_notes=strategy.learning_style_notes,
    )
    messages = _build_messages(make_tactics_system_prompt(), user_prompt)

    response_content = invoke_with_retry(model, messages, config, "Tactics Agent")
    logger.info("Tactics agent received response from LLM")

    try:
        result = extract_json_from_response(response_content)
        tactics_output = _parse_tactics_output(result)

        logger.info(f"Tactics output: {len(tactics_output.weekly_plans)} weekly plans created")

        return {
            "tactics_output": tactics_output,
            "current_week": 1,
            "current_day": "day1",
            "current_task_index": 0,
            "learning_sessions": [],
        }

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse tactics response: {e}")
        logger.error(f"Raw response: {response_content[:500] if response_content else 'None'}...")
        raise ValueError(f"Tactics agent failed to produce valid output: {e}")


# =============================================================================
# Execution Layer Agents
# =============================================================================


def _get_current_task(state: HierarchicalAgentState) -> DailyTask:
    """Get the current task from state."""
    tactics = state["tactics_output"]
    if tactics is None:
        raise ValueError("No tactics output in state")

    week_plan = tactics.weekly_plans[state["current_week"] - 1]
    day_tasks = week_plan.daily_tasks.get(state["current_day"], [])
    task_index = state["current_task_index"]

    if task_index >= len(day_tasks):
        raise ValueError(f"No task at index {task_index} for {state['current_day']}")

    return day_tasks[task_index]


def _parse_learning_content(result: dict, task: DailyTask) -> LearningContent:
    """Parse learning content from JSON result with safe defaults."""
    content_type = _safe_enum_parse(
        ContentType,
        result.get("content_type", "article"),
        ContentType.ARTICLE,
    )

    return LearningContent(
        content_id=result.get("content_id", f"content_{task.task_id}"),
        task_id=result.get("task_id", task.task_id),
        title=result.get("title", task.title),
        content_type=content_type,
        content_body=result.get("content_body", ""),
        key_concepts=result.get("key_concepts", task.learning_objectives or []),
        resources=result.get("resources", []),
    )


def content_agent(state: HierarchicalAgentState, config: RunnableConfig) -> LearningContent:
    """Content generation agent that creates learning content for a task."""
    strategy = state["strategy_output"]
    if strategy is None:
        raise ValueError("Content agent requires strategy output")

    task = _get_current_task(state)
    logger.info(f"Content Agent: Creating content for task {task.task_id}")

    model = _create_chat_model(config)
    user_prompt = make_content_user_prompt(
        task_id=task.task_id,
        title=task.title,
        description=task.description,
        content_type=task.content_type.value,
        learning_objectives=task.learning_objectives,
        learner_level=strategy.roadmap.current_level.value,
    )
    messages = _build_messages(make_content_system_prompt(), user_prompt)

    response_content = invoke_with_retry(model, messages, config, "Content Agent")

    try:
        result = extract_json_from_response(response_content)
        content = _parse_learning_content(result, task)
        logger.info(f"Content created: {content.title}")
        return content

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse content response: {e}")
        logger.error(f"Raw response: {response_content[:500] if response_content else 'None'}...")
        raise ValueError(f"Content agent failed: {e}")


def _parse_quiz_question(data: dict, index: int, key_concepts: list[str]) -> QuizQuestion:
    """Parse a quiz question from JSON data with safe defaults."""
    question_type = _safe_enum_parse(
        QuestionType,
        data.get("question_type", "multiple_choice"),
        QuestionType.MULTIPLE_CHOICE,
    )
    difficulty = _safe_enum_parse(
        SkillLevel,
        data.get("difficulty", "beginner"),
        SkillLevel.BEGINNER,
    )

    return QuizQuestion(
        question_id=data.get("question_id", f"q_{index + 1:03d}"),
        question_type=question_type,
        question_text=data.get("question_text", ""),
        options=data.get("options", []),
        correct_answer=data.get("correct_answer", ""),
        explanation=data.get("explanation", ""),
        difficulty=difficulty,
        related_concepts=data.get("related_concepts", key_concepts or []),
    )


def _parse_quiz(result: dict, task_id: str, title: str, key_concepts: list[str]) -> Quiz:
    """Parse quiz from JSON result with safe defaults."""
    questions = [_parse_quiz_question(q, i, key_concepts) for i, q in enumerate(result.get("questions", []))]

    return Quiz(
        quiz_id=result.get("quiz_id", f"quiz_{task_id}"),
        task_id=result.get("task_id", task_id),
        title=result.get("title", f"Quiz: {title}"),
        questions=questions,
        passing_score=result.get("passing_score", 70),
        time_limit_minutes=result.get("time_limit_minutes", 0),
    )


def quiz_agent(
    task_id: str,
    title: str,
    key_concepts: list[str],
    learner_level: str,
    config: RunnableConfig,
) -> Quiz:
    """Quiz generation agent that creates quizzes for learning content."""
    logger.info(f"Quiz Agent: Creating quiz for task {task_id}")

    model = _create_chat_model(config)
    user_prompt = make_quiz_user_prompt(
        task_id=task_id,
        title=title,
        key_concepts=key_concepts,
        learner_level=learner_level,
    )
    messages = _build_messages(make_quiz_system_prompt(), user_prompt)

    response_content = invoke_with_retry(model, messages, config, "Quiz Agent")

    try:
        result = extract_json_from_response(response_content)
        quiz = _parse_quiz(result, task_id, title, key_concepts)
        logger.info(f"Quiz created: {quiz.title} ({len(quiz.questions)} questions)")
        return quiz

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse quiz response: {e}")
        logger.error(f"Raw response: {response_content[:500] if response_content else 'None'}...")
        raise ValueError(f"Quiz agent failed: {e}")


def _calculate_next_task_position(
    state: HierarchicalAgentState,
    tactics: TacticsOutput,
) -> tuple[int, str, int]:
    """Calculate the next task position (week, day, index) after current task."""
    current_week = state["current_week"]
    current_day = state["current_day"]
    task_index = state["current_task_index"] + 1

    week_plan = tactics.weekly_plans[current_week - 1]
    day_tasks = week_plan.daily_tasks.get(current_day, [])

    # Check if more tasks in current day
    if task_index < len(day_tasks):
        return current_week, current_day, task_index

    # Move to next day
    day_keys = list(week_plan.daily_tasks.keys())
    current_day_idx = day_keys.index(current_day) if current_day in day_keys else 0

    if current_day_idx + 1 < len(day_keys):
        return current_week, day_keys[current_day_idx + 1], 0

    # Move to next week
    if current_week < len(tactics.weekly_plans):
        next_week = current_week + 1
        next_day = list(tactics.weekly_plans[next_week - 1].daily_tasks.keys())[0]
        return next_week, next_day, 0

    # No more tasks
    return current_week, current_day, task_index


def execution_agent(state: HierarchicalAgentState, config: RunnableConfig) -> dict:
    """Execution layer agent that orchestrates content and quiz generation."""
    tactics = state["tactics_output"]
    strategy = state["strategy_output"]
    if tactics is None or strategy is None:
        raise ValueError("Execution agent requires strategy and tactics output")

    current_sessions = list(state["learning_sessions"])

    if len(current_sessions) >= MAX_SESSIONS_FIRST_WEEK:
        logger.info(f"Reached maximum sessions ({MAX_SESSIONS_FIRST_WEEK})")
        return {"learning_sessions": current_sessions}

    try:
        task = _get_current_task(state)
    except ValueError:
        logger.info(f"No more tasks for {state['current_day']}")
        return {"learning_sessions": current_sessions}

    _log_layer_start(
        "EXECUTION LAYER",
        f"Session {len(current_sessions) + 1}/{MAX_SESSIONS_FIRST_WEEK}",
    )
    logger.info(f"Week {state['current_week']}, {state['current_day']}, Task: {task.task_id}")

    # Generate content and quiz
    content = content_agent(state, config)
    quiz = quiz_agent(
        task_id=task.task_id,
        title=content.title,
        key_concepts=content.key_concepts,
        learner_level=strategy.roadmap.current_level.value,
        config=config,
    )

    # Create session
    session = LearningSession(
        session_id=f"session_{uuid4().hex[:8]}",
        task_id=task.task_id,
        content=content,
        quiz=quiz,
        feedback=None,
    )
    current_sessions.append(session)
    logger.info(f"Session created: {session.session_id}")

    # Calculate next position
    new_week, new_day, new_task_index = _calculate_next_task_position(state, tactics)

    return {
        "learning_sessions": current_sessions,
        "current_task_index": new_task_index,
        "current_day": new_day,
        "current_week": new_week,
    }


def _has_more_tasks(state: HierarchicalAgentState) -> bool:
    """Check if there are more tasks to execute."""
    tactics = state["tactics_output"]
    if not tactics:
        return False

    current_week = state["current_week"]
    if current_week > len(tactics.weekly_plans):
        return False

    week_plan = tactics.weekly_plans[current_week - 1]
    day_tasks = week_plan.daily_tasks.get(state["current_day"], [])
    return state["current_task_index"] < len(day_tasks)


def should_continue_execution(state: HierarchicalAgentState) -> Literal["execute", "progress"]:
    """Determine whether to continue executing or move to progress reporting."""
    sessions = state["learning_sessions"]

    if len(sessions) < MAX_SESSIONS_FIRST_WEEK and _has_more_tasks(state):
        logger.info(f"Continuing execution: {len(sessions)}/{MAX_SESSIONS_FIRST_WEEK} sessions")
        return "execute"

    logger.info("Moving to progress reporting")
    return "progress"


# =============================================================================
# Progress Monitoring Agent
# =============================================================================


def _parse_progress_metrics(data: dict) -> ProgressMetrics:
    """Parse progress metrics from JSON data with safe defaults."""
    return ProgressMetrics(
        modules_completed=data.get("modules_completed", 0),
        total_modules=data.get("total_modules", 0),
        current_week=data.get("current_week", 1),
        tasks_completed_this_week=data.get("tasks_completed_this_week", 0),
        total_tasks_this_week=data.get("total_tasks_this_week", 0),
        average_quiz_score=data.get("average_quiz_score") or 0.0,
        study_hours_logged=data.get("study_hours_logged") or 0.0,
        streak_days=data.get("streak_days") or 0,
        competencies_acquired=data.get("competencies_acquired", []),
        on_track=data.get("on_track", True),
    )


def _parse_progress_report(result: dict) -> ProgressReport:
    """Parse progress report from JSON result."""
    return ProgressReport(
        report_id=result["report_id"],
        metrics=_parse_progress_metrics(result.get("metrics", {})),
        progress_summary=result["progress_summary"],
        achievements=result["achievements"],
        recommendations=result["recommendations"],
        curriculum_adjustment_needed=result["curriculum_adjustment_needed"],
        adjustment_reason=result.get("adjustment_reason", ""),
    )


def progress_agent(state: HierarchicalAgentState, config: RunnableConfig) -> dict:
    """Progress monitoring agent that creates a progress report."""
    _log_layer_start("PROGRESS MONITORING", "Creating progress report")

    strategy = state["strategy_output"]
    tactics = state["tactics_output"]
    sessions = state["learning_sessions"]

    if strategy is None or tactics is None:
        raise ValueError("Progress agent requires strategy and tactics output")

    model = _create_chat_model(config)

    sessions_info = "\n".join(f"- {s.content.title}: クイズ {len(s.quiz.questions)}問" for s in sessions)

    user_prompt = make_progress_user_prompt(
        learning_domain=strategy.learning_domain,
        target_level=strategy.roadmap.target_level.value,
        total_duration_weeks=strategy.roadmap.total_duration_weeks,
        total_modules=len(strategy.roadmap.modules),
        current_week=1,
        sessions_completed=len(sessions),
        sessions_this_week=sessions_info or "まだセッションなし",
    )
    messages = _build_messages(make_progress_system_prompt(), user_prompt)

    response_content = invoke_with_retry(model, messages, config, "Progress Agent")

    try:
        result = extract_json_from_response(response_content)
        progress_report = _parse_progress_report(result)

        logger.info(f"Progress report created: {progress_report.report_id}")
        logger.info(f"On track: {progress_report.metrics.on_track}")

        return {"progress_report": progress_report}

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse progress response: {e}")
        logger.error(f"Raw response: {response_content[:500] if response_content else 'None'}...")
        raise ValueError(f"Progress agent failed: {e}")


# =============================================================================
# Graph Construction
# =============================================================================


def create_learning_platform_graph() -> StateGraph:
    """Create the hierarchical personalized learning platform graph."""
    logger.info("Creating hierarchical learning platform graph...")

    graph = StateGraph(HierarchicalAgentState)

    # Add nodes: Strategy -> Tactics -> Execution (loop) -> Progress
    graph.add_node("strategy", strategy_agent)
    graph.add_node("tactics", tactics_agent)
    graph.add_node("execution", execution_agent)
    graph.add_node("progress", progress_agent)

    # Define flow
    graph.set_entry_point("strategy")
    graph.add_edge("strategy", "tactics")
    graph.add_edge("tactics", "execution")
    graph.add_conditional_edges(
        "execution",
        should_continue_execution,
        {"execute": "execution", "progress": "progress"},
    )
    graph.add_edge("progress", END)

    logger.info("Learning platform graph created successfully")
    return graph.compile()


# =============================================================================
# Main Entry Point
# =============================================================================


def _create_initial_state(learner_profile: LearnerProfile) -> HierarchicalAgentState:
    """Create initial state for the learning platform."""
    return {
        "learner_profile": learner_profile,
        "strategy_output": None,
        "tactics_output": None,
        "learning_sessions": [],
        "progress_report": None,
        "current_week": 1,
        "current_day": "day1",
        "current_task_index": 0,
        "messages": [],
    }


def _create_plan_from_state(
    final_state: dict,
    learner_profile: LearnerProfile,
) -> PersonalizedLearningPlan | None:
    """Create a PersonalizedLearningPlan from final graph state."""
    strategy = final_state.get("strategy_output")
    tactics = final_state.get("tactics_output")
    sessions = final_state.get("learning_sessions", [])
    progress = final_state.get("progress_report")

    if not (strategy and tactics and progress):
        logger.warning("Learning plan incomplete")
        return None

    return PersonalizedLearningPlan(
        plan_id=f"plan_{uuid4().hex[:8]}",
        learner_profile=learner_profile,
        strategy=strategy,
        curriculum=tactics,
        first_week_sessions=sessions,
        progress_report=progress,
    )


async def run_personalized_learning(
    learner_profile: LearnerProfile,
    model: str = OpenAIModel.GPT_4O,
) -> PersonalizedLearningPlan | None:
    """Run the hierarchical personalized learning agent system."""
    logger.info("=" * 80)
    logger.info("HIERARCHICAL PERSONALIZED LEARNING PLATFORM")
    logger.info("=" * 80)
    logger.info(f"Learner goal: {learner_profile.learning_goal}")
    logger.info(f"Available hours/week: {learner_profile.available_hours_per_week}")
    logger.info(f"Target duration: {learner_profile.target_duration_weeks} weeks")
    logger.info(f"Model: {model}")

    graph = create_learning_platform_graph()
    config = RunnableConfig(configurable={"model": model})

    try:
        final_state = await graph.ainvoke(_create_initial_state(learner_profile), config)
        plan = _create_plan_from_state(final_state, learner_profile)

        if plan:
            logger.info("=" * 80)
            logger.info("LEARNING PLAN CREATED SUCCESSFULLY")
            logger.info("=" * 80)

        return plan

    except Exception as e:
        logger.error(f"Learning platform failed: {str(e)}")
        raise
