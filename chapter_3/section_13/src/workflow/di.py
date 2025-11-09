"""
Dependency Injection for LLM Workflows - Consolidated Module.

This module provides all DI components (interfaces, implementations, container)
in a single file for simplicity.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Protocol, TypeVar, cast, runtime_checkable

from google.genai.types import GenerateContentConfig
from pydantic import BaseModel

from src.client.llm_client import GeminiModel, OpenAIModel, google_genai_client, openai_client
from src.logger import make_logger
from src.workflow.base import ExecutionContext

logger = make_logger(__name__)
T = TypeVar("T")


# ============================================================================
# Protocols (Interfaces)
# ============================================================================


@runtime_checkable
class IPromptBuilder(Protocol):
    """Interface for prompt building components."""

    def build_prompt(self, context: ExecutionContext) -> str | list[dict[str, Any]]: ...


@runtime_checkable
class ILLMClient(Protocol):
    """Interface for LLM client components."""

    async def generate(
        self, prompt: str | list[dict[str, Any]], context: ExecutionContext, **kwargs: Any
    ) -> dict[str, Any]: ...


@runtime_checkable
class IResponseParser(Protocol):
    """Interface for response parsing components."""

    def parse_response(self, raw_response: dict[str, Any], context: ExecutionContext) -> Any: ...


# ============================================================================
# Base Classes
# ============================================================================


class BasePromptBuilder(ABC):
    """Base class for prompt builders with template support."""

    def __init__(self, template: str | None = None):
        self.template = template

    @abstractmethod
    def build_prompt(self, context: ExecutionContext) -> str | list[dict[str, Any]]:
        pass

    def _format(self, context: ExecutionContext) -> str:
        return self.template.format(**context.variables) if self.template else ""


class BaseLLMClient(ABC):
    """Base class for LLM clients."""

    def __init__(self, model: str, **params: Any):
        self.model = model
        self.params = params

    @abstractmethod
    async def generate(
        self, prompt: str | list[dict[str, Any]], context: ExecutionContext, **kwargs: Any
    ) -> dict[str, Any]:
        pass


# ============================================================================
# Prompt Builder Implementations
# ============================================================================


class TemplatePromptBuilder(BasePromptBuilder):
    """Simple template-based prompt builder."""

    def build_prompt(self, context: ExecutionContext) -> str:
        return self._format(context) or str(context.get_variable("prompt", ""))


class MessageListPromptBuilder(BasePromptBuilder):
    """Builds chat message lists."""

    def __init__(self, system_message: str | None = None):
        super().__init__()
        self.system_message = system_message

    def build_prompt(self, context: ExecutionContext) -> list[dict[str, Any]]:
        messages = []
        if self.system_message:
            messages.append({"role": "system", "content": self.system_message})
        user_msg = context.get_variable("user_message", context.get_variable("prompt", ""))
        if user_msg:
            messages.append({"role": "user", "content": str(user_msg)})
        messages.extend(context.get_variable("conversation_history", []))
        return messages


class DynamicPromptBuilder(BasePromptBuilder):
    """Advanced prompt builder with history support."""

    def __init__(self, base_template: str | None = None, include_history: bool = False, max_history: int = 5):
        super().__init__(base_template)
        self.include_history = include_history
        self.max_history = max_history

    def build_prompt(self, context: ExecutionContext) -> str | list[dict[str, Any]]:
        if self.include_history and context.get_variable("conversation_history"):
            history = context.get_variable("conversation_history", [])[-self.max_history :]
            current = self._format(context) if self.template else str(context.get_variable("prompt", ""))
            return history + ([{"role": "user", "content": current}] if current else [])
        return self._format(context) if self.template else str(context.get_variable("prompt", ""))


# ============================================================================
# LLM Client Implementations
# ============================================================================


class OpenAILLMClient(BaseLLMClient):
    """OpenAI LLM client."""

    def __init__(self, model: str = OpenAIModel.GPT_4O_MINI, response_format: type[BaseModel] | None = None, **params):
        super().__init__(model, **params)
        self.response_format = response_format

    async def generate(self, prompt: str | list[dict[str, Any]], context: ExecutionContext, **kwargs) -> dict[str, Any]:
        messages = [{"role": "user", "content": prompt}] if isinstance(prompt, str) else prompt
        params = {**self.params, **kwargs}

        if self.response_format:
            result = await openai_client.responses.parse(
                model=self.model, input=messages, text_format=self.response_format, **params
            )
            return {
                "content": result.output_text,
                "parsed": result.output_parsed,
                "model": self.model,
                "usage": result.usage,
            }
        else:
            result = await openai_client.chat.completions.create(model=self.model, messages=messages, **params)
            return {
                "content": result.choices[0].message.content,
                "model": result.model,
                "usage": result.usage.model_dump() if result.usage else None,
                "finish_reason": result.choices[0].finish_reason,
            }


class GeminiLLMClient(BaseLLMClient):
    """Gemini LLM client."""

    def __init__(
        self,
        model: str = GeminiModel.GEMINI_2_5_FLASH,
        response_schema: type[BaseModel] | None = None,
        system_instruction: str | None = None,
        **params,
    ):
        super().__init__(model, **params)
        self.response_schema = response_schema
        self.system_instruction = system_instruction

    async def generate(self, prompt: str | list[dict[str, Any]], context: ExecutionContext, **kwargs) -> dict[str, Any]:
        # Extract content
        if isinstance(prompt, str):
            content = prompt
            sys_inst = self.system_instruction
        else:
            sys_inst = self.system_instruction
            content_parts = []
            for msg in prompt:
                if msg.get("role") == "system":
                    sys_inst = sys_inst or msg.get("content", "")
                else:
                    content_parts.append(msg.get("content", ""))
            content = "\n".join(content_parts)

        # Build config
        config_params = {**self.params, **kwargs}
        if sys_inst:
            config_params["system_instruction"] = sys_inst
        if self.response_schema:
            config_params["response_mime_type"] = "application/json"
            config_params["response_schema"] = self.response_schema

        result = await google_genai_client.aio.models.generate_content(
            model=self.model, contents=content, config=GenerateContentConfig(**config_params)
        )

        usage = {
            "prompt_tokens": result.usage_metadata.prompt_token_count if result.usage_metadata else None,
            "completion_tokens": result.usage_metadata.candidates_token_count if result.usage_metadata else None,
            "total_tokens": result.usage_metadata.total_token_count if result.usage_metadata else None,
        }

        return {
            "content": result.text,
            "parsed": result.parsed if self.response_schema else None,
            "model": self.model,
            "usage": usage,
            "finish_reason": result.candidates[0].finish_reason.name if result.candidates else None,
        }


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing."""

    def __init__(self, mock_response: str = "Mock response"):
        super().__init__("mock-model")
        self.mock_response = mock_response
        self.call_count = 0
        self.last_prompt: str | list[dict[str, Any]] | None = None

    async def generate(self, prompt: str | list[dict[str, Any]], context: ExecutionContext, **kwargs) -> dict[str, Any]:
        self.call_count += 1
        self.last_prompt = prompt
        return {
            "content": self.mock_response,
            "model": "mock-model",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            "finish_reason": "stop",
        }


