"""Concrete node implementations for the workflow engine."""

import asyncio
from typing import Any, Callable

from src.logger import make_logger
from src.workflow.base import ExecutionContext, Node

logger = make_logger(__name__)


class StartNode(Node):
    """Entry point node for the workflow."""

    def __init__(self, node_id: str = "start", name: str | None = None, initial_data: dict[str, Any] | None = None):
        """
        Initialize a start node.

        Args:
            node_id: Unique identifier for the node
            name: Optional human-readable name
            initial_data: Initial data to populate in context
        """
        super().__init__(node_id, name or "Start")
        self.initial_data = initial_data or {}

    async def execute(self, context: ExecutionContext) -> dict[str, Any]:
        """
        Execute the start node.

        Args:
            context: Execution context

        Returns:
            Initial data
        """
        logger.info(f"Starting workflow: {context.workflow_id}")

        # Populate initial data
        for key, value in self.initial_data.items():
            context.set_variable(key, value)

        result = {"status": "started", "initial_data": self.initial_data}
        context.set_node_output(self.node_id, result)
        return result


class EndNode(Node):
    """Terminal node for the workflow."""

    def __init__(self, node_id: str = "end", name: str | None = None, collect_outputs: bool = True):
        """
        Initialize an end node.

        Args:
            node_id: Unique identifier for the node
            name: Optional human-readable name
            collect_outputs: Whether to collect all node outputs
        """
        super().__init__(node_id, name or "End")
        self.collect_outputs = collect_outputs

    async def execute(self, context: ExecutionContext) -> dict[str, Any]:
        """
        Execute the end node.

        Args:
            context: Execution context

        Returns:
            Final workflow results (simplified to avoid circular references in checkpoints)
        """
        logger.info(f"Ending workflow: {context.workflow_id}")

        # Return a simplified result that doesn't include the full node_outputs
        # to avoid circular references when this gets stored back to context.node_outputs
        # The engine will provide access to all outputs via context.node_outputs anyway
        result = {
            "status": "completed",
            "workflow_id": context.workflow_id,
        }

        # Note: We intentionally don't include outputs/variables here to avoid circular reference
        # The engine already has access to all outputs via context.node_outputs
        # and variables via context.variables
        return result


