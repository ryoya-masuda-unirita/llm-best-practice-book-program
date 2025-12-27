"""Factory function for creating default controller with handlers."""

from src.agent.core.controller import ExecutionController
from src.agent.extensions.handlers.cost_limit import CostLimitHandler
from src.agent.extensions.handlers.dangerous_action import DangerousActionHandler
from src.agent.extensions.handlers.loop_detection import LoopDetectionHandler
from src.agent.extensions.handlers.max_steps import MaxStepsHandler
from src.agent.extensions.handlers.tool_rate_limit import ToolRateLimitHandler


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
