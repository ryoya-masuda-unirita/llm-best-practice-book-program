"""Base strategy with common LLM interaction logic."""

import json
import re
from typing import TypeVar, overload

from google.genai.types import GenerateContentConfig
from pydantic import BaseModel
from src.agent.core.base import Action, ActionType, Strategy, Tool, ToolResult
from src.client.llm_client import GeminiModel, google_genai_client
from src.logger import make_logger

T = TypeVar("T", bound=BaseModel)

logger = make_logger(__name__)


class BaseStrategy(Strategy):
    """Base strategy with common LLM interaction logic.

    This class provides shared functionality for LLM-based strategies,
    including LLM calls and action parsing.
    """

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
        """Parse LLM response to extract action.

        Handles various LLM response formats including:
        - TOOL: tool_name | PARAMS: {"key": "value"}
        - Markdown formatted **TOOL:** or *TOOL:*
        - Case variations (Tool:, tool:, TOOL:)
        - JSON in code blocks
        """
        lines = [x.strip() for x in response.strip().split("\n") if x.strip()]
        normalized_response = re.sub(r"\*+", "", response)
        normalized_lines = [x.strip() for x in normalized_response.strip().split("\n") if x.strip()]

        for i, line in enumerate(normalized_lines):
            line_upper = line.upper()
            thought = "\n".join(lines[:i])

            if "TOOL:" in line_upper:
                return self._parse_tool_action(line, normalized_lines, i, thought)

            if "ANSWER:" in line_upper:
                return self._parse_answer_action(line, normalized_lines, i, thought)

        return Action(type=ActionType.THINK, thought=response.strip())

    def _parse_tool_action(self, line: str, normalized_lines: list[str], line_index: int, thought: str) -> Action:
        """Parse a tool call action from the response line."""
        tool_start = line.upper().find("TOOL:") + 5
        rest = line[tool_start:]
        parts = rest.split("|")
        tool_name = parts[0].strip()

        params_text = self._extract_params_from_parts(parts)
        if not params_text:
            params_text = self._extract_params_from_lines(normalized_lines, line_index)

        params = self._parse_params_json(params_text)
        return Action(type=ActionType.TOOL_CALL, tool_name=tool_name, params=params, thought=thought)

    def _extract_params_from_parts(self, parts: list[str]) -> str:
        """Extract params text from pipe-separated parts."""
        if len(parts) <= 1:
            return ""
        for part in parts[1:]:
            if "PARAMS:" in part.upper():
                params_idx = part.upper().find("PARAMS:") + 7
                return part[params_idx:].strip()
        return ""

    def _extract_params_from_lines(self, lines: list[str], start_index: int) -> str:
        """Extract params from subsequent lines (PARAMS:, raw JSON, or code block)."""
        for j in range(start_index + 1, min(start_index + 3, len(lines))):
            next_line = lines[j]
            if next_line.upper().startswith("PARAMS:"):
                return next_line[7:].strip()
            if next_line.startswith("{"):
                return next_line
            if next_line.startswith("```"):
                return self._extract_json_from_code_block(lines, j)
        return ""

    def _extract_json_from_code_block(self, lines: list[str], block_start: int) -> str:
        """Extract JSON from a code block starting at the given index."""
        for k in range(block_start + 1, min(block_start + 5, len(lines))):
            if lines[k].startswith("{"):
                return lines[k]
            if lines[k].startswith("```"):
                break
        return ""

    def _parse_params_json(self, params_text: str) -> dict[str, str | int | float | bool | list | dict | None]:
        """Parse params JSON string, returning empty dict on failure."""
        if not params_text:
            return {}
        params_text = params_text.rstrip("`").strip()
        try:
            return json.loads(params_text)
        except Exception as e:
            logger.error(f"Failed to parse params: {e}")
            return {}

    def _parse_answer_action(self, line: str, normalized_lines: list[str], line_index: int, thought: str) -> Action:
        """Parse a final answer action from the response line."""
        answer_start = line.upper().find("ANSWER:") + 7
        first_line_content = line[answer_start:].strip()
        remaining_lines = (
            "\n".join(normalized_lines[line_index + 1 :]) if line_index + 1 < len(normalized_lines) else ""
        )
        full_answer = f"{first_line_content}\n{remaining_lines}".strip() if remaining_lines else first_line_content
        return Action(type=ActionType.FINAL_ANSWER, answer=full_answer, thought=thought)

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

    def think(self, goal: str, context: dict[str, object], available_tools: list[Tool]) -> Action:
        """Default think implementation. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement think()")
