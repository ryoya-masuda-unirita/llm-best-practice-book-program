"""Handler to limit maximum execution steps."""

from src.agent.core.controller import ExecutionHandler, ExecutionRequest, ExecutionResponse


class MaxStepsHandler(ExecutionHandler):
    """Handler to limit maximum execution steps."""

    def __init__(self, max_steps: int = 50):
        super().__init__()
        self.max_steps = max_steps
        self.current_steps = 0

    def _check(self, request: ExecutionRequest) -> ExecutionResponse:
        self.current_steps += 1
        if self.current_steps > self.max_steps:
            return ExecutionResponse(allowed=False, reason=f"Maximum steps ({self.max_steps}) exceeded")
        return ExecutionResponse(allowed=True)

    def reset(self) -> None:
        self.current_steps = 0
