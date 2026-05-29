"""Thinking strategies for AI agents (Strategy pattern)."""

import ast
import json
import re
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

    def _parse_json_params(self, param_str: str) -> dict[str, str | int | float | bool | list | dict | None]:
        """Parse JSON parameters with robust error handling for LLM output."""
        parsers = [
            self._try_parse_json,
            self._try_parse_single_quotes,
            self._try_parse_unquoted_keys,
            self._try_parse_trailing_commas,
            self._try_parse_python_literal,
        ]
        for parser in parsers:
            result = parser(param_str)
            if result is not None:
                return result

        logger.warning(f"Failed to parse params: {param_str}")
        return {}

    def _try_parse_json(self, param_str: str) -> dict | None:
        """Try parsing as valid JSON."""
        try:
            return json.loads(param_str)
        except json.JSONDecodeError:
            return None

    def _try_parse_single_quotes(self, param_str: str) -> dict | None:
        """Try parsing after replacing single quotes with double quotes."""
        fixed = re.sub(r"'([^']*)'", r'"\1"', param_str)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return None

    def _try_parse_unquoted_keys(self, param_str: str) -> dict | None:
        """Try parsing after quoting unquoted keys."""
        fixed = re.sub(r"'([^']*)'", r'"\1"', param_str)
        fixed = re.sub(r"(\{|,)\s*(\w+)\s*:", r'\1"\2":', fixed)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return None

    def _try_parse_trailing_commas(self, param_str: str) -> dict | None:
        """Try parsing after removing trailing commas."""
        fixed = re.sub(r"'([^']*)'", r'"\1"', param_str)
        fixed = re.sub(r"(\{|,)\s*(\w+)\s*:", r'\1"\2":', fixed)
        fixed = re.sub(r",\s*}", "}", fixed)
        fixed = re.sub(r",\s*]", "]", fixed)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return None

    def _try_parse_python_literal(self, param_str: str) -> dict | None:
        """Try parsing as Python literal (dict syntax)."""
        try:
            result = ast.literal_eval(param_str)
            return result if isinstance(result, dict) else None
        except (ValueError, SyntaxError):
            return None

    def _parse_action(self, response: str) -> Action:
        """Parse LLM response to extract action."""
        response_text = response.strip()

        action = self._try_parse_tool_action(response_text)
        if action:
            return action

        action = self._try_parse_answer_action(response_text)
        if action:
            return action

        action = self._try_parse_line_by_line(response_text)
        if action:
            return action

        return Action(type=ActionType.THINK, thought=response_text)

    def _try_parse_tool_action(self, response_text: str) -> Action | None:
        """Try to parse TOOL: pattern from response."""
        tool_match = re.search(r"(?:Action:\s*)?TOOL:\s*(\w+)\s*\|\s*PARAMS:\s*(\{.*?\})", response_text, re.DOTALL)
        if not tool_match:
            return None

        tool_name = tool_match.group(1).strip()
        param_str = tool_match.group(2).strip()
        params = self._safe_parse_params(param_str)
        thought = response_text[: tool_match.start()].strip()
        return Action(type=ActionType.TOOL_CALL, tool_name=tool_name, params=params, thought=thought)

    def _try_parse_answer_action(self, response_text: str) -> Action | None:
        """Try to parse ANSWER: pattern from response."""
        answer_match = re.search(r"(?:Action:\s*)?ANSWER:\s*(.+)", response_text, re.DOTALL)
        if not answer_match:
            return None

        answer_content = answer_match.group(1).strip()
        thought = response_text[: answer_match.start()].strip()
        return Action(type=ActionType.FINAL_ANSWER, answer=answer_content, thought=thought)

    def _try_parse_line_by_line(self, response_text: str) -> Action | None:
        """Fallback: parse response line by line for simpler patterns."""
        lines = [x.strip() for x in response_text.split("\n") if x.strip()]
        for i, line in enumerate(lines):
            action = self._parse_tool_line(line, lines[:i])
            if action:
                return action

            action = self._parse_answer_line(line, lines[:i])
            if action:
                return action
        return None

    def _parse_tool_line(self, line: str, preceding_lines: list[str]) -> Action | None:
        """Parse a single line for TOOL: pattern."""
        if "TOOL:" not in line or "|" not in line:
            return None

        parts = line.split("TOOL:", 1)[1].split("|")
        tool_name = parts[0].strip()
        params: dict[str, str | int | float | bool | list | dict | None] = {}
        if len(parts) > 1 and "PARAMS:" in parts[1]:
            param_str = parts[1].split("PARAMS:")[1].strip()
            params = self._safe_parse_params(param_str)
        return Action(type=ActionType.TOOL_CALL, tool_name=tool_name, params=params, thought="\n".join(preceding_lines))

    def _parse_answer_line(self, line: str, preceding_lines: list[str]) -> Action | None:
        """Parse a single line for ANSWER: pattern."""
        if "ANSWER:" not in line:
            return None
        answer_content = line.split("ANSWER:", 1)[1].strip()
        return Action(type=ActionType.FINAL_ANSWER, answer=answer_content, thought="\n".join(preceding_lines))

    def _safe_parse_params(self, param_str: str) -> dict[str, str | int | float | bool | list | dict | None]:
        """Safely parse parameters with error handling."""
        try:
            return self._parse_json_params(param_str)
        except Exception as e:
            logger.error(e)
            return {}

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

    def _format_tools_description(self, tools: list[Tool]) -> str:
        """Format tool list as description string."""
        return "\n".join([f"- {t.name}: {t.description}" for t in tools])

    def _format_observation(self, obs: str | ToolResult) -> str:
        """Format an observation for display."""
        if isinstance(obs, ToolResult):
            return f"Success: {obs.success}, Data: {obs.data}" if obs.success else f"Error: {obs.error}"
        return str(obs)

    def _get_actions_and_observations(self, context: dict[str, object]) -> tuple[list[Action], list[str | ToolResult]]:
        """Extract actions and observations from context."""
        actions = context.get("actions", [])
        observations = context.get("observations", [])
        action_list = [a for a in (actions if isinstance(actions, list) else []) if isinstance(a, Action)]
        obs_list = observations if isinstance(observations, list) else []
        return action_list, obs_list


