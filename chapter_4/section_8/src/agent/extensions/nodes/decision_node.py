"""Node that makes routing decisions based on conditions."""

from collections.abc import Callable

from src.agent.core.mediator import Node, NodeResult, NodeType


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
