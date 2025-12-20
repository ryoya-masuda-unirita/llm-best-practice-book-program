"""Thinking strategies for AI agents (Strategy pattern)."""

import json
from dataclasses import dataclass, field
from typing import TypeVar, overload

from google.genai.types import GenerateContentConfig
from pydantic import BaseModel
from src.agent.base import Action, ActionType, Strategy, Tool, ToolResult
from src.client.llm_client import GeminiModel, google_genai_client
from src.logger import make_logger

T = TypeVar("T", bound=BaseModel)

logger = make_logger(__name__)


@dataclass
class ThoughtNode:
    """A node in the thought tree for Tree-of-Thought strategy."""

    thought: str
    score: float


@dataclass
class ThoughtTreeLevel:
    """A level in the thought tree."""

    depth: int
    alternatives: list[ThoughtNode] = field(default_factory=list)


class BaseStrategy(Strategy):
    """Base strategy with common LLM interaction logic."""

    def __init__(self, name: str, model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH, max_iterations: int = 10):
        super().__init__(name)
        self.model = model
        self.max_iterations = max_iterations
        self.iteration = 0

    @overload
    def _call_llm(self, prompt: str) -> str: ...

    @overload
    def _call_llm(self, prompt: str, *, response_schema: type[T]) -> T: ...

    def _call_llm(self, prompt: str, *, response_schema: type[T] | None = None) -> str | T:
        """Call LLM with prompt.

        Args:
            prompt: The prompt to send to the LLM.
            response_schema: Optional Pydantic model class for structured output.
                When provided, the response will be validated and returned as
                an instance of this model.

        Returns:
            If response_schema is None, returns the raw text response.
            If response_schema is provided, returns a validated instance of that model.
        """
        try:
            config = None
            if response_schema is not None:
                config = GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                )

            response = google_genai_client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )

            if response_schema is not None:
                return response_schema.model_validate_json(response.text)

            return response.text
        except Exception as e:
            if response_schema is not None:
                raise
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
                params: dict[str, str | int | float | bool | list | dict | None] = {}
                if len(parts) > 1 and "PARAMS:" in parts[1]:
                    try:
                        params = json.loads(parts[1].split("PARAMS:")[1].strip())
                    except Exception as e:
                        logger.error(e)
                return Action(type=ActionType.TOOL_CALL, tool_name=tool_name, params=params, thought=thought)

            if line.startswith("ANSWER:"):
                thought = "\n".join(lines[:i])
                return Action(type=ActionType.FINAL_ANSWER, answer=line[7:].strip(), thought=thought)

        return Action(type=ActionType.THINK, thought=response.strip())

    def update_context(self, context: dict[str, object], action: Action, result: ToolResult | str) -> dict[str, object]:
        """Update context with step information."""
        context = context.copy()
        steps = context.get("steps")
        if not isinstance(steps, list):
            steps = []
        steps.append(
            {
                "iteration": self.iteration,
                "thought": action.thought,
                "action": action.type.value,
                "result": result,
            }
        )
        context["steps"] = steps
        return context


class ChainOfThoughtStrategy(BaseStrategy):
    """Chain-of-Thought strategy: Sequential reasoning steps."""

    def __init__(self, model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH, max_steps: int = 10):
        super().__init__("Chain-of-Thought", model, max_steps)

    def think(self, goal: str, context: dict[str, object], available_tools: list[Tool]) -> Action:
        self.iteration += 1
        if self.iteration > self.max_iterations:
            return Action(type=ActionType.FINAL_ANSWER, answer="Maximum reasoning steps reached")

        tools_desc = "\n".join([f"- {t.name}: {t.description}" for t in available_tools])
        steps = context.get("steps", [])
        history = ""
        if isinstance(steps, list):
            history = "\n".join(
                [f"Step {s.get('iteration')}: {s.get('thought', 'N/A')}" for s in steps if isinstance(s, dict)]
            )

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

    def __init__(self, model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH, max_iterations: int = 10):
        super().__init__("ReAct", model, max_iterations)

    def think(self, goal: str, context: dict[str, object], available_tools: list[Tool]) -> Action:
        self.iteration += 1
        if self.iteration > self.max_iterations:
            return Action(type=ActionType.FINAL_ANSWER, answer="Maximum iterations reached")

        tools_desc = "\n".join([f"- {t.name}: {t.description}" for t in available_tools])
        steps = context.get("steps", [])
        trajectory = ""
        if isinstance(steps, list):
            trajectory = "\n".join(
                [
                    f"Iteration {s.get('iteration')}:\nThought: {s.get('thought')}\nAction: {s.get('action')}\nObservation: {s.get('result')}"
                    for s in steps
                    if isinstance(s, dict)
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

    def __init__(self, model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH, max_depth: int = 3, branch_factor: int = 3):
        super().__init__("Tree-of-Thought", model, max_depth)
        self.branch_factor = branch_factor
        self.thought_tree: list[ThoughtTreeLevel] = []

    def think(self, goal: str, context: dict[str, object], available_tools: list[Tool]) -> Action:
        if self.iteration >= self.max_iterations:
            best_path = " -> ".join(
                [
                    max(node.alternatives, key=lambda x: x.score).thought
                    for node in self.thought_tree
                    if node.alternatives
                ]
            )
            return Action(type=ActionType.FINAL_ANSWER, answer=f"Best solution: {best_path}")

        # Generate and evaluate alternatives
        alternatives = self._generate_alternatives(goal)
        evaluated = [ThoughtNode(thought=alt, score=self._evaluate(alt, goal)) for alt in alternatives]
        self.thought_tree.append(ThoughtTreeLevel(depth=self.iteration, alternatives=evaluated))

        best = max(evaluated, key=lambda x: x.score)
        self.iteration += 1
        return Action(type=ActionType.THINK, thought=f"Exploring: {best.thought} (score: {best.score})")

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
