"""Pipeline memory with phase-based rollback support (Memento pattern)."""

import copy
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

import click
from src.agent.core.memory import Memory, MemorySnapshot
from src.agent.extensions.nodes.pipeline import PipelineState
from src.client.llm_client import LLMProvider
from src.logger import make_logger
from src.model.model import (
    CompletedArticle,
)

logger = make_logger(__name__)


@dataclass
class PipelinePhaseSnapshot:
    """Snapshot of pipeline state at a specific phase (Memento)."""

    timestamp: datetime
    phase: int
    phase_name: str
    state: PipelineState


class PipelineMemory(Memory):
    """Memory for article generation pipeline with phase-based rollback.

    This memory implementation uses the Memento pattern to enable rollback
    to any previous phase in the pipeline. Each phase completion is tracked
    as a snapshot that can be restored.

    Simplified phase detection (single session, no parallel worlds):
    - Phase 0: Initial state (only theme, language, metadata)
    - Phase 1: outline populated
    - Phase 2: first_half populated
    - Phase 3: second_half populated
    - Phase 4: review populated
    - Phase 5: human_approved populated
    """

    PHASE_NAMES = {
        0: "Initial State",
        1: "Outline Generation Complete",
        2: "First Half Complete",
        3: "Second Half Complete",
        4: "Article Reviewed",
        5: "Approval Decision Made",
    }

    def __init__(self, initial_state: PipelineState):
        self._state = initial_state
        self._phase_snapshots: list[PipelinePhaseSnapshot] = []
        self._observations: list[Any] = []
        self._actions: list[Any] = []
        self._metadata: dict[str, Any] = {}

    @property
    def state(self) -> PipelineState:
        return self._state

    @state.setter
    def state(self, value: PipelineState) -> None:
        self._state = value

    def get_context(self) -> dict[str, object]:
        return {
            "state": self._state,
            "current_phase": self.get_current_phase(),
            "phase_name": self.get_phase_name(self.get_current_phase()),
            "observations": self._observations.copy(),
            "actions": self._actions.copy(),
            "metadata": self._metadata.copy(),
            "history_length": len(self._observations) + len(self._actions),
        }

    def add_observation(self, observation: Any) -> None:
        self._observations.append(observation)

    def add_action(self, action: Any) -> None:
        self._actions.append(action)

    def clear(self) -> None:
        self._observations.clear()
        self._actions.clear()
        self._metadata.clear()

    def save_snapshot(self) -> MemorySnapshot:
        return MemorySnapshot(
            timestamp=datetime.now(),
            observations=copy.deepcopy(self._observations),
            actions=copy.deepcopy(self._actions),
            metadata=copy.deepcopy(self._metadata),
        )

    def restore_snapshot(self, snapshot: MemorySnapshot) -> None:
        self._observations = copy.deepcopy(snapshot.observations)
        self._actions = copy.deepcopy(snapshot.actions)
        self._metadata = copy.deepcopy(snapshot.metadata)

    def get_current_phase(self) -> int:
        if self._state.human_approved is not None:
            return 5
        elif self._state.review is not None:
            return 4
        elif self._state.second_half is not None:
            return 3
        elif self._state.first_half is not None:
            return 2
        elif self._state.outline is not None:
            return 1
        else:
            return 0

    def get_phase_name(self, phase: int) -> str:
        return self.PHASE_NAMES.get(phase, "Unknown Phase")

    def save_phase_snapshot(self) -> int:
        current_phase = self.get_current_phase()
        snapshot = PipelinePhaseSnapshot(
            timestamp=datetime.now(),
            phase=current_phase,
            phase_name=self.get_phase_name(current_phase),
            state=copy.deepcopy(self._state),
        )
        self._phase_snapshots.append(snapshot)
        return len(self._phase_snapshots) - 1

    def get_available_rollback_phases(self) -> list[tuple[int, str]]:
        current_phase = self.get_current_phase()
        return [(phase, self.get_phase_name(phase)) for phase in range(current_phase)]

    def forget_phases_after(self, target_phase: int) -> None:
        click.echo(f"\n🔄 Rolling back to Phase {target_phase}: {self.get_phase_name(target_phase)}")
        click.echo("   Forgetting all subsequent phases...\n")

        if target_phase < 5:
            self._state.human_approved = None
            self._state.review_loop_iteration = 0
            self._state.previous_feedback = None
            logger.info("Forgot Phase 5: Approval decision")

        if target_phase < 4:
            self._state.review = None
            logger.info("Forgot Phase 4: Article review")

        if target_phase < 3:
            self._state.second_half = None
            logger.info("Forgot Phase 3: Second half")

        if target_phase < 2:
            self._state.first_half = None
            logger.info("Forgot Phase 2: First half")

        if target_phase < 1:
            self._state.outline = None
            logger.info("Forgot Phase 1: Outline")

        self._state.error = None

        click.echo(f"✅ Rolled back to Phase {target_phase}. Forgotten phases will be regenerated.\n")

    def restore_to_phase(self, target_phase: int) -> bool:
        for snapshot in reversed(self._phase_snapshots):
            if snapshot.phase <= target_phase:
                self._state = copy.deepcopy(snapshot.state)
                logger.info(f"Restored to phase {snapshot.phase}: {snapshot.phase_name}")
                return True

        # If no snapshot found, use forget_phases_after instead
        self.forget_phases_after(target_phase)
        return True

    def get_final_article(self) -> CompletedArticle | None:
        if not self._state.outline or not self._state.first_half or not self._state.second_half:
            return None

        return CompletedArticle(
            outline=self._state.outline,
            first_half=self._state.first_half,
            second_half=self._state.second_half,
            review=self._state.review,
            language=self._state.language,
        )


class PipelineMemoryCaretaker:
    """Caretaker for managing pipeline memory snapshots (Memento pattern)."""

    def __init__(self):
        self.phase_snapshots: list[PipelinePhaseSnapshot] = []

    def save_phase(self, memory: PipelineMemory) -> int:
        snapshot = PipelinePhaseSnapshot(
            timestamp=datetime.now(),
            phase=memory.get_current_phase(),
            phase_name=memory.get_phase_name(memory.get_current_phase()),
            state=copy.deepcopy(memory.state),
        )
        self.phase_snapshots.append(snapshot)
        return len(self.phase_snapshots) - 1

    def restore_phase(self, memory: PipelineMemory, index: int) -> bool:
        if 0 <= index < len(self.phase_snapshots):
            snapshot = self.phase_snapshots[index]
            memory.state = copy.deepcopy(snapshot.state)
            return True
        return False

    def get_snapshots(self) -> list[PipelinePhaseSnapshot]:
        return self.phase_snapshots.copy()

    def clear_snapshots(self) -> None:
        self.phase_snapshots.clear()


def create_initial_state(
    theme: str,
    language: Literal["en", "ja"],
    llm_provider: LLMProvider,
    model: str,
) -> PipelineState:
    return PipelineState(
        theme=theme,
        language=language,
        llm_provider=llm_provider,
        model=model,
    )
