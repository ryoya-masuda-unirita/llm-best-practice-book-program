"""Main entry point for running workflow examples."""

import asyncio
import sys
from functools import wraps

import click

from src.examples import (
    example_1_agent_with_conservative_lock,
    example_2_with_optimistic_lock,
    example_3_with_preemptive_lock,
    example_4_with_immutable_memory,
)
from src.logger import make_logger

logger = make_logger(__name__)

AGENTS = {
    "example_1_agent_with_conservative_lock": example_1_agent_with_conservative_lock,
    "example_2_with_optimistic_lock": example_2_with_optimistic_lock,
    "example_3_with_preemptive_lock": example_3_with_preemptive_lock,
    "example_4_with_immutable_memory": example_4_with_immutable_memory,
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
@click.option(
    "--memory-directory",
    "-md",
    type=click.Path(),
    required=False,
    default="memory",
    help="The directory to save memory files.",
)
@async_cmd
async def main(
    agent: str,
    memory_directory: str,
):
    if agent == "all":
        logger.info("Running all agent examples...\n")

        for name, agent_func in AGENTS.items():
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Running workflow: {name}")
            logger.info(f"{'=' * 60}\n")

            ts_log = agent_func(memory_directory=memory_directory)

            logger.info(f"\n✓ Agent '{name}' completed successfully")
            ts_log.print_log()

            await asyncio.sleep(1)

        logger.info("\n" + "=" * 60)
        logger.info("ALL AGENTS COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)

    else:
        if agent not in AGENTS:
            logger.error(f"Unknown agent: {agent}")
            logger.info(f"Available agents: {', '.join(AGENTS.keys())}, all")
            sys.exit(1)

        logger.info(f"Running agent: {agent}\n")

        agent_func = AGENTS[agent]
        ts_log = agent_func(memory_directory=memory_directory)

        logger.info(f"\n✓ Agent '{agent}' completed successfully")
        ts_log.print_log()


if __name__ == "__main__":
    main()
