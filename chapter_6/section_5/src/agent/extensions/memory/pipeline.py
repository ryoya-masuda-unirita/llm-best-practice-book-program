"""Pipeline memory for article generation pipeline state management."""

import copy
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

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
    """Memory for article generation pipeline state management.

    This memory implementation tracks the pipeline state through different phases.
    Each phase completion is tracked as a snapshot for state management.

    Phase detection is based on which state fields are populated:
    - Phase 0: Initial state (only theme, language, metadata)
    - Phase 1: outline_sessions populated
    - Phase 2: selected_outline_session_id populated
    - Phase 3: first_half_session populated
    - Phase 4: second_half_sessions populated
    - Phase 5: reviewed_sessions populated
    - Phase 6: final_selected_session_id populated
    - Phase 7: human_approved populated
    """

    PHASE_NAMES = {
        0: "Initial State",
        1: "Outline Generation Complete",
        2: "Outline Selected",
        3: "First Half Complete",
        4: "Second Half Variants Generated",
        5: "All Articles Reviewed",
        6: "Article Selected",
        7: "Approval Decision Made",
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
            return 7
        elif self._state.final_selected_session_id is not None:
            return 6
        elif self._state.reviewed_sessions:
            return 5
        elif self._state.second_half_sessions:
            return 4
        elif self._state.first_half_session is not None:
            return 3
        elif self._state.selected_outline_session_id is not None:
            return 2
        elif self._state.outline_sessions:
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

    def get_final_article(self) -> CompletedArticle | None:
        if not self._state.final_selected_session_id or not self._state.reviewed_sessions:
            return None

        final_session = next(
            (s for s in self._state.reviewed_sessions if s.session_id == self._state.final_selected_session_id),
            self._state.reviewed_sessions[0] if self._state.reviewed_sessions else None,
        )

        if not final_session:
            return None

        return final_session.to_completed_article(self._state.language)


class PipelineMemoryCaretaker:
    """Caretaker for managing pipeline memory snapshots."""

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
    num_outline_variants: int = 3,
    num_second_half_variants: int = 3,
) -> PipelineState:
    return PipelineState(
        theme=theme,
        language=language,
        llm_provider=llm_provider,
        model=model,
        num_outline_variants=num_outline_variants,
        num_second_half_variants=num_second_half_variants,
    )
