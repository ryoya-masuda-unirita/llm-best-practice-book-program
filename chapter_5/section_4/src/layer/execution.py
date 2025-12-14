"""
Execution Layer Module (実行層).

The Execution Layer performs concrete tasks, responsible for:
- Content generation and quiz creation
- Operating external tools (LLM for content generation)
- Faithfully executing assigned tasks from the Tactics Layer
- Reporting results back to upper layers

Reference: REFERENCE.md Section "実行層 (Execution Layer)"
"""

from uuid import uuid4

from langchain_core.runnables import RunnableConfig

from src.layer.base import BaseAgent
from src.model.llm_pipeline_model import (
    ContentType,
    DailyTask,
    HierarchicalAgentState,
    LearningContent,
    LearningSession,
    QuestionType,
    Quiz,
    QuizQuestion,
    SkillLevel,
    TacticsOutput,
)
from src.prompt.llm_pipeline_prompt import (
    make_content_system_prompt,
    make_content_user_prompt,
    make_quiz_system_prompt,
    make_quiz_user_prompt,
)

# =============================================================================
# Constants
# =============================================================================

MAX_SESSIONS_FIRST_WEEK = 5


# =============================================================================
# Content Generation Agent
# =============================================================================


class ContentAgent(BaseAgent):
    """
    Content Generation Agent (コンテンツ生成エージェント).

    Generates learning content for assigned tasks, tailored to learner level.
    """

    def __init__(self):
        super().__init__(layer_name="EXECUTION", agent_name="ContentAgent")

    def _parse_learning_content(self, result: dict, task: DailyTask) -> LearningContent:
        """Parse learning content from JSON result with safe defaults."""
        return LearningContent(
            content_id=result.get("content_id", f"content_{task.task_id}"),
            task_id=result.get("task_id", task.task_id),
            title=result.get("title", task.title),
            content_type=self._safe_enum_parse(ContentType, result.get("content_type", "article"), ContentType.ARTICLE),
            content_body=result.get("content_body", ""),
            key_concepts=result.get("key_concepts", task.learning_objectives or []),
            resources=result.get("resources", []),
        )

    def execute(self, task: DailyTask, learner_level: str, config: RunnableConfig) -> LearningContent:
        """Generate learning content for a specific task."""
        self.logger.info(f"Creating content for task: {task.task_id}")

        user_prompt = make_content_user_prompt(
            task_id=task.task_id,
            title=task.title,
            description=task.description,
            content_type=task.content_type.value,
            learning_objectives=task.learning_objectives,
            learner_level=learner_level,
        )

        try:
            result = self._invoke_and_parse(config, make_content_system_prompt(), user_prompt)
            content = self._parse_learning_content(result, task)
            self.logger.info(f"Content created: {content.title}")
            return content

        except (KeyError, ValueError) as e:
            self._handle_parse_error(e)
            raise ValueError(f"Content agent failed: {e}")


# =============================================================================
# Quiz Generation Agent
# =============================================================================


class QuizAgent(BaseAgent):
    """
    Quiz Generation Agent (クイズ生成エージェント).

    Creates assessment quizzes based on key concepts from content.
    """

    def __init__(self):
        super().__init__(layer_name="EXECUTION", agent_name="QuizAgent")

    def _parse_quiz_question(self, data: dict, index: int, key_concepts: list[str]) -> QuizQuestion:
        """Parse a quiz question from JSON data with safe defaults."""
        return QuizQuestion(
            question_id=data.get("question_id", f"q_{index + 1:03d}"),
            question_type=self._safe_enum_parse(
                QuestionType, data.get("question_type", "multiple_choice"), QuestionType.MULTIPLE_CHOICE
            ),
            question_text=data.get("question_text", ""),
            options=data.get("options", []),
            correct_answer=data.get("correct_answer", ""),
            explanation=data.get("explanation", ""),
            difficulty=self._safe_enum_parse(SkillLevel, data.get("difficulty", "beginner"), SkillLevel.BEGINNER),
            related_concepts=data.get("related_concepts", key_concepts or []),
        )

    def _parse_quiz(self, result: dict, task_id: str, title: str, key_concepts: list[str]) -> Quiz:
        """Parse quiz from JSON result with safe defaults."""
        questions = [self._parse_quiz_question(q, i, key_concepts) for i, q in enumerate(result.get("questions", []))]

        return Quiz(
            quiz_id=result.get("quiz_id", f"quiz_{task_id}"),
            task_id=result.get("task_id", task_id),
            title=result.get("title", f"Quiz: {title}"),
            questions=questions,
            passing_score=result.get("passing_score", 70),
            time_limit_minutes=result.get("time_limit_minutes", 0),
        )

    def execute(
        self,
        task_id: str,
        title: str,
        key_concepts: list[str],
        learner_level: str,
        config: RunnableConfig,
    ) -> Quiz:
        """Generate a quiz for learning content."""
        self.logger.info(f"Creating quiz for task: {task_id}")

        user_prompt = make_quiz_user_prompt(
            task_id=task_id,
            title=title,
            key_concepts=key_concepts,
            learner_level=learner_level,
        )

        try:
            result = self._invoke_and_parse(config, make_quiz_system_prompt(), user_prompt)
            quiz = self._parse_quiz(result, task_id, title, key_concepts)
            self.logger.info(f"Quiz created: {quiz.title} ({len(quiz.questions)} questions)")
            return quiz

        except (KeyError, ValueError) as e:
            self._handle_parse_error(e)
            raise ValueError(f"Quiz agent failed: {e}")


