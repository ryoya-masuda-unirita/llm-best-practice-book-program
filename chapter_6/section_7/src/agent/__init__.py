"""AI Agent Framework with comprehensive design patterns.

This package is organized into two layers following the "Stable Core and
Flexible Extensions" architecture pattern:

Core Layer (src.agent.core):
    Contains stable abstractions and base classes that rarely change.
    - Abstract base classes (ABCs) defining interfaces
    - Core data structures and type definitions
    - Base agent orchestration logic
    - State machine framework
    - Execution control abstractions

Extension Layer (src.agent.extensions):
    Contains concrete implementations that can evolve independently.
    - Specific LLM-based strategies (CoT, ReAct, ToT)
    - Concrete memory implementations
    - Execution handlers (rate limiting, cost control)
    - Tool implementations
    - Specialized agents
    - Graph mediators and nodes

For backward compatibility, all public APIs are re-exported from this module.
"""

from src.agent.core import (
    ActingState,
    Action,
    ActionType,
    AgentContext,
    AgentEvent,
    AgentState,
    AgentStatus,
    BaseAgent,
    CompletedState,
    ContextData,
    Edge,
    EdgeType,
    ErrorState,
    ExecutionController,
    ExecutionHandler,
    ExecutionLogEntry,
    ExecutionRequest,
    ExecutionResponse,
    GraphExecutionResult,
    GraphMediator,
    IdleState,
    Memory,
    MemorySnapshot,
    Message,
    MetadataDict,
    Node,
    NodeResult,
    NodeType,
    ParamValue,
    PausedState,
    StateTransition,
    StepInfo,
    Strategy,
    ThinkingState,
    Tool,
    ToolBox,
    ToolData,
    ToolParams,
    ToolResult,
    WaitingState,
)
from src.agent.extensions import (
    AgentBuilder,
    AgentNode,
    AggregatorNode,
    BaseStrategy,
    CalculatorTool,
    CategorizableToolBox,
    ChainOfThoughtStrategy,
    ConfigurableAgent,
    ContextMemory,
    ConversationalMemory,
    CostLimitHandler,
    DangerousActionHandler,
    DecisionNode,
    LoopDetectionHandler,
    MaxStepsHandler,
    MemoryCaretaker,
    MultiStrategyAgent,
    ParallelGraphMediator,
    ReActStrategy,
    SimpleGraphMediator,
    ToolRateLimitHandler,
    TreeOfThoughtStrategy,
    WebSearchTool,
    create_agent_from_config,
    create_default_controller,
)

__all__ = [
    "Action",
    "ActionType",
    "ActingState",
    "AgentBuilder",
    "AgentContext",
    "AgentEvent",
    "AgentNode",
    "AgentState",
    "AgentStatus",
    "AggregatorNode",
    "BaseAgent",
    "BaseStrategy",
    "CalculatorTool",
    "CategorizableToolBox",
    "ChainOfThoughtStrategy",
    "CompletedState",
    "ConfigurableAgent",
    "ContextData",
    "ContextMemory",
    "ConversationalMemory",
    "CostLimitHandler",
    "DangerousActionHandler",
    "DecisionNode",
    "Edge",
    "EdgeType",
    "ErrorState",
    "ExecutionController",
    "ExecutionHandler",
    "ExecutionLogEntry",
    "ExecutionRequest",
    "ExecutionResponse",
    "GraphExecutionResult",
    "GraphMediator",
    "IdleState",
    "LoopDetectionHandler",
    "MaxStepsHandler",
    "Memory",
    "MemoryCaretaker",
    "MemorySnapshot",
    "Message",
    "MetadataDict",
    "MultiStrategyAgent",
    "Node",
    "NodeResult",
    "NodeType",
    "ParallelGraphMediator",
    "ParamValue",
    "PausedState",
    "ReActStrategy",
    "SimpleGraphMediator",
    "StateTransition",
    "StepInfo",
    "Strategy",
    "ThinkingState",
    "Tool",
    "ToolBox",
    "ToolData",
    "ToolParams",
    "ToolRateLimitHandler",
    "ToolResult",
    "TreeOfThoughtStrategy",
    "WaitingState",
    "WebSearchTool",
    "create_agent_from_config",
    "create_default_controller",
]
