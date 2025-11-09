"""Builder Pattern: Controls step-by-step construction of complex workflows."""

from typing import Any, Callable

from src.workflow.base import Edge, ExecutionContext
from src.workflow.nodes import EndNode, IfElseNode, LoopNode, PromptNode, PythonScriptNode, StartNode
from src.workflow.workflow import Workflow


class WorkflowBuilder:
    """
    Builder Pattern: Provides a fluent interface for constructing complex workflows.
    Controls the step-by-step construction process.
    """

    def __init__(self, workflow_id: str, name: str | None = None):
        """
        Initialize the workflow builder.

        Args:
            workflow_id: Unique identifier for the workflow
            name: Optional human-readable name
        """
        self._workflow = Workflow(workflow_id, name)
        self._last_node_id: str | None = None

    def add_start_node(
        self, node_id: str = "start", name: str | None = None, initial_data: dict[str, Any] | None = None
    ) -> "WorkflowBuilder":
        """Add a start node to the workflow."""
        node = StartNode(node_id, name, initial_data)
        self._workflow.add_node(node)
        self._workflow.set_start_node(node_id)
        self._last_node_id = node_id
        return self

    def add_end_node(
        self, node_id: str = "end", name: str | None = None, collect_outputs: bool = True
    ) -> "WorkflowBuilder":
        """Add an end node to the workflow."""
        node = EndNode(node_id, name, collect_outputs)
        self._workflow.add_node(node)
        self._workflow.add_end_node(node_id)
        return self

    def add_prompt_node(
        self,
        node_id: str,
        name: str | None = None,
        prompt_template: str | None = None,
        prompt_builder: Callable[[ExecutionContext], str | list[dict]] | None = None,
        llm_executor: Callable[[str | list[dict], ExecutionContext], Any] | None = None,
        **executor_kwargs: Any,
    ) -> "WorkflowBuilder":
        """Add a prompt node to the workflow."""
        node = PromptNode(node_id, name, prompt_template, prompt_builder, llm_executor, **executor_kwargs)
        self._workflow.add_node(node)
        return self

    def add_if_else_node(
        self,
        node_id: str,
        name: str | None = None,
        condition: Callable[[ExecutionContext], bool] | None = None,
        condition_expr: str | None = None,
    ) -> "WorkflowBuilder":
        """Add an if-else node to the workflow."""
        node = IfElseNode(node_id, name, condition, condition_expr)
        self._workflow.add_node(node)
        return self

    def add_loop_node(
        self,
        node_id: str,
        name: str | None = None,
        collection_key: str | None = None,
        max_iterations: int = 100,
        condition: Callable[[ExecutionContext, int], bool] | None = None,
    ) -> "WorkflowBuilder":
        """Add a loop node to the workflow."""
        node = LoopNode(node_id, name, collection_key, max_iterations, condition)
        self._workflow.add_node(node)
        return self

    def add_python_script_node(
        self,
        node_id: str,
        name: str | None = None,
        script: str | None = None,
        script_func: Callable[[ExecutionContext], Any] | None = None,
    ) -> "WorkflowBuilder":
        """Add a Python script node to the workflow."""
        node = PythonScriptNode(node_id, name, script, script_func)
        self._workflow.add_node(node)
        return self

    def add_edge(self, from_node_id: str, to_node_id: str, condition: str | None = None) -> "WorkflowBuilder":
        """Add an edge between two nodes."""
        edge = Edge(from_node_id=from_node_id, to_node_id=to_node_id, condition=condition)
        self._workflow.add_edge(edge)
        self._last_node_id = to_node_id
        return self

    def connect_to_last(self, node_id: str, condition: str | None = None) -> "WorkflowBuilder":
        """Connect a node to the last added node."""
        if self._last_node_id is None:
            raise ValueError("No previous node to connect from")
        return self.add_edge(self._last_node_id, node_id, condition)

    def set_if_else_branches(self, if_else_node_id: str, true_branch: str, false_branch: str) -> "WorkflowBuilder":
        """Set the branches for an if-else node."""
        node = self._workflow.get_node(if_else_node_id)
        if node and hasattr(node, "set_branches"):
            node.set_branches(true_branch, false_branch)
        self.add_edge(if_else_node_id, true_branch)
        self.add_edge(if_else_node_id, false_branch)
        return self

    def set_loop_nodes(self, loop_node_id: str, loop_body_node: str, exit_node: str) -> "WorkflowBuilder":
        """Set the loop body and exit nodes for a loop node."""
        node = self._workflow.get_node(loop_node_id)
        if node and hasattr(node, "set_loop_nodes"):
            node.set_loop_nodes(loop_body_node, exit_node)
        self.add_edge(loop_node_id, loop_body_node)
        self.add_edge(loop_body_node, loop_node_id)
        self.add_edge(loop_node_id, exit_node)
        return self

    def build(self) -> Workflow:
        """Build and return the complete workflow."""
        self._workflow.validate()
        return self._workflow
