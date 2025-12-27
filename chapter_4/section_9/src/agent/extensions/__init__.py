"""Extension layer - Concrete implementations and customizable components.

This layer contains implementations that can change independently from the core:
- Specific LLM-based strategies (CoT, ReAct, ToT)
- Concrete memory implementations
- Execution handlers (rate limiting, cost control)
- Tool implementations
- Specialized agents
- Graph mediators and nodes
"""

from src.agent.extensions.agents import ConfigurableAgent, MultiStrategyAgent
from src.agent.extensions.factory import (
    AgentBuilder,
    create_agent_from_config,
)
from src.agent.extensions.handlers import (
    CostLimitHandler,
    DangerousActionHandler,
    LoopDetectionHandler,
    MaxStepsHandler,
    ToolRateLimitHandler,
    create_default_controller,
)
from src.agent.extensions.mediators import (
    ParallelGraphMediator,
    SimpleGraphMediator,
)
from src.agent.extensions.memory import (
    ContextMemory,
    ConversationalMemory,
    MemoryCaretaker,
)
from src.agent.extensions.nodes import (
    AgentNode,
    AggregatorNode,
    DecisionNode,
)
from src.agent.extensions.strategies import (
    BaseStrategy,
    ChainOfThoughtStrategy,
    ReActStrategy,
    TreeOfThoughtStrategy,
)
from src.agent.extensions.tools import (
    CalculatorTool,
    CategorizableToolBox,
    TextGeneratorTool,
    WebSearchTool,
)

__all__ = [
    "AgentBuilder",
    "AgentNode",
    "AggregatorNode",
    "BaseStrategy",
    "CalculatorTool",
    "CategorizableToolBox",
    "ChainOfThoughtStrategy",
    "ConfigurableAgent",
    "ContextMemory",
    "ConversationalMemory",
    "CostLimitHandler",
    "DangerousActionHandler",
    "DecisionNode",
    "LoopDetectionHandler",
    "MaxStepsHandler",
    "MemoryCaretaker",
    "MultiStrategyAgent",
    "ParallelGraphMediator",
    "ReActStrategy",
    "SimpleGraphMediator",
    "TextGeneratorTool",
    "ToolRateLimitHandler",
    "TreeOfThoughtStrategy",
    "WebSearchTool",
    "create_agent_from_config",
    "create_default_controller",
]
