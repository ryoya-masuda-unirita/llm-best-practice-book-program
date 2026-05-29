"""WorldManager: fork, run, compare, and select speculative parallel worlds."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

import click
from src.agent.extensions.speculative.world import World, WorldStatus, WorldSummary
from src.logger import make_logger

logger = make_logger(__name__)


class WorldManager:
    """Manages speculative parallel-world execution.

    At branch points in the pipeline, the WorldManager:
    1. Forks N worlds with independent state copies
    2. Runs the pipeline in each world concurrently
    3. Collects results and presents summaries to the user
    4. Lets the user select the best world
    5. Cancels/discards unselected worlds

    This is inspired by CPU speculative execution (branch prediction).
    The trade-off is N times the API cost for the ability to compare
    final outcomes rather than just candidates.
    """

    def __init__(self, max_parallel_worlds: int = 3) -> None:
        self.max_parallel_worlds = max_parallel_worlds
        self._worlds: dict[str, World] = {}

    @property
    def worlds(self) -> dict[str, World]:
        return self._worlds

    def create_worlds(
        self,
        candidates: list[Any],
        candidate_labels: list[str],
        branch_phase: int,
        base_state: Any,
    ) -> list[World]:
        """Create worlds for each candidate, up to max_parallel_worlds.

        Args:
            candidates: List of candidate objects (e.g., ArticleOutline instances)
            candidate_labels: Human-readable labels for each candidate
            branch_phase: The pipeline phase where branching occurs
            base_state: The pipeline state to fork from
        """
        num_worlds = min(len(candidates), self.max_parallel_worlds)
        worlds: list[World] = []

        for i in range(num_worlds):
            world_id = uuid4().hex[:8]
            world = World.create_from_state(
                world_id=world_id,
                branch_point_phase=branch_phase,
                candidate=candidates[i],
                candidate_label=candidate_labels[i],
                base_state=base_state,
            )
            self._worlds[world_id] = world
            worlds.append(world)

        logger.info("Created %d speculative worlds at phase %d", num_worlds, branch_phase)
        return worlds

    async def execute_worlds(
        self,
        worlds: list[World],
        execute_fn: Callable[[Any, Any], Awaitable[Any]],
    ) -> list[World]:
        """Execute the pipeline in each world concurrently.

        Args:
            worlds: List of worlds to execute
            execute_fn: Async function that takes (state, candidate) and returns a result
        """
        click.echo(f"\n  Launching {len(worlds)} parallel worlds for speculative execution...")

        async def run_world(world: World) -> None:
            world.mark_running()
            try:
                logger.info("World %s (%s): starting execution", world.world_id, world.candidate_label)
                result = await execute_fn(world.state, world.candidate)
                world.mark_completed(result)
                logger.info("World %s (%s): completed", world.world_id, world.candidate_label)
            except Exception as e:
                error_msg = str(e)
                world.mark_failed(error_msg)
                logger.error("World %s (%s): failed - %s", world.world_id, world.candidate_label, error_msg)

        # Run all worlds concurrently
        tasks = [run_world(w) for w in worlds]
        await asyncio.gather(*tasks, return_exceptions=True)

        completed = sum(1 for w in worlds if w.status == WorldStatus.COMPLETED)
        failed = sum(1 for w in worlds if w.status == WorldStatus.FAILED)
        click.echo(f"  Speculative execution complete: {completed} succeeded, {failed} failed")

        return worlds

    def get_world_summaries(self, worlds: list[World]) -> list[WorldSummary]:
        """Get summaries for all worlds for user comparison."""
        return [w.get_summary() for w in worlds]

    def display_world_summaries(self, worlds: list[World]) -> None:
        """Display world summaries for user decision-making."""
        click.echo("\n  Speculative Execution Results:")
        click.echo("  " + "=" * 70)

        for i, world in enumerate(worlds, 1):
            summary = world.get_summary()
            status_icon = {
                WorldStatus.COMPLETED: "✅",
                WorldStatus.FAILED: "❌",
                WorldStatus.RUNNING: "⏳",
                WorldStatus.PENDING: "⏸️",
                WorldStatus.CANCELLED: "🚫",
            }.get(summary.status, "❓")

            click.echo(f"\n  {status_icon} World {i}: {summary.candidate_label}")
            click.echo(f"     Status: {summary.status.value}")

            if summary.review_grade is not None:
                click.echo(f"     Grade: {summary.review_grade}/5")
            if summary.review_reasoning:
                click.echo(f"     Review: {summary.review_reasoning[:120]}...")
            if summary.preview:
                click.echo(f"     Preview: {summary.preview[:120]}...")

        click.echo("\n  " + "=" * 70)

    def select_world(
        self,
        worlds: list[World],
        auto_select: bool = False,
    ) -> World | None:
        """Let the user select the best world (or auto-select by grade).

        Args:
            worlds: List of worlds to choose from
            auto_select: If True, automatically pick the highest-graded world
        """
        completed_worlds = [w for w in worlds if w.status == WorldStatus.COMPLETED]

        if not completed_worlds:
            click.echo("  No worlds completed successfully.")
            return None

        if auto_select:
            return self._auto_select(completed_worlds)

        return self._interactive_select(completed_worlds)

    def cancel_unselected(self, worlds: list[World], selected_world: World) -> None:
        """Cancel/discard all worlds except the selected one."""
        for world in worlds:
            if world.world_id != selected_world.world_id:
                if world.status in (WorldStatus.PENDING, WorldStatus.RUNNING):
                    world.mark_cancelled()
                # Remove from tracking
                self._worlds.pop(world.world_id, None)

        logger.info(
            "Selected world %s (%s), cancelled %d others",
            selected_world.world_id,
            selected_world.candidate_label,
            len(worlds) - 1,
        )

    def _auto_select(self, worlds: list[World]) -> World:
        """Automatically select the world with the highest review grade."""

        def grade_key(w: World) -> int:
            if w.result and hasattr(w.result, "article") and w.result.article and w.result.article.review:
                return w.result.article.review.grade
            return 0

        best = max(worlds, key=grade_key)
        click.echo(f"\n  Auto-selected World: {best.candidate_label}")
        return best

    def _interactive_select(self, worlds: list[World]) -> World | None:
        """Let the user interactively choose a world."""
        click.echo("\n  Select the world you want to continue with:")
        for i, world in enumerate(worlds, 1):
            summary = world.get_summary()
            grade_str = f" (Grade: {summary.review_grade}/5)" if summary.review_grade else ""
            click.echo(f"    {i}. {summary.candidate_label}{grade_str}")

        while True:
            try:
                choice = click.prompt(
                    f"\n  Enter your choice (1-{len(worlds)})",
                    type=int,
                )
                if 1 <= choice <= len(worlds):
                    selected = worlds[choice - 1]
                    click.echo(f"\n  Selected: {selected.candidate_label}")
                    return selected
                else:
                    click.echo(f"  Please enter a number between 1 and {len(worlds)}")
            except (ValueError, click.Abort):
                click.echo("  Invalid input. Please try again.")

    def clear(self) -> None:
        """Clear all worlds."""
        self._worlds.clear()
