"""Configurable agent with logging and iteration limits."""

from src.agent.core.agent import BaseAgent
from src.agent.core.base import Strategy
from src.agent.core.controller import ExecutionController
from src.agent.core.memory import Memory
from src.agent.core.toolbox import ToolBox
from src.logger import make_logger

logger = make_logger(__name__)


class ConfigurableAgent(BaseAgent):
    """Agent with additional configuration options."""

    def __init__(
        self,
        strategy: Strategy,
        toolbox: ToolBox,
        memory: Memory | None = None,
        controller: ExecutionController | None = None,
        enable_logging: bool = True,
        max_iterations: int = 50,
    ):
        super().__init__(strategy, toolbox, memory, controller)
        self.enable_logging = enable_logging
        self.max_iterations = max_iterations
        self._current_iteration = 0

    def execute(self, goal: str) -> str:
        self._current_iteration = 0
        result = super().execute(goal)
        if self.enable_logging:
            self._log_execution()
        return result

    def _log_execution(self) -> None:
        trace = self.get_execution_trace()
        logger.info(f"Execution completed. State history: {len(trace.get('state_history', []))} transitions")
        logger.info(f"Events: {len(trace.get('events', []))}")

    def _is_task_complete(self, goal: str) -> bool:
        self._current_iteration += 1
        if self._current_iteration > self.max_iterations:
            return True
        return super()._is_task_complete(goal)
