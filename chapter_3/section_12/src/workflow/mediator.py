"""Mediator Pattern: Manages complex dependencies between nodes."""

from typing import Any

from src.logger import make_logger
from src.workflow.base import ExecutionContext, Node

logger = make_logger(__name__)


class NodeMediator:
    """
    Mediator Pattern: Coordinates communication and dependencies between nodes.
    Reduces coupling by preventing nodes from referring to each other explicitly.
    """

    def __init__(self):
        """Initialize the node mediator."""
        self._nodes: dict[str, Node] = {}
        self._dependencies: dict[str, list[str]] = {}  # node_id -> list of dependency node_ids
        self._dependents: dict[str, list[str]] = {}  # node_id -> list of dependent node_ids

    def register_node(self, node: Node) -> None:
        """
        Register a node with the mediator.

        Args:
            node: Node to register
        """
        self._nodes[node.node_id] = node
        if node.node_id not in self._dependencies:
            self._dependencies[node.node_id] = []
        if node.node_id not in self._dependents:
            self._dependents[node.node_id] = []

        logger.debug(f"Registered node {node.node_id} with mediator")

    def add_dependency(self, node_id: str, depends_on: str) -> None:
        """
        Add a dependency relationship between nodes.

        Args:
            node_id: Node that has the dependency
            depends_on: Node that is depended upon
        """
        if node_id not in self._dependencies:
            self._dependencies[node_id] = []
        if depends_on not in self._dependents:
            self._dependents[depends_on] = []

        if depends_on not in self._dependencies[node_id]:
            self._dependencies[node_id].append(depends_on)

        if node_id not in self._dependents[depends_on]:
            self._dependents[depends_on].append(node_id)

        logger.debug(f"Added dependency: {node_id} depends on {depends_on}")

    def get_dependencies(self, node_id: str) -> list[str]:
        """
        Get all nodes that a given node depends on.

        Args:
            node_id: Node ID

        Returns:
            List of dependency node IDs
        """
        return self._dependencies.get(node_id, []).copy()

    def get_dependents(self, node_id: str) -> list[str]:
        """
        Get all nodes that depend on a given node.

        Args:
            node_id: Node ID

        Returns:
            List of dependent node IDs
        """
        return self._dependents.get(node_id, []).copy()

    def are_dependencies_met(self, node_id: str, context: ExecutionContext) -> bool:
        """
        Check if all dependencies for a node have been satisfied.

        Args:
            node_id: Node ID
            context: Execution context

        Returns:
            True if all dependencies are met
        """
        dependencies = self.get_dependencies(node_id)

        for dep_node_id in dependencies:
            # Check if dependency node has output in context
            if context.get_node_output(dep_node_id) is None:
                logger.debug(f"Dependency {dep_node_id} not met for node {node_id}")
                return False

        logger.debug(f"All dependencies met for node {node_id}")
        return True

    def get_ready_nodes(self, pending_nodes: list[str], context: ExecutionContext) -> list[str]:
        """
        Get nodes that are ready to execute (all dependencies met).

        Args:
            pending_nodes: List of pending node IDs
            context: Execution context

        Returns:
            List of ready node IDs
        """
        ready_nodes = []

        for node_id in pending_nodes:
            if self.are_dependencies_met(node_id, context):
                ready_nodes.append(node_id)

        return ready_nodes

    def notify_completion(self, node_id: str, output: Any, context: ExecutionContext) -> list[str]:
        """
        Notify mediator that a node has completed and get newly ready dependents.

        Args:
            node_id: Completed node ID
            output: Node output
            context: Execution context

        Returns:
            List of newly ready dependent node IDs
        """
        logger.info(f"Node {node_id} completed")

        # Store output in context
        context.set_node_output(node_id, output)

        # Check which dependents are now ready
        dependents = self.get_dependents(node_id)
        ready_dependents = []

        for dependent_id in dependents:
            if self.are_dependencies_met(dependent_id, context):
                ready_dependents.append(dependent_id)

        logger.debug(f"Newly ready dependents: {ready_dependents}")
        return ready_dependents

    def get_execution_order(self) -> list[str]:
        """
        Get a valid execution order for all nodes (topological sort).

        Returns:
            List of node IDs in execution order

        Raises:
            ValueError: If circular dependency detected
        """
        visited = set()
        temp_mark = set()
        order = []

        def visit(node_id: str) -> None:
            if node_id in temp_mark:
                raise ValueError(f"Circular dependency detected involving node {node_id}")

            if node_id not in visited:
                temp_mark.add(node_id)

                for dep_id in self._dependencies.get(node_id, []):
                    visit(dep_id)

                temp_mark.remove(node_id)
                visited.add(node_id)
                order.insert(0, node_id)

        for node_id in self._nodes:
            if node_id not in visited:
                visit(node_id)

        logger.debug(f"Execution order: {order}")
        return order

    def visualize_dependencies(self) -> str:
        """
        Create a text visualization of the dependency graph.

        Returns:
            String representation of dependencies
        """
        lines = ["Dependency Graph:", "=" * 50]

        for node_id in sorted(self._nodes.keys()):
            deps = self._dependencies.get(node_id, [])
            if deps:
                lines.append(f"{node_id} depends on: {', '.join(deps)}")
            else:
                lines.append(f"{node_id} (no dependencies)")

        return "\n".join(lines)
