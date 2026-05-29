"""Workflow execution engine with retry and checkpointing."""

import asyncio
from typing import Any

from src.logger import make_logger
from src.workflow.checkpoint import CheckpointManager
from src.workflow.models import ExecutionContext, WorkflowState
from src.workflow.workflow import Workflow

logger = make_logger(__name__)


class WorkflowEngine:
    """Executes workflows with retry logic and optional checkpointing."""

    def __init__(
        self,
        enable_checkpointing: bool = True,
        checkpoint_interval: int = 5,
        checkpoint_dir: str = "checkpoints",
        max_retries: int = 3,
    ):
        self.enable_checkpointing = enable_checkpointing
        self.checkpoint_interval = checkpoint_interval
        self.max_retries = max_retries
        self.checkpoint_manager = CheckpointManager(checkpoint_dir) if enable_checkpointing else None

    async def execute(
        self,
        workflow: Workflow,
        initial_data: dict[str, Any] | None = None,
        resume_from_checkpoint: str | None = None,
    ) -> dict[str, Any]:
        logger.info(f"Starting workflow: {workflow.workflow_id}")
        workflow.validate()

        if resume_from_checkpoint and self.checkpoint_manager:
            memento = self.checkpoint_manager.load_checkpoint(workflow.workflow_id, resume_from_checkpoint)
            state, context = self.checkpoint_manager.restore_from_checkpoint(memento)
            state.resume_workflow()
        else:
            context = ExecutionContext(workflow_id=workflow.workflow_id)
            state = WorkflowState(workflow_id=workflow.workflow_id)
            if initial_data:
                for key, value in initial_data.items():
                    context.set_variable(key, value)

        state.start_workflow()

        try:
            result = await self._run(workflow, context, state)
            state.complete_workflow()
            logger.info(f"Workflow {workflow.workflow_id} completed")
            return result
        except Exception as e:
            logger.error(f"Workflow {workflow.workflow_id} failed: {e}")
            state.fail_workflow(str(e))
            self._save_checkpoint(workflow.workflow_id, state, context, {"status": "failed"})
            raise

    async def _run(self, workflow: Workflow, context: ExecutionContext, state: WorkflowState) -> dict[str, Any]:
        current_node_id = workflow.start_node_id
        visited = set()
        nodes_executed = 0

        while current_node_id:
            if current_node_id in visited:
                logger.warning(f"Node {current_node_id} already visited")
                break
            visited.add(current_node_id)

            node = workflow.get_node(current_node_id)
            if not node:
                break

            logger.info(f"Executing: {current_node_id} ({node.name})")
            state.start_node(current_node_id)

            output = await self._execute_with_retry(node, context, state)
            state.complete_node(current_node_id, output)
            context.set_node_output(current_node_id, output)
            nodes_executed += 1

            if self.enable_checkpointing and nodes_executed % self.checkpoint_interval == 0:
                self._save_checkpoint(workflow.workflow_id, state, context, {"node": current_node_id})

            if current_node_id in workflow.end_node_ids:
                logger.info(f"Reached end: {current_node_id}")
                break

            current_node_id = self._get_next_node(workflow, node, output, context)

        return {
            "workflow_id": workflow.workflow_id,
            "status": "completed",
            "nodes_executed": nodes_executed,
            "outputs": context.node_outputs,
            "variables": context.variables,
        }

    async def _execute_with_retry(self, node: Any, context: ExecutionContext, state: WorkflowState) -> Any:
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                return await node.execute(context)
            except Exception as e:
                last_error = e
                state.increment_retry(node.node_id)
                if attempt < self.max_retries:
                    wait = 2**attempt
                    logger.warning(f"{node.node_id} failed (attempt {attempt + 1}), retry in {wait}s: {e}")
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"{node.node_id} failed after {self.max_retries + 1} attempts")
        raise last_error

    def _get_next_node(self, workflow: Workflow, node: Any, output: Any, context: ExecutionContext) -> str | None:
        if hasattr(node, "true_branch") and hasattr(node, "false_branch"):
            result = output.get("condition_result", False)
            return node.true_branch if result else node.false_branch

        if hasattr(node, "exit_node") and node.exit_node:
            return node.exit_node

        next_nodes = workflow.get_next_nodes(node.node_id, context)
        return next_nodes[0] if next_nodes else None

    def _save_checkpoint(
        self, workflow_id: str, state: WorkflowState, context: ExecutionContext, metadata: dict
    ) -> None:
        if not self.checkpoint_manager:
            return
        memento = self.checkpoint_manager.create_checkpoint(workflow_id, state, context, metadata=metadata)
        self.checkpoint_manager.save_checkpoint(memento)
        logger.info(f"Checkpoint: {memento.checkpoint_id}")

    def list_checkpoints(self, workflow_id: str) -> list[dict[str, Any]]:
        if not self.checkpoint_manager:
            return []
        return self.checkpoint_manager.list_checkpoints(workflow_id)
