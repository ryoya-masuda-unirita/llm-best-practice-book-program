"""ReAct (Reasoning + Acting) strategy implementation."""

from src.agent.core.base import Action, ActionType, Tool
from src.agent.extensions.strategies.base_strategy import BaseStrategy


class ReActStrategy(BaseStrategy):
    """ReAct pattern with interleaved thought/action/observation cycles."""

    def __init__(self, model: str = "gemini-2.5-flash", max_iterations: int = 10):
        super().__init__("react", model, max_iterations)

    def think(self, goal: str, context: dict[str, object], available_tools: list[Tool]) -> Action:
        if self._iteration >= self.max_iterations:
            return Action(type=ActionType.FINAL_ANSWER, answer="Maximum iterations reached")

        trajectory = self._build_trajectory()
        tool_descriptions = "\n".join(f"- {t.name}: {t.description}" for t in available_tools)

        prompt = f"""You are a ReAct agent (Reasoning + Acting).

Goal: {goal}

Available Tools:
{tool_descriptions}

Previous Trajectory:
{trajectory}

Follow the Thought -> Action -> Observation cycle.
Thought: Think about what to do next
Action: Use a tool or provide final answer
If you need to use a tool, respond with: Tool: <tool_name>
If you have the final answer, respond with: Answer: <your_answer>
"""
        response = self._call_llm(prompt)
        return self._parse_action(response, available_tools)

    def _build_trajectory(self) -> str:
        if not self._steps:
            return "No previous steps."
        lines = []
        for step in self._steps:
            lines.append(f"Iteration {step.iteration + 1}:")
            if step.thought:
                lines.append(f"  Thought: {step.thought}")
            lines.append(f"  Action: {step.action}")
            if step.result:
                lines.append(f"  Observation: {step.result}")
        return "\n".join(lines)
