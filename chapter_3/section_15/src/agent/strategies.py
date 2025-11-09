"""Thinking strategies for AI agents (Strategy pattern)."""

import json
from typing import Any

from src.agent.base import Action, ActionType, Strategy, Tool
from src.client.llm_client import GeminiModel, google_genai_client
from src.logger import make_logger

logger = make_logger(__name__)


class BaseStrategy(Strategy):
    """Base strategy with common LLM interaction logic."""

    def __init__(self, name: str, model: str = GeminiModel.GEMINI_2_5_FLASH, max_iterations: int = 10):
        super().__init__(name)
        self.model = model
        self.max_iterations = max_iterations
        self.iteration = 0

    def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt."""
        try:
            response = google_genai_client.models.generate_content(model=self.model, contents=prompt)
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"

    def _parse_action(self, response: str) -> Action:
        """Parse LLM response to extract action."""
        lines = [x.strip() for x in response.strip().split("\n") if x.strip()]
        thought = ""

        for i, line in enumerate(lines):
            if line.startswith("TOOL:"):
                thought = "\n".join(lines[:i])
                parts = line[5:].split("|")
                tool_name = parts[0].strip()
                params = {}
                if len(parts) > 1 and "PARAMS:" in parts[1]:
                    try:
                        params = json.loads(parts[1].split("PARAMS:")[1].strip())
                    except Exception as e:
                        logger.error(e)
                        pass
                return Action(type=ActionType.TOOL_CALL, tool_name=tool_name, params=params, thought=thought)

            if line.startswith("ANSWER:"):
                thought = "\n".join(lines[:i])
                return Action(type=ActionType.FINAL_ANSWER, answer=line[7:].strip(), thought=thought)

        return Action(type=ActionType.THINK, thought=response.strip())

    def update_context(self, context: dict[str, Any], action: Action, result: Any) -> dict[str, Any]:
        """Update context with step information."""
        context = context.copy()
        context.setdefault("steps", []).append(
            {
                "iteration": self.iteration,
                "thought": action.thought,
                "action": action.type.value,
                "result": result,
            }
        )
        return context


class ChainOfThoughtStrategy(BaseStrategy):
    """Chain-of-Thought strategy: Sequential reasoning steps."""

    def __init__(self, model: str = GeminiModel.GEMINI_2_5_FLASH, max_steps: int = 10):
        super().__init__("Chain-of-Thought", model, max_steps)

    def think(self, goal: str, context: dict[str, Any], available_tools: list[Tool]) -> Action:
        self.iteration += 1
        if self.iteration > self.max_iterations:
            return Action(type=ActionType.FINAL_ANSWER, answer="Maximum reasoning steps reached")

        tools_desc = "\n".join([f"- {t.name}: {t.description}" for t in available_tools])
        history = "\n".join([f"Step {s['iteration']}: {s.get('thought', 'N/A')}" for s in context.get("steps", [])])

        prompt = f"""Goal: {goal}
Available tools: {tools_desc}
{f"Previous steps: {history}" if history else ""}

Think step-by-step. You can:
1. TOOL: <tool_name> | PARAMS: <json_params>
2. ANSWER: <your_answer>

Provide your reasoning and action:"""

        return self._parse_action(self._call_llm(prompt))


class ReActStrategy(BaseStrategy):
    """ReAct strategy: Reasoning and Acting in sync."""

    def __init__(self, model: str = GeminiModel.GEMINI_2_5_FLASH, max_iterations: int = 10):
        super().__init__("ReAct", model, max_iterations)

    def think(self, goal: str, context: dict[str, Any], available_tools: list[Tool]) -> Action:
        self.iteration += 1
        if self.iteration > self.max_iterations:
            return Action(type=ActionType.FINAL_ANSWER, answer="Maximum iterations reached")

        tools_desc = "\n".join([f"- {t.name}: {t.description}" for t in available_tools])
        trajectory = "\n".join(
            [
                f"Iteration {s['iteration']}:\nThought: {s.get('thought')}\nAction: {s['action']}\nObservation: {s.get('result')}"
                for s in context.get("steps", [])
            ]
        )

        prompt = f"""Goal: {goal}
Available Tools: {tools_desc}
{f"Trajectory: {trajectory}" if trajectory else ""}

Use this format:
Thought: <your reasoning>
Action: TOOL: <tool_name> | PARAMS: <json_params>
or
Thought: <your final reasoning>
Action: ANSWER: <final_answer>

Provide your Thought and Action:"""

        return self._parse_action(self._call_llm(prompt))


class TreeOfThoughtStrategy(BaseStrategy):
    """Tree-of-Thought strategy: Explores multiple reasoning paths."""

    def __init__(self, model: str = GeminiModel.GEMINI_2_5_FLASH, max_depth: int = 3, branch_factor: int = 3):
        super().__init__("Tree-of-Thought", model, max_depth)
        self.branch_factor = branch_factor
        self.thought_tree: list[dict[str, Any]] = []

    def think(self, goal: str, context: dict[str, Any], available_tools: list[Tool]) -> Action:
        if self.iteration >= self.max_iterations:
            best_path = " -> ".join(
                [max(node["alternatives"], key=lambda x: x["score"])["thought"] for node in self.thought_tree]
            )
            return Action(type=ActionType.FINAL_ANSWER, answer=f"Best solution: {best_path}")

        # Generate and evaluate alternatives
        alternatives = self._generate_alternatives(goal)
        evaluated = [{"thought": alt, "score": self._evaluate(alt, goal)} for alt in alternatives]
        self.thought_tree.append({"depth": self.iteration, "alternatives": evaluated})

        best = max(evaluated, key=lambda x: x["score"])
        self.iteration += 1
        return Action(type=ActionType.THINK, thought=f"Exploring: {best['thought']} (score: {best['score']})")

    def _generate_alternatives(self, goal: str) -> list[str]:
        """Generate alternative thoughts."""
        prompt = f"Generate {self.branch_factor} different approaches to solve: {goal}\n\nProvide {self.branch_factor} distinct thoughts, one per line:"
        try:
            lines = [x.strip() for x in self._call_llm(prompt).split("\n") if x.strip()]
            return lines[: self.branch_factor]
        except Exception as e:
            logger.error(e)
            return [f"Alternative approach {i + 1}" for i in range(self.branch_factor)]

    def _evaluate(self, thought: str, goal: str) -> float:
        """Evaluate a thought."""
        try:
            prompt = f"Rate this approach for solving the goal (0-10):\nGoal: {goal}\nApproach: {thought}\n\nProvide only a number 0-10:"
            return float(self._call_llm(prompt).strip())
        except Exception as e:
            logger.error(e)
            return 5.0
