"""
Hierarchical Personalized Learning Platform Service with Learning Capabilities.

This module implements a hierarchical multi-agent system for creating
personalized learning plans using LangGraph. It includes a learning feedback
loop that allows the system to improve based on user feedback.

Architecture:
    Learning Agent (analyzes past experiences)
         |
    Strategy Layer -> Tactics Layer -> Execution Layer -> Progress Monitoring
         |                                                       |
         +-------------------> Experience Store <-----------------+

The Learning Agent analyzes accumulated experiences and extracts patterns
that are injected into other agents' prompts to improve output quality.
"""

import json
import re
import time
from datetime import datetime
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
    AdaptationResult,
    ContentType,
    DailyTask,
    ExperiencePattern,
    ExperienceRecord,
    ExperienceStore,
    HierarchicalAgentState,
    LearnerProfile,
    LearningContent,
    LearningInsight,
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
    UserFeedback,
    WeeklyPlan,
)
from src.prompt.llm_pipeline_prompt import (
    format_learned_patterns_context,
    make_content_system_prompt,
    make_content_user_prompt,
    make_learning_system_prompt,
    make_learning_user_prompt,
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
    experience_store = state.get("experience_store")
    model = _create_chat_model(config)

    # Get learned context for this agent type
    learned_context = get_learned_context_for_agent(experience_store, "strategy")

    user_prompt = make_strategy_user_prompt(
        learning_goal=learner.learning_goal,
        current_knowledge=learner.current_knowledge,
        available_hours_per_week=learner.available_hours_per_week,
        target_duration_weeks=learner.target_duration_weeks,
        preferred_content_types=[ct.value for ct in learner.preferred_content_types],
    )
    messages = _build_messages(make_strategy_system_prompt(learned_context), user_prompt)

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

    experience_store = state.get("experience_store")
    model = _create_chat_model(config)

    # Get learned context for this agent type
    learned_context = get_learned_context_for_agent(experience_store, "tactics")

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
    messages = _build_messages(make_tactics_system_prompt(learned_context), user_prompt)

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

    experience_store = state.get("experience_store")
    task = _get_current_task(state)
    logger.info(f"Content Agent: Creating content for task {task.task_id}")

    # Get learned context for this agent type
    learned_context = get_learned_context_for_agent(experience_store, "content")

    model = _create_chat_model(config)
    user_prompt = make_content_user_prompt(
        task_id=task.task_id,
        title=task.title,
        description=task.description,
        content_type=task.content_type.value,
        learning_objectives=task.learning_objectives,
        learner_level=strategy.roadmap.current_level.value,
    )
    messages = _build_messages(make_content_system_prompt(learned_context), user_prompt)

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
    experience_store: ExperienceStore | None = None,
) -> Quiz:
    """Quiz generation agent that creates quizzes for learning content."""
    logger.info(f"Quiz Agent: Creating quiz for task {task_id}")

    # Get learned context for this agent type
    learned_context = get_learned_context_for_agent(experience_store, "quiz")

    model = _create_chat_model(config)
    user_prompt = make_quiz_user_prompt(
        task_id=task_id,
        title=title,
        key_concepts=key_concepts,
        learner_level=learner_level,
    )
    messages = _build_messages(make_quiz_system_prompt(learned_context), user_prompt)

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
    experience_store = state.get("experience_store")
    content = content_agent(state, config)
    quiz = quiz_agent(
        task_id=task.task_id,
        title=content.title,
        key_concepts=content.key_concepts,
        learner_level=strategy.roadmap.current_level.value,
        config=config,
        experience_store=experience_store,
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
    experience_store = state.get("experience_store")

    if strategy is None or tactics is None:
        raise ValueError("Progress agent requires strategy and tactics output")

    # Get learned context for this agent type
    learned_context = get_learned_context_for_agent(experience_store, "progress")

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
    messages = _build_messages(make_progress_system_prompt(learned_context), user_prompt)

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
# Learning Agent (Analyzes experiences and extracts patterns)
# =============================================================================


def _format_experience_for_prompt(experience: ExperienceRecord) -> str:
    """Format an experience record for inclusion in learning prompts."""
    feedback_info = ""
    if experience.user_feedback:
        fb = experience.user_feedback
        feedback_info = f"""
  - 評価: {fb.rating.value}
  - 良かった点: {", ".join(fb.helpful_aspects) if fb.helpful_aspects else "なし"}
  - 改善提案: {", ".join(fb.improvement_suggestions) if fb.improvement_suggestions else "なし"}
  - ユーザー修正: {fb.user_corrections if fb.user_corrections else "なし"}"""

    return f"""
### 経験ID: {experience.experience_id}
- エージェント: {experience.agent_type}
- ドメイン: {experience.learning_domain}
- 入力コンテキスト: {json.dumps(experience.input_context, ensure_ascii=False)[:200]}...
- 生成出力: {json.dumps(experience.output_generated, ensure_ascii=False)[:200]}...
- フィードバック:{feedback_info}
"""


def _parse_learning_patterns(result: dict) -> list[ExperiencePattern]:
    """Parse patterns from learning agent response."""
    patterns = []
    for p in result.get("patterns", []):
        patterns.append(
            ExperiencePattern(
                pattern_id=p.get("pattern_id", f"pattern_{uuid4().hex[:8]}"),
                agent_type=p.get("agent_type", "unknown"),
                pattern_description=p.get("pattern_description", ""),
                positive_examples=p.get("positive_examples", []),
                negative_examples=p.get("negative_examples", []),
                applicable_contexts=p.get("applicable_contexts", []),
                confidence_score=float(p.get("confidence_score", 0.5)),
                source_experience_count=int(p.get("source_experience_count", 0)),
            )
        )
    return patterns


def _parse_learning_insights(result: dict) -> list[LearningInsight]:
    """Parse insights from learning agent response."""
    insights = []
    for i in result.get("insights", []):
        insights.append(
            LearningInsight(
                insight_id=i.get("insight_id", f"insight_{uuid4().hex[:8]}"),
                agent_type=i.get("agent_type", "unknown"),
                insight_type=i.get("insight_type", "improvement"),
                description=i.get("description", ""),
                action_recommendations=i.get("action_recommendations", []),
                priority=i.get("priority", "medium"),
                based_on_experience_count=int(i.get("based_on_experience_count", 0)),
            )
        )
    return insights


def learning_agent(
    experience_store: ExperienceStore,
    agent_type: str,
    config: RunnableConfig,
) -> tuple[list[ExperiencePattern], list[LearningInsight], list[str]]:
    """Learning agent that analyzes experiences and extracts patterns.

    Args:
        experience_store: Store containing past experiences
        agent_type: Type of agent to analyze experiences for
        config: LangGraph runnable config

    Returns:
        Tuple of (patterns, insights, prompt_adjustments)
    """
    _log_layer_start("LEARNING AGENT", f"Analyzing experiences for {agent_type}")

    positive_experiences = experience_store.get_positive_experiences(agent_type)
    negative_experiences = experience_store.get_negative_experiences(agent_type)

    total_experiences = len(experience_store.get_experiences_by_agent(agent_type))

    if total_experiences < 3:
        logger.info(f"Not enough experiences for {agent_type} ({total_experiences} < 3)")
        return [], [], []

    model = _create_chat_model(config)

    positive_exp_str = "\n".join(_format_experience_for_prompt(exp) for exp in positive_experiences[:5])
    negative_exp_str = "\n".join(_format_experience_for_prompt(exp) for exp in negative_experiences[:5])

    user_prompt = make_learning_user_prompt(
        agent_type=agent_type,
        positive_experiences=positive_exp_str,
        negative_experiences=negative_exp_str,
        total_experiences=total_experiences,
        positive_count=len(positive_experiences),
        negative_count=len(negative_experiences),
    )

    messages = _build_messages(make_learning_system_prompt(), user_prompt)

    try:
        response_content = invoke_with_retry(model, messages, config, "Learning Agent")
        result = extract_json_from_response(response_content)

        patterns = _parse_learning_patterns(result)
        insights = _parse_learning_insights(result)
        prompt_adjustments = result.get("prompt_adjustments", [])

        logger.info(f"Learning agent extracted {len(patterns)} patterns, {len(insights)} insights")

        return patterns, insights, prompt_adjustments

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse learning response: {e}")
        return [], [], []


def run_learning_cycle(
    experience_store: ExperienceStore,
    config: RunnableConfig,
) -> AdaptationResult:
    """Run a complete learning cycle analyzing all agent types.

    This function analyzes experiences for each agent type and updates
    the experience store with learned patterns.

    Args:
        experience_store: Store containing past experiences
        config: LangGraph runnable config

    Returns:
        AdaptationResult with details of what was learned
    """
    _log_layer_start("LEARNING CYCLE", "Running adaptation from experiences")

    agent_types = ["strategy", "tactics", "content", "quiz", "progress"]
    all_patterns = []
    all_insights = []
    all_adjustments = []

    for agent_type in agent_types:
        patterns, insights, adjustments = learning_agent(experience_store, agent_type, config)
        all_patterns.extend(patterns)
        all_insights.extend(insights)
        all_adjustments.extend(adjustments)

        # Add patterns to the store
        for pattern in patterns:
            experience_store.add_learned_pattern(pattern)

    result = AdaptationResult(
        adaptation_id=f"adapt_{uuid4().hex[:8]}",
        timestamp=datetime.now().isoformat(),
        experiences_analyzed=len(experience_store.experiences),
        new_patterns_learned=len(all_patterns),
        insights_generated=all_insights,
        prompt_adjustments=all_adjustments,
        success=True,
    )

    logger.info(f"Learning cycle complete: {len(all_patterns)} patterns, {len(all_insights)} insights")

    return result


def get_learned_context_for_agent(
    experience_store: ExperienceStore | None,
    agent_type: str,
) -> str:
    """Get formatted learned context for a specific agent type.

    Args:
        experience_store: Store containing learned patterns (may be None)
        agent_type: Type of agent to get context for

    Returns:
        Formatted string to inject into agent prompts
    """
    if experience_store is None:
        return ""

    patterns = experience_store.get_patterns_for_agent(agent_type)
    # Filter insights that apply to this agent
    insights = [
        LearningInsight(
            insight_id=f"insight_{i}",
            agent_type=agent_type,
            insight_type="improvement",
            description=p.pattern_description,
            action_recommendations=p.positive_examples[:2],
            priority="medium",
            based_on_experience_count=p.source_experience_count,
        )
        for i, p in enumerate(patterns)
        if p.confidence_score > 0.6
    ]

    return format_learned_patterns_context(patterns, insights)


# =============================================================================
# Experience Recording Functions
# =============================================================================


def record_experience(
    experience_store: ExperienceStore,
    learner_id: str,
    agent_type: str,
    input_context: dict,
    output_generated: dict,
    learning_domain: str,
    user_feedback: UserFeedback | None = None,
) -> ExperienceRecord:
    """Record an experience to the experience store.

    Args:
        experience_store: Store to add experience to
        learner_id: ID of the learner
        agent_type: Type of agent that generated the output
        input_context: Input given to the agent
        output_generated: Output generated by the agent
        learning_domain: Domain of learning
        user_feedback: Optional user feedback on the output

    Returns:
        The created experience record
    """
    experience = ExperienceRecord(
        experience_id=f"exp_{uuid4().hex[:8]}",
        learner_id=learner_id,
        agent_type=agent_type,
        input_context=input_context,
        output_generated=output_generated,
        user_feedback=user_feedback,
        learning_domain=learning_domain,
    )

    experience_store.add_experience(experience)
    logger.info(f"Recorded experience {experience.experience_id} for {agent_type}")

    return experience


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


def _create_initial_state(
    learner_profile: LearnerProfile,
    experience_store: ExperienceStore | None = None,
) -> HierarchicalAgentState:
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
        "experience_store": experience_store,
        "learned_patterns_context": "",
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
    experience_store: ExperienceStore | None = None,
    run_learning_before: bool = True,
) -> tuple[PersonalizedLearningPlan | None, ExperienceStore | None]:
    """Run the hierarchical personalized learning agent system.

    This function runs the learning platform with optional experience-based learning.
    When an experience store is provided and run_learning_before is True, it will
    first analyze past experiences to extract patterns before generating the plan.

    Args:
        learner_profile: Profile of the learner
        model: OpenAI model to use
        experience_store: Optional store containing past experiences
        run_learning_before: Whether to run learning cycle before generating plan

    Returns:
        Tuple of (learning plan, updated experience store)
    """
    logger.info("=" * 80)
    logger.info("HIERARCHICAL PERSONALIZED LEARNING PLATFORM (WITH LEARNING)")
    logger.info("=" * 80)
    logger.info(f"Learner goal: {learner_profile.learning_goal}")
    logger.info(f"Available hours/week: {learner_profile.available_hours_per_week}")
    logger.info(f"Target duration: {learner_profile.target_duration_weeks} weeks")
    logger.info(f"Model: {model}")

    if experience_store:
        logger.info(f"Experience store loaded: {len(experience_store.experiences)} experiences")
        logger.info(f"Learned patterns: {len(experience_store.learned_patterns)}")
    else:
        logger.info("No experience store provided - starting fresh")

    graph = create_learning_platform_graph()
    config = RunnableConfig(configurable={"model": model})

    # Run learning cycle if we have enough experiences
    if experience_store and run_learning_before and len(experience_store.experiences) >= 3:
        logger.info("Running learning cycle to extract patterns from past experiences...")
        adaptation_result = run_learning_cycle(experience_store, config)
        logger.info(f"Learning cycle complete: {adaptation_result.new_patterns_learned} new patterns")

    try:
        initial_state = _create_initial_state(learner_profile, experience_store)
        final_state = await graph.ainvoke(initial_state, config)
        plan = _create_plan_from_state(final_state, learner_profile)

        if plan:
            logger.info("=" * 80)
            logger.info("LEARNING PLAN CREATED SUCCESSFULLY")
            logger.info("=" * 80)

        return plan, experience_store

    except Exception as e:
        logger.error(f"Learning platform failed: {str(e)}")
        raise


def create_new_experience_store(store_id: str | None = None) -> ExperienceStore:
    """Create a new empty experience store.

    Args:
        store_id: Optional ID for the store. If not provided, a random ID is generated.

    Returns:
        A new empty ExperienceStore
    """
    return ExperienceStore(
        store_id=store_id or f"store_{uuid4().hex[:8]}",
        experiences=[],
        learned_patterns=[],
    )
