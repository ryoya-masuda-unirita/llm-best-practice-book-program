"""Node representing an agent in the graph."""

from src.agent.core.agent import BaseAgent
from src.agent.core.mediator import Node, NodeResult, NodeType


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
