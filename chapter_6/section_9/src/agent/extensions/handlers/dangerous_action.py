"""Dangerous action handler."""

from src.agent.core.base import ActionType
from src.agent.core.controller import ExecutionHandler, ExecutionRequest, ExecutionResponse


class DangerousActionHandler(ExecutionHandler):
    def __init__(self, dangerous_tools: list[str] | None = None):
        super().__init__()
        self.dangerous_tools = dangerous_tools or ["delete", "destroy", "remove_all"]

    def _check(self, request: ExecutionRequest) -> ExecutionResponse:
        if request.action.type == ActionType.TOOL_CALL and request.action.tool_name in self.dangerous_tools:
            return ExecutionResponse(
                allowed=False,
                reason=f"Tool '{request.action.tool_name}' is blocked as dangerous",
            )
        return ExecutionResponse(allowed=True)
