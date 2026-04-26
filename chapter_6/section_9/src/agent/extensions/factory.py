"""Factory and Builder patterns for agent construction."""

from src.agent.core.agent import BaseAgent
from src.agent.core.base import Strategy
from src.agent.core.controller import ExecutionController
from src.agent.core.memory import Memory
from src.agent.core.toolbox import ToolBox
from src.agent.extensions.agents.configurable import ConfigurableAgent
from src.agent.extensions.agents.multi_strategy import MultiStrategyAgent
from src.agent.extensions.handlers.factory import create_default_controller
from src.agent.extensions.memory.context import ContextMemory
from src.agent.extensions.memory.conversational import ConversationalMemory
from src.agent.extensions.strategies.chain_of_thought import ChainOfThoughtStrategy
from src.agent.extensions.strategies.react import ReActStrategy
from src.agent.extensions.strategies.tree_of_thought import TreeOfThoughtStrategy
from src.agent.extensions.tools.categorizable_toolbox import CategorizableToolBox


class AgentBuilder:
    """Fluent builder for step-by-step agent construction."""

    def __init__(self) -> None:
        self._strategy: Strategy | None = None
        self._toolbox: ToolBox | None = None
        self._memory: Memory | None = None
        self._controller: ExecutionController | None = None
        self._agent_type: str = "base"
        self._config: dict[str, object] = {}

    def with_strategy(self, strategy: Strategy) -> "AgentBuilder":
        self._strategy = strategy
        return self

    def with_toolbox(self, toolbox: ToolBox) -> "AgentBuilder":
        self._toolbox = toolbox
        return self

    def with_memory(self, memory: Memory) -> "AgentBuilder":
        self._memory = memory
        return self

    def with_controller(self, controller: ExecutionController) -> "AgentBuilder":
        self._controller = controller
        return self

    def with_agent_type(self, agent_type: str) -> "AgentBuilder":
        self._agent_type = agent_type
        return self

    def with_config(self, **kwargs: object) -> "AgentBuilder":
        self._config.update(kwargs)
        return self

    def build(self) -> BaseAgent:
        if not self._strategy:
            self._strategy = ChainOfThoughtStrategy()
        if not self._toolbox:
            self._toolbox = ToolBox()
        if not self._memory:
            self._memory = ContextMemory()
        if not self._controller:
            self._controller = create_default_controller()

        if self._agent_type == "configurable":
            return ConfigurableAgent(
                strategy=self._strategy,
                toolbox=self._toolbox,
                memory=self._memory,
                controller=self._controller,
                enable_logging=bool(self._config.get("enable_logging", True)),
                max_iterations=int(self._config.get("max_iterations", 50)),
            )
        elif self._agent_type == "multi_strategy":
            strategies = self._config.get("strategies", {})
            if not isinstance(strategies, dict):
                strategies = {"default": self._strategy}
            default_name = str(self._config.get("default_strategy", "default"))
            if default_name not in strategies:
                strategies[default_name] = self._strategy
            return MultiStrategyAgent(
                strategies=strategies,
                default_strategy=default_name,
                toolbox=self._toolbox,
                memory=self._memory,
                controller=self._controller,
            )
        else:
            return BaseAgent(
                strategy=self._strategy,
                toolbox=self._toolbox,
                memory=self._memory,
                controller=self._controller,
            )


def create_agent_from_config(config: dict[str, object]) -> BaseAgent:
    """Factory function to create an agent from a config dictionary."""
    builder = AgentBuilder()

    # Strategy
    strategy_name = str(config.get("strategy", "chain_of_thought"))
    model = str(config.get("model", "gemini-2.5-flash"))
    strategy = _create_strategy(strategy_name, model)
    builder.with_strategy(strategy)

    # Toolbox
    toolbox_type = str(config.get("toolbox_type", "basic"))
    toolbox = _create_toolbox(toolbox_type)
    builder.with_toolbox(toolbox)

    # Memory
    memory_type = str(config.get("memory_type", "context"))
    memory = _create_memory(memory_type, config)
    builder.with_memory(memory)

    # Controller
    controller = _create_controller(config)
    builder.with_controller(controller)

    # Agent type
    agent_type = str(config.get("agent_type", "base"))
    builder.with_agent_type(agent_type)

    return builder.build()


def _create_strategy(name: str, model: str) -> Strategy:
    strategies: dict[str, type[Strategy]] = {
        "chain_of_thought": ChainOfThoughtStrategy,
        "react": ReActStrategy,
        "tree_of_thought": TreeOfThoughtStrategy,
    }
    cls = strategies.get(name, ChainOfThoughtStrategy)
    return cls(model=model)  # type: ignore[call-arg]


def _create_toolbox(toolbox_type: str) -> ToolBox:
    if toolbox_type == "categorizable":
        return CategorizableToolBox()
    return ToolBox()


def _create_memory(memory_type: str, config: dict[str, object]) -> Memory:
    if memory_type == "conversational":
        max_turns = int(config.get("max_turns", 50))
        return ConversationalMemory(max_turns=max_turns)
    max_history = int(config.get("max_history", 100))
    return ContextMemory(max_history=max_history)


def _create_controller(config: dict[str, object]) -> ExecutionController:
    max_steps = int(config.get("max_steps", 50))
    max_cost = float(config.get("max_cost", 10.0))  # type: ignore[arg-type]
    max_calls = int(config.get("max_calls_per_tool", 10))
    return create_default_controller(max_steps, max_cost, max_calls)