class PromptNode(Node):
    """
    Node for executing LLM prompts with dependency injection support.

    This node supports both legacy executor functions and modern DI-based approach.
    The DI approach is recommended for new implementations.
    """

    def __init__(
        self,
        node_id: str,
        name: str | None = None,
        prompt_template: str | None = None,
        prompt_builder: Callable[[ExecutionContext], str | list[dict]] | None = None,
        llm_executor: Callable[[str | list[dict], ExecutionContext], Any] | None = None,
        # New DI-based parameters
        injected_prompt_builder: Any | None = None,  # IPromptBuilder
        injected_llm_client: Any | None = None,  # ILLMClient
        injected_response_parser: Any | None = None,  # IResponseParser
        **executor_kwargs: Any,
    ):
        """
        Initialize a prompt node.

        Args:
            node_id: Unique identifier for the node
            name: Optional human-readable name
            prompt_template: Template string for the prompt (legacy, can use {variable_name})
            prompt_builder: Function to build prompt from context (legacy)
            llm_executor: Async function to execute the LLM call (legacy)
            injected_prompt_builder: Injected IPromptBuilder implementation (DI)
            injected_llm_client: Injected ILLMClient implementation (DI)
            injected_response_parser: Injected IResponseParser implementation (DI)
            **executor_kwargs: Additional kwargs to store and pass to executor if needed
        """
        super().__init__(node_id, name or f"Prompt_{node_id}")
        # Legacy approach
        self.prompt_template = prompt_template
        self.prompt_builder = prompt_builder
        self.llm_executor = llm_executor
        self.executor_kwargs = executor_kwargs
        # DI approach
        self.injected_prompt_builder = injected_prompt_builder
        self.injected_llm_client = injected_llm_client
        self.injected_response_parser = injected_response_parser

    async def execute(self, context: ExecutionContext) -> Any:
        """
        Execute the LLM prompt using either DI or legacy approach.

        Args:
            context: Execution context

        Returns:
            LLM response (parsed if parser is provided)
        """
        logger.info(f"Executing prompt node: {self.name}")

        # Determine which approach to use
        use_di = self.injected_llm_client is not None

        if use_di:
            return await self._execute_with_di(context)
        else:
            return await self._execute_legacy(context)

    async def _execute_with_di(self, context: ExecutionContext) -> Any:
        """Execute using dependency injection approach."""
        # Build prompt using injected builder
        if self.injected_prompt_builder:
            prompt = self.injected_prompt_builder.build_prompt(context)
        elif self.prompt_template:
            from src.workflow.di_implementations import TemplatePromptBuilder

            builder = TemplatePromptBuilder(self.prompt_template)
            prompt = builder.build_prompt(context)
        else:
            prompt = context.get_variable("prompt", "")

        # Log prompt preview
        if isinstance(prompt, str):
            logger.info(f"Prompt: {prompt[:100]}...")
        else:
            logger.info(f"Prompt messages: {len(prompt) if isinstance(prompt, list) else 'custom'}")

        try:
            # Generate response using injected client
            raw_response = await self.injected_llm_client.generate(prompt, context, **self.executor_kwargs)

            # Parse response if parser is provided
            if self.injected_response_parser:
                result = self.injected_response_parser.parse_response(raw_response, context)
            else:
                result = raw_response

            context.set_node_output(self.node_id, result)
            context.set_variable(f"{self.node_id}_output", result)
            return result
        except Exception as e:
            logger.error(f"Error in DI-based prompt node {self.name}: {e}")
            context.error = str(e)
            raise

    async def _execute_legacy(self, context: ExecutionContext) -> Any:
        """Execute using legacy executor function approach."""
        # Build prompt
        if self.prompt_builder:
            prompt = self.prompt_builder(context)
        elif self.prompt_template:
            prompt = self.prompt_template.format(**context.variables)
        else:
            prompt = context.get_variable("prompt", "")

        # Log prompt preview
        if isinstance(prompt, str):
            logger.info(f"Prompt: {prompt[:100]}...")
        else:
            logger.info(f"Prompt messages: {len(prompt) if isinstance(prompt, list) else 'custom'}")

        # Execute LLM request
        try:
            if self.llm_executor:
                # Use custom executor
                result = self.llm_executor(prompt, context)
                if asyncio.iscoroutine(result):
                    result = await result
            else:
                # If no executor provided, just return the prompt for testing
                logger.warning(f"No LLM executor provided for {self.name}, returning prompt as result")
                result = {"prompt": prompt, "response": None}

            context.set_node_output(self.node_id, result)
            context.set_variable(f"{self.node_id}_output", result)
            return result
        except Exception as e:
            logger.error(f"Error in prompt node {self.name}: {e}")
            context.error = str(e)
            raise


class IfElseNode(Node):
    """Conditional branching node."""

    def __init__(
        self,
        node_id: str,
        name: str | None = None,
        condition: Callable[[ExecutionContext], bool] | None = None,
        condition_expr: str | None = None,
    ):
        """
        Initialize an if-else node.

        Args:
            node_id: Unique identifier for the node
            name: Optional human-readable name
            condition: Function to evaluate condition
            condition_expr: Expression string to evaluate
        """
        super().__init__(node_id, name or f"IfElse_{node_id}")
        self.condition = condition
        self.condition_expr = condition_expr
        self.true_branch: str | None = None
        self.false_branch: str | None = None

    def set_branches(self, true_branch: str, false_branch: str) -> None:
        """Set the branch node IDs."""
        self.true_branch = true_branch
        self.false_branch = false_branch

    async def execute(self, context: ExecutionContext) -> dict[str, Any]:
        """
        Execute the conditional logic.

        Args:
            context: Execution context

        Returns:
            Branch decision result
        """
        logger.info(f"Evaluating condition in node: {self.name}")

        # Evaluate condition
        if self.condition:
            condition_result = self.condition(context)
        elif self.condition_expr:
            try:
                condition_result = eval(self.condition_expr, {"context": context, "variables": context.variables})
            except Exception as e:
                logger.error(f"Error evaluating condition: {e}")
                condition_result = False
        else:
            condition_result = False

        logger.info(f"Condition result: {condition_result}")

        result = {
            "condition_result": condition_result,
            "next_branch": self.true_branch if condition_result else self.false_branch,
        }
        context.set_node_output(self.node_id, result)
        context.set_variable(f"{self.node_id}_result", condition_result)
        return result

    def get_next_nodes(self) -> list[str]:
        """Override to return the appropriate branch based on last execution."""
        # This will be determined during execution
        return [n for n in [self.true_branch, self.false_branch] if n is not None]


