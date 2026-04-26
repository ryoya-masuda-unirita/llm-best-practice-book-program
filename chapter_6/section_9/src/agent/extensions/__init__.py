"""Extension layer - Concrete implementations and customizable components.

This layer contains implementations that can change independently from the core:
- Specific LLM-based strategies (CoT, ReAct, ToT)
- Concrete memory implementations
- Execution handlers (rate limiting, cost control)
- Tool implementations
- Specialized agents
- Graph mediators and nodes
- Article generation pipeline components
- Replay mechanism for WAL-based prompt replay
- Speculative execution for parallel-world branching
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
    ArticlePipelineMediator,
    ParallelGraphMediator,
    PipelineResult,
    SimpleGraphMediator,
    run_article_pipeline,
)
from src.agent.extensions.memory import (
    ContextMemory,
    ConversationalMemory,
    MemoryCaretaker,
    PipelineMemory,
    PipelineMemoryCaretaker,
    PipelinePhaseSnapshot,
    create_initial_state,
)
from src.agent.extensions.nodes import (
    AgentNode,
    AggregatorNode,
    ArticleReviewNode,
    DecisionNode,
    FirstHalfGenerationNode,
    HumanDecisionNode,
    OutlineGenerationNode,
    PipelineState,
    SecondHalfGenerationNode,
    SecondHalfRegenerationNode,
)
from src.agent.extensions.replay import (
    PromptLog,
    PromptLogEntry,
    PromptType,
    ReplayDecision,
    ReplayDiff,
    ReplayEngine,
    ReplayFilter,
    ReplayResult,
)
from src.agent.extensions.speculative import (
    BranchDetector,
    World,
    WorldManager,
    WorldStatus,
    WorldSummary,
)
from src.agent.extensions.strategies import (
    BaseStrategy,
    ChainOfThoughtStrategy,
    ReActStrategy,
    TreeOfThoughtStrategy,
)
from src.agent.extensions.tools import (
    ArticleReviewerTool,
    BestFirstHalfSelectorTool,
    CalculatorTool,
    CategorizableToolBox,
    FirstHalfGeneratorTool,
    GenerationToolBox,
    OutlineGeneratorTool,
    SecondHalfGeneratorTool,
    SecondHalfRegeneratorTool,
    TextGeneratorTool,
    WebSearchTool,
)

__all__ = [
    # Agents
    "AgentBuilder",
    "ConfigurableAgent",
    "MultiStrategyAgent",
    "create_agent_from_config",
    # Handlers
    "CostLimitHandler",
    "DangerousActionHandler",
    "LoopDetectionHandler",
    "MaxStepsHandler",
    "ToolRateLimitHandler",
    "create_default_controller",
    # Mediators
    "ArticlePipelineMediator",
    "ParallelGraphMediator",
    "PipelineResult",
    "SimpleGraphMediator",
    "run_article_pipeline",
    # Memory
    "ContextMemory",
    "ConversationalMemory",
    "MemoryCaretaker",
    "PipelineMemory",
    "PipelineMemoryCaretaker",
    "PipelinePhaseSnapshot",
    "create_initial_state",
    # Nodes
    "AgentNode",
    "AggregatorNode",
    "ArticleReviewNode",
    "DecisionNode",
    "FirstHalfGenerationNode",
    "HumanDecisionNode",
    "OutlineGenerationNode",
    "PipelineState",
    "SecondHalfGenerationNode",
    "SecondHalfRegenerationNode",
    # Replay
    "PromptLog",
    "PromptLogEntry",
    "PromptType",
    "ReplayDecision",
    "ReplayDiff",
    "ReplayEngine",
    "ReplayFilter",
    "ReplayResult",
    # Speculative
    "BranchDetector",
    "World",
    "WorldManager",
    "WorldStatus",
    "WorldSummary",
    # Strategies
    "BaseStrategy",
    "ChainOfThoughtStrategy",
    "ReActStrategy",
    "TreeOfThoughtStrategy",
    # Tools
    "ArticleReviewerTool",
    "BestFirstHalfSelectorTool",
    "CalculatorTool",
    "CategorizableToolBox",
    "FirstHalfGeneratorTool",
    "GenerationToolBox",
    "OutlineGeneratorTool",
    "SecondHalfGeneratorTool",
    "SecondHalfRegeneratorTool",
    "TextGeneratorTool",
    "WebSearchTool",
]
