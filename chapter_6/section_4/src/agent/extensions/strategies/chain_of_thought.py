"""Chain of Thought strategy implementation."""

from src.agent.core.base import Action, ActionType, Tool
from src.agent.extensions.strategies.base_strategy import BaseStrategy


class ChainOfThoughtStrategy(BaseStrategy):
    """Sequential reasoning with step-by-step history building."""

    def __init__(self, model: str = "global.anthropic.claude-haiku-4-5-20251001-v1:0", max_iterations: int = 10):
        super().__init__("chain_of_thought", model, max_iterations)

    def think(self, goal: str, context: dict[str, object], available_tools: list[Tool]) -> Action:
        if self._iteration >= self.max_iterations:
            return Action(type=ActionType.FINAL_ANSWER, answer="Maximum iterations reached")

        history = self._build_history()
        tool_descriptions = "\n".join(f"- {t.name}: {t.description}" for t in available_tools)

        prompt = f"""You are a reasoning agent using Chain of Thought.

Goal: {goal}

Available Tools:
{tool_descriptions}

Previous Steps:
{history}

Think step by step. What should you do next?
If you need to use a tool, respond with: Tool: <tool_name>
If you have the final answer, respond with: Answer: <your_answer>
"""
        response = self._call_llm(prompt)
        return self._parse_action(response, available_tools)

    def _build_history(self) -> str:
        if not self._steps:
            return "No previous steps."
        lines = []
        for step in self._steps:
            lines.append(f"Step {step.iteration + 1}: {step.action}")
            if step.thought:
                lines.append(f"  Thought: {step.thought}")
            if step.result:
                lines.append(f"  Result: {step.result}")
        return "\n".join(lines)