class LoopNode(Node):
    """Loop node for iterating over collections or repeating logic."""

    def __init__(
        self,
        node_id: str,
        name: str | None = None,
        collection_key: str | None = None,
        max_iterations: int = 100,
        condition: Callable[[ExecutionContext, int], bool] | None = None,
    ):
        """
        Initialize a loop node.

        Args:
            node_id: Unique identifier for the node
            name: Optional human-readable name
            collection_key: Variable key containing collection to iterate over
            max_iterations: Maximum number of iterations
            condition: Function to determine if loop should continue
        """
        super().__init__(node_id, name or f"Loop_{node_id}")
        self.collection_key = collection_key
        self.max_iterations = max_iterations
        self.condition = condition
        self.loop_body_node: str | None = None
        self.exit_node: str | None = None

    def set_loop_nodes(self, loop_body_node: str, exit_node: str) -> None:
        """Set the loop body and exit node IDs."""
        self.loop_body_node = loop_body_node
        self.exit_node = exit_node

    async def execute(self, context: ExecutionContext) -> dict[str, Any]:
        """
        Execute the loop logic.

        Args:
            context: Execution context

        Returns:
            Loop execution results
        """
        logger.info(f"Executing loop node: {self.name}")

        iterations = 0
        results = []

        # Get collection if specified
        collection = context.get_variable(self.collection_key, []) if self.collection_key else []

        if collection:
            # Iterate over collection
            for idx, item in enumerate(collection):
                if iterations >= self.max_iterations:
                    logger.warning(f"Loop {self.name} reached max iterations: {self.max_iterations}")
                    break

                context.set_variable(f"{self.node_id}_current_item", item)
                context.set_variable(f"{self.node_id}_current_index", idx)
                iterations += 1

                logger.info(f"Loop iteration {iterations}/{len(collection)}")
        else:
            # Condition-based loop
            while iterations < self.max_iterations:
                if self.condition and not self.condition(context, iterations):
                    break
                iterations += 1
                context.set_variable(f"{self.node_id}_iteration", iterations)
                logger.info(f"Loop iteration {iterations}")

        result = {
            "iterations": iterations,
            "results": results,
        }
        context.set_node_output(self.node_id, result)
        return result


class PythonScriptNode(Node):
    """Node for executing arbitrary Python code."""

    def __init__(
        self,
        node_id: str,
        name: str | None = None,
        script: str | None = None,
        script_func: Callable[[ExecutionContext], Any] | None = None,
    ):
        """
        Initialize a Python script node.

        Args:
            node_id: Unique identifier for the node
            name: Optional human-readable name
            script: Python code as string
            script_func: Python function to execute
        """
        super().__init__(node_id, name or f"Script_{node_id}")
        self.script = script
        self.script_func = script_func

    async def execute(self, context: ExecutionContext) -> Any:
        """
        Execute the Python script.

        Args:
            context: Execution context

        Returns:
            Script execution result
        """
        logger.info(f"Executing Python script node: {self.name}")

        try:
            if self.script_func:
                # Execute function
                result = self.script_func(context)
                if asyncio.iscoroutine(result):
                    result = await result
            elif self.script:
                # Execute script string
                local_vars = {"context": context, "variables": context.variables}
                exec(self.script, {}, local_vars)
                result = local_vars.get("result", None)
            else:
                result = None

            context.set_node_output(self.node_id, result)
            logger.info(f"Script result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error executing script in node {self.name}: {e}")
            context.error = str(e)
            raise
