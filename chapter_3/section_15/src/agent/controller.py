"""Execution controller with Chain of Responsibility pattern."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from src.agent.base import Action, ActionType


@dataclass
class ExecutionRequest:
    """Request to execute an action."""

    action: Action
    context: dict[str, Any]
    metadata: dict[str, Any] | None = None


@dataclass
class ExecutionResponse:
    """Response from execution control."""

    allowed: bool
    reason: str | None = None
    metadata: dict[str, Any] | None = None


class ExecutionHandler(ABC):
    """Abstract handler in chain of responsibility."""

    def __init__(self):
        self._next_handler: ExecutionHandler | None = None

    def set_next(self, handler: "ExecutionHandler") -> "ExecutionHandler":
        self._next_handler = handler
        return handler

    def handle(self, request: ExecutionRequest) -> ExecutionResponse:
        response = self._check(request)
        if not response.allowed or not self._next_handler:
            return response
        return self._next_handler.handle(request)

    @abstractmethod
    def _check(self, request: ExecutionRequest) -> ExecutionResponse:
        pass


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


class CostLimitHandler(ExecutionHandler):
    """Handler to limit execution cost."""

    def __init__(self, max_cost: float = 10.0):
        super().__init__()
        self.max_cost = max_cost
        self.current_cost = 0.0
        self.cost_map = {ActionType.TOOL_CALL: 0.01, ActionType.THINK: 0.005, ActionType.FINAL_ANSWER: 0.001}

    def _check(self, request: ExecutionRequest) -> ExecutionResponse:
        self.current_cost += self.cost_map.get(request.action.type, 0.0)
        if self.current_cost > self.max_cost:
            return ExecutionResponse(allowed=False, reason=f"Cost limit (${self.max_cost}) exceeded")
        return ExecutionResponse(allowed=True, metadata={"current_cost": self.current_cost})

    def reset(self) -> None:
        self.current_cost = 0.0


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


class DangerousActionHandler(ExecutionHandler):
    """Handler to block potentially dangerous actions."""

    def __init__(self, dangerous_tools: list[str] | None = None):
        super().__init__()
        self.dangerous_tools = set(dangerous_tools or ["delete", "destroy", "remove_all"])

    def _check(self, request: ExecutionRequest) -> ExecutionResponse:
        if request.action.type == ActionType.TOOL_CALL and request.action.tool_name in self.dangerous_tools:
            return ExecutionResponse(allowed=False, reason=f"Tool '{request.action.tool_name}' is blocked for safety")
        return ExecutionResponse(allowed=True)


class LoopDetectionHandler(ExecutionHandler):
    """Handler to detect infinite loops."""

    def __init__(self, window_size: int = 5, threshold: int = 3):
        super().__init__()
        self.window_size = window_size
        self.threshold = threshold
        self.action_history: list[str] = []

    def _check(self, request: ExecutionRequest) -> ExecutionResponse:
        signature = f"{request.action.type.value}:{request.action.tool_name}:{str(request.action.params)}"
        self.action_history.append(signature)
        self.action_history = self.action_history[-self.window_size :]

        if self.action_history.count(signature) >= self.threshold:
            return ExecutionResponse(
                allowed=False, reason=f"Possible infinite loop detected: action repeated {self.threshold} times"
            )
        return ExecutionResponse(allowed=True)

    def reset(self) -> None:
        self.action_history.clear()


class ExecutionController:
    """Main execution controller that manages the chain of handlers."""

    def __init__(self):
        self.handlers: list[ExecutionHandler] = []
        self._chain_head: ExecutionHandler | None = None

    def add_handler(self, handler: ExecutionHandler) -> "ExecutionController":
        self.handlers.append(handler)
        self._rebuild_chain()
        return self

    def check_execution(self, request: ExecutionRequest) -> ExecutionResponse:
        return self._chain_head.handle(request) if self._chain_head else ExecutionResponse(allowed=True)

    def reset_all(self) -> None:
        for handler in self.handlers:
            if hasattr(handler, "reset"):
                handler.reset()

    def _rebuild_chain(self) -> None:
        if not self.handlers:
            self._chain_head = None
            return
        self._chain_head = self.handlers[0]
        for i in range(len(self.handlers) - 1):
            self.handlers[i].set_next(self.handlers[i + 1])


def create_default_controller(
    max_steps: int = 50, max_cost: float = 10.0, max_calls_per_tool: int = 10
) -> ExecutionController:
    """Create a controller with default safety handlers."""
    controller = ExecutionController()
    controller.add_handler(MaxStepsHandler(max_steps))
    controller.add_handler(CostLimitHandler(max_cost))
    controller.add_handler(ToolRateLimitHandler(max_calls_per_tool))
    controller.add_handler(DangerousActionHandler())
    controller.add_handler(LoopDetectionHandler())
    return controller
