"""Main entry point for running workflow examples."""

import asyncio
import sys
from functools import wraps

import click

from src.examples import (
    example_1_basic_agent,
    example_2_react_agent,
    example_3_multi_strategy_agent,
    example_4_config_based_agent,
    example_5_graph_mediator,
    example_6_parallel_execution,
    example_7_memory_snapshots,
    example_8_execution_control,
)
from src.logger import make_logger

logger = make_logger(__name__)

# Mapping of workflow names to their functions
AGENTS = {
    "example_1_basic_agent": example_1_basic_agent,
    "example_2_react_agent": example_2_react_agent,
    "example_3_multi_strategy_agent": example_3_multi_strategy_agent,
    "example_4_config_based_agent": example_4_config_based_agent,
    "example_5_graph_mediator": example_5_graph_mediator,
    "example_6_parallel_execution": example_6_parallel_execution,
    "example_7_memory_snapshots": example_7_memory_snapshots,
    "example_8_execution_control": example_8_execution_control,
}


def async_cmd(func):
    """Decorator to run async functions with click."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.command()
@click.option(
    "--agent",
    "-a",
    type=click.Choice(list(AGENTS.keys()) + ["all"]),
    required=True,
    help="The agent workflow to run.",
)
@async_cmd
async def main(agent: str):
    try:
        if agent == "all":
            logger.info("Running all agent examples...\n")

            for name, agent_func in AGENTS.items():
                logger.info(f"\n{'=' * 60}")
                logger.info(f"Running workflow: {name}")
                logger.info(f"{'=' * 60}\n")

                result = agent_func()

                logger.info(f"\n✓ Agent '{name}' completed successfully")
                if isinstance(result, dict):
                    logger.info(f"  Result: {result}")
                else:
                    logger.info(f"  Output: {result}")

                await asyncio.sleep(1)

            logger.info("\n" + "=" * 60)
            logger.info("ALL AGENTS COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)

        else:
            # Run specific workflow
            if agent not in AGENTS:
                logger.error(f"Unknown agent: {agent}")
                logger.info(f"Available agents: {', '.join(AGENTS.keys())}, all")
                sys.exit(1)

            logger.info(f"Running agent: {agent}\n")

            agent_func = AGENTS[agent]
            agent_func()

    except KeyboardInterrupt:
        logger.info("\n\nAgent execution interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n✗ Agent execution failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
