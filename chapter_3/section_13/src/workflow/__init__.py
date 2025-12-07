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

__all__ = [
    # Core workflow components
    "WorkflowBuilder",
    "WorkflowEngine",
    "Workflow",
    "StartNode",
    "EndNode",
    "PromptNode",
    "IfElseNode",
    "LoopNode",
    "PythonScriptNode",
    "ExecutionState",
    "WorkflowState",
    # Dependency Injection
    "DIContainer",
    "DIScope",
    "ServiceLifetime",
    # DI Interfaces
    "IPromptBuilder",
    "ILLMClient",
    "IResponseParser",
    # DI Base Classes
    "BasePromptBuilder",
    "BaseLLMClient",
    # DI Implementations - Prompt Builders
    "TemplatePromptBuilder",
    "MessageListPromptBuilder",
    "DynamicPromptBuilder",
    # DI Implementations - LLM Clients
    "OpenAILLMClient",
    "GeminiLLMClient",
    "MockLLMClient",
    # DI Implementations - Response Parsers
    "TextResponseParser",
    "StructuredResponseParser",
    "JSONResponseParser",
    "EnhancedResponseParser",
]
