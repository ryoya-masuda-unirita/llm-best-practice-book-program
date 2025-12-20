"""Main entry point for running workflow examples."""

import asyncio
import sys
from functools import wraps
from typing import Optional

import click
from src.client.llm_client import (
    LLMProvider,
)
from src.examples import (
    example_1_manual_di,
    example_2_di_container_singleton,
    example_3_swapping_providers,
    example_4_multi_stage_pipeline,
    example_5_structured_output,
    example_6_testing_pattern,
)
from src.logger import make_logger

logger = make_logger(__name__)

WORKFLOWS = {
    "example_1_manual_di": example_1_manual_di,
    "example_2_di_container_singleton": example_2_di_container_singleton,
    "example_3_swapping_providers": example_3_swapping_providers,
    "example_4_multi_stage_pipeline": example_4_multi_stage_pipeline,
    "example_5_structured_output": example_5_structured_output,
    "example_6_testing_pattern": example_6_testing_pattern,
}


def async_cmd(func):
    """Decorator to run async functions with click."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.command()
@click.option(
    "--llm-provider",
    "-lp",
    type=click.Choice(LLMProvider),
    required=False,
    default=None,
    help="The LLM provider to use.",
)
@click.option(
    "--workflow",
    "-w",
    type=click.Choice(list(WORKFLOWS.keys()) + ["all"]),
    required=False,
    default="example_1_manual_di",
    help="The workflow example to run. Use 'all' to run all workflows.",
)
@async_cmd
async def main(
    llm_provider: Optional[LLMProvider],
    workflow: str,
):
    """
    Run Dependency Injection workflow examples.

    This command allows you to run different workflow examples that demonstrate
    the LLM workflow orchestration engine with Dependency Injection patterns.

    Examples:
        # Run example 1 (manual DI)
        python -m src.main --workflow example_1_manual_di

        # Run example 4 (multi-stage pipeline)
        python -m src.main --workflow example_4_multi_stage_pipeline

        # Run all workflows
        python -m src.main --workflow all

    """

    try:
        if workflow == "all":
            logger.info("Running all workflow examples...\n")

            for name, workflow_func in WORKFLOWS.items():
                logger.info(f"\n{'=' * 60}")
                logger.info(f"Running workflow: {name}")
                logger.info(f"{'=' * 60}\n")

                result = await workflow_func(llm_provider=llm_provider)

                logger.info(f"\n✓ Workflow '{name}' completed successfully")
                logger.info(f"  Status: {result.get('status', 'unknown')}")
                logger.info(f"  Nodes executed: {result.get('nodes_executed', 0)}")

                await asyncio.sleep(1)  # Brief pause between workflows

            logger.info("\n" + "=" * 60)
            logger.info("ALL WORKFLOWS COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)

        else:
            if workflow not in WORKFLOWS:
                logger.error(f"Unknown workflow: {workflow}")
                logger.info(f"Available workflows: {', '.join(WORKFLOWS.keys())}, all")
                sys.exit(1)

            logger.info(f"Running workflow: {workflow}\n")

            workflow_func = WORKFLOWS[workflow]
            result = await workflow_func(llm_provider=llm_provider)

            logger.info("\n✓ Workflow completed successfully")
            logger.info(f"  Status: {result.get('status', 'unknown')}")
            logger.info(f"  Nodes executed: {result.get('nodes_executed', 0)}")

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
