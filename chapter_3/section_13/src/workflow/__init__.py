"""Workflow orchestration engine for LLM-based workflows with Dependency Injection."""

from src.workflow.builder import WorkflowBuilder

# Dependency Injection components (consolidated in di.py)
from src.workflow.di import (
    BaseLLMClient,
    BasePromptBuilder,
    DIContainer,
    DIScope,
    DynamicPromptBuilder,
    EnhancedResponseParser,
    GeminiLLMClient,
    ILLMClient,
    IPromptBuilder,
    IResponseParser,
    JSONResponseParser,
    MessageListPromptBuilder,
    MockLLMClient,
    OpenAILLMClient,
    ServiceLifetime,
    StructuredResponseParser,
    TemplatePromptBuilder,
    TextResponseParser,
)
from src.workflow.engine import WorkflowEngine
from src.workflow.nodes import EndNode, IfElseNode, LoopNode, PromptNode, PythonScriptNode, StartNode
from src.workflow.state import ExecutionState, WorkflowState
from src.workflow.workflow import Workflow

# Optional: LLM executor helpers (legacy)
try:
    from src.workflow import llm_executors
except ImportError:
    llm_executors = None

__all__ = [
    # Core workflow components
    "WorkflowBuilder",
    "WorkflowEngine",
    "StartNode",
    "EndNode",
    "PromptNode",
    "IfElseNode",
    "LoopNode",
    "PythonScriptNode",
    "ExecutionState",
    "WorkflowState",
    "Workflow",
    # Dependency Injection
    "DIContainer",
    "DIScope",
    "ServiceLifetime",
    # DI Interfaces
    "IPromptBuilder",
    "ILLMClient",
    "IResponseParser",
    "BasePromptBuilder",
    "BaseLLMClient",
    "BaseResponseParser",
    # DI Implementations
    "TemplatePromptBuilder",
    "MessageListPromptBuilder",
    "DynamicPromptBuilder",
    "OpenAILLMClient",
    "GeminiLLMClient",
    "MockLLMClient",
    "TextResponseParser",
    "StructuredResponseParser",
    "JSONResponseParser",
    "EnhancedResponseParser",
    # Legacy
    "llm_executors",
]
