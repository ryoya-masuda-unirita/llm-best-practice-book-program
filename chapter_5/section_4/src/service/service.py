"""Hierarchical Personalized Learning Platform Service."""

from typing import Literal
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from src.client.llm_client import OpenAIModel
from src.layer.execution import MAX_SESSIONS_FIRST_WEEK, execution_agent_node
from src.layer.reflection import reflection_agent_node
from src.layer.strategy import strategy_agent_node
from src.layer.tactics import tactics_agent_node
from src.logger import make_logger
from src.model.model import (
    HierarchicalAgentState,
    LearnerProfile,
    PersonalizedLearningPlan,
)

logger = make_logger(__name__)


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


def should_continue_execution(state: HierarchicalAgentState) -> Literal["execute", "reflect"]:
    """Determine whether to continue executing or move to reflection."""
    sessions = state["learning_sessions"]

    if len(sessions) < MAX_SESSIONS_FIRST_WEEK and _has_more_tasks(state):
        logger.info(f"Continuing execution: {len(sessions)}/{MAX_SESSIONS_FIRST_WEEK} sessions")
        return "execute"

    logger.info("Moving to Reflection Layer for evaluation")
    return "reflect"


def create_learning_platform_graph() -> StateGraph:
    """Create the hierarchical personalized learning platform graph."""
    logger.info("Creating hierarchical learning platform graph...")

    graph = StateGraph(HierarchicalAgentState)

    graph.add_node("strategy", strategy_agent_node)
    graph.add_node("tactics", tactics_agent_node)
    graph.add_node("execution", execution_agent_node)
    graph.add_node("reflection", reflection_agent_node)

    graph.set_entry_point("strategy")
    graph.add_edge("strategy", "tactics")
    graph.add_edge("tactics", "execution")
    graph.add_conditional_edges(
        "execution",
        should_continue_execution,
        {"execute": "execution", "reflect": "reflection"},
    )
    graph.add_edge("reflection", END)

    logger.info("Learning platform graph created successfully")
    return graph.compile()


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
        logger.warning("Learning plan incomplete - missing layer outputs")
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
    logger.info("4-Layer Architecture: Strategy -> Tactics -> Execution -> Reflection")
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
            logger.info("All layers completed: Strategy -> Tactics -> Execution -> Reflection")
            logger.info("=" * 80)

        return plan

    except Exception as e:
        logger.error(f"Learning platform failed: {str(e)}")
        raise
