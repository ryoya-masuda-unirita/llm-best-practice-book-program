"""Factory for creating default execution controller."""

from src.agent.core.controller import ExecutionController
from src.agent.extensions.handlers.cost_limit import CostLimitHandler
from src.agent.extensions.handlers.max_steps import MaxStepsHandler
from src.agent.extensions.handlers.tool_rate_limit import ToolRateLimitHandler


def create_default_controller(
    max_steps: int = 50,
    max_cost: float = 10.0,
    max_calls_per_tool: int = 10,
) -> ExecutionController:
    controller = ExecutionController()
    controller.add_handler(MaxStepsHandler(max_steps))
    controller.add_handler(CostLimitHandler(max_cost))
    controller.add_handler(ToolRateLimitHandler(max_calls_per_tool))
    return controller
