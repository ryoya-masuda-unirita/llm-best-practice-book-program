"""Context-based memory implementation."""

import copy
from datetime import datetime

from src.agent.core.base import Action, MetadataDict, ToolResult
from src.agent.core.memory import Memory, MemorySnapshot


class ContextMemory(Memory):
    """Simple list-based memory implementation with Memento pattern."""

    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.observations: list[str | ToolResult] = []
        self.actions: list[Action] = []
        self.metadata: MetadataDict = {}

    def get_context(self) -> dict[str, object]:
        return {
            "observations": self.observations.copy(),
            "actions": self.actions.copy(),
            "metadata": self.metadata.copy(),
            "history_length": len(self.observations) + len(self.actions),
        }

    def add_observation(self, observation: str | ToolResult) -> None:
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
