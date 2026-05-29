"""Factory and Builder patterns for agent construction."""

from src.agent.core.agent import BaseAgent
from src.agent.core.base import Strategy, Tool
from src.agent.core.controller import ExecutionController
from src.agent.core.memory import Memory
from src.agent.core.toolbox import ToolBox
from src.agent.extensions.agents import ConfigurableAgent, MultiStrategyAgent
from src.agent.extensions.handlers import (
    CostLimitHandler,
    DangerousActionHandler,
    LoopDetectionHandler,
    MaxStepsHandler,
    ToolRateLimitHandler,
)
from src.agent.extensions.memory import ContextMemory, ConversationalMemory
from src.agent.extensions.strategies import ChainOfThoughtStrategy, ReActStrategy, TreeOfThoughtStrategy
from src.agent.extensions.tools import CalculatorTool, CategorizableToolBox, TextGeneratorTool, WebSearchTool
from src.client.llm_client import GeminiModel

StrategyConfig = dict[str, str | int]
ToolConfig = dict[str, str]
ToolboxConfig = dict[str, bool | list[ToolConfig]]
MemoryConfig = dict[str, str | int]
HandlersConfig = dict[str, int | float | bool | list[str] | None]
ControllerConfig = dict[str, HandlersConfig]
AgentConfig = dict[str, str | StrategyConfig | ToolboxConfig | MemoryConfig | ControllerConfig | bool | int]


