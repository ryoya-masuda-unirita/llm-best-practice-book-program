"""Base classes and interfaces for workflow nodes (Composite Pattern)."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ExecutionContext(BaseModel):
    """Context object that carries data between nodes (Chain of Responsibility)."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="allow",
        arbitrary_types_allowed=True,
    )

    workflow_id: str = Field(default_factory=lambda: uuid4().hex, description="Workflow execution ID")
    variables: dict[str, Any] = Field(default_factory=dict, description="Workflow variables")
    node_outputs: dict[str, Any] = Field(default_factory=dict, description="Outputs from each node")
    error: str | None = Field(default=None, description="Error message if any")

    def set_variable(self, key: str, value: Any) -> None:
        """Set a workflow variable."""
        self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a workflow variable."""
        return self.variables.get(key, default)

    def set_node_output(self, node_id: str, output: Any) -> None:
        """Set output from a node."""
        self.node_outputs[node_id] = output

    def get_node_output(self, node_id: str, default: Any = None) -> Any:
        """Get output from a node."""
        return self.node_outputs.get(node_id, default)


class NodeExecutionStrategy(ABC):
    """Strategy Pattern: Defines the interface for node execution strategies."""

    @abstractmethod
    async def execute(self, context: ExecutionContext) -> Any:
        """Execute the node logic."""
        pass


class Node(ABC):
    """
    Composite Pattern: Base class for all workflow nodes.
    Provides a unified interface for treating individual nodes and workflows hierarchically.
    """

    def __init__(self, node_id: str, name: str | None = None):
        """
        Initialize a node.

        Args:
            node_id: Unique identifier for the node
            name: Optional human-readable name for the node
        """
        self.node_id = node_id
        self.name = name or node_id
        self.next_nodes: list[str] = []  # IDs of next nodes
        self.execution_strategy: NodeExecutionStrategy | None = None

    @abstractmethod
    async def execute(self, context: ExecutionContext) -> Any:
        """
        Execute the node logic.

        Args:
            context: Execution context containing workflow state

        Returns:
            Node execution result
        """
        pass

    def add_next_node(self, node_id: str) -> None:
        """Add a next node ID."""
        if node_id not in self.next_nodes:
            self.next_nodes.append(node_id)

    def get_next_nodes(self) -> list[str]:
        """Get list of next node IDs."""
        return self.next_nodes.copy()

    def set_execution_strategy(self, strategy: NodeExecutionStrategy) -> None:
        """Strategy Pattern: Set the execution strategy for this node."""
        self.execution_strategy = strategy

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(node_id={self.node_id}, name={self.name})"


class Edge(BaseModel):
    """Represents a directed edge in the DAG."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    from_node_id: str = Field(..., description="Source node ID")
    to_node_id: str = Field(..., description="Target node ID")
    condition: str | None = Field(default=None, description="Optional condition for edge traversal")

    def should_traverse(self, context: ExecutionContext) -> bool:
        """
        Determine if this edge should be traversed based on the condition.

        Args:
            context: Execution context

        Returns:
            True if edge should be traversed
        """
        if self.condition is None:
            return True

        # Evaluate condition using context variables
        try:
            # Simple condition evaluation - can be extended
            return eval(self.condition, {"context": context, "variables": context.variables})
        except Exception:
            return False
