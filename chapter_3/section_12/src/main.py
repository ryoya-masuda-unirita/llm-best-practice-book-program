"""Main entry point for running workflow examples."""

import asyncio
import sys
from functools import wraps

import click
from src.examples import (
    example_checkpoint_recovery,
    example_complex_content_pipeline,
    example_complex_research_workflow,
    example_conditional_workflow,
    example_gemini_simple,
    example_loop_workflow,
    example_multi_provider,
    example_openai_simple,
)
from src.logger import make_logger

logger = make_logger(__name__)

# Mapping of workflow names to their functions
WORKFLOWS = {
    "example_gemini_simple": example_gemini_simple,
    "example_openai_simple": example_openai_simple,
    "example_multi_provider": example_multi_provider,
    "example_checkpoint_recovery": example_checkpoint_recovery,
    "example_loop_workflow": example_loop_workflow,
    "example_conditional_workflow": example_conditional_workflow,
    "example_complex_content_pipeline": example_complex_content_pipeline,
    "example_complex_research_workflow": example_complex_research_workflow,
}


def async_cmd(func):
    """Decorator to run async functions with click."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.command()
@click.option(
    "--workflow",
    "-w",
    type=click.Choice(list(WORKFLOWS.keys()) + ["all"]),
    required=False,
    default="simple",
    help="The workflow example to run. Use 'all' to run all workflows.",
)
@async_cmd
async def main(workflow: str):
    """
    Run workflow orchestration examples.

    This command allows you to run different workflow examples that demonstrate
    the LLM workflow orchestration engine with various design patterns.

    Examples:
        # Run the simple workflow
        python -m src.main --workflow simple

        # Run the complex workflow
        python -m src.main --workflow complex

        # Run all workflows
        python -m src.main --workflow all

    """
    try:
        if workflow == "all":
            # Run all workflows
            logger.info("Running all workflow examples...\n")

            for name, workflow_func in WORKFLOWS.items():
                logger.info(f"\n{'=' * 60}")
                logger.info(f"Running workflow: {name}")
                logger.info(f"{'=' * 60}\n")

                result = await workflow_func()

                logger.info(f"\n✓ Workflow '{name}' completed successfully")
                logger.info(f"  Status: {result.get('status', 'unknown')}")
                logger.info(f"  Nodes executed: {result.get('nodes_executed', 0)}")

                await asyncio.sleep(1)  # Brief pause between workflows

            logger.info("\n" + "=" * 60)
            logger.info("ALL WORKFLOWS COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)

        else:
            # Run specific workflow
            if workflow not in WORKFLOWS:
                logger.error(f"Unknown workflow: {workflow}")
                logger.info(f"Available workflows: {', '.join(WORKFLOWS.keys())}, all")
                sys.exit(1)

            logger.info(f"Running workflow: {workflow}\n")

            workflow_func = WORKFLOWS[workflow]
            result = await workflow_func()

            logger.info("\n✓ Workflow completed successfully")
            logger.info(f"  Status: {result.get('status', 'unknown')}")
            logger.info(f"  Nodes executed: {result.get('nodes_executed', 0)}")

            # Show outputs if available
            if "outputs" in result and result["outputs"]:
                logger.info("\n  Final outputs:")
                for node_id, output in result["outputs"].items():
                    logger.info(f"    {node_id}: {str(output)}...")

    except KeyboardInterrupt:
        logger.info("\n\nWorkflow execution interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n✗ Workflow execution failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
