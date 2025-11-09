"""Workflow execution engine that orchestrates all components."""

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
    """
    Main workflow execution engine.
    Orchestrates all design patterns and components to execute workflows.
    """

    def __init__(
        self,
        enable_checkpointing: bool = True,
        checkpoint_interval: int = 5,
        checkpoint_dir: str = "checkpoints",
        max_retries: int = 3,
    ):
        """
        Initialize the workflow engine.

        Args:
            enable_checkpointing: Whether to enable automatic checkpointing
            checkpoint_interval: Create checkpoint every N nodes
            checkpoint_dir: Directory for checkpoints
            max_retries: Maximum retries per node on failure
        """
        self.enable_checkpointing = enable_checkpointing
        self.checkpoint_interval = checkpoint_interval
        self.max_retries = max_retries

        # Initialize components
        self.checkpoint_manager = CheckpointManager(checkpoint_dir) if enable_checkpointing else None
        self.mediator = NodeMediator()

        logger.info(f"Workflow engine initialized (checkpointing: {enable_checkpointing})")

    async def execute(
        self,
        workflow: Workflow,
        initial_data: dict[str, Any] | None = None,
        resume_from_checkpoint: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute a workflow.

        Args:
            workflow: Workflow to execute
            initial_data: Initial data for the workflow
            resume_from_checkpoint: Optional checkpoint ID to resume from

        Returns:
            Workflow execution results
        """
        logger.info(f"Starting workflow execution: {workflow.workflow_id}")

        # Validate workflow
        workflow.validate()

        # Initialize or restore state
        if resume_from_checkpoint and self.checkpoint_manager:
            workflow_state, context = await self._resume_from_checkpoint(workflow.workflow_id, resume_from_checkpoint)
        else:
            context = ExecutionContext(workflow_id=workflow.workflow_id)
            workflow_state = WorkflowState(workflow_id=workflow.workflow_id)

            # Set initial data
            if initial_data:
                for key, value in initial_data.items():
                    context.set_variable(key, value)

        # Register nodes with mediator
        self._setup_mediator(workflow)

        # Start workflow
        workflow_state.start_workflow()

        try:
            # Execute workflow
            result = await self._execute_workflow(workflow, context, workflow_state)

            # Mark as completed
            workflow_state.complete_workflow()
            logger.info(f"Workflow {workflow.workflow_id} completed successfully")

            return result

        except Exception as e:
            logger.error(f"Workflow {workflow.workflow_id} failed: {e}")
            workflow_state.fail_workflow(str(e))
            context.error = str(e)

            # Save checkpoint on failure
            if self.enable_checkpointing and self.checkpoint_manager:
                memento = self.checkpoint_manager.create_checkpoint(
                    workflow.workflow_id, workflow_state, context, metadata={"status": "failed", "error": str(e)}
                )
                self.checkpoint_manager.save_checkpoint(memento)

            raise

    async def _execute_workflow(
        self, workflow: Workflow, context: ExecutionContext, workflow_state: WorkflowState
    ) -> dict[str, Any]:
        """
        Execute the workflow DAG.

        Args:
            workflow: Workflow to execute
            context: Execution context
            workflow_state: Workflow state

        Returns:
            Workflow results
        """
        current_node_id = workflow.start_node_id
        visited_nodes = set()
        nodes_executed = 0

        while current_node_id:
            # Check if already visited (prevent infinite loops)
            if current_node_id in visited_nodes:
                logger.warning(f"Node {current_node_id} already visited, breaking loop")
                break

            visited_nodes.add(current_node_id)

            # Execute node
            node = workflow.get_node(current_node_id)
            if not node:
                logger.error(f"Node {current_node_id} not found")
                break

            logger.info(f"Executing node: {current_node_id} ({node.name})")
            workflow_state.start_node(current_node_id)

            try:
                # Execute node with retries
                output = await self._execute_node_with_retry(node, context, workflow_state)

                # Mark as completed
                workflow_state.complete_node(current_node_id, output)
                context.set_node_output(current_node_id, output)

                # Notify mediator
                self.mediator.notify_completion(current_node_id, output, context)

                nodes_executed += 1

                # Checkpoint if needed
                if self.enable_checkpointing and nodes_executed % self.checkpoint_interval == 0:
                    await self._create_checkpoint(workflow.workflow_id, workflow_state, context)

                # Check if this is an end node
                if current_node_id in workflow.end_node_ids:
                    logger.info(f"Reached end node: {current_node_id}")
                    break

                # Get next nodes
                next_nodes = workflow.get_next_nodes(current_node_id, context)

                # Handle different node types
                if hasattr(node, "true_branch") and hasattr(node, "false_branch"):
                    # IfElse node
                    condition_result = output.get("condition_result", False)
                    current_node_id = node.true_branch if condition_result else node.false_branch
                elif hasattr(node, "loop_body_node") and hasattr(node, "exit_node") and node.exit_node:
                    # Loop node with explicit exit - simplified handling
                    current_node_id = node.exit_node
                elif next_nodes:
                    current_node_id = next_nodes[0]
                else:
                    logger.info("No next nodes, workflow ending")
                    current_node_id = None

            except Exception as e:
                logger.error(f"Node {current_node_id} failed: {e}")
                workflow_state.fail_node(current_node_id, str(e))
                raise

        # Return final results
        result = {
            "workflow_id": workflow.workflow_id,
            "status": "completed",
            "nodes_executed": nodes_executed,
            "outputs": context.node_outputs,
            "variables": context.variables,
        }

        return result

    async def _execute_node_with_retry(
        self, node: Any, context: ExecutionContext, workflow_state: WorkflowState
    ) -> Any:
        """
        Execute a node with retry logic.

        Args:
            node: Node to execute
            context: Execution context
            workflow_state: Workflow state

        Returns:
            Node output
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                output = await node.execute(context)
                return output

            except Exception as e:
                last_error = e
                workflow_state.increment_retry(node.node_id)

                if attempt < self.max_retries:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Node {node.node_id} failed (attempt {attempt + 1}/{self.max_retries + 1}), retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Node {node.node_id} failed after {self.max_retries + 1} attempts: {e}")

        if last_error:
            raise last_error

    def _setup_mediator(self, workflow: Workflow) -> None:
        """
        Setup the mediator with workflow nodes and dependencies.

        Args:
            workflow: Workflow
        """
        # Register all nodes
        for node in workflow.nodes.values():
            self.mediator.register_node(node)

        # Add dependencies based on edges
        for edge in workflow.edges:
            self.mediator.add_dependency(edge.to_node_id, edge.from_node_id)

        logger.debug("Mediator setup complete")
        logger.debug(self.mediator.visualize_dependencies())

    async def _create_checkpoint(
        self, workflow_id: str, workflow_state: WorkflowState, context: ExecutionContext
    ) -> None:
        """
        Create a checkpoint of the current workflow state.

        Args:
            workflow_id: Workflow ID
            workflow_state: Current workflow state
            context: Current execution context
        """
        if not self.checkpoint_manager:
            return

        memento = self.checkpoint_manager.create_checkpoint(
            workflow_id, workflow_state, context, metadata={"type": "auto", "node": workflow_state.current_node_id}
        )
        self.checkpoint_manager.save_checkpoint(memento)
        logger.info(f"Checkpoint created: {memento.checkpoint_id}")

    async def _resume_from_checkpoint(
        self, workflow_id: str, checkpoint_id: str
    ) -> tuple[WorkflowState, ExecutionContext]:
        """
        Resume workflow from a checkpoint.

        Args:
            workflow_id: Workflow ID
            checkpoint_id: Checkpoint ID

        Returns:
            Tuple of (WorkflowState, ExecutionContext)
        """
        if not self.checkpoint_manager:
            raise ValueError("Checkpointing not enabled")

        logger.info(f"Resuming workflow {workflow_id} from checkpoint {checkpoint_id}")

        memento = self.checkpoint_manager.load_checkpoint(workflow_id, checkpoint_id)
        workflow_state, context = self.checkpoint_manager.restore_from_checkpoint(memento)

        # Resume the workflow state
        workflow_state.resume_workflow()

        return workflow_state, context

    def pause_workflow(self, workflow_id: str, workflow_state: WorkflowState, context: ExecutionContext) -> str:
        """
        Pause a workflow and create a checkpoint.

        Args:
            workflow_id: Workflow ID
            workflow_state: Current workflow state
            context: Current execution context

        Returns:
            Checkpoint ID for resuming
        """
        workflow_state.pause_workflow()
        logger.info(f"Workflow {workflow_id} paused")

        if self.checkpoint_manager:
            memento = self.checkpoint_manager.create_checkpoint(
                workflow_id, workflow_state, context, metadata={"type": "manual_pause"}
            )
            self.checkpoint_manager.save_checkpoint(memento)
            return memento.checkpoint_id

        return ""

    def list_checkpoints(self, workflow_id: str) -> list[dict[str, Any]]:
        """
        List all checkpoints for a workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            List of checkpoint metadata
        """
        if not self.checkpoint_manager:
            return []

        return self.checkpoint_manager.list_checkpoints(workflow_id)
