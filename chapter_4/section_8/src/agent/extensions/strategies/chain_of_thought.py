"""Chain-of-Thought strategy: Sequential reasoning steps."""

from src.agent.core.base import Action, ActionType, Tool, ToolResult
from src.agent.extensions.strategies.base_strategy import BaseStrategy
from src.client.llm_client import GeminiModel


class ChainOfThoughtStrategy(BaseStrategy):
    """Chain-of-Thought strategy: Sequential reasoning steps."""

    def __init__(self, model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH, max_steps: int = 10):
        super().__init__("Chain-of-Thought", model, max_steps)

    def _build_history(self, context: dict[str, object]) -> str:
        """Build history from actions and observations stored in memory."""
        actions = context.get("actions", [])
        observations = context.get("observations", [])

        if not isinstance(actions, list) or not actions:
            return ""

        history_parts = []
        for i, action in enumerate(actions):
            if isinstance(action, Action):
                step_info = f"Step {i + 1}:"
                if action.thought:
                    step_info += f" Thought: {action.thought}"
                if action.type == ActionType.TOOL_CALL:
                    step_info += f" Action: Called {action.tool_name} with {action.params}"
                    if i < len(observations):
                        obs = observations[i]
                        if isinstance(obs, ToolResult):
                            step_info += f" Result: {obs.data}" if obs.success else f" Error: {obs.error}"
                        else:
                            step_info += f" Result: {obs}"
                history_parts.append(step_info)

        return "\n".join(history_parts)

    def think(self, goal: str, context: dict[str, object], available_tools: list[Tool]) -> Action:
        self.iteration += 1
        if self.iteration > self.max_iterations:
            return Action(type=ActionType.FINAL_ANSWER, answer="Maximum reasoning steps reached")

        tools_desc = "\n".join([f"- {t.name}: {t.description}" for t in available_tools])
        history = self._build_history(context)

        prompt = f"""Goal: {goal}
Available tools: {tools_desc}
{f"Previous steps:\n{history}" if history else ""}

Think step-by-step. You can:
1. TOOL: <tool_name> | PARAMS: {{"param": "value"}}
2. ANSWER: <your_answer>

Provide your reasoning and action:"""

        return self._parse_action(self._call_llm(prompt))
