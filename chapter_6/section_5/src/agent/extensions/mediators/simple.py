"""Simple graph mediator implementation."""

from datetime import datetime

from src.agent.core.mediator import (
    Edge,
    EdgeType,
    ExecutionLogEntry,
    GraphExecutionResult,
    GraphMediator,
    Message,
    Node,
    NodeResult,
)


class SimpleGraphMediator(GraphMediator):
    """Simple implementation of graph mediator."""

    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, list[Edge]] = {}
        self.message_log: list[Message] = []
        self.execution_log: list[ExecutionLogEntry] = []

    def add_node(self, node: Node) -> None:
        self.nodes[node.node_id] = node
        node.set_mediator(self)

    def add_edge(self, edge: Edge) -> None:
        self.edges.setdefault(edge.source_id, []).append(edge)

    def execute_graph(self, start_node_id: str, input_data: str | dict | list) -> GraphExecutionResult:
        if start_node_id not in self.nodes:
            return GraphExecutionResult(
                success=False,
                results={},
                final_output=None,
                execution_log=[],
                message_log=[],
                error=f"Start node '{start_node_id}' not found",
            )

        visited: set[str] = set()
        results: dict[str, NodeResult] = {}

        def execute_node(node_id: str, data: str | dict | list) -> NodeResult:
            if node_id in visited:
                return NodeResult(node_id=node_id, success=False, output=None, error="Cycle detected")

            visited.add(node_id)
            result = self.nodes[node_id].execute(data)
            results[node_id] = result

            self.execution_log.append(
                ExecutionLogEntry(
                    timestamp=datetime.now(),
                    node_id=node_id,
                    success=result.success,
                    output=result.output,
                )
            )

            if result.success and node_id in self.edges:
                for edge in self.edges[node_id]:
                    if edge.edge_type == EdgeType.CONDITIONAL:
                        if edge.condition and not edge.condition(result.output):
                            continue
                    execute_node(edge.target_id, result.output or "")

            return result

        final_result = execute_node(start_node_id, input_data)
        return GraphExecutionResult(
            success=final_result.success,
            results=results,
            final_output=final_result.output,
            execution_log=self.execution_log.copy(),
            message_log=self.message_log.copy(),
        )

    def route_message(self, message: Message) -> None:
        self.message_log.append(message)
        if message.receiver_id and message.receiver_id in self.nodes:
            self.nodes[message.receiver_id].execute(message.content)
        elif not message.receiver_id:  # Broadcast
            for node_id, node in self.nodes.items():
                if node_id != message.sender_id:
                    node.execute(message.content)
