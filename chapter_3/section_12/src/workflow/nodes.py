"""Concrete node implementations for workflow execution."""

import asyncio
from typing import Any, Callable

from src.logger import make_logger
from src.workflow.models import ExecutionContext, Node

logger = make_logger(__name__)


class StartNode(Node):
    """Entry point node that initializes workflow variables."""

    def __init__(self, node_id: str = "start", name: str | None = None, initial_data: dict[str, Any] | None = None):
        super().__init__(node_id, name or "Start")
        self.initial_data = initial_data or {}

    async def execute(self, context: ExecutionContext) -> dict[str, Any]:
        logger.info(f"Starting workflow: {context.workflow_id}")
        for key, value in self.initial_data.items():
            context.set_variable(key, value)
        return {"status": "started", "initial_data": self.initial_data}


class EndNode(Node):
    """Terminal node that marks workflow completion."""

    def __init__(self, node_id: str = "end", name: str | None = None):
        super().__init__(node_id, name or "End")

    async def execute(self, context: ExecutionContext) -> dict[str, Any]:
        logger.info(f"Ending workflow: {context.workflow_id}")
        return {"status": "completed", "workflow_id": context.workflow_id}


class PromptNode(Node):
    """Executes LLM prompts using a provided executor function."""

    def __init__(
        self,
        node_id: str,
        name: str | None = None,
        prompt_template: str | None = None,
        prompt_builder: Callable[[ExecutionContext], str | list[dict]] | None = None,
        llm_executor: Callable[[str | list[dict], ExecutionContext], Any] | None = None,
    ):
        super().__init__(node_id, name or f"Prompt_{node_id}")
        self.prompt_template = prompt_template
        self.prompt_builder = prompt_builder
        self.llm_executor = llm_executor

    async def execute(self, context: ExecutionContext) -> Any:
        logger.info(f"Executing prompt node: {self.name}")

        if self.prompt_builder:
            prompt = self.prompt_builder(context)
        elif self.prompt_template:
            prompt = self.prompt_template.format(**context.variables)
        else:
            prompt = context.get_variable("prompt", "")

        if not self.llm_executor:
            logger.warning(f"No LLM executor for {self.name}")
            return {"prompt": prompt, "response": None}

        result = self.llm_executor(prompt, context)
        if asyncio.iscoroutine(result):
            result = await result

        context.set_variable(f"{self.node_id}_output", result)
        return result


class IfElseNode(Node):
    """Conditional branching node."""

    def __init__(
        self,
        node_id: str,
        name: str | None = None,
        condition: Callable[[ExecutionContext], bool] | None = None,
    ):
        super().__init__(node_id, name or f"IfElse_{node_id}")
        self.condition = condition
        self.true_branch: str | None = None
        self.false_branch: str | None = None

    def set_branches(self, true_branch: str, false_branch: str) -> None:
        self.true_branch = true_branch
        self.false_branch = false_branch

    async def execute(self, context: ExecutionContext) -> dict[str, Any]:
        logger.info(f"Evaluating condition: {self.name}")
        result = self.condition(context) if self.condition else False
        logger.info(f"Condition result: {result}")
        return {
            "condition_result": result,
            "next_branch": self.true_branch if result else self.false_branch,
        }


class LoopNode(Node):
    """Iterates over a collection or repeats until condition is met."""

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
        self.exit_node: str | None = None

    def set_loop_nodes(self, loop_body_node: str, exit_node: str) -> None:
        self.exit_node = exit_node

    async def execute(self, context: ExecutionContext) -> dict[str, Any]:
        logger.info(f"Executing loop: {self.name}")
        collection = context.get_variable(self.collection_key, []) if self.collection_key else []

        iterations = 0
        if collection:
            for idx, item in enumerate(collection):
                if iterations >= self.max_iterations:
                    break
                context.set_variable(f"{self.node_id}_current_item", item)
                context.set_variable(f"{self.node_id}_current_index", idx)
                iterations += 1
        else:
            while iterations < self.max_iterations:
                if self.condition and not self.condition(context, iterations):
                    break
                iterations += 1
                context.set_variable(f"{self.node_id}_iteration", iterations)

        return {"iterations": iterations}


class ScriptNode(Node):
    """Executes a Python function."""

    def __init__(
        self,
        node_id: str,
        name: str | None = None,
        func: Callable[[ExecutionContext], Any] | None = None,
    ):
        super().__init__(node_id, name or f"Script_{node_id}")
        self.func = func

    async def execute(self, context: ExecutionContext) -> Any:
        logger.info(f"Executing script: {self.name}")
        if not self.func:
            return None
        result = self.func(context)
        if asyncio.iscoroutine(result):
            result = await result
        return result


PythonScriptNode = ScriptNode  # backward compatibility
