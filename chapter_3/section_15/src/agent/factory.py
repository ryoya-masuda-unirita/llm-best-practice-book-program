"""Factory and Builder patterns for agent construction."""

from typing import Any

from src.agent.agent import BaseAgent, ConfigurableAgent, MultiStrategyAgent
from src.agent.controller import (
    CostLimitHandler,
    DangerousActionHandler,
    ExecutionController,
    LoopDetectionHandler,
    MaxStepsHandler,
    ToolRateLimitHandler,
)
from src.agent.memory import ContextMemory, ConversationalMemory
from src.agent.strategies import ChainOfThoughtStrategy, ReActStrategy, TreeOfThoughtStrategy
from src.agent.toolbox import CalculatorTool, CategorizableToolBox, ToolBox, WebSearchTool
from src.client.llm_client import GeminiModel


class AgentBuilder:
    """Builder for step-by-step agent construction."""

    def __init__(self):
        self.strategy = None
        self.toolbox = None
        self.memory = None
        self.controller = None
        self.agent_type = "base"
        self.agent_config: dict[str, Any] = {}

    def with_strategy(self, strategy):
        """Set the strategy (Strategy instance or dict config)."""
        self.strategy = self._create_strategy(strategy) if isinstance(strategy, dict) else strategy
        return self

    def with_toolbox(self, toolbox):
        """Set the toolbox (ToolBox instance or dict config)."""
        self.toolbox = self._create_toolbox(toolbox) if isinstance(toolbox, dict) else toolbox
        return self

    def with_memory(self, memory):
        """Set the memory (Memory instance or dict config)."""
        self.memory = self._create_memory(memory) if isinstance(memory, dict) else memory
        return self

    def with_controller(self, controller):
        """Set the controller (Controller instance or dict config)."""
        self.controller = self._create_controller(controller) if isinstance(controller, dict) else controller
        return self

    def with_agent_type(self, agent_type: str):
        """Set the agent type ('base', 'configurable', 'multi_strategy')."""
        self.agent_type = agent_type
        return self

    def with_config(self, **kwargs):
        """Add additional configuration."""
        self.agent_config.update(kwargs)
        return self

    def build(self) -> BaseAgent:
        """Build the agent."""
        if not self.toolbox:
            raise ValueError("ToolBox is required")
        if self.agent_type != "multi_strategy" and not self.strategy:
            raise ValueError("Strategy is required")

        if self.agent_type == "configurable":
            return ConfigurableAgent(
                self.strategy,
                self.toolbox,
                self.memory,
                self.controller,
                self.agent_config.get("enable_logging", True),
                self.agent_config.get("max_iterations", 50),
            )
        elif self.agent_type == "multi_strategy":
            strategies = self.agent_config.get("strategies", {})
            default = self.agent_config.get("default_strategy")
            if not strategies or not default:
                raise ValueError("Multi-strategy agent requires 'strategies' and 'default_strategy'")
            return MultiStrategyAgent(strategies, default, self.toolbox, self.memory, self.controller)
        else:  # base
            return BaseAgent(self.strategy, self.toolbox, self.memory, self.controller)

    def _create_strategy(self, config: dict):
        """Create strategy from config."""
        stype = config.get("type", "chain_of_thought")
        model = config.get("model", GeminiModel.GEMINI_2_5_FLASH)

        if stype == "react":
            return ReActStrategy(model, config.get("max_iterations", 10))
        elif stype == "tree_of_thought":
            return TreeOfThoughtStrategy(model, config.get("max_depth", 3), config.get("branch_factor", 3))
        else:  # chain_of_thought
            return ChainOfThoughtStrategy(model, config.get("max_steps", 10))

    def _create_toolbox(self, config: dict):
        """Create toolbox from config."""
        toolbox = CategorizableToolBox() if config.get("categorized") else ToolBox()
        for tool_cfg in config.get("tools", []):
            tool = self._create_tool(tool_cfg)
            if tool:
                if config.get("categorized") and "category" in tool_cfg:
                    toolbox.add_to_category(tool_cfg["category"], tool)
                else:
                    toolbox.add(tool)
        return toolbox

    def _create_memory(self, config: dict):
        """Create memory from config."""
        mtype = config.get("type", "conversational")
        if mtype == "context":
            return ContextMemory(config.get("max_history", 100))
        return ConversationalMemory(config.get("max_turns", 50))

    def _create_controller(self, config: dict):
        """Create controller from config."""
        controller = ExecutionController()
        handlers = config.get("handlers", {})

        if "max_steps" in handlers:
            controller.add_handler(MaxStepsHandler(handlers["max_steps"]))
        if "max_cost" in handlers:
            controller.add_handler(CostLimitHandler(handlers["max_cost"]))
        if "max_calls_per_tool" in handlers:
            controller.add_handler(ToolRateLimitHandler(handlers["max_calls_per_tool"]))
        if handlers.get("enable_dangerous_action_filter", True):
            controller.add_handler(DangerousActionHandler(handlers.get("dangerous_tools")))
        if handlers.get("enable_loop_detection", True):
            controller.add_handler(
                LoopDetectionHandler(handlers.get("loop_window_size", 5), handlers.get("loop_threshold", 3))
            )
        return controller

    def _create_tool(self, config: dict):
        """Create tool from config."""
        ttype = config.get("type")
        return {"calculator": CalculatorTool(), "web_search": WebSearchTool()}.get(ttype)


def create_agent_from_config(config: dict[str, Any]) -> BaseAgent:
    """Create an agent from a complete configuration."""
    builder = AgentBuilder()
    builder.with_agent_type(config.get("type", "base"))

    if "strategy" in config:
        builder.with_strategy(config["strategy"])
    if "toolbox" in config:
        builder.with_toolbox(config["toolbox"])
    if "memory" in config:
        builder.with_memory(config["memory"])
    if "controller" in config:
        builder.with_controller(config["controller"])

    # Add extra config
    extra = {k: v for k, v in config.items() if k not in ["type", "strategy", "toolbox", "memory", "controller"]}
    if extra:
        builder.with_config(**extra)

    return builder.build()
