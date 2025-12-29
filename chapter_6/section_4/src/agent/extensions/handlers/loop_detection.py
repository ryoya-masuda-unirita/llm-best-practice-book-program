"""Handler to detect infinite loops."""

from src.agent.core.base import ActionType
from src.agent.core.controller import ExecutionHandler, ExecutionRequest, ExecutionResponse


class LoopDetectionHandler(ExecutionHandler):
    """Handler to detect infinite loops.

    Only tracks TOOL_CALL actions to avoid false positives from
    consecutive THINK actions during reasoning.
    """

    def __init__(self, window_size: int = 5, threshold: int = 3):
        super().__init__()
        self.window_size = window_size
        self.threshold = threshold
        self.action_history: list[str] = []

    def _check(self, request: ExecutionRequest) -> ExecutionResponse:
        if request.action.type != ActionType.TOOL_CALL:
            return ExecutionResponse(allowed=True)

        signature = f"{request.action.tool_name}:{str(request.action.params)}"
        self.action_history.append(signature)
        self.action_history = self.action_history[-self.window_size :]

        if self.action_history.count(signature) >= self.threshold:
            return ExecutionResponse(
                allowed=False, reason=f"Possible infinite loop detected: action repeated {self.threshold} times"
            )
        return ExecutionResponse(allowed=True)

    def reset(self) -> None:
        self.action_history.clear()
