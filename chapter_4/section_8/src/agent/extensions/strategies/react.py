"""ReAct strategy: Reasoning and Acting in sync."""

from src.agent.core.base import Action, ActionType, Tool, ToolResult
from src.agent.extensions.strategies.base_strategy import BaseStrategy
from src.client.llm_client import AnthropicModel


class ReActStrategy(BaseStrategy):
    """ReAct strategy: Reasoning and Acting in sync."""

    def __init__(self, model: AnthropicModel = AnthropicModel.CLAUDE_HAIKU_4_5, max_iterations: int = 10):
        super().__init__("ReAct", model, max_iterations)

    def _build_trajectory(self, context: dict[str, object]) -> str:
        """Build trajectory from actions and observations stored in memory."""
        actions = context.get("actions", [])
        observations = context.get("observations", [])

        if not isinstance(actions, list) or not actions:
            return ""

        trajectory_parts = []
        for i, action in enumerate(actions):
            if isinstance(action, Action):
                entry = f"Iteration {i + 1}:\n"
                entry += f"Thought: {action.thought or 'N/A'}\n"
                if action.type == ActionType.TOOL_CALL:
                    entry += f"Action: {action.tool_name}({action.params})\n"
                    if i < len(observations):
                        obs = observations[i]
                        if isinstance(obs, ToolResult):
                            entry += f"Observation: {obs.data}" if obs.success else f"Observation: Error - {obs.error}"
                        else:
                            entry += f"Observation: {obs}"
                trajectory_parts.append(entry)

        return "\n".join(trajectory_parts)

    def think(self, goal: str, context: dict[str, object], available_tools: list[Tool]) -> Action:
        self.iteration += 1
        if self.iteration > self.max_iterations:
            return Action(type=ActionType.FINAL_ANSWER, answer="Maximum iterations reached")

        tools_desc = "\n".join([f"- {t.name}: {t.description}" for t in available_tools])
        trajectory = self._build_trajectory(context)

        prompt = f"""Goal: {goal}
Available Tools: {tools_desc}
{f"Trajectory:\n{trajectory}" if trajectory else ""}

Use this format:
Thought: <your reasoning>
Action: TOOL: <tool_name> | PARAMS: {{"param": "value"}}
or
Thought: <your final reasoning>
Action: ANSWER: <final_answer>

Provide your Thought and Action:"""

        return self._parse_action(self._call_llm(prompt))
