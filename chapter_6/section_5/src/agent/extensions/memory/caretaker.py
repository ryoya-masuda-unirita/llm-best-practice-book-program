"""Memory caretaker for managing snapshots (Memento pattern)."""

from src.agent.core.memory import Memory, MemorySnapshot


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
