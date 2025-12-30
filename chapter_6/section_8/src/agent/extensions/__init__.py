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
    CompactionResult,
    ConservativeLockMemory,
    ContextMemory,
    ConversationalMemory,
    ImmutableMemory,
    ImmutableMemoryEntry,
    LocalDictLockManager,
    LockAcquisitionError,
    LockHandle,
    LockInfo,
    LockManager,
    LockNotHeldError,
    MemoryCaretaker,
    MemoryDocument,
    MemoryEntry,
    MemoryEntryType,
    OptimisticLockConflictError,
    OptimisticLockMemory,
    OptimisticTransaction,
    PreemptedError,
    PreemptibleLockMemory,
    SessionMemory,
    ShadowCopy,
    VersionMismatchError,
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
    "CompactionResult",
    "ConfigurableAgent",
    "ConservativeLockMemory",
    "ContextMemory",
    "ConversationalMemory",
    "CostLimitHandler",
    "DangerousActionHandler",
    "DecisionNode",
    "ImmutableMemory",
    "ImmutableMemoryEntry",
    "LocalDictLockManager",
    "LockAcquisitionError",
    "LockHandle",
    "LockInfo",
    "LockManager",
    "LockNotHeldError",
    "LoopDetectionHandler",
    "MaxStepsHandler",
    "MemoryCaretaker",
    "MemoryDocument",
    "MemoryEntry",
    "MemoryEntryType",
    "MultiStrategyAgent",
    "OptimisticLockConflictError",
    "OptimisticLockMemory",
    "OptimisticTransaction",
    "ParallelGraphMediator",
    "PreemptedError",
    "PreemptibleLockMemory",
    "ReActStrategy",
    "SessionMemory",
    "ShadowCopy",
    "SimpleGraphMediator",
    "TextGeneratorTool",
    "ToolRateLimitHandler",
    "TreeOfThoughtStrategy",
    "VersionMismatchError",
    "WebSearchTool",
    "create_agent_from_config",
    "create_default_controller",
]
