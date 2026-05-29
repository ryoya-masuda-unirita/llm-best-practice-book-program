"""Workflow execution engine - Simplified version."""

import asyncio
from typing import Any

from src.logger import make_logger
from src.workflow.base import ExecutionContext
from src.workflow.mediator import NodeMediator
from src.workflow.memento import CheckpointManager
from src.workflow.state import WorkflowState
from src.workflow.workflow import Workflow

logger = make_logger(__name__)


class WorkflowEngine:
    """Main workflow execution engine with DI support."""

    def __init__(
        self,
        enable_checkpointing: bool = True,
        checkpoint_interval: int = 5,
        checkpoint_dir: str = "checkpoints",
        max_retries: int = 3,
        di_container: Any | None = None,
    ):
        self.enable_checkpointing = enable_checkpointing
        self.checkpoint_interval = checkpoint_interval
        self.max_retries = max_retries
        self.di_container = di_container
        self.checkpoint_manager = CheckpointManager(checkpoint_dir) if enable_checkpointing else None
        self.mediator = NodeMediator()
        logger.info(f"Engine initialized (checkpointing: {enable_checkpointing}, DI: {di_container is not None})")

    async def execute(
        self, workflow: Workflow, initial_data: dict[str, Any] | None = None, resume_from_checkpoint: str | None = None
    ) -> dict[str, Any]:
        """Execute a workflow."""
        logger.info(f"Starting workflow: {workflow.workflow_id}")
        workflow.validate()

        if resume_from_checkpoint and self.checkpoint_manager:
            workflow_state, context = await self._resume(workflow.workflow_id, resume_from_checkpoint)
        else:
            context = ExecutionContext(workflow_id=workflow.workflow_id)
            workflow_state = WorkflowState(workflow_id=workflow.workflow_id)
            if initial_data:
                for k, v in initial_data.items():
                    context.set_variable(k, v)

        self._setup_mediator(workflow)
        workflow_state.start_workflow()

        try:
            result = await self._run(workflow, context, workflow_state)
            workflow_state.complete_workflow()
            logger.info(f"Workflow {workflow.workflow_id} completed")
            return result
        except Exception as e:
            logger.error(f"Workflow {workflow.workflow_id} failed: {e}")
            workflow_state.fail_workflow(str(e))
            context.error = str(e)
            if self.checkpoint_manager:
                self.checkpoint_manager.save_checkpoint(
                    self.checkpoint_manager.create_checkpoint(
                        workflow.workflow_id, workflow_state, context, {"status": "failed", "error": str(e)}
                    )
                )
            raise

    async def _run(self, workflow: Workflow, context: ExecutionContext, state: WorkflowState) -> dict[str, Any]:
        """Execute the workflow DAG."""
        current_id = workflow.start_node_id
        visited = set()
        nodes_executed = 0

        while current_id:
            if current_id in visited:
                logger.warning(f"Node {current_id} already visited")
                break
            visited.add(current_id)

            node = workflow.get_node(current_id)
            if not node:
                break

            logger.info(f"Executing: {current_id} ({node.name})")
            state.start_node(current_id)

            try:
                output = await self._execute_with_retry(node, context, state)
                state.complete_node(current_id, output)
                context.set_node_output(current_id, output)
                self.mediator.notify_completion(current_id, output, context)
                nodes_executed += 1

                if self.enable_checkpointing and nodes_executed % self.checkpoint_interval == 0:
                    await self._checkpoint(workflow.workflow_id, state, context)

                if current_id in workflow.end_node_ids:
                    break

                next_nodes = workflow.get_next_nodes(current_id, context)
                if hasattr(node, "true_branch"):
                    current_id = node.true_branch if output.get("condition_result") else node.false_branch
                elif hasattr(node, "exit_node") and node.exit_node:
                    current_id = node.exit_node
                elif next_nodes:
                    current_id = next_nodes[0]
                else:
                    current_id = None

            except Exception as e:
                logger.error(f"Node {current_id} failed: {e}")
                state.fail_node(current_id, str(e))
                raise

        return {
            "workflow_id": workflow.workflow_id,
            "status": "completed",
            "nodes_executed": nodes_executed,
            "outputs": context.node_outputs,
            "variables": context.variables,
        }

    async def _execute_with_retry(self, node: Any, context: ExecutionContext, state: WorkflowState) -> Any:
        """Execute node with retries."""
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                return await node.execute(context)
            except Exception as e:
                last_error = e
                state.increment_retry(node.node_id)
                if attempt < self.max_retries:
                    wait = 2**attempt
                    logger.warning(f"Node {node.node_id} failed (attempt {attempt + 1}), retrying in {wait}s")
                    await asyncio.sleep(wait)
        raise last_error

    def _setup_mediator(self, workflow: Workflow) -> None:
        """Setup mediator with nodes and dependencies."""
        for node in workflow.nodes.values():
            self.mediator.register_node(node)
        for edge in workflow.edges:
            self.mediator.add_dependency(edge.to_node_id, edge.from_node_id)
        logger.debug("Mediator setup complete")
        logger.debug(self.mediator.visualize_dependencies())

    async def _checkpoint(self, workflow_id: str, state: WorkflowState, context: ExecutionContext) -> None:
        """Create checkpoint."""
        if self.checkpoint_manager:
            memento = self.checkpoint_manager.create_checkpoint(
                workflow_id, state, context, {"type": "auto", "node": state.current_node_id}
            )
            self.checkpoint_manager.save_checkpoint(memento)
            logger.info(f"Checkpoint: {memento.checkpoint_id}")

    async def _resume(self, workflow_id: str, checkpoint_id: str) -> tuple[WorkflowState, ExecutionContext]:
        """Resume from checkpoint."""
        if not self.checkpoint_manager:
            raise ValueError("Checkpointing not enabled")
        logger.info(f"Resuming {workflow_id} from {checkpoint_id}")
        memento = self.checkpoint_manager.load_checkpoint(workflow_id, checkpoint_id)
        state, context = self.checkpoint_manager.restore_from_checkpoint(memento)
        state.resume_workflow()
        return state, context

    def pause_workflow(self, workflow_id: str, state: WorkflowState, context: ExecutionContext) -> str:
        """Pause workflow and create checkpoint."""
        state.pause_workflow()
        if self.checkpoint_manager:
            memento = self.checkpoint_manager.create_checkpoint(workflow_id, state, context, {"type": "manual_pause"})
            self.checkpoint_manager.save_checkpoint(memento)
            return memento.checkpoint_id
        return ""

    def list_checkpoints(self, workflow_id: str) -> list[dict[str, Any]]:
        """List checkpoints for a workflow."""
        return self.checkpoint_manager.list_checkpoints(workflow_id) if self.checkpoint_manager else []
