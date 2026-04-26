"""Aggregator node for combining multiple inputs."""

from collections.abc import Callable

from src.agent.core.mediator import Node, NodeResult, NodeType


class AggregatorNode(Node):
    def __init__(
        self,
        node_id: str,
        aggregation_fn: Callable[[list[str | dict | list]], str | dict | list],
        expected_inputs: int = 2,
    ):
        super().__init__(node_id, NodeType.AGGREGATOR)
        self.aggregation_fn = aggregation_fn
        self.expected_inputs = expected_inputs
        self._pending_inputs: list[str | dict | list] = []

    def execute(self, input_data: str | dict | list) -> NodeResult:
        self._pending_inputs.append(input_data)
        if len(self._pending_inputs) >= self.expected_inputs:
            try:
                result = self.aggregation_fn(self._pending_inputs)
                self._pending_inputs.clear()
                return NodeResult(node_id=self.node_id, success=True, output=result)
            except Exception as e:
                return NodeResult(node_id=self.node_id, success=False, output=None, error=str(e))
        return NodeResult(
            node_id=self.node_id,
            success=True,
            output=None,
            metadata={"waiting_for": str(self.expected_inputs - len(self._pending_inputs))},
        )
