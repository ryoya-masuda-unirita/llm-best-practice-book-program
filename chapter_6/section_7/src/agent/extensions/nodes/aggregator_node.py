"""Node that aggregates results from multiple sources."""

from collections.abc import Callable

from src.agent.core.mediator import Node, NodeResult, NodeType


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
