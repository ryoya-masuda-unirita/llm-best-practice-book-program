"""Strategy Layer Module (戦略・プランニング層)."""

from langchain_core.runnables import RunnableConfig
from src.layer.base import BaseAgent
from src.model.model import HierarchicalAgentState, StrategyOutput
from src.prompt.prompt import (
    make_strategy_system_prompt,
    make_strategy_user_prompt,
)


class StrategyAgent(BaseAgent):
    """
    Strategy Layer Agent (戦略エージェント).

    Analyzes learner goals, assesses current skill levels, and creates
    a comprehensive learning roadmap as a blueprint for lower layers.
    """

    def __init__(self):
        super().__init__(layer_name="STRATEGY", agent_name="StrategyAgent")

    def execute(self, state: HierarchicalAgentState, config: RunnableConfig) -> dict:
        """Execute the strategy layer to create a learning roadmap."""
        self._log_layer_start("Creating learning roadmap (blueprint)")

        learner = state["learner_profile"]

        user_prompt = make_strategy_user_prompt(
            learning_goal=learner.learning_goal,
            current_knowledge=learner.current_knowledge,
            available_hours_per_week=learner.available_hours_per_week,
            target_duration_weeks=learner.target_duration_weeks,
            preferred_content_types=[ct.value for ct in learner.preferred_content_types],
        )

        try:
            strategy_output = self._invoke_with_structured_output(
                config, make_strategy_system_prompt(), user_prompt, StrategyOutput
            )

            self.logger.info(f"Learning domain: {strategy_output.learning_domain}")
            self.logger.info(f"Modules created: {len(strategy_output.roadmap.modules)}")
            self.logger.info(
                f"Level progression: {strategy_output.roadmap.current_level} -> {strategy_output.roadmap.target_level}"
            )

            return {"strategy_output": strategy_output}

        except Exception as e:
            self._handle_parse_error(e)
            raise ValueError(f"Strategy agent failed to produce valid output: {e}")


def strategy_agent_node(state: HierarchicalAgentState, config: RunnableConfig) -> dict:
    """LangGraph node function for the Strategy Layer."""
    return StrategyAgent().execute(state, config)
