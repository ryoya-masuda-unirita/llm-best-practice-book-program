"""Cost limit execution handler."""

from src.agent.core.base import ActionType
from src.agent.core.controller import ExecutionHandler, ExecutionRequest, ExecutionResponse


class CostLimitHandler(ExecutionHandler):
    COST_MAP = {
        ActionType.TOOL_CALL: 0.01,
        ActionType.THINK: 0.005,
        ActionType.FINAL_ANSWER: 0.001,
    }

    def __init__(self, max_cost: float = 10.0):
        super().__init__()
        self.max_cost = max_cost
        self.current_cost = 0.0

    def _check(self, request: ExecutionRequest) -> ExecutionResponse:
        cost = self.COST_MAP.get(request.action.type, 0.0)
        self.current_cost += cost
        if self.current_cost > self.max_cost:
            return ExecutionResponse(allowed=False, reason=f"Cost limit ({self.max_cost}) exceeded")
        return ExecutionResponse(allowed=True)

    def reset(self) -> None:
        self.current_cost = 0.0