# ============================================================================
# Response Parser Implementations
# ============================================================================


class TextResponseParser:
    """Extracts text content from responses."""

    def parse_response(self, raw_response: dict[str, Any], context: ExecutionContext) -> str:
        return raw_response.get("content", "")


class StructuredResponseParser:
    """Extracts parsed Pydantic models from responses."""

    def parse_response(self, raw_response: dict[str, Any], context: ExecutionContext) -> Any:
        return raw_response.get("parsed", raw_response.get("content", ""))


class JSONResponseParser:
    """Parses JSON from text responses."""

    def __init__(self, strict: bool = True):
        self.strict = strict

    def parse_response(self, raw_response: dict[str, Any], context: ExecutionContext) -> dict[str, Any] | str:
        import json

        content = raw_response.get("content", "")
        if not content:
            return {} if self.strict else ""

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            if self.strict:
                raise
            logger.warning(f"JSON parsing failed: {e}")
            return content


class EnhancedResponseParser:
    """Parser that includes metadata and usage tracking."""

    def parse_response(self, raw_response: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        # Track usage
        if usage := raw_response.get("usage"):
            total = context.get_variable("total_tokens_used", 0)
            context.set_variable("total_tokens_used", total + usage.get("total_tokens", 0))

        return {
            "content": raw_response.get("content", ""),
            "model": raw_response.get("model", "unknown"),
            "usage": raw_response.get("usage", {}),
            "finish_reason": raw_response.get("finish_reason", "unknown"),
            "parsed_data": raw_response.get("parsed"),
        }


# ============================================================================
# DI Container
# ============================================================================


class ServiceLifetime(str, Enum):
    """Service lifetime options."""

    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


class DIContainer:
    """Lightweight dependency injection container."""

    def __init__(self):
        self._services: dict[type, tuple[Callable, ServiceLifetime, Any]] = {}
        self._scoped: dict[str, dict[type, Any]] = {}

    def register(
        self,
        service_type: type[T],
        impl: Callable[..., T] | type[T] | None = None,
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
    ) -> DIContainer:
        """Register a service."""
        self._services[service_type] = (impl or service_type, lifetime, None)
        return self

    def register_singleton(self, service_type: type[T], impl: Callable[..., T] | type[T] | None = None) -> DIContainer:
        return self.register(service_type, impl, ServiceLifetime.SINGLETON)

    def register_transient(self, service_type: type[T], impl: Callable[..., T] | type[T] | None = None) -> DIContainer:
        return self.register(service_type, impl, ServiceLifetime.TRANSIENT)

    def register_scoped(self, service_type: type[T], impl: Callable[..., T] | type[T] | None = None) -> DIContainer:
        return self.register(service_type, impl, ServiceLifetime.SCOPED)

    def register_instance(self, service_type: type[T], instance: T) -> DIContainer:
        """Register an existing instance as singleton."""
        self._services[service_type] = (lambda: instance, ServiceLifetime.SINGLETON, instance)
        return self

    def resolve(self, service_type: type[T], scope_id: str | None = None) -> T:
        """Resolve a service from the container."""
        if service_type not in self._services:
            raise ValueError(f"Service {service_type.__name__} not registered")

        impl, lifetime, instance = self._services[service_type]

        if lifetime == ServiceLifetime.SINGLETON:
            if instance is None:
                instance = impl() if callable(impl) else impl
                self._services[service_type] = (impl, lifetime, instance)
            return cast(T, instance)

        elif lifetime == ServiceLifetime.SCOPED:
            if not scope_id:
                raise ValueError(f"Scope ID required for {service_type.__name__}")
            if scope_id not in self._scoped:
                self._scoped[scope_id] = {}
            if service_type not in self._scoped[scope_id]:
                self._scoped[scope_id][service_type] = impl() if callable(impl) else impl
            return cast(T, self._scoped[scope_id][service_type])

        else:  # TRANSIENT
            return cast(T, impl() if callable(impl) else impl)

    def create_scope(self, scope_id: str) -> DIScope:
        """Create a new dependency injection scope."""
        return DIScope(self, scope_id)

    def clear_scope(self, scope_id: str) -> None:
        """Clear scoped instances."""
        self._scoped.pop(scope_id, None)


class DIScope:
    """Represents a DI scope for managing scoped service lifetimes."""

    def __init__(self, container: DIContainer, scope_id: str):
        self.container = container
        self.scope_id = scope_id

    def resolve(self, service_type: type[T]) -> T:
        return self.container.resolve(service_type, self.scope_id)

    def __enter__(self) -> DIScope:
        return self

    def __exit__(self, *args) -> None:
        self.container.clear_scope(self.scope_id)


# Type aliases
PromptBuilder = IPromptBuilder
LLMClient = ILLMClient
ResponseParser = IResponseParser
