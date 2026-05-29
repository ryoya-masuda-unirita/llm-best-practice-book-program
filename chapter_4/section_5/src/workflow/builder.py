"""Fluent builder for workflow construction."""

from typing import Any, Callable

from src.workflow.models import Edge, ExecutionContext
from src.workflow.nodes import EndNode, IfElseNode, LoopNode, PromptNode, ScriptNode, StartNode
from src.workflow.workflow import Workflow


class WorkflowBuilder:
    """Provides a fluent interface for constructing workflows."""

    def __init__(self, workflow_id: str, name: str | None = None):
        self._workflow = Workflow(workflow_id, name)

    def add_start_node(
        self, node_id: str = "start", name: str | None = None, initial_data: dict[str, Any] | None = None
    ) -> "WorkflowBuilder":
        node = StartNode(node_id, name, initial_data)
        self._workflow.add_node(node)
        self._workflow.set_start_node(node_id)
        return self

    def add_end_node(self, node_id: str = "end", name: str | None = None) -> "WorkflowBuilder":
        node = EndNode(node_id, name)
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
    ) -> "WorkflowBuilder":
        node = PromptNode(node_id, name, prompt_template, prompt_builder, llm_executor)
        self._workflow.add_node(node)
        return self

    def add_if_else_node(
        self,
        node_id: str,
        name: str | None = None,
        condition: Callable[[ExecutionContext], bool] | None = None,
    ) -> "WorkflowBuilder":
        node = IfElseNode(node_id, name, condition)
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
        node = LoopNode(node_id, name, collection_key, max_iterations, condition)
        self._workflow.add_node(node)
        return self

    def add_script_node(
        self,
        node_id: str,
        name: str | None = None,
        func: Callable[[ExecutionContext], Any] | None = None,
    ) -> "WorkflowBuilder":
        node = ScriptNode(node_id, name, func)
        self._workflow.add_node(node)
        return self

    def add_python_script_node(
        self,
        node_id: str,
        name: str | None = None,
        script: str | None = None,
        script_func: Callable[[ExecutionContext], Any] | None = None,
    ) -> "WorkflowBuilder":
        return self.add_script_node(node_id, name, script_func)

    def add_edge(self, from_node_id: str, to_node_id: str) -> "WorkflowBuilder":
        edge = Edge(from_node_id=from_node_id, to_node_id=to_node_id)
        self._workflow.add_edge(edge)
        return self

    def set_if_else_branches(self, node_id: str, true_branch: str, false_branch: str) -> "WorkflowBuilder":
        node = self._workflow.get_node(node_id)
        if node and hasattr(node, "set_branches"):
            node.set_branches(true_branch, false_branch)
        self.add_edge(node_id, true_branch)
        self.add_edge(node_id, false_branch)
        return self

    def set_loop_nodes(self, loop_node_id: str, loop_body_node: str, exit_node: str) -> "WorkflowBuilder":
        node = self._workflow.get_node(loop_node_id)
        if node and hasattr(node, "set_loop_nodes"):
            node.set_loop_nodes(loop_body_node, exit_node)
        self.add_edge(loop_node_id, loop_body_node)
        self.add_edge(loop_body_node, loop_node_id)
        self.add_edge(loop_node_id, exit_node)
        return self

    def build(self) -> Workflow:
        self._workflow.validate()
        return self._workflow
