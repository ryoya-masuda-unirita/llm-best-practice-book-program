"""Write-Ahead Log for user prompts, enabling replay after rollback."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class PromptType(Enum):
    """Classification of user prompts for replay decisions."""

    REQUIREMENT = "requirement"
    FEEDBACK = "feedback"
    CONFIRMATION = "confirmation"
    CONTEXT_DEPENDENT = "context_dependent"


@dataclass
class PromptLogEntry:
    """A single entry in the prompt WAL."""

    index: int
    timestamp: datetime
    phase: int
    prompt_text: str
    prompt_type: PromptType
    depends_on_prior_response: bool = False
    response_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    caused_error: bool = False


class PromptLog:
    """Write-Ahead Log that records all user prompts for potential replay.

    Inspired by database WAL and event sourcing patterns. Every user
    interaction is logged so that after a rollback, valid prompts can
    be identified and replayed automatically.
    """

    def __init__(self) -> None:
        self._entries: list[PromptLogEntry] = []
        self._next_index: int = 0

    def append(
        self,
        phase: int,
        prompt_text: str,
        prompt_type: PromptType,
        depends_on_prior_response: bool = False,
        response_text: str | None = None,
        metadata: dict[str, Any] | None = None,
        caused_error: bool = False,
    ) -> PromptLogEntry:
        """Append a new entry to the prompt log."""
        entry = PromptLogEntry(
            index=self._next_index,
            timestamp=datetime.now(),
            phase=phase,
            prompt_text=prompt_text,
            prompt_type=prompt_type,
            depends_on_prior_response=depends_on_prior_response,
            response_text=response_text,
            metadata=metadata or {},
            caused_error=caused_error,
        )
        self._entries.append(entry)
        self._next_index += 1
        return entry

    def get_entries_after_phase(self, phase: int) -> list[PromptLogEntry]:
        """Get all entries recorded after a given phase."""
        return [e for e in self._entries if e.phase > phase]

    def get_entries_in_phase(self, phase: int) -> list[PromptLogEntry]:
        """Get all entries recorded during a specific phase."""
        return [e for e in self._entries if e.phase == phase]

    def get_all_entries(self) -> list[PromptLogEntry]:
        """Get all entries in the log."""
        return self._entries.copy()

    def mark_entry_as_error(self, index: int) -> None:
        """Mark a specific entry as having caused an error."""
        for entry in self._entries:
            if entry.index == index:
                entry.caused_error = True
                break

    def update_response(self, index: int, response_text: str) -> None:
        """Update the response text for a given entry."""
        for entry in self._entries:
            if entry.index == index:
                entry.response_text = response_text
                break

    def clear_after_phase(self, phase: int) -> int:
        """Remove all entries after a given phase. Returns count of removed entries."""
        original_count = len(self._entries)
        self._entries = [e for e in self._entries if e.phase <= phase]
        return original_count - len(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        return f"PromptLog(entries={len(self._entries)})"
