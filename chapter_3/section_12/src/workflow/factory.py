"""Abstract Factory Pattern: Creates different types of nodes and edges."""

from typing import Any, Callable

from src.workflow.base import Edge, ExecutionContext, Node
from src.workflow.nodes import EndNode, IfElseNode, LoopNode, PromptNode, PythonScriptNode, StartNode
from src.workflow.workflow import Workflow


class NodeFactory:
    """
    Abstract Factory Pattern: Factory for creating different types of nodes.
    Provides a unified interface for node creation.
    """

    @staticmethod
    def create_start_node(
        node_id: str = "start", name: str | None = None, initial_data: dict[str, Any] | None = None
    ) -> StartNode:
        """
        Create a start node.

        Args:
            node_id: Unique identifier
            name: Optional name
            initial_data: Initial data

        Returns:
            StartNode instance
        """
        return StartNode(node_id=node_id, name=name, initial_data=initial_data)

    @staticmethod
    def create_end_node(node_id: str = "end", name: str | None = None, collect_outputs: bool = True) -> EndNode:
        """
        Create an end node.

        Args:
            node_id: Unique identifier
            name: Optional name
            collect_outputs: Whether to collect outputs

        Returns:
            EndNode instance
        """
        return EndNode(node_id=node_id, name=name, collect_outputs=collect_outputs)

    @staticmethod
    def create_prompt_node(
        node_id: str,
        name: str | None = None,
        prompt_template: str | None = None,
        prompt_builder: Callable[[ExecutionContext], str | list[dict]] | None = None,
        llm_executor: Callable[[str | list[dict], ExecutionContext], Any] | None = None,
        **executor_kwargs: Any,
    ) -> PromptNode:
        """
        Create a prompt node.

        Args:
            node_id: Unique identifier
            name: Optional name
            prompt_template: Prompt template
            prompt_builder: Prompt builder function
            llm_executor: Custom LLM executor function
            **executor_kwargs: Additional kwargs for the executor

        Returns:
            PromptNode instance
        """
        return PromptNode(
            node_id=node_id,
            name=name,
            prompt_template=prompt_template,
            prompt_builder=prompt_builder,
            llm_executor=llm_executor,
            **executor_kwargs,
        )

    @staticmethod
    def create_if_else_node(
        node_id: str,
        name: str | None = None,
        condition: Callable[[ExecutionContext], bool] | None = None,
        condition_expr: str | None = None,
    ) -> IfElseNode:
        """
        Create an if-else node.

        Args:
            node_id: Unique identifier
            name: Optional name
            condition: Condition function
            condition_expr: Condition expression

        Returns:
            IfElseNode instance
        """
        return IfElseNode(node_id=node_id, name=name, condition=condition, condition_expr=condition_expr)

    @staticmethod
    def create_loop_node(
        node_id: str,
        name: str | None = None,
        collection_key: str | None = None,
        max_iterations: int = 100,
        condition: Callable[[ExecutionContext, int], bool] | None = None,
    ) -> LoopNode:
        """
        Create a loop node.

        Args:
            node_id: Unique identifier
            name: Optional name
            collection_key: Variable key for collection
            max_iterations: Maximum iterations
            condition: Loop condition

        Returns:
            LoopNode instance
        """
        return LoopNode(
            node_id=node_id,
            name=name,
            collection_key=collection_key,
            max_iterations=max_iterations,
            condition=condition,
        )

    @staticmethod
    def create_python_script_node(
        node_id: str,
        name: str | None = None,
        script: str | None = None,
        script_func: Callable[[ExecutionContext], Any] | None = None,
    ) -> PythonScriptNode:
        """
        Create a Python script node.

        Args:
            node_id: Unique identifier
            name: Optional name
            script: Python script string
            script_func: Python function

        Returns:
            PythonScriptNode instance
        """
        return PythonScriptNode(node_id=node_id, name=name, script=script, script_func=script_func)

    @staticmethod
    def create_node_from_config(node_type: str, config: dict[str, Any]) -> Node:
        """
        Create a node from configuration dictionary.

        Args:
            node_type: Type of node to create
            config: Configuration dictionary

        Returns:
            Node instance

        Raises:
            ValueError: If node type is unknown
        """
        node_type = node_type.lower()

        if node_type == "start":
            return NodeFactory.create_start_node(**config)
        elif node_type == "end":
            return NodeFactory.create_end_node(**config)
        elif node_type == "prompt":
            return NodeFactory.create_prompt_node(**config)
        elif node_type == "ifelse" or node_type == "if_else":
            return NodeFactory.create_if_else_node(**config)
        elif node_type == "loop":
            return NodeFactory.create_loop_node(**config)
        elif node_type == "script" or node_type == "python":
            return NodeFactory.create_python_script_node(**config)
        else:
            raise ValueError(f"Unknown node type: {node_type}")


class EdgeFactory:
    """Factory for creating edges between nodes."""

    @staticmethod
    def create_edge(from_node_id: str, to_node_id: str, condition: str | None = None) -> Edge:
        """
        Create an edge.

        Args:
            from_node_id: Source node ID
            to_node_id: Target node ID
            condition: Optional condition

        Returns:
            Edge instance
        """
        return Edge(from_node_id=from_node_id, to_node_id=to_node_id, condition=condition)

    @staticmethod
    def create_conditional_edge(from_node_id: str, to_node_id: str, condition: str) -> Edge:
        """
        Create a conditional edge.

        Args:
            from_node_id: Source node ID
            to_node_id: Target node ID
            condition: Condition expression

        Returns:
            Edge instance
        """
        return Edge(from_node_id=from_node_id, to_node_id=to_node_id, condition=condition)


class WorkflowFactory:
    """Factory for creating complete workflows."""

    @staticmethod
    def create_workflow(workflow_id: str, name: str | None = None) -> Workflow:
        """
        Create a new workflow.

        Args:
            workflow_id: Unique identifier
            name: Optional name

        Returns:
            Workflow instance
        """
        return Workflow(workflow_id=workflow_id, name=name)

    @staticmethod
    def create_workflow_from_config(config: dict[str, Any]) -> Workflow:
        """
        Create a workflow from configuration dictionary.

        Args:
            config: Configuration dictionary with structure:
                {
                    "workflow_id": str,
                    "name": str (optional),
                    "nodes": [{"type": str, "config": dict}, ...],
                    "edges": [{"from": str, "to": str, "condition": str (optional)}, ...],
                    "start_node": str,
                    "end_nodes": [str, ...]
                }

        Returns:
            Workflow instance
        """
        workflow = Workflow(workflow_id=config["workflow_id"], name=config.get("name"))

        # Create nodes
        for node_config in config.get("nodes", []):
            node = NodeFactory.create_node_from_config(node_config["type"], node_config.get("config", {}))
            workflow.add_node(node)

        # Create edges
        for edge_config in config.get("edges", []):
            edge = EdgeFactory.create_edge(
                from_node_id=edge_config["from"],
                to_node_id=edge_config["to"],
                condition=edge_config.get("condition"),
            )
            workflow.add_edge(edge)

        # Set start and end nodes
        if "start_node" in config:
            workflow.set_start_node(config["start_node"])

        for end_node_id in config.get("end_nodes", []):
            workflow.add_end_node(end_node_id)

        return workflow
