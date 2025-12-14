"""Workflow class representing a DAG of nodes and edges."""

from typing import Any

from src.logger import make_logger
from src.workflow.base import Edge, ExecutionContext, Node

logger = make_logger(__name__)


class Workflow:
    """
    Represents a complete workflow as a Directed Acyclic Graph (DAG).
    Composite Pattern: Can be treated as a single node in a larger workflow.
    """

    def __init__(self, workflow_id: str, name: str | None = None):
        self.workflow_id = workflow_id
        self.name = name or workflow_id
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self.start_node_id: str | None = None
        self.end_node_ids: list[str] = []

    def add_node(self, node: Node) -> None:
        self.nodes[node.node_id] = node

    def add_edge(self, edge: Edge) -> None:
        if edge.from_node_id not in self.nodes or edge.to_node_id not in self.nodes:
            raise ValueError(f"Edge nodes not found: {edge.from_node_id} -> {edge.to_node_id}")
        self.edges.append(edge)
        self.nodes[edge.from_node_id].add_next_node(edge.to_node_id)

    def set_start_node(self, node_id: str) -> None:
        if node_id not in self.nodes:
            raise ValueError(f"Start node {node_id} not found")
        self.start_node_id = node_id

    def add_end_node(self, node_id: str) -> None:
        if node_id not in self.nodes:
            raise ValueError(f"End node {node_id} not found")
        if node_id not in self.end_node_ids:
            self.end_node_ids.append(node_id)

    def get_node(self, node_id: str) -> Node | None:
        return self.nodes.get(node_id)

    def get_next_nodes(self, node_id: str, context: ExecutionContext) -> list[str]:
        """Get the next nodes to execute after a given node."""
        next_node_ids = []

        for edge in self.edges:
            if edge.from_node_id == node_id:
                if edge.should_traverse(context):
                    next_node_ids.append(edge.to_node_id)

        # If no conditional edges, use node's next_nodes
        if not next_node_ids:
            node = self.get_node(node_id)
            if node:
                next_node_ids = node.get_next_nodes()

        return next_node_ids

    def validate(self) -> bool:
        """Validate the workflow structure."""
        if not self.start_node_id:
            raise ValueError("Workflow must have a start node")

        if not self.end_node_ids:
            raise ValueError("Workflow must have at least one end node")

        if self.start_node_id not in self.nodes:
            raise ValueError(f"Start node {self.start_node_id} not found")

        for end_node_id in self.end_node_ids:
            if end_node_id not in self.nodes:
                raise ValueError(f"End node {end_node_id} not found")

        if self._has_cycle():
            raise ValueError("Workflow contains cycles (not a valid DAG)")

        logger.info(f"Workflow {self.workflow_id} validated successfully")
        return True

    def _has_cycle(self) -> bool:
        """Check if the workflow has cycles using DFS."""
        visited = set()
        rec_stack = set()

        def _dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            for edge in self.edges:
                if edge.from_node_id == node_id:
                    neighbor = edge.to_node_id
                    if neighbor not in visited:
                        if _dfs(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        return True

            rec_stack.remove(node_id)
            return False

        for node_id in self.nodes:
            if node_id not in visited:
                if _dfs(node_id):
                    return True

        return False

    def to_dict(self) -> dict[str, Any]:
        """Convert workflow to dictionary representation."""
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "start_node_id": self.start_node_id,
            "end_node_ids": self.end_node_ids,
            "nodes": {
                node_id: {
                    "type": node.__class__.__name__,
                    "name": node.name,
                    "next_nodes": node.next_nodes,
                }
                for node_id, node in self.nodes.items()
            },
            "edges": [
                {
                    "from": edge.from_node_id,
                    "to": edge.to_node_id,
                    "condition": edge.condition,
                }
                for edge in self.edges
            ],
        }
