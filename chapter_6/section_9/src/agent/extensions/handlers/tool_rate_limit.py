"""Tool rate limit handler."""

from src.agent.core.base import ActionType
from src.agent.core.controller import ExecutionHandler, ExecutionRequest, ExecutionResponse


class ToolRateLimitHandler(ExecutionHandler):
    def __init__(self, max_calls_per_tool: int = 10):
        super().__init__()
        self.max_calls_per_tool = max_calls_per_tool
        self.tool_calls: dict[str, int] = {}

    def _check(self, request: ExecutionRequest) -> ExecutionResponse:
        if request.action.type != ActionType.TOOL_CALL or not request.action.tool_name:
            return ExecutionResponse(allowed=True)

        tool_name = request.action.tool_name
        self.tool_calls[tool_name] = self.tool_calls.get(tool_name, 0) + 1

        if self.tool_calls[tool_name] > self.max_calls_per_tool:
            return ExecutionResponse(
                allowed=False,
                reason=f"Rate limit for tool '{tool_name}' ({self.max_calls_per_tool}) exceeded",
            )
        return ExecutionResponse(allowed=True)

    def reset(self) -> None:
        self.tool_calls.clear()
