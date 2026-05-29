"""Mediator pattern for managing complex agent interactions."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.agent.agent import BaseAgent
from src.agent.base import MetadataDict


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


class Node(ABC):
    """Abstract base class for nodes in the agent graph."""

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


class AgentNode(Node):
    """Node representing an agent."""

    def __init__(self, node_id: str, agent: BaseAgent):
        super().__init__(node_id, NodeType.AGENT)
        self.agent = agent

    def execute(self, input_data: str | dict | list) -> NodeResult:
        try:
            result = self.agent.execute(str(input_data))
            return NodeResult(node_id=self.node_id, success=True, output=result)
        except Exception as e:
            return NodeResult(node_id=self.node_id, success=False, output=None, error=str(e))


class DecisionNode(Node):
    """Node that makes routing decisions based on conditions."""

    def __init__(self, node_id: str, decision_fn: Callable[[str | dict | list], str]):
        super().__init__(node_id, NodeType.DECISION)
        self.decision_fn = decision_fn

    def execute(self, input_data: str | dict | list) -> NodeResult:
        try:
            next_node_id = self.decision_fn(input_data)
            return NodeResult(
                node_id=self.node_id,
                success=True,
                output=next_node_id,
                metadata={"decision": "route_to", "next_node": next_node_id},
            )
        except Exception as e:
            return NodeResult(node_id=self.node_id, success=False, output=None, error=str(e))


class AggregatorNode(Node):
    """Node that aggregates results from multiple sources."""

    def __init__(self, node_id: str, aggregation_fn: Callable[[list[str | dict | list]], str | dict | list]):
        super().__init__(node_id, NodeType.AGGREGATOR)
        self.aggregation_fn = aggregation_fn
        self.pending_inputs: list[str | dict | list] = []

    def execute(self, input_data: str | dict | list) -> NodeResult:
        try:
            if isinstance(input_data, list):
                self.pending_inputs.extend(input_data)
            else:
                self.pending_inputs.append(input_data)
            result = self.aggregation_fn(self.pending_inputs)
            self.pending_inputs.clear()
            return NodeResult(node_id=self.node_id, success=True, output=result)
        except Exception as e:
            return NodeResult(node_id=self.node_id, success=False, output=None, error=str(e))


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


class GraphMediator(ABC):
    """Abstract mediator for managing node interactions."""

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


class SimpleGraphMediator(GraphMediator):
    """Simple implementation of graph mediator."""

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, list[Edge]] = {}
        self.message_log: list[Message] = []
        self.execution_log: list[ExecutionLogEntry] = []
        self._visited: set[str] = set()
        self._results: dict[str, NodeResult] = {}

    def add_node(self, node: Node) -> None:
        self.nodes[node.node_id] = node
        node.set_mediator(self)

    def add_edge(self, edge: Edge) -> None:
        self.edges.setdefault(edge.source_id, []).append(edge)

    def execute_graph(self, start_node_id: str, input_data: str | dict | list) -> GraphExecutionResult:
        if start_node_id not in self.nodes:
            return self._create_error_result(f"Start node '{start_node_id}' not found")

        self._reset_execution_state()
        final_result = self._execute_node(start_node_id, input_data)
        return self._create_success_result(final_result)

    def _reset_execution_state(self) -> None:
        """Reset state for new execution."""
        self._visited = set()
        self._results = {}

    def _create_error_result(self, error: str) -> GraphExecutionResult:
        """Create an error result."""
        return GraphExecutionResult(
            success=False, results={}, final_output=None, execution_log=[], message_log=[], error=error
        )

    def _create_success_result(self, final_result: NodeResult) -> GraphExecutionResult:
        """Create a success result from final node result."""
        return GraphExecutionResult(
            success=final_result.success,
            results=self._results.copy(),
            final_output=final_result.output,
            execution_log=self.execution_log.copy(),
            message_log=self.message_log.copy(),
        )

    def _execute_node(self, node_id: str, data: str | dict | list) -> NodeResult:
        """Execute a single node and process its edges."""
        if node_id in self._visited:
            return NodeResult(node_id=node_id, success=False, output=None, error="Cycle detected")

        self._visited.add(node_id)
        result = self.nodes[node_id].execute(data)
        self._results[node_id] = result
        self._log_execution(node_id, result)

        if result.success:
            self._process_edges(node_id, result.output)

        return result

    def _log_execution(self, node_id: str, result: NodeResult, parallel: bool = False) -> None:
        """Log node execution."""
        self.execution_log.append(
            ExecutionLogEntry(
                timestamp=datetime.now(),
                node_id=node_id,
                success=result.success,
                output=result.output,
                parallel=parallel,
            )
        )

    def _process_edges(self, node_id: str, output: str | dict | list | None) -> None:
        """Process outgoing edges from a node."""
        if node_id not in self.edges:
            return
        for edge in self.edges[node_id]:
            if self._should_follow_edge(edge, output):
                self._execute_node(edge.target_id, output or "")

    def _should_follow_edge(self, edge: Edge, output: str | dict | list | None) -> bool:
        """Check if an edge should be followed."""
        if edge.edge_type == EdgeType.CONDITIONAL:
            return edge.condition is None or edge.condition(output)
        return True

    def route_message(self, message: Message) -> None:
        self.message_log.append(message)
        if message.receiver_id and message.receiver_id in self.nodes:
            self.nodes[message.receiver_id].execute(message.content)
        elif not message.receiver_id:
            self._broadcast_message(message)

    def _broadcast_message(self, message: Message) -> None:
        """Broadcast message to all nodes except sender."""
        for node_id, node in self.nodes.items():
            if node_id != message.sender_id:
                node.execute(message.content)


class ParallelGraphMediator(SimpleGraphMediator):
    """Graph mediator with support for parallel execution."""

    def _execute_node(self, node_id: str, data: str | dict | list) -> NodeResult:
        """Execute a node with support for parallel edges."""
        if node_id in self._visited:
            cached = self._results.get(node_id)
            if cached:
                return cached
            return NodeResult(node_id=node_id, success=False, output=None, error="Cycle")

        self._visited.add(node_id)
        result = self.nodes[node_id].execute(data)
        self._results[node_id] = result
        self._log_execution(node_id, result, parallel=False)

        if result.success:
            self._process_parallel_and_sequential_edges(node_id, result.output)

        return result

    def _process_parallel_and_sequential_edges(self, node_id: str, output: str | dict | list | None) -> None:
        """Process edges with parallel/sequential distinction."""
        if node_id not in self.edges:
            return

        parallel_targets, sequential_targets = self._categorize_edges(node_id)
        self._execute_parallel_nodes(parallel_targets, output)
        self._execute_sequential_nodes(sequential_targets, output)

    def _categorize_edges(self, node_id: str) -> tuple[list[str], list[str]]:
        """Categorize edges into parallel and sequential targets."""
        parallel = [e.target_id for e in self.edges[node_id] if e.edge_type == EdgeType.PARALLEL]
        sequential = [e.target_id for e in self.edges[node_id] if e.edge_type != EdgeType.PARALLEL]
        return parallel, sequential

    def _execute_parallel_nodes(self, targets: list[str], output: str | dict | list | None) -> None:
        """Execute parallel nodes."""
        for target_id in targets:
            if target_id not in self._visited:
                self._visited.add(target_id)
                result = self.nodes[target_id].execute(output or "")
                self._results[target_id] = result
                self._log_execution(target_id, result, parallel=True)

    def _execute_sequential_nodes(self, targets: list[str], output: str | dict | list | None) -> None:
        """Execute sequential nodes."""
        for target_id in targets:
            self._execute_node(target_id, output or "")
