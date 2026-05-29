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
        self.current_iteration = 0

    def execute(self, goal: str) -> str:
        """Execute with iteration counting and logging."""
        self.current_iteration = 0
        result = super().execute(goal)
        if self.enable_logging:
            self._log_execution()
        return result

    def _is_task_complete(self, goal: str) -> bool:
        """Check if task complete with iteration limit."""
        self.current_iteration += 1
        if self.current_iteration >= self.max_iterations:
            self.agent_context.add_event(f"Maximum iterations ({self.max_iterations}) reached")
            return True
        return super()._is_task_complete(goal)

    def _log_execution(self) -> None:
        """Log execution details."""
        trace = self.get_execution_trace()
        logger.info("\n=== Agent Execution Trace ===")
        logger.info(f"Iterations: {self.current_iteration}")
        logger.info(f"Final State: {trace['current_state']}\n")
        logger.info("State History:")
        state_history = trace.get("state_history")
        if isinstance(state_history, list):
            for state in state_history:
                if isinstance(state, dict):
                    logger.info(f"  {state.get('from_state')} -> {state.get('to_state')} at {state.get('timestamp')}")
        logger.info("\nEvents:")
        events = trace.get("events")
        if isinstance(events, list):
            for event in events:
                if isinstance(event, dict):
                    logger.info(f"  [{event.get('state')}] {event.get('message')}")
