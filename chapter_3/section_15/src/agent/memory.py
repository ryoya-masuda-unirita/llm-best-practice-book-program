"""Memory and context management with Memento pattern."""

import copy
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.agent.base import Action, Memory


@dataclass
class MemorySnapshot:
    """Memento: Snapshot of memory state for restoration."""

    timestamp: datetime
    observations: list[Any]
    actions: list[Action]
    metadata: dict[str, Any]


class ContextMemory(Memory):
    """Simple list-based memory implementation with Memento pattern."""

    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.observations: list[Any] = []
        self.actions: list[Action] = []
        self.metadata: dict[str, Any] = {}

    def get_context(self) -> dict[str, Any]:
        return {
            "observations": self.observations.copy(),
            "actions": self.actions.copy(),
            "metadata": self.metadata.copy(),
            "history_length": len(self.observations) + len(self.actions),
        }

    def add_observation(self, observation: Any) -> None:
        self.observations.append(observation)
        self._trim_history()

    def add_action(self, action: Action) -> None:
        self.actions.append(action)
        self._trim_history()

    def clear(self) -> None:
        self.observations.clear()
        self.actions.clear()
        self.metadata.clear()

    def save_snapshot(self) -> MemorySnapshot:
        return MemorySnapshot(
            timestamp=datetime.now(),
            observations=copy.deepcopy(self.observations),
            actions=copy.deepcopy(self.actions),
            metadata=copy.deepcopy(self.metadata),
        )

    def restore_snapshot(self, snapshot: MemorySnapshot) -> None:
        self.observations = copy.deepcopy(snapshot.observations)
        self.actions = copy.deepcopy(snapshot.actions)
        self.metadata = copy.deepcopy(snapshot.metadata)

    def _trim_history(self) -> None:
        total = len(self.observations) + len(self.actions)
        if total > self.max_history:
            excess = total - self.max_history
            obs_remove = min(excess, len(self.observations))
            if obs_remove > 0:
                self.observations = self.observations[obs_remove:]
            if (remaining := excess - obs_remove) > 0:
                self.actions = self.actions[remaining:]


class ConversationalMemory(ContextMemory):
    """Memory organized by conversation turns (inherits from ContextMemory)."""

    def __init__(self, max_turns: int = 50):
        super().__init__(max_history=max_turns * 2)  # 2 items per turn (action + observation)
        self.max_turns = max_turns
        self._turn_count = 0

    def get_context(self) -> dict[str, Any]:
        context = super().get_context()
        context["num_turns"] = self._turn_count
        return context

    def add_observation(self, observation: Any) -> None:
        super().add_observation(observation)
        self._turn_count = min(len(self.observations), self.max_turns)


class MemoryCaretaker:
    """Caretaker for managing memory snapshots (Memento pattern)."""

    def __init__(self):
        self.snapshots: list[MemorySnapshot] = []

    def save(self, memory: Memory) -> int:
        self.snapshots.append(memory.save_snapshot())
        return len(self.snapshots) - 1

    def restore(self, memory: Memory, index: int) -> bool:
        if 0 <= index < len(self.snapshots):
            memory.restore_snapshot(self.snapshots[index])
            return True
        return False

    def clear_snapshots(self) -> None:
        self.snapshots.clear()
