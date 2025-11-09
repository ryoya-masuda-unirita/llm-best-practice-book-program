"""AI Agent Framework with comprehensive design patterns."""

# Base abstractions
# Agent implementations
from src.agent.agent import BaseAgent, ConfigurableAgent, MultiStrategyAgent
from src.agent.base import Action, ActionType, Memory, Strategy, Tool, ToolResult

# Execution control
from src.agent.controller import (
    CostLimitHandler,
    DangerousActionHandler,
    ExecutionController,
    ExecutionHandler,
    ExecutionRequest,
    ExecutionResponse,
    LoopDetectionHandler,
    MaxStepsHandler,
    ToolRateLimitHandler,
    create_default_controller,
)

# Factory and Builder
from src.agent.factory import (
    AgentBuilder,
    create_agent_from_config,
)

# Mediator for multi-agent coordination
from src.agent.mediator import (
    AgentNode,
    AggregatorNode,
    DecisionNode,
    Edge,
    EdgeType,
    GraphMediator,
    Message,
    Node,
    NodeResult,
    NodeType,
    ParallelGraphMediator,
    SimpleGraphMediator,
)

# Memory implementations
from src.agent.memory import (
    ContextMemory,
    ConversationalMemory,
    MemoryCaretaker,
    MemorySnapshot,
)

# State management
from src.agent.states import (
    ActingState,
    AgentContext,
    AgentState,
    AgentStatus,
    CompletedState,
    ErrorState,
    IdleState,
    PausedState,
    ThinkingState,
    WaitingState,
)

# Thinking strategies
from src.agent.strategies import (
    ChainOfThoughtStrategy,
    ReActStrategy,
    TreeOfThoughtStrategy,
)

# ToolBox implementations
from src.agent.toolbox import (
    CalculatorTool,
    CategorizableToolBox,
    ToolBox,
    WebSearchTool,
)

__all__ = [
    # Base
    "Action",
    "ActionType",
    "Memory",
    "Strategy",
    "Tool",
    "ToolResult",
    # Agents
    "BaseAgent",
    "ConfigurableAgent",
    "MultiStrategyAgent",
    # Memory
    "ContextMemory",
    "ConversationalMemory",
    "MemoryCaretaker",
    "MemorySnapshot",
    # ToolBox
    "ToolBox",
    "CategorizableToolBox",
    "CalculatorTool",
    "WebSearchTool",
    # Strategies
    "ChainOfThoughtStrategy",
    "ReActStrategy",
    "TreeOfThoughtStrategy",
    # States
    "AgentState",
    "AgentStatus",
    "AgentContext",
    "IdleState",
    "ThinkingState",
    "ActingState",
    "WaitingState",
    "CompletedState",
    "ErrorState",
    "PausedState",
    # Controller
    "ExecutionController",
    "ExecutionHandler",
    "ExecutionRequest",
    "ExecutionResponse",
    "MaxStepsHandler",
    "CostLimitHandler",
    "ToolRateLimitHandler",
    "DangerousActionHandler",
    "LoopDetectionHandler",
    "create_default_controller",
    # Factory & Builder
    "AgentBuilder",
    "create_agent_from_config",
    # Mediator
    "Node",
    "NodeType",
    "NodeResult",
    "AgentNode",
    "DecisionNode",
    "AggregatorNode",
    "Edge",
    "EdgeType",
    "Message",
    "GraphMediator",
    "SimpleGraphMediator",
    "ParallelGraphMediator",
]
