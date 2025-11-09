"""Concrete node implementations - Simplified version."""

import asyncio
from typing import Any, Callable

from src.logger import make_logger
from src.workflow.base import ExecutionContext, Node

logger = make_logger(__name__)


class StartNode(Node):
    """Entry point node."""

    def __init__(self, node_id: str = "start", name: str | None = None, initial_data: dict[str, Any] | None = None):
        super().__init__(node_id, name or "Start")
        self.initial_data = initial_data or {}

    async def execute(self, context: ExecutionContext) -> dict[str, Any]:
        logger.info(f"Starting workflow: {context.workflow_id}")
        for key, value in self.initial_data.items():
            context.set_variable(key, value)
        result = {"status": "started", "initial_data": self.initial_data}
        context.set_node_output(self.node_id, result)
        return result


class EndNode(Node):
    """Terminal node."""

    def __init__(self, node_id: str = "end", name: str | None = None, collect_outputs: bool = True):
        super().__init__(node_id, name or "End")
        self.collect_outputs = collect_outputs

    async def execute(self, context: ExecutionContext) -> dict[str, Any]:
        logger.info(f"Ending workflow: {context.workflow_id}")
        return {"status": "completed", "workflow_id": context.workflow_id}


class PromptNode(Node):
    """Node for executing LLM prompts with DI support."""

    def __init__(
        self,
        node_id: str,
        name: str | None = None,
        prompt_template: str | None = None,
        prompt_builder: Callable[[ExecutionContext], str | list[dict]] | None = None,
        llm_executor: Callable[[str | list[dict], ExecutionContext], Any] | None = None,
        injected_prompt_builder: Any | None = None,
        injected_llm_client: Any | None = None,
        injected_response_parser: Any | None = None,
        **executor_kwargs: Any,
    ):
        super().__init__(node_id, name or f"Prompt_{node_id}")
        self.prompt_template = prompt_template
        self.prompt_builder = prompt_builder
        self.llm_executor = llm_executor
        self.injected_prompt_builder = injected_prompt_builder
        self.injected_llm_client = injected_llm_client
        self.injected_response_parser = injected_response_parser
        self.executor_kwargs = executor_kwargs

    async def execute(self, context: ExecutionContext) -> Any:
        logger.info(f"Executing prompt node: {self.name}")

        # Build prompt
        if self.injected_prompt_builder:
            prompt = self.injected_prompt_builder.build_prompt(context)
        elif self.prompt_builder:
            prompt = self.prompt_builder(context)
        elif self.prompt_template:
            prompt = self.prompt_template.format(**context.variables)
        else:
            prompt = context.get_variable("prompt", "")

        # Log preview
        preview = prompt[:100] if isinstance(prompt, str) else f"{len(prompt)} messages"
        logger.info(f"Prompt: {preview}...")

        # Execute
        try:
            if self.injected_llm_client:
                # DI approach
                raw_response = await self.injected_llm_client.generate(prompt, context, **self.executor_kwargs)
                result = (
                    self.injected_response_parser.parse_response(raw_response, context)
                    if self.injected_response_parser
                    else raw_response
                )
            elif self.llm_executor:
                # Legacy approach
                result = self.llm_executor(prompt, context)
                if asyncio.iscoroutine(result):
                    result = await result
            else:
                logger.warning(f"No executor for {self.name}, returning prompt")
                result = {"prompt": prompt, "response": None}

            context.set_node_output(self.node_id, result)
            context.set_variable(f"{self.node_id}_output", result)
            return result
        except Exception as e:
            logger.error(f"Error in {self.name}: {e}")
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
        super().__init__(node_id, name or f"IfElse_{node_id}")
        self.condition = condition
        self.condition_expr = condition_expr
        self.true_branch: str | None = None
        self.false_branch: str | None = None

    def set_branches(self, true_branch: str, false_branch: str) -> None:
        self.true_branch = true_branch
        self.false_branch = false_branch

    async def execute(self, context: ExecutionContext) -> dict[str, Any]:
        logger.info(f"Evaluating condition: {self.name}")

        # Evaluate
        if self.condition:
            result = self.condition(context)
        elif self.condition_expr:
            try:
                result = eval(self.condition_expr, {"context": context, "variables": context.variables})
            except Exception as e:
                logger.error(f"Error evaluating condition: {e}")
                result = False
        else:
            result = False

        logger.info(f"Condition result: {result}")
        output = {"condition_result": result, "next_branch": self.true_branch if result else self.false_branch}
        context.set_node_output(self.node_id, output)
        context.set_variable(f"{self.node_id}_result", result)
        return output

    def get_next_nodes(self) -> list[str]:
        return [n for n in [self.true_branch, self.false_branch] if n]


class LoopNode(Node):
    """Loop node for iteration."""

    def __init__(
        self,
        node_id: str,
        name: str | None = None,
        collection_key: str | None = None,
        max_iterations: int = 100,
        condition: Callable[[ExecutionContext, int], bool] | None = None,
    ):
        super().__init__(node_id, name or f"Loop_{node_id}")
        self.collection_key = collection_key
        self.max_iterations = max_iterations
        self.condition = condition
        self.loop_body_node: str | None = None
        self.exit_node: str | None = None

    def set_loop_nodes(self, loop_body_node: str, exit_node: str) -> None:
        self.loop_body_node = loop_body_node
        self.exit_node = exit_node

    async def execute(self, context: ExecutionContext) -> dict[str, Any]:
        logger.info(f"Executing loop: {self.name}")
        iterations = 0
        collection = context.get_variable(self.collection_key, []) if self.collection_key else []

        if collection:
            # Iterate over collection
            for idx, item in enumerate(collection):
                if iterations >= self.max_iterations:
                    logger.warning(f"Loop {self.name} reached max iterations")
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

        result = {"iterations": iterations, "results": []}
        context.set_node_output(self.node_id, result)
        return result


class PythonScriptNode(Node):
    """Node for executing Python code."""

    def __init__(
        self,
        node_id: str,
        name: str | None = None,
        script: str | None = None,
        script_func: Callable[[ExecutionContext], Any] | None = None,
    ):
        super().__init__(node_id, name or f"Script_{node_id}")
        self.script = script
        self.script_func = script_func

    async def execute(self, context: ExecutionContext) -> Any:
        logger.info(f"Executing script: {self.name}")

        try:
            if self.script_func:
                result = self.script_func(context)
                if asyncio.iscoroutine(result):
                    result = await result
            elif self.script:
                local_vars = {"context": context, "variables": context.variables}
                exec(self.script, {}, local_vars)
                result = local_vars.get("result")
            else:
                result = None

            context.set_node_output(self.node_id, result)
            logger.info(f"Script result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in script {self.name}: {e}")
            context.error = str(e)
            raise
