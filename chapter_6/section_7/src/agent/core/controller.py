"""Execution controller with Chain of Responsibility pattern.

This module defines the abstract handler interface and controller for managing
action execution. Concrete handler implementations should be placed in the
extensions layer.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.agent.core.base import Action, MetadataDict


@dataclass
class ExecutionRequest:
    """Request to execute an action."""

    action: Action
    context: dict[str, object]
    metadata: MetadataDict | None = None


@dataclass
class ExecutionResponse:
    """Response from execution control."""

    allowed: bool
    reason: str | None = None
    metadata: MetadataDict | None = None


class ExecutionHandler(ABC):
    """Abstract handler in chain of responsibility.

    This interface defines how execution requests are processed.
    Concrete handlers (e.g., rate limiting, cost control) should be
    implemented in the extensions layer.
    """

    def __init__(self):
        self._next_handler: ExecutionHandler | None = None

    def set_next(self, handler: "ExecutionHandler") -> "ExecutionHandler":
        self._next_handler = handler
        return handler

    def handle(self, request: ExecutionRequest) -> ExecutionResponse:
        response = self._check(request)
        if not response.allowed or not self._next_handler:
            return response
        return self._next_handler.handle(request)

    @abstractmethod
    def _check(self, request: ExecutionRequest) -> ExecutionResponse:
        pass

    def reset(self) -> None:
        pass


class ExecutionController:
    """Main execution controller that manages the chain of handlers.

    This controller orchestrates a chain of ExecutionHandler instances
    to validate and control action execution.
    """

    def __init__(self):
        self.handlers: list[ExecutionHandler] = []
        self._chain_head: ExecutionHandler | None = None

    def add_handler(self, handler: ExecutionHandler) -> "ExecutionController":
        self.handlers.append(handler)
        self._rebuild_chain()
        return self

    def check_execution(self, request: ExecutionRequest) -> ExecutionResponse:
        return self._chain_head.handle(request) if self._chain_head else ExecutionResponse(allowed=True)

    def reset_all(self) -> None:
        for handler in self.handlers:
            handler.reset()

    def _rebuild_chain(self) -> None:
        if not self.handlers:
            self._chain_head = None
            return
        self._chain_head = self.handlers[0]
        for i in range(len(self.handlers) - 1):
            self.handlers[i].set_next(self.handlers[i + 1])
