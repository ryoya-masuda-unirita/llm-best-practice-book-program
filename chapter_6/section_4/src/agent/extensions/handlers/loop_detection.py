"""Loop detection handler."""

from src.agent.core.base import ActionType
from src.agent.core.controller import ExecutionHandler, ExecutionRequest, ExecutionResponse


class LoopDetectionHandler(ExecutionHandler):
    def __init__(self, window_size: int = 5, threshold: int = 3):
        super().__init__()
        self.window_size = window_size
        self.threshold = threshold
        self.action_history: list[str] = []

    def _check(self, request: ExecutionRequest) -> ExecutionResponse:
        if request.action.type != ActionType.TOOL_CALL:
            return ExecutionResponse(allowed=True)

        action_key = f"{request.action.tool_name}:{request.action.params}"
        self.action_history.append(action_key)

        window = self.action_history[-self.window_size :]
        if len(window) >= self.threshold:
            most_common = max(set(window), key=window.count)
            if window.count(most_common) >= self.threshold:
                return ExecutionResponse(
                    allowed=False,
                    reason=f"Loop detected: action '{most_common}' repeated {window.count(most_common)} times",
                )
        return ExecutionResponse(allowed=True)

    def reset(self) -> None:
        self.action_history.clear()
