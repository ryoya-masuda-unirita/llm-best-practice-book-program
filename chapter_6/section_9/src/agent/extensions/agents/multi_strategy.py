"""Multi-strategy agent with dynamic strategy switching."""

from src.agent.core.agent import BaseAgent
from src.agent.core.base import Strategy
from src.agent.core.controller import ExecutionController
from src.agent.core.memory import Memory
from src.agent.core.toolbox import ToolBox


class MultiStrategyAgent(BaseAgent):
    """Agent that can switch strategies dynamically."""

    def __init__(
        self,
        strategies: dict[str, Strategy],
        default_strategy: str,
        toolbox: ToolBox,
        memory: Memory | None = None,
        controller: ExecutionController | None = None,
    ):
        self._strategies = strategies
        super().__init__(strategies[default_strategy], toolbox, memory, controller)

    def switch_strategy(self, strategy_name: str) -> bool:
        if strategy_name in self._strategies:
            self.strategy = self._strategies[strategy_name]
            return True
        return False

    def get_current_strategy(self) -> str:
        return self.strategy.name