# =============================================================================
# Execution Coordinator
# =============================================================================


class ExecutionCoordinator(BaseAgent):
    """
    Execution Layer Coordinator (実行層コーディネーター).

    Orchestrates content and quiz generation for each learning task.
    """

    def __init__(self):
        super().__init__(layer_name="EXECUTION", agent_name="Coordinator")
        self.content_agent = ContentAgent()
        self.quiz_agent = QuizAgent()

    def _get_current_task(self, state: HierarchicalAgentState) -> DailyTask | None:
        """Get the current task from state, or None if no more tasks."""
        tactics = state["tactics_output"]
        if tactics is None:
            return None

        try:
            week_plan = tactics.weekly_plans[state["current_week"] - 1]
            day_tasks = week_plan.daily_tasks.get(state["current_day"], [])
            if state["current_task_index"] < len(day_tasks):
                return day_tasks[state["current_task_index"]]
        except (IndexError, KeyError):
            pass
        return None

    def _calculate_next_task_position(
        self,
        state: HierarchicalAgentState,
        tactics: TacticsOutput,
    ) -> tuple[int, str, int]:
        """Calculate the next task position (week, day, index) after current task."""
        current_week = state["current_week"]
        current_day = state["current_day"]
        next_task_index = state["current_task_index"] + 1

        week_plan = tactics.weekly_plans[current_week - 1]
        day_tasks = week_plan.daily_tasks.get(current_day, [])

        # More tasks in current day?
        if next_task_index < len(day_tasks):
            return current_week, current_day, next_task_index

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

        return current_week, current_day, next_task_index

    def _create_learning_session(
        self,
        task: DailyTask,
        learner_level: str,
        config: RunnableConfig,
    ) -> LearningSession:
        """Create a learning session with content and quiz."""
        content = self.content_agent.execute(task, learner_level, config)
        quiz = self.quiz_agent.execute(
            task_id=task.task_id,
            title=content.title,
            key_concepts=content.key_concepts,
            learner_level=learner_level,
            config=config,
        )

        return LearningSession(
            session_id=f"session_{uuid4().hex[:8]}",
            task_id=task.task_id,
            content=content,
            quiz=quiz,
            feedback=None,
        )

    def execute(self, state: HierarchicalAgentState, config: RunnableConfig) -> dict:
        """Execute the current task by coordinating content and quiz generation."""
        tactics = state["tactics_output"]
        strategy = state["strategy_output"]
        if tactics is None or strategy is None:
            raise ValueError("Execution requires strategy and tactics output")

        current_sessions = list(state["learning_sessions"])

        # Check if max sessions reached
        if len(current_sessions) >= MAX_SESSIONS_FIRST_WEEK:
            self.logger.info(f"Reached maximum sessions ({MAX_SESSIONS_FIRST_WEEK})")
            return {"learning_sessions": current_sessions}

        # Get current task
        task = self._get_current_task(state)
        if task is None:
            self.logger.info(f"No more tasks for {state['current_day']}")
            return {"learning_sessions": current_sessions}

        self._log_layer_start(f"Session {len(current_sessions) + 1}/{MAX_SESSIONS_FIRST_WEEK}")
        self.logger.info(f"Week {state['current_week']}, {state['current_day']}, Task: {task.task_id}")

        # Create session
        session = self._create_learning_session(
            task=task,
            learner_level=strategy.roadmap.current_level.value,
            config=config,
        )
        current_sessions.append(session)
        self.logger.info(f"Session created: {session.session_id}")

        # Calculate next position
        new_week, new_day, new_task_index = self._calculate_next_task_position(state, tactics)

        return {
            "learning_sessions": current_sessions,
            "current_task_index": new_task_index,
            "current_day": new_day,
            "current_week": new_week,
        }


def execution_agent_node(state: HierarchicalAgentState, config: RunnableConfig) -> dict:
    """LangGraph node function for the Execution Layer."""
    return ExecutionCoordinator().execute(state, config)
