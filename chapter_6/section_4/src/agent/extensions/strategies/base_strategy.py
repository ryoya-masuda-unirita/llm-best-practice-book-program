"""Base strategy with LLM integration and action parsing."""

from src.agent.core.base import Action, ActionType, StepInfo, Strategy, Tool, ToolResult
from src.client.llm_client import anthropic_sync_client
from src.logger import make_logger

logger = make_logger(__name__)


class BaseStrategy(Strategy):
    """Base strategy implementation with Anthropic integration."""

    def __init__(
        self, name: str, model: str = "global.anthropic.claude-haiku-4-5-20251001-v1:0", max_iterations: int = 10
    ):
        super().__init__(name)
        self.model = model
        self.max_iterations = max_iterations
        self._steps: list[StepInfo] = []
        self._iteration = 0

    def _call_llm(self, prompt: str, response_schema: type | None = None) -> str:
        try:
            messages = [{"role": "user", "content": prompt}]
            if response_schema:
                response = anthropic_sync_client.messages.parse(
                    model=self.model,
                    max_tokens=4096,
                    messages=messages,
                    output_format=response_schema,
                )
            else:
                response = anthropic_sync_client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    messages=messages,
                )
            return next((block.text for block in response.content if block.type == "text"), "")
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return ""

    def _parse_action(self, response: str, available_tools: list[Tool]) -> Action:
        response_lower = response.lower()
        if "tool:" in response_lower or "action:" in response_lower:
            return self._parse_tool_action(response, available_tools)
        if "answer:" in response_lower or "final answer:" in response_lower:
            return self._parse_answer_action(response)
        return Action(type=ActionType.THINK, thought=response)

    def _parse_tool_action(self, response: str, available_tools: list[Tool]) -> Action:
        tool_names = [t.name for t in available_tools]
        for tool_name in tool_names:
            if tool_name.lower() in response.lower():
                return Action(type=ActionType.TOOL_CALL, tool_name=tool_name)
        return Action(type=ActionType.THINK, thought=response)

    def _parse_answer_action(self, response: str) -> Action:
        for prefix in ["Final Answer:", "Answer:", "ANSWER:"]:
            if prefix in response:
                answer = response.split(prefix, 1)[1].strip()
                return Action(type=ActionType.FINAL_ANSWER, answer=answer)
        return Action(type=ActionType.FINAL_ANSWER, answer=response)

    def update_context(self, context: dict[str, object], action: Action, result: ToolResult | str) -> dict[str, object]:
        step = StepInfo(
            iteration=self._iteration,
            thought=action.thought,
            action=action.type.value,
            result=result if isinstance(result, ToolResult) else None,
        )
        self._steps.append(step)
        self._iteration += 1

        if "steps" not in context:
            context["steps"] = []
        steps_list = context["steps"]
        if isinstance(steps_list, list):
            steps_list.append(
                {
                    "iteration": step.iteration,
                    "thought": step.thought,
                    "action": step.action,
                    "result": step.result,
                }
            )
        return context

    def think(self, goal: str, context: dict[str, object], available_tools: list[Tool]) -> Action:
        if self._iteration >= self.max_iterations:
            return Action(type=ActionType.FINAL_ANSWER, answer="Maximum iterations reached")

        tool_descriptions = "\n".join(f"- {t.name}: {t.description}" for t in available_tools)
        prompt = f"""Goal: {goal}

Available Tools:
{tool_descriptions}

Think about the goal and decide what to do next.
If you need to use a tool, respond with: Tool: <tool_name>
If you have the final answer, respond with: Answer: <your_answer>
"""
        response = self._call_llm(prompt)
        return self._parse_action(response, available_tools)
