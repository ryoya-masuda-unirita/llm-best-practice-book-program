"""Multi-strategy agent that can switch between strategies dynamically."""

from src.agent.core.agent import BaseAgent
from src.agent.core.base import Strategy
from src.agent.core.controller import ExecutionController
from src.agent.core.memory import Memory
from src.agent.core.toolbox import ToolBox


class MultiStrategyAgent(BaseAgent):
    """Agent that can switch between multiple strategies dynamically."""

    def __init__(
        self,
        strategies: dict[str, Strategy],
        default_strategy: str,
        toolbox: ToolBox,
        memory: Memory | None = None,
        controller: ExecutionController | None = None,
    ):
        if default_strategy not in strategies:
            raise ValueError(f"Default strategy '{default_strategy}' not found in strategies")

        super().__init__(strategies[default_strategy], toolbox, memory, controller)
        self.strategies = strategies
        self.current_strategy_name = default_strategy

    def switch_strategy(self, strategy_name: str) -> bool:
        """Switch to a different thinking strategy."""
        if strategy_name not in self.strategies:
            return False
        self.strategy = self.strategies[strategy_name]
        self.current_strategy_name = strategy_name
        self.agent_context.add_event(f"Switched to strategy: {strategy_name}")
        return True

    def get_current_strategy(self) -> str:
        """Get name of current strategy."""
        return self.current_strategy_name
