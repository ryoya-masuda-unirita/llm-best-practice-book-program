"""Handler to rate limit tool calls."""

from src.agent.core.base import ActionType
from src.agent.core.controller import ExecutionHandler, ExecutionRequest, ExecutionResponse


class ToolRateLimitHandler(ExecutionHandler):
    """Handler to rate limit tool calls."""

    def __init__(self, max_calls_per_tool: int = 10):
        super().__init__()
        self.max_calls_per_tool = max_calls_per_tool
        self.tool_calls: dict[str, int] = {}

    def _check(self, request: ExecutionRequest) -> ExecutionResponse:
        if request.action.type != ActionType.TOOL_CALL or not request.action.tool_name:
            return ExecutionResponse(allowed=True)

        tool_name = request.action.tool_name
        calls = self.tool_calls.get(tool_name, 0)
        if calls >= self.max_calls_per_tool:
            return ExecutionResponse(
                allowed=False, reason=f"Tool '{tool_name}' rate limit ({self.max_calls_per_tool}) exceeded"
            )

        self.tool_calls[tool_name] = calls + 1
        return ExecutionResponse(allowed=True)

    def reset(self) -> None:
        self.tool_calls.clear()
