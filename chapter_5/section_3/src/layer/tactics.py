"""Tactics Layer Module (戦術・マネジメント層)."""

from langchain_core.runnables import RunnableConfig
from src.layer.base import BaseAgent
from src.model.model import HierarchicalAgentState, TacticsOutput
from src.prompt.prompt import (
    make_tactics_system_prompt,
    make_tactics_user_prompt,
)


class TacticsAgent(BaseAgent):
    """
    Tactics Layer Agent (戦術エージェント).

    Bridges strategy and execution by transforming roadmaps into
    weekly themes and daily actionable tasks.
    """

    def __init__(self):
        super().__init__(layer_name="TACTICS", agent_name="TacticsAgent")

    def _format_modules_for_prompt(self, strategy) -> str:
        """Format modules list for the user prompt."""
        return "\n".join(
            f"- {m.module_id}: {m.name} ({m.category.value}) - {m.estimated_hours}時間"
            for m in strategy.roadmap.modules
        )

    def _format_milestones_for_prompt(self, strategy) -> str:
        """Format milestones list for the user prompt."""
        return "\n".join(f"- {ms}" for ms in strategy.roadmap.milestones)

    def execute(self, state: HierarchicalAgentState, config: RunnableConfig) -> dict:
        """Execute the tactics layer to create detailed curriculum."""
        self._log_layer_start("Designing curriculum (sub-task assignment)")

        strategy = state["strategy_output"]
        if strategy is None:
            raise ValueError("Tactics agent requires strategy output from upper layer")

        user_prompt = make_tactics_user_prompt(
            learning_domain=strategy.learning_domain,
            goal_summary=strategy.roadmap.goal_summary,
            current_level=strategy.roadmap.current_level.value,
            target_level=strategy.roadmap.target_level.value,
            total_duration_weeks=strategy.roadmap.total_duration_weeks,
            modules=self._format_modules_for_prompt(strategy),
            milestones=self._format_milestones_for_prompt(strategy),
            recommended_study_hours_per_week=strategy.recommended_study_hours_per_week,
            learning_style_notes=strategy.learning_style_notes,
        )

        try:
            tactics_output = self._invoke_with_structured_output(
                config, make_tactics_system_prompt(), user_prompt, TacticsOutput
            )

            self.logger.info(f"Weekly plans created: {len(tactics_output.weekly_plans)}")

            return {
                "tactics_output": tactics_output,
                "current_week": 1,
                "current_day": "day1",
                "current_task_index": 0,
                "learning_sessions": [],
            }

        except Exception as e:
            self._handle_parse_error(e)
            raise ValueError(f"Tactics agent failed to produce valid output: {e}")


def tactics_agent_node(state: HierarchicalAgentState, config: RunnableConfig) -> dict:
    """LangGraph node function for the Tactics Layer."""
    return TacticsAgent().execute(state, config)