class AgentBuilder:
    """Builder for step-by-step agent construction."""

    def __init__(self):
        self.strategy: Strategy | None = None
        self.toolbox: ToolBox | None = None
        self.memory: Memory | None = None
        self.controller: ExecutionController | None = None
        self.agent_type: str = "base"
        self.agent_config: dict[str, object] = {}

    def with_strategy(self, strategy: Strategy | StrategyConfig) -> "AgentBuilder":
        self.strategy = self._create_strategy(strategy) if isinstance(strategy, dict) else strategy
        return self

    def with_toolbox(self, toolbox: ToolBox | ToolboxConfig) -> "AgentBuilder":
        self.toolbox = self._create_toolbox(toolbox) if isinstance(toolbox, dict) else toolbox
        return self

    def with_memory(self, memory: Memory | MemoryConfig) -> "AgentBuilder":
        self.memory = self._create_memory(memory) if isinstance(memory, dict) else memory
        return self

    def with_controller(self, controller: ExecutionController | ControllerConfig) -> "AgentBuilder":
        self.controller = self._create_controller(controller) if isinstance(controller, dict) else controller
        return self

    def with_agent_type(self, agent_type: str) -> "AgentBuilder":
        self.agent_type = agent_type
        return self

    def with_config(self, **kwargs: object) -> "AgentBuilder":
        self.agent_config.update(kwargs)
        return self

    def build(self) -> BaseAgent:
        if not self.toolbox:
            raise ValueError("ToolBox is required")
        if self.agent_type != "multi_strategy" and not self.strategy:
            raise ValueError("Strategy is required")

        if self.agent_type == "configurable":
            enable_logging = self.agent_config.get("enable_logging", True)
            max_iterations = self.agent_config.get("max_iterations", 50)
            return ConfigurableAgent(
                self.strategy,  # type: ignore[arg-type]
                self.toolbox,
                self.memory,
                self.controller,
                bool(enable_logging),
                int(max_iterations) if isinstance(max_iterations, (int, float)) else 50,
            )
        elif self.agent_type == "multi_strategy":
            strategies = self.agent_config.get("strategies")
            default = self.agent_config.get("default_strategy")
            if not isinstance(strategies, dict) or not isinstance(default, str):
                raise ValueError("Multi-strategy agent requires 'strategies' and 'default_strategy'")
            return MultiStrategyAgent(strategies, default, self.toolbox, self.memory, self.controller)
        else:  # base
            return BaseAgent(self.strategy, self.toolbox, self.memory, self.controller)  # type: ignore[arg-type]

    def _create_strategy(self, config: StrategyConfig) -> Strategy:
        stype = config.get("type", "chain_of_thought")
        model = str(config.get("model", GeminiModel.GEMINI_2_5_FLASH))

        if stype == "react":
            max_iter = config.get("max_iterations", 10)
            return ReActStrategy(model, int(max_iter) if isinstance(max_iter, (int, float)) else 10)
        elif stype == "tree_of_thought":
            max_depth = config.get("max_depth", 3)
            branch = config.get("branch_factor", 3)
            return TreeOfThoughtStrategy(
                model,
                int(max_depth) if isinstance(max_depth, (int, float)) else 3,
                int(branch) if isinstance(branch, (int, float)) else 3,
            )
        else:  # chain_of_thought
            max_steps = config.get("max_steps", 10)
            return ChainOfThoughtStrategy(model, int(max_steps) if isinstance(max_steps, (int, float)) else 10)

    def _create_toolbox(self, config: ToolboxConfig) -> ToolBox:
        toolbox: ToolBox = CategorizableToolBox() if config.get("categorized") else ToolBox()
        tools = config.get("tools", [])
        if isinstance(tools, list):
            for tool_cfg in tools:
                if isinstance(tool_cfg, dict):
                    tool = self._create_tool(tool_cfg)
                    if tool:
                        category = tool_cfg.get("category")
                        if (
                            config.get("categorized")
                            and isinstance(category, str)
                            and isinstance(toolbox, CategorizableToolBox)
                        ):
                            toolbox.add_to_category(category, tool)
                        else:
                            toolbox.add(tool)
        return toolbox

    def _create_memory(self, config: MemoryConfig) -> Memory:
        mtype = config.get("type", "conversational")
        if mtype == "context":
            max_history = config.get("max_history", 100)
            return ContextMemory(int(max_history) if isinstance(max_history, (int, float)) else 100)
        max_turns = config.get("max_turns", 50)
        return ConversationalMemory(int(max_turns) if isinstance(max_turns, (int, float)) else 50)

    def _create_controller(self, config: ControllerConfig) -> ExecutionController:
        controller = ExecutionController()
        handlers = config.get("handlers", {})
        if not isinstance(handlers, dict):
            return controller

        self._add_max_steps_handler(controller, handlers)
        self._add_cost_limit_handler(controller, handlers)
        self._add_rate_limit_handler(controller, handlers)
        self._add_dangerous_action_handler(controller, handlers)
        self._add_loop_detection_handler(controller, handlers)
        return controller

    def _add_max_steps_handler(self, controller: ExecutionController, handlers: HandlersConfig) -> None:
        max_steps = handlers.get("max_steps")
        if isinstance(max_steps, (int, float)):
            controller.add_handler(MaxStepsHandler(int(max_steps)))

    def _add_cost_limit_handler(self, controller: ExecutionController, handlers: HandlersConfig) -> None:
        max_cost = handlers.get("max_cost")
        if isinstance(max_cost, (int, float)):
            controller.add_handler(CostLimitHandler(float(max_cost)))

    def _add_rate_limit_handler(self, controller: ExecutionController, handlers: HandlersConfig) -> None:
        max_calls = handlers.get("max_calls_per_tool")
        if isinstance(max_calls, (int, float)):
            controller.add_handler(ToolRateLimitHandler(int(max_calls)))

    def _add_dangerous_action_handler(self, controller: ExecutionController, handlers: HandlersConfig) -> None:
        if not handlers.get("enable_dangerous_action_filter", True):
            return
        dangerous_tools = handlers.get("dangerous_tools")
        controller.add_handler(DangerousActionHandler(dangerous_tools if isinstance(dangerous_tools, list) else None))

    def _add_loop_detection_handler(self, controller: ExecutionController, handlers: HandlersConfig) -> None:
        if not handlers.get("enable_loop_detection", True):
            return
        window = handlers.get("loop_window_size", 5)
        threshold = handlers.get("loop_threshold", 3)
        controller.add_handler(
            LoopDetectionHandler(
                int(window) if isinstance(window, (int, float)) else 5,
                int(threshold) if isinstance(threshold, (int, float)) else 3,
            )
        )

    def _create_tool(self, config: ToolConfig) -> Tool | None:
        ttype = config.get("type")
        tool_map: dict[str, Tool] = {
            "calculator": CalculatorTool(),
            "web_search": WebSearchTool(),
            "text_generator": TextGeneratorTool(),
        }
        return tool_map.get(ttype) if isinstance(ttype, str) else None


def create_agent_from_config(config: AgentConfig) -> BaseAgent:
    """Create an agent from a complete configuration."""
    builder = AgentBuilder()

    agent_type = config.get("type", "base")
    builder.with_agent_type(str(agent_type))

    strategy = config.get("strategy")
    if isinstance(strategy, dict):
        builder.with_strategy(strategy)

    toolbox = config.get("toolbox")
    if isinstance(toolbox, dict):
        builder.with_toolbox(toolbox)

    memory = config.get("memory")
    if isinstance(memory, dict):
        builder.with_memory(memory)

    controller = config.get("controller")
    if isinstance(controller, dict):
        builder.with_controller(controller)

    reserved_keys = {"type", "strategy", "toolbox", "memory", "controller"}
    extra = {k: v for k, v in config.items() if k not in reserved_keys}
    if extra:
        builder.with_config(**extra)

    return builder.build()
