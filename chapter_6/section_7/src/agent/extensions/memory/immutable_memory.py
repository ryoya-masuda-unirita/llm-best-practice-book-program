"""Immutable Memory Implementation.

This module implements a memory strategy where data is never modified,
only appended. Each session/operation creates a new timestamped file,
and the current state is reconstructed by reducing all files in order.

Use cases:
- Conversation history and chat logs
- Action/behavior logs
- Time-series data
- Audit trails
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from src.agent.extensions.memory.models import (
    CompactionResult,
    ImmutableMemoryEntry,
    MemoryDocument,
    MemoryEntry,
    MemoryEntryType,
)


class ImmutableMemory:
    """Memory with immutable append-only strategy.

    This implementation never modifies existing files. Instead, each
    operation creates a new file with a timestamp. The current state
    is reconstructed by reading and merging all files in timestamp order.

    Key characteristics:
    - No locks required (append-only)
    - Natural audit trail
    - No conflict risk
    - Requires periodic compaction

    Tradeoffs:
    - No lock contention
    - I/O overhead for reads (multiple files)
    - Storage growth without compaction
    - Best for time-series/log data
    """

    def __init__(
        self,
        memory_dir: str | Path,
        agent_id: str,
        session_id: str | None = None,
    ) -> None:
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.agent_id = agent_id
        self.session_id = session_id or str(uuid4())
        self._current_entries: list[MemoryEntry] = []

    def _generate_filename(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"{timestamp}_{self.agent_id}_{self.session_id}.json"

    def _list_memory_files(self, namespace: str | None = None) -> list[Path]:
        pattern = f"{namespace}_*.json" if namespace else "*.json"
        files = list(self.memory_dir.glob(pattern))
        return sorted(files)

    def _load_entry(self, file_path: Path) -> ImmutableMemoryEntry:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
            return ImmutableMemoryEntry.model_validate(data)

    def _save_entry(self, entry: ImmutableMemoryEntry) -> Path:
        filename = self._generate_filename()
        file_path = self.memory_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(entry.model_dump(mode="json"), f, indent=2, default=str)
        return file_path

    def append(
        self,
        entry_type: MemoryEntryType,
        content: str,
        metadata: dict[str, Any] | None = None,
        flush: bool = False,
    ) -> MemoryEntry:
        entry = MemoryEntry(
            id=str(uuid4()),
            type=entry_type,
            content=content,
            agent_id=self.agent_id,
            metadata=metadata or {},
        )
        self._current_entries.append(entry)

        if flush:
            self.flush()

        return entry

    def flush(self) -> Path | None:
        if not self._current_entries:
            return None

        immutable_entry = ImmutableMemoryEntry(
            id=str(uuid4()),
            agent_id=self.agent_id,
            session_id=self.session_id,
            timestamp=datetime.now(),
            entries=self._current_entries.copy(),
            is_compacted=False,
        )

        file_path = self._save_entry(immutable_entry)
        self._current_entries.clear()
        return file_path

    def read_all(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[MemoryEntry]:
        """Reducer operation that reconstructs current state from all files."""
        all_entries: list[MemoryEntry] = []

        for file_path in self._list_memory_files():
            try:
                immutable_entry = self._load_entry(file_path)

                for entry in immutable_entry.entries:
                    if since and entry.timestamp < since:
                        continue
                    if until and entry.timestamp > until:
                        continue
                    all_entries.append(entry)
            except (json.JSONDecodeError, ValueError):
                continue

        all_entries.extend(self._current_entries)

        return sorted(all_entries, key=lambda e: e.timestamp)

    def read_by_type(self, entry_type: MemoryEntryType) -> list[MemoryEntry]:
        return [e for e in self.read_all() if e.type == entry_type]

    def read_by_agent(self, agent_id: str) -> list[MemoryEntry]:
        return [e for e in self.read_all() if e.agent_id == agent_id]

    def reduce(
        self,
        reducer: Callable[[dict[str, Any], MemoryEntry], dict[str, Any]],
        initial: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Apply a reducer function to reconstruct state."""
        state = initial if initial is not None else {}
        for entry in self.read_all():
            state = reducer(state, entry)
        return state

    def to_document(self, document_id: str) -> MemoryDocument:
        """Convert all entries to a MemoryDocument for lock-based memory compatibility."""
        entries = self.read_all()
        return MemoryDocument(
            id=document_id,
            version=len(entries),
            entries=entries,
        )

    def compact(
        self,
        keep_recent_files: int = 5,
        min_files_for_compaction: int = 10,
    ) -> CompactionResult | None:
        """Compaction operation that reduces storage and I/O by merging old files."""
        files = self._list_memory_files()

        if len(files) < min_files_for_compaction:
            return None

        files_to_compact = files[:-keep_recent_files] if keep_recent_files > 0 else files

        if len(files_to_compact) < 2:
            return None

        all_entries: list[MemoryEntry] = []
        source_file_ids: list[str] = []

        for file_path in files_to_compact:
            try:
                immutable_entry = self._load_entry(file_path)
                all_entries.extend(immutable_entry.entries)
                source_file_ids.append(file_path.stem)
            except (json.JSONDecodeError, ValueError):
                continue

        all_entries.sort(key=lambda e: e.timestamp)

        compacted_entry = ImmutableMemoryEntry(
            id=str(uuid4()),
            agent_id=self.agent_id,
            session_id="compacted",
            timestamp=datetime.now(),
            entries=all_entries,
            is_compacted=True,
        )

        compacted_filename = f"compacted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        compacted_path = self.memory_dir / compacted_filename
        with open(compacted_path, "w", encoding="utf-8") as f:
            json.dump(compacted_entry.model_dump(mode="json"), f, indent=2, default=str)

        for file_path in files_to_compact:
            file_path.unlink()

        return CompactionResult(
            compacted_file_id=compacted_path.stem,
            source_files=source_file_ids,
            total_entries=len(all_entries),
            timestamp=datetime.now(),
        )

    def get_stats(self) -> dict[str, Any]:
        files = self._list_memory_files()
        total_entries = 0
        total_size = 0
        compacted_files = 0

        for file_path in files:
            total_size += file_path.stat().st_size
            try:
                entry = self._load_entry(file_path)
                total_entries += len(entry.entries)
                if entry.is_compacted:
                    compacted_files += 1
            except (json.JSONDecodeError, ValueError):
                continue

        return {
            "total_files": len(files),
            "compacted_files": compacted_files,
            "total_entries": total_entries + len(self._current_entries),
            "buffered_entries": len(self._current_entries),
            "total_size_bytes": total_size,
        }

    def cleanup_old_files(self, max_age_days: int = 30) -> int:
        cutoff = datetime.now().timestamp() - (max_age_days * 86400)
        deleted = 0
        for file_path in self._list_memory_files():
            if file_path.stat().st_mtime < cutoff:
                file_path.unlink()
                deleted += 1
        return deleted


class SessionMemory(ImmutableMemory):
    """Convenience class for session-scoped immutable memory.

    Each session automatically flushes on close.
    """

    def __init__(
        self,
        memory_dir: str | Path,
        agent_id: str,
        session_id: str | None = None,
    ) -> None:
        super().__init__(memory_dir, agent_id, session_id)
        self._closed = False

    def close(self) -> Path | None:
        if self._closed:
            return None
        self._closed = True
        return self.flush()

    def __enter__(self) -> "SessionMemory":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
