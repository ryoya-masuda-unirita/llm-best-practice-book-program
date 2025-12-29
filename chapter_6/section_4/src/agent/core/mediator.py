"""Mediator pattern for managing complex agent interactions.

This module defines the abstract interfaces for graph-based agent coordination.
Concrete node and mediator implementations should be placed in the extensions layer.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.agent.core.base import MetadataDict


class NodeType(Enum):
    """Types of nodes in the agent graph."""

    AGENT = "agent"
    DECISION = "decision"
    AGGREGATOR = "aggregator"


class EdgeType(Enum):
    """Types of edges between nodes."""

    SEQUENTIAL = "sequential"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"


@dataclass
class Message:
    """Message passed between nodes."""

    sender_id: str
    receiver_id: str | None
    content: str | dict | list
    message_type: str = "data"
    metadata: MetadataDict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class NodeResult:
    """Result from a node execution."""

    node_id: str
    success: bool
    output: str | dict | list | None
    error: str | None = None
    metadata: MetadataDict = field(default_factory=dict)


@dataclass
class ExecutionLogEntry:
    """An entry in the execution log."""

    timestamp: datetime
    node_id: str
    success: bool
    output: str | dict | list | None
    parallel: bool = False


@dataclass
class Edge:
    """Edge connecting two nodes."""

    source_id: str
    target_id: str
    edge_type: EdgeType = EdgeType.SEQUENTIAL
    condition: Callable[[str | dict | list | None], bool] | None = None
    weight: float = 1.0


@dataclass
class GraphExecutionResult:
    """Result from executing a graph."""

    success: bool
    results: dict[str, NodeResult]
    final_output: str | dict | list | None
    execution_log: list[ExecutionLogEntry]
    message_log: list[Message]
    error: str | None = None


class Node(ABC):
    """Abstract base class for nodes in the agent graph.

    This interface defines how nodes execute and communicate.
    Concrete node implementations should be placed in the extensions layer.
    """

    def __init__(self, node_id: str, node_type: NodeType):
        self.node_id = node_id
        self.node_type = node_type
        self.mediator: "GraphMediator | None" = None

    def set_mediator(self, mediator: "GraphMediator") -> None:
        self.mediator = mediator

    @abstractmethod
    def execute(self, input_data: str | dict | list) -> NodeResult:
        pass

    def send_message(self, receiver_id: str | None, content: str | dict | list, message_type: str = "data") -> None:
        if self.mediator:
            self.mediator.route_message(Message(self.node_id, receiver_id, content, message_type))


class GraphMediator(ABC):
    """Abstract mediator for managing node interactions.

    This interface defines how graphs are constructed and executed.
    Concrete mediator implementations should be placed in the extensions layer.
    """

    @abstractmethod
    def add_node(self, node: Node) -> None:
        pass

    @abstractmethod
    def add_edge(self, edge: Edge) -> None:
        pass

    @abstractmethod
    def execute_graph(self, start_node_id: str, input_data: str | dict | list) -> GraphExecutionResult:
        pass

    @abstractmethod
    def route_message(self, message: Message) -> None:
        pass
