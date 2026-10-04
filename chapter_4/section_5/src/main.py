"""CLI entry point for running workflow examples."""

import asyncio
import sys
from functools import wraps

import click
from src.client import anthropic_client
from src.examples import (
    example_anthropic_simple,
    example_checkpoint_recovery,
    example_complex_content_pipeline,
    example_complex_research_workflow,
    example_conditional_workflow,
    example_loop_workflow,
)
from src.logger import make_logger

logger = make_logger(__name__)

WORKFLOWS = {
    "example_anthropic_simple": example_anthropic_simple,
    "example_checkpoint_recovery": example_checkpoint_recovery,
    "example_loop_workflow": example_loop_workflow,
    "example_conditional_workflow": example_conditional_workflow,
    "example_complex_content_pipeline": example_complex_content_pipeline,
    "example_complex_research_workflow": example_complex_research_workflow,
}


def async_cmd(func):
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
    default="example_anthropic_simple",
    help="Workflow to run. Use 'all' to run all workflows.",
)
@async_cmd
async def main(workflow: str):
    """Run workflow orchestration examples."""
    try:
        if workflow == "all":
            logger.info("Running all workflows...")
            for name, func in WORKFLOWS.items():
                logger.info(f"\n{'=' * 60}\nRunning: {name}\n{'=' * 60}")
                result = await func()
                logger.info(f"Completed: {result.get('status')} ({result.get('nodes_executed')} nodes)")
                await asyncio.sleep(1)
            logger.info("\n" + "=" * 60 + "\nALL WORKFLOWS COMPLETED\n" + "=" * 60)
        else:
            if workflow not in WORKFLOWS:
                logger.error(f"Unknown workflow: {workflow}")
                sys.exit(1)
            logger.info(f"Running: {workflow}")
            result = await WORKFLOWS[workflow]()
            logger.info(f"Completed: {result.get('status')} ({result.get('nodes_executed')} nodes)")
    except Exception as e:
        logger.error(f"Failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await anthropic_client.close()


if __name__ == "__main__":
    main()
