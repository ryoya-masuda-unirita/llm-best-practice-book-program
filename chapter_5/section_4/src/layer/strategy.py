"""
Strategy Layer Module (戦略・プランニング層).

The Strategy Layer is the top of the hierarchy, responsible for:
- Interpreting user's goals and requirements
- Setting overall learning objectives and architecture
- Creating high-level learning roadmaps (blueprints)
- Not involving itself in implementation details

Reference: REFERENCE.md Section "戦略・プランニング層 (Strategy & Planning Layer)"
"""

from langchain_core.runnables import RunnableConfig

from src.layer.base import BaseAgent
from src.model.llm_pipeline_model import (
    HierarchicalAgentState,
    LearningModule,
    LearningModuleCategory,
    LearningRoadmap,
    SkillLevel,
    StrategyOutput,
)
from src.prompt.llm_pipeline_prompt import (
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

    def _parse_learning_module(self, data: dict) -> LearningModule:
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

    def _parse_strategy_output(self, result: dict) -> StrategyOutput:
        """Parse strategy output from JSON result."""
        roadmap_data = result["roadmap"]
        modules = [self._parse_learning_module(m) for m in roadmap_data["modules"]]

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
            result = self._invoke_and_parse(config, make_strategy_system_prompt(), user_prompt)
            strategy_output = self._parse_strategy_output(result)

            self.logger.info(f"Learning domain: {strategy_output.learning_domain}")
            self.logger.info(f"Modules created: {len(strategy_output.roadmap.modules)}")
            self.logger.info(
                f"Level progression: {strategy_output.roadmap.current_level} -> {strategy_output.roadmap.target_level}"
            )

            return {"strategy_output": strategy_output}

        except (KeyError, ValueError) as e:
            self._handle_parse_error(e)
            raise ValueError(f"Strategy agent failed to produce valid output: {e}")


def strategy_agent_node(state: HierarchicalAgentState, config: RunnableConfig) -> dict:
    """LangGraph node function for the Strategy Layer."""
    return StrategyAgent().execute(state, config)
