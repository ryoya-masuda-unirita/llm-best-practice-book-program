"""Reflection Layer Module (自己評価・省察層)."""

from langchain_core.runnables import RunnableConfig
from src.layer.base import BaseAgent
from src.model.model import HierarchicalAgentState, ProgressReport
from src.prompt.prompt import (
    make_progress_system_prompt,
    make_progress_user_prompt,
)


class ReflectionAgent(BaseAgent):
    """
    Reflection Layer Agent (自己評価・省察エージェント).

    Acts as an independent quality auditor, monitoring execution outputs
    and evaluating their alignment with the original strategy and goals.
    """

    def __init__(self):
        super().__init__(layer_name="REFLECTION", agent_name="ReflectionAgent")

    def _summarize_sessions(self, state: HierarchicalAgentState) -> str:
        """Summarize learning sessions for evaluation prompt."""
        sessions = state["learning_sessions"]
        if not sessions:
            return "まだセッションなし"

        return "\n".join(
            f"- {s.content.title}: キーコンセプト{len(s.content.key_concepts)}個, クイズ{len(s.quiz.questions)}問"
            for s in sessions
        )

    def execute(self, state: HierarchicalAgentState, config: RunnableConfig) -> dict:
        """Evaluate execution outputs and create progress report."""
        self._log_layer_start("Evaluating execution outputs")

        strategy = state["strategy_output"]
        tactics = state["tactics_output"]
        sessions = state["learning_sessions"]

        if strategy is None or tactics is None:
            raise ValueError("Reflection agent requires strategy and tactics output")

        user_prompt = make_progress_user_prompt(
            learning_domain=strategy.learning_domain,
            target_level=strategy.roadmap.target_level.value,
            total_duration_weeks=strategy.roadmap.total_duration_weeks,
            total_modules=len(strategy.roadmap.modules),
            current_week=1,
            sessions_completed=len(sessions),
            sessions_this_week=self._summarize_sessions(state),
        )

        try:
            progress_report = self._invoke_with_structured_output(
                config, make_progress_system_prompt(), user_prompt, ProgressReport
            )

            self.logger.info(f"Progress report created: {progress_report.report_id}")
            self.logger.info(f"On track: {progress_report.metrics.on_track}")

            if progress_report.curriculum_adjustment_needed:
                self.logger.warning(f"Curriculum adjustment needed: {progress_report.adjustment_reason}")
            else:
                self.logger.info("Execution aligned with strategic goals")

            return {"progress_report": progress_report}

        except Exception as e:
            self._handle_parse_error(e)
            raise ValueError(f"Reflection agent failed: {e}")


def reflection_agent_node(state: HierarchicalAgentState, config: RunnableConfig) -> dict:
    """LangGraph node function for the Reflection Layer."""
    return ReflectionAgent().execute(state, config)
