import json
import re
from typing import Literal
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from src.client.llm_client import OpenAIModel
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
    Quiz,
    QuestionType,
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

# Maximum number of sessions to generate in the first week
MAX_SESSIONS_FIRST_WEEK = 5


# =============================================================================
# JSON Parsing Utilities
# =============================================================================


def extract_json_from_response(response: str) -> dict:
    """
    Extract JSON from LLM response that may contain markdown code blocks.

    Args:
        response: Raw LLM response text

    Returns:
        Parsed JSON dictionary
    """
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        json_str = response.strip()

    return json.loads(json_str)


# =============================================================================
# Strategy Layer Agent - Learning Strategy Agent
# =============================================================================


def strategy_agent(state: HierarchicalAgentState, config: RunnableConfig) -> dict:
    """
    Strategy layer agent that creates the learning roadmap.

    This is the top-level agent that analyzes the learner's goal and
    creates a comprehensive learning strategy.

    Args:
        state: Current hierarchical agent state
        config: Runtime configuration

    Returns:
        Updated state with strategy output
    """
    logger.info("=" * 60)
    logger.info("STRATEGY LAYER: Creating learning roadmap")
    logger.info("=" * 60)

    learner = state["learner_profile"]
    model_name = config.get("configurable", {}).get("model", OpenAIModel.GPT_4O)
    model = ChatOpenAI(model=model_name, temperature=0.7)

    system_prompt = make_strategy_system_prompt()
    user_prompt = make_strategy_user_prompt(
        learning_goal=learner.learning_goal,
        current_knowledge=learner.current_knowledge,
        available_hours_per_week=learner.available_hours_per_week,
        target_duration_weeks=learner.target_duration_weeks,
        preferred_content_types=[ct.value for ct in learner.preferred_content_types],
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = model.invoke(messages, config)
    logger.info("Strategy agent received response from LLM")

    try:
        result = extract_json_from_response(response.content)

        roadmap_data = result["roadmap"]
        modules = [
            LearningModule(
                module_id=m["module_id"],
                name=m["name"],
                category=LearningModuleCategory(m["category"]),
                description=m["description"],
                prerequisites=m.get("prerequisites", []),
                estimated_hours=m["estimated_hours"],
                target_competencies=m["target_competencies"],
            )
            for m in roadmap_data["modules"]
        ]

        roadmap = LearningRoadmap(
            goal_summary=roadmap_data["goal_summary"],
            target_level=SkillLevel(roadmap_data["target_level"]),
            current_level=SkillLevel(roadmap_data["current_level"]),
            total_duration_weeks=roadmap_data["total_duration_weeks"],
            modules=modules,
            milestones=roadmap_data["milestones"],
            success_criteria=roadmap_data["success_criteria"],
        )

        strategy_output = StrategyOutput(
            learning_domain=result["learning_domain"],
            roadmap=roadmap,
            recommended_study_hours_per_week=result["recommended_study_hours_per_week"],
            learning_style_notes=result["learning_style_notes"],
        )

        logger.info(f"Strategy output: domain={strategy_output.learning_domain}")
        logger.info(f"Strategy output: {len(modules)} modules created")
        logger.info(f"Strategy output: {roadmap.current_level} -> {roadmap.target_level}")

        return {"strategy_output": strategy_output}

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse strategy response: {e}")
        logger.error(f"Raw response: {response.content}")
        raise ValueError(f"Strategy agent failed to produce valid output: {e}")


# =============================================================================
# Tactics Layer Agent - Curriculum Design Agent
# =============================================================================


def tactics_agent(state: HierarchicalAgentState, config: RunnableConfig) -> dict:
    """
    Tactics layer agent that creates the detailed curriculum.

    This agent breaks down the learning roadmap into weekly and daily plans.

    Args:
        state: Current hierarchical agent state
        config: Runtime configuration

    Returns:
        Updated state with tactics output
    """
    logger.info("=" * 60)
    logger.info("TACTICS LAYER: Designing curriculum")
    logger.info("=" * 60)

    strategy = state["strategy_output"]
    if strategy is None:
        raise ValueError("Tactics agent requires strategy output")

    model_name = config.get("configurable", {}).get("model", OpenAIModel.GPT_4O)
    model = ChatOpenAI(model=model_name, temperature=0.5)

    modules_str = "\n".join(
        f"- {m.module_id}: {m.name} ({m.category.value}) - {m.estimated_hours}時間"
        for m in strategy.roadmap.modules
    )
    milestones_str = "\n".join(f"- {ms}" for ms in strategy.roadmap.milestones)

    system_prompt = make_tactics_system_prompt()
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

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = model.invoke(messages, config)
    logger.info("Tactics agent received response from LLM")

    try:
        result = extract_json_from_response(response.content)

        weekly_plans = []
        for wp in result["weekly_plans"]:
            daily_tasks_dict = {}
            for day_key, tasks in wp["daily_tasks"].items():
                daily_tasks_dict[day_key] = [
                    DailyTask(
                        task_id=t["task_id"],
                        title=t["title"],
                        description=t["description"],
                        content_type=ContentType(t["content_type"]),
                        estimated_minutes=t["estimated_minutes"],
                        learning_objectives=t["learning_objectives"],
                    )
                    for t in tasks
                ]

            weekly_plans.append(
                WeeklyPlan(
                    week_number=wp["week_number"],
                    module_id=wp["module_id"],
                    theme=wp["theme"],
                    learning_goals=wp["learning_goals"],
                    daily_tasks=daily_tasks_dict,
                    weekly_assessment=wp["weekly_assessment"],
                )
            )

        tactics_output = TacticsOutput(
            curriculum_summary=result["curriculum_summary"],
            weekly_plans=weekly_plans,
            assessment_strategy=result["assessment_strategy"],
            adaptation_notes=result["adaptation_notes"],
        )

        logger.info(f"Tactics output: {len(weekly_plans)} weekly plans created")

        return {
            "tactics_output": tactics_output,
            "current_week": 1,
            "current_day": "day1",
            "current_task_index": 0,
            "learning_sessions": [],
        }

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse tactics response: {e}")
        logger.error(f"Raw response: {response.content}")
        raise ValueError(f"Tactics agent failed to produce valid output: {e}")


# =============================================================================
# Execution Layer Agents
# =============================================================================


def content_agent(state: HierarchicalAgentState, config: RunnableConfig) -> LearningContent:
    """
    Content generation agent that creates learning content for a task.

    Args:
        state: Current hierarchical agent state
        config: Runtime configuration

    Returns:
        LearningContent for the current task
    """
    tactics = state["tactics_output"]
    strategy = state["strategy_output"]
    if tactics is None or strategy is None:
        raise ValueError("Content agent requires strategy and tactics output")

    # Get current task
    current_week = state["current_week"]
    current_day = state["current_day"]
    week_plan = tactics.weekly_plans[current_week - 1]
    task_index = state["current_task_index"]

    day_tasks = week_plan.daily_tasks.get(current_day, [])
    if task_index >= len(day_tasks):
        raise ValueError(f"No task at index {task_index} for {current_day}")

    task = day_tasks[task_index]

    logger.info(f"Content Agent: Creating content for task {task.task_id}")

    model_name = config.get("configurable", {}).get("model", OpenAIModel.GPT_4O)
    model = ChatOpenAI(model=model_name, temperature=0.7)

    system_prompt = make_content_system_prompt()
    user_prompt = make_content_user_prompt(
        task_id=task.task_id,
        title=task.title,
        description=task.description,
        content_type=task.content_type.value,
        learning_objectives=task.learning_objectives,
        learner_level=strategy.roadmap.current_level.value,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = model.invoke(messages, config)

    try:
        result = extract_json_from_response(response.content)

        content = LearningContent(
            content_id=result["content_id"],
            task_id=result["task_id"],
            title=result["title"],
            content_type=ContentType(result["content_type"]),
            content_body=result["content_body"],
            key_concepts=result["key_concepts"],
            resources=result.get("resources", []),
        )

        logger.info(f"Content created: {content.title}")
        return content

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse content response: {e}")
        raise ValueError(f"Content agent failed: {e}")


def quiz_agent(
    task_id: str,
    title: str,
    key_concepts: list[str],
    learner_level: str,
    config: RunnableConfig,
) -> Quiz:
    """
    Quiz generation agent that creates quizzes for learning content.

    Args:
        task_id: ID of the task
        title: Title of the content
        key_concepts: Key concepts to test
        learner_level: Current learner level
        config: Runtime configuration

    Returns:
        Quiz for the content
    """
    logger.info(f"Quiz Agent: Creating quiz for task {task_id}")

    model_name = config.get("configurable", {}).get("model", OpenAIModel.GPT_4O)
    model = ChatOpenAI(model=model_name, temperature=0.5)

    system_prompt = make_quiz_system_prompt()
    user_prompt = make_quiz_user_prompt(
        task_id=task_id,
        title=title,
        key_concepts=key_concepts,
        learner_level=learner_level,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = model.invoke(messages, config)

    try:
        result = extract_json_from_response(response.content)

        questions = [
            QuizQuestion(
                question_id=q["question_id"],
                question_type=QuestionType(q["question_type"]),
                question_text=q["question_text"],
                options=q.get("options", []),
                correct_answer=q["correct_answer"],
                explanation=q["explanation"],
                difficulty=SkillLevel(q["difficulty"]),
                related_concepts=q["related_concepts"],
            )
            for q in result["questions"]
        ]

        quiz = Quiz(
            quiz_id=result["quiz_id"],
            task_id=result["task_id"],
            title=result["title"],
            questions=questions,
            passing_score=result["passing_score"],
            time_limit_minutes=result.get("time_limit_minutes", 0),
        )

        logger.info(f"Quiz created: {quiz.title} ({len(questions)} questions)")
        return quiz

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse quiz response: {e}")
        raise ValueError(f"Quiz agent failed: {e}")


def execution_agent(state: HierarchicalAgentState, config: RunnableConfig) -> dict:
    """
    Execution layer agent that orchestrates content and quiz generation.

    This agent creates learning sessions by coordinating the content
    and quiz agents for each task.

    Args:
        state: Current hierarchical agent state
        config: Runtime configuration

    Returns:
        Updated state with new learning session
    """
    tactics = state["tactics_output"]
    strategy = state["strategy_output"]
    if tactics is None or strategy is None:
        raise ValueError("Execution agent requires strategy and tactics output")

    current_sessions = list(state["learning_sessions"])

    # Check if we've reached the limit
    if len(current_sessions) >= MAX_SESSIONS_FIRST_WEEK:
        logger.info(f"Reached maximum sessions ({MAX_SESSIONS_FIRST_WEEK})")
        return {"learning_sessions": current_sessions}

    # Get current task
    current_week = state["current_week"]
    current_day = state["current_day"]
    task_index = state["current_task_index"]

    week_plan = tactics.weekly_plans[current_week - 1]
    day_tasks = week_plan.daily_tasks.get(current_day, [])

    if task_index >= len(day_tasks):
        logger.info(f"No more tasks for {current_day}")
        return {"learning_sessions": current_sessions}

    task = day_tasks[task_index]

    logger.info("=" * 60)
    logger.info(f"EXECUTION LAYER: Session {len(current_sessions) + 1}/{MAX_SESSIONS_FIRST_WEEK}")
    logger.info(f"Week {current_week}, {current_day}, Task: {task.task_id}")
    logger.info("=" * 60)

    # Generate content
    content = content_agent(state, config)

    # Generate quiz
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

    # Update task index for next iteration
    new_task_index = task_index + 1
    new_day = current_day
    new_week = current_week

    # Move to next day if all tasks for current day are done
    if new_task_index >= len(day_tasks):
        day_keys = list(week_plan.daily_tasks.keys())
        current_day_idx = day_keys.index(current_day) if current_day in day_keys else 0

        if current_day_idx + 1 < len(day_keys):
            new_day = day_keys[current_day_idx + 1]
            new_task_index = 0
        else:
            # Move to next week if all days are done
            if current_week < len(tactics.weekly_plans):
                new_week = current_week + 1
                new_day = list(tactics.weekly_plans[new_week - 1].daily_tasks.keys())[0]
                new_task_index = 0

    return {
        "learning_sessions": current_sessions,
        "current_task_index": new_task_index,
        "current_day": new_day,
        "current_week": new_week,
    }


def should_continue_execution(state: HierarchicalAgentState) -> Literal["execute", "progress"]:
    """
    Determine whether to continue executing or move to progress reporting.

    Args:
        state: Current hierarchical agent state

    Returns:
        "execute" to continue or "progress" to create progress report
    """
    sessions = state["learning_sessions"]

    if len(sessions) < MAX_SESSIONS_FIRST_WEEK:
        tactics = state["tactics_output"]
        if tactics:
            current_week = state["current_week"]
            current_day = state["current_day"]
            task_index = state["current_task_index"]

            if current_week <= len(tactics.weekly_plans):
                week_plan = tactics.weekly_plans[current_week - 1]
                day_tasks = week_plan.daily_tasks.get(current_day, [])

                if task_index < len(day_tasks):
                    logger.info(f"Continuing execution: {len(sessions)}/{MAX_SESSIONS_FIRST_WEEK} sessions")
                    return "execute"

    logger.info("Moving to progress reporting")
    return "progress"


# =============================================================================
# Progress Monitoring Agent
# =============================================================================


def progress_agent(state: HierarchicalAgentState, config: RunnableConfig) -> dict:
    """
    Progress monitoring agent that creates a progress report.

    Args:
        state: Current hierarchical agent state
        config: Runtime configuration

    Returns:
        Updated state with progress report
    """
    logger.info("=" * 60)
    logger.info("PROGRESS MONITORING: Creating progress report")
    logger.info("=" * 60)

    strategy = state["strategy_output"]
    tactics = state["tactics_output"]
    sessions = state["learning_sessions"]

    if strategy is None or tactics is None:
        raise ValueError("Progress agent requires strategy and tactics output")

    model_name = config.get("configurable", {}).get("model", OpenAIModel.GPT_4O)
    model = ChatOpenAI(model=model_name, temperature=0.3)

    # Calculate sessions this week
    week_plan = tactics.weekly_plans[0] if tactics.weekly_plans else None
    total_tasks_week = 0
    if week_plan:
        for tasks in week_plan.daily_tasks.values():
            total_tasks_week += len(tasks)

    sessions_info = "\n".join(
        f"- {s.content.title}: クイズ {len(s.quiz.questions)}問"
        for s in sessions
    )

    system_prompt = make_progress_system_prompt()
    user_prompt = make_progress_user_prompt(
        learning_domain=strategy.learning_domain,
        target_level=strategy.roadmap.target_level.value,
        total_duration_weeks=strategy.roadmap.total_duration_weeks,
        total_modules=len(strategy.roadmap.modules),
        current_week=1,
        sessions_completed=len(sessions),
        sessions_this_week=sessions_info if sessions_info else "まだセッションなし",
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = model.invoke(messages, config)

    try:
        result = extract_json_from_response(response.content)

        metrics = ProgressMetrics(
            modules_completed=result["metrics"]["modules_completed"],
            total_modules=result["metrics"]["total_modules"],
            current_week=result["metrics"]["current_week"],
            tasks_completed_this_week=result["metrics"]["tasks_completed_this_week"],
            total_tasks_this_week=result["metrics"]["total_tasks_this_week"],
            average_quiz_score=result["metrics"]["average_quiz_score"],
            study_hours_logged=result["metrics"]["study_hours_logged"],
            streak_days=result["metrics"]["streak_days"],
            competencies_acquired=result["metrics"]["competencies_acquired"],
            on_track=result["metrics"]["on_track"],
        )

        progress_report = ProgressReport(
            report_id=result["report_id"],
            metrics=metrics,
            progress_summary=result["progress_summary"],
            achievements=result["achievements"],
            recommendations=result["recommendations"],
            curriculum_adjustment_needed=result["curriculum_adjustment_needed"],
            adjustment_reason=result.get("adjustment_reason", ""),
        )

        logger.info(f"Progress report created: {progress_report.report_id}")
        logger.info(f"On track: {metrics.on_track}")

        return {"progress_report": progress_report}

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse progress response: {e}")
        raise ValueError(f"Progress agent failed: {e}")


# =============================================================================
# Graph Construction
# =============================================================================


def create_learning_platform_graph() -> StateGraph:
    """
    Create the hierarchical personalized learning platform graph.

    The graph follows the hierarchical pattern:
    1. Strategy Agent: Creates learning roadmap
    2. Tactics Agent: Designs curriculum with daily tasks
    3. Execution Agents: Generate content and quizzes (loop)
    4. Progress Agent: Creates progress report

    Returns:
        Compiled StateGraph for the learning platform
    """
    logger.info("Creating hierarchical learning platform graph...")

    graph = StateGraph(HierarchicalAgentState)

    # Add nodes for each layer
    graph.add_node("strategy", strategy_agent)
    graph.add_node("tactics", tactics_agent)
    graph.add_node("execution", execution_agent)
    graph.add_node("progress", progress_agent)

    # Set entry point
    graph.set_entry_point("strategy")

    # Strategy -> Tactics
    graph.add_edge("strategy", "tactics")

    # Tactics -> Execution (first session)
    graph.add_edge("tactics", "execution")

    # Execution loop or progress
    graph.add_conditional_edges(
        "execution",
        should_continue_execution,
        {
            "execute": "execution",
            "progress": "progress",
        },
    )

    # Progress -> END
    graph.add_edge("progress", END)

    logger.info("Learning platform graph created successfully")
    return graph.compile()


# =============================================================================
# Main Entry Point
# =============================================================================


async def run_personalized_learning(
    learner_profile: LearnerProfile,
    model: str = OpenAIModel.GPT_4O,
) -> PersonalizedLearningPlan | None:
    """
    Run the hierarchical personalized learning agent system.

    This function orchestrates the entire learning platform using
    a hierarchical multi-agent system.

    Args:
        learner_profile: Profile of the learner
        model: The OpenAI model to use

    Returns:
        PersonalizedLearningPlan if successful, None otherwise
    """
    logger.info("=" * 80)
    logger.info("HIERARCHICAL PERSONALIZED LEARNING PLATFORM")
    logger.info("=" * 80)
    logger.info(f"Learner goal: {learner_profile.learning_goal}")
    logger.info(f"Available hours/week: {learner_profile.available_hours_per_week}")
    logger.info(f"Target duration: {learner_profile.target_duration_weeks} weeks")
    logger.info(f"Model: {model}")

    initial_state: HierarchicalAgentState = {
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

    graph = create_learning_platform_graph()
    config = RunnableConfig(configurable={"model": model})

    try:
        final_state = await graph.ainvoke(initial_state, config)

        strategy = final_state.get("strategy_output")
        tactics = final_state.get("tactics_output")
        sessions = final_state.get("learning_sessions", [])
        progress = final_state.get("progress_report")

        if strategy and tactics and progress:
            plan = PersonalizedLearningPlan(
                plan_id=f"plan_{uuid4().hex[:8]}",
                learner_profile=learner_profile,
                strategy=strategy,
                curriculum=tactics,
                first_week_sessions=sessions,
                progress_report=progress,
            )

            logger.info("=" * 80)
            logger.info("LEARNING PLAN CREATED SUCCESSFULLY")
            logger.info("=" * 80)
            return plan
        else:
            logger.warning("Learning plan incomplete")
            return None

    except Exception as e:
        logger.error(f"Learning platform failed: {str(e)}")
        raise