class ChainOfThoughtStrategy(BaseStrategy):
    """Chain-of-Thought strategy: Sequential reasoning steps."""

    def __init__(self, model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH, max_steps: int = 10):
        super().__init__("Chain-of-Thought", model, max_steps)

    def think(self, goal: str, context: dict[str, object], available_tools: list[Tool]) -> Action:
        self.iteration += 1
        if self.iteration > self.max_iterations:
            return Action(type=ActionType.FINAL_ANSWER, answer="Maximum reasoning steps reached")

        tools_desc = self._format_tools_description(available_tools)
        history = self._build_history(context)
        prompt = self._build_cot_prompt(goal, tools_desc, history)
        return self._parse_action(self._call_llm(prompt))

    def _build_history(self, context: dict[str, object]) -> str:
        """Build step history from context."""
        actions, obs_list = self._get_actions_and_observations(context)
        history_lines = []
        for i, action in enumerate(actions):
            obs = obs_list[i] if i < len(obs_list) else "N/A"
            obs_str = self._format_observation(obs) if not isinstance(obs, str) else obs
            history_lines.append(f"Step {i + 1}: {action.thought or action.type.value} -> Result: {obs_str}")
        return "\n".join(history_lines)

    def _build_cot_prompt(self, goal: str, tools_desc: str, history: str) -> str:
        """Build the Chain-of-Thought prompt."""
        history_section = f"Previous steps:\n{history}" if history else "This is the first step."
        return f"""Goal: {goal}

Available tools:
{tools_desc}

{history_section}

Instructions:
- For simple tasks (like writing, answering questions) that you can do directly, provide the ANSWER immediately
- Only use tools when you need specific capabilities (searching, calculating, etc.)
- You MUST respond with EXACTLY one of these formats:

To provide the final answer (PREFERRED for simple tasks):
ANSWER: <your complete answer here>

To use a tool (only if necessary):
TOOL: <tool_name> | PARAMS: {{"param1": "value1", "param2": "value2"}}

Your response:"""


class ReActStrategy(BaseStrategy):
    """ReAct strategy: Reasoning and Acting in sync."""

    def __init__(self, model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH, max_iterations: int = 10):
        super().__init__("ReAct", model, max_iterations)

    def think(self, goal: str, context: dict[str, object], available_tools: list[Tool]) -> Action:
        self.iteration += 1
        if self.iteration > self.max_iterations:
            return Action(type=ActionType.FINAL_ANSWER, answer="Maximum iterations reached")

        tools_desc = self._format_tools_description(available_tools)
        trajectory = self._build_trajectory(context)
        prompt = self._build_react_prompt(goal, tools_desc, trajectory)
        return self._parse_action(self._call_llm(prompt))

    def _build_trajectory(self, context: dict[str, object]) -> str:
        """Build trajectory from context with detailed action info."""
        actions, obs_list = self._get_actions_and_observations(context)
        trajectory_lines = []
        for i, action in enumerate(actions):
            obs = obs_list[i] if i < len(obs_list) else "N/A"
            obs_str = self._format_observation(obs) if not isinstance(obs, str) else obs
            action_desc = self._format_action_description(action)
            trajectory_lines.append(
                f"Iteration {i + 1}:\nThought: {action.thought}\nAction: {action_desc}\nObservation: {obs_str}"
            )
        return "\n".join(trajectory_lines)

    def _format_action_description(self, action: Action) -> str:
        """Format action as description string."""
        if action.type == ActionType.TOOL_CALL:
            return f"TOOL: {action.tool_name} | PARAMS: {action.params}"
        elif action.type == ActionType.FINAL_ANSWER:
            return f"ANSWER: {action.answer}"
        return action.thought or "thinking"

    def _build_react_prompt(self, goal: str, tools_desc: str, trajectory: str) -> str:
        """Build the ReAct prompt."""
        trajectory_section = f"Previous trajectory:\n{trajectory}" if trajectory else "This is the first iteration."
        return f"""Goal: {goal}

Available Tools:
{tools_desc}

{trajectory_section}

Instructions:
- Reason about what to do next
- For simple tasks (like writing, answering questions) that you can do directly, provide the ANSWER immediately
- Only use tools when you need specific capabilities (searching for information, calculating, etc.)
- You MUST respond in this EXACT format:

To provide the final answer (PREFERRED for simple tasks):
ANSWER: <your complete answer here>

To use a tool (only if necessary):
TOOL: <tool_name> | PARAMS: {{"param1": "value1", "param2": "value2"}}

Your response:"""


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
