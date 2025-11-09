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
        self._nodes: dict[str, Node] = {}
        self._dependencies: dict[str, list[str]] = {}
        self._dependents: dict[str, list[str]] = {}

    def register_node(self, node: Node) -> None:
        self._nodes[node.node_id] = node
        self._dependencies.setdefault(node.node_id, [])
        self._dependents.setdefault(node.node_id, [])

    def add_dependency(self, node_id: str, depends_on: str) -> None:
        self._dependencies.setdefault(node_id, [])
        self._dependents.setdefault(depends_on, [])
        if depends_on not in self._dependencies[node_id]:
            self._dependencies[node_id].append(depends_on)
        if node_id not in self._dependents[depends_on]:
            self._dependents[depends_on].append(node_id)

    def get_dependencies(self, node_id: str) -> list[str]:
        return self._dependencies.get(node_id, []).copy()

    def get_dependents(self, node_id: str) -> list[str]:
        return self._dependents.get(node_id, []).copy()

    def are_dependencies_met(self, node_id: str, context: ExecutionContext) -> bool:
        return all(context.get_node_output(dep) is not None for dep in self.get_dependencies(node_id))

    def notify_completion(self, node_id: str, output: Any, context: ExecutionContext) -> list[str]:
        context.set_node_output(node_id, output)
        return [dep_id for dep_id in self.get_dependents(node_id) if self.are_dependencies_met(dep_id, context)]

    def visualize_dependencies(self) -> str:
        """Create a text visualization of the dependency graph."""
        lines = []
        for node_id in sorted(self._nodes.keys()):
            deps = self._dependencies.get(node_id, [])
            if deps:
                lines.append(f"{node_id} -> {', '.join(deps)}")
        return "\n".join(lines) if lines else "No dependencies"
