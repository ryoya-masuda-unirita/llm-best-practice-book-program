"""Conversational memory organized by turns."""

from src.agent.core.base import ToolResult
from src.agent.core.memory import MemorySnapshot
from src.agent.extensions.memory.context import ContextMemory


class ConversationalMemory(ContextMemory):
    """Memory organized by conversation turns (inherits from ContextMemory)."""

    def __init__(self, max_turns: int = 50):
        super().__init__(max_history=max_turns * 2)  # 2 items per turn (action + observation)
        self.max_turns = max_turns
        self._turn_count = 0

    def get_context(self) -> dict[str, object]:
        context = super().get_context()
        context["num_turns"] = self._turn_count
        return context

    def add_observation(self, observation: str | ToolResult) -> None:
        super().add_observation(observation)
        self._turn_count = min(len(self.observations), self.max_turns)

    def save_snapshot(self) -> MemorySnapshot:
        snapshot = super().save_snapshot()
        snapshot.metadata["_turn_count"] = self._turn_count
        return snapshot

    def restore_snapshot(self, snapshot: MemorySnapshot) -> None:
        super().restore_snapshot(snapshot)
        self._turn_count = snapshot.metadata.get("_turn_count", len(self.observations))
