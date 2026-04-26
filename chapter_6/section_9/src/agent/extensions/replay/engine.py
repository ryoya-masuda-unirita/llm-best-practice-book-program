"""Replay engine that orchestrates prompt replay after rollback."""

from dataclasses import dataclass, field

import click
from src.agent.extensions.replay.filter import ReplayDecision, ReplayFilter
from src.agent.extensions.replay.prompt_log import PromptLog, PromptLogEntry
from src.logger import make_logger

logger = make_logger(__name__)


@dataclass
class ReplayDiff:
    """Comparison of original vs replayed response for a single prompt."""

    prompt_index: int
    prompt_text: str
    original_response: str | None
    replayed_response: str | None
    changed: bool = False


@dataclass
class ReplayResult:
    """Result of a replay operation."""

    replayed_count: int = 0
    skipped_count: int = 0
    confirmed_count: int = 0
    diffs: list[ReplayDiff] = field(default_factory=list)
    success: bool = True
    error: str | None = None


class ReplayEngine:
    """Orchestrates the replay of user prompts after a rollback.

    After the pipeline rolls back to a previous phase (Forget), the
    ReplayEngine identifies which user prompts should be re-sent and
    replays them in order on the clean context. This preserves the user's
    valid inputs without requiring manual re-entry.

    The engine:
    1. Gets all prompts after the rollback phase from the WAL
    2. Filters each prompt through ReplayFilter
    3. For REPLAY prompts: re-sends in order
    4. For CONFIRM prompts: asks user
    5. For SKIP prompts: discards
    6. Returns a diff of before/after responses
    """

    def __init__(self, prompt_log: PromptLog, replay_filter: ReplayFilter) -> None:
        self.prompt_log = prompt_log
        self.replay_filter = replay_filter

    def get_replayable_entries(
        self,
        rollback_phase: int,
        auto_select: bool = False,
    ) -> list[PromptLogEntry]:
        """Identify and return entries that should be replayed.

        Returns the filtered list of entries that will actually be replayed.
        For CONFIRM entries in interactive mode, asks the user.
        """
        entries = self.prompt_log.get_entries_after_phase(rollback_phase)

        if not entries:
            logger.info("No entries to replay after rollback phase %d", rollback_phase)
            return []

        replayable: list[PromptLogEntry] = []
        replayed = 0
        skipped = 0
        confirmed = 0

        for entry in entries:
            decision = self.replay_filter.classify(entry, rollback_phase)

            if decision == ReplayDecision.REPLAY:
                replayable.append(entry)
                replayed += 1
            elif decision == ReplayDecision.SKIP:
                skipped += 1
            elif decision == ReplayDecision.CONFIRM:
                if auto_select:
                    # In auto mode, skip context-dependent prompts
                    skipped += 1
                else:
                    should_replay = self._ask_user_confirmation(entry)
                    if should_replay:
                        replayable.append(entry)
                        confirmed += 1
                    else:
                        skipped += 1

        logger.info(
            "Replay analysis: %d to replay, %d skipped, %d user-confirmed",
            replayed,
            skipped,
            confirmed,
        )
        return replayable

    def build_replay_result(
        self,
        replayable_entries: list[PromptLogEntry],
        new_responses: dict[int, str],
    ) -> ReplayResult:
        """Build a ReplayResult with diffs comparing original vs new responses.

        Args:
            replayable_entries: Entries that were replayed.
            new_responses: Map of entry index -> new response text.
        """
        diffs: list[ReplayDiff] = []
        for entry in replayable_entries:
            new_response = new_responses.get(entry.index)
            changed = (entry.response_text or "") != (new_response or "")
            diffs.append(
                ReplayDiff(
                    prompt_index=entry.index,
                    prompt_text=entry.prompt_text,
                    original_response=entry.response_text,
                    replayed_response=new_response,
                    changed=changed,
                )
            )

        return ReplayResult(
            replayed_count=len(replayable_entries),
            skipped_count=0,
            confirmed_count=0,
            diffs=diffs,
            success=True,
        )

    def display_replay_summary(self, result: ReplayResult) -> None:
        """Display a summary of what changed during replay."""
        if not result.diffs:
            click.echo("\n  No prompts were replayed.")
            return

        click.echo(f"\n  Replay Summary: {result.replayed_count} prompt(s) replayed")

        changed_count = sum(1 for d in result.diffs if d.changed)
        if changed_count > 0:
            click.echo(f"  {changed_count} response(s) changed after replay:")
            for diff in result.diffs:
                if diff.changed:
                    click.echo(f'    - Prompt: "{diff.prompt_text[:60]}..."')
        else:
            click.echo("  All responses remained the same after replay.")

    def _ask_user_confirmation(self, entry: PromptLogEntry) -> bool:
        """Ask the user whether to replay a context-dependent prompt."""
        click.echo(f"\n  Context-dependent prompt detected (Phase {entry.phase}):")
        click.echo(f'  "{entry.prompt_text[:100]}"')

        while True:
            try:
                response = (
                    click.prompt(
                        "  Replay this prompt? (yes/no)",
                        type=str,
                    )
                    .lower()
                    .strip()
                )
                if response in ("yes", "y"):
                    return True
                elif response in ("no", "n"):
                    return False
                else:
                    click.echo("  Please enter 'yes' or 'no'")
            except click.Abort:
                return False
