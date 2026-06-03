"""Memory data models using Pydantic.

This module defines the data structures for memory entries and lock information
that are persisted as JSON files in the memory directory.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MemoryEntryType(str, Enum):
    """Type of memory entry."""

    OBSERVATION = "observation"
    ACTION = "action"
    TOOL_RESULT = "tool_result"
    THOUGHT = "thought"


class MemoryEntry(BaseModel):
    """Single entry in the memory store."""

    id: str = Field(description="Unique identifier for the entry")
    type: MemoryEntryType = Field(description="Type of the memory entry")
    content: str = Field(description="Content of the memory entry")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)
    agent_id: str | None = Field(default=None, description="ID of the agent that created this entry")


class MemoryDocument(BaseModel):
    """Complete memory document stored as JSON file."""

    id: str = Field(description="Unique identifier for the memory document")
    version: int = Field(default=1, description="Version number for optimistic locking")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    entries: list[MemoryEntry] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_entry(self, entry: MemoryEntry) -> None:
        """Add an entry and update the version."""
        self.entries.append(entry)
        self.version += 1
        self.updated_at = datetime.now()


class LockInfo(BaseModel):
    """Information about a lock held on a resource."""

    resource_id: str = Field(description="ID of the locked resource")
    holder_id: str = Field(description="ID of the lock holder (agent)")
    priority: int = Field(default=0, description="Priority of the lock holder (higher = more priority)")
    acquired_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime | None = Field(default=None, description="TTL expiration time")
    version: int = Field(default=1, description="Version at time of lock acquisition")


class ShadowCopy(BaseModel):
    """Shadow copy of data for preemptible lock recovery."""

    original_resource_id: str = Field(description="ID of the original resource")
    holder_id: str = Field(description="ID of the agent whose lock was preempted")
    preempted_by: str = Field(description="ID of the agent that preempted the lock")
    timestamp: datetime = Field(default_factory=datetime.now)
    data: dict[str, Any] = Field(description="Copy of the data at preemption time")


class ImmutableMemoryEntry(BaseModel):
    """Immutable memory entry with timestamp-based filename."""

    id: str = Field(description="Unique identifier")
    agent_id: str = Field(description="Agent that created this entry")
    session_id: str = Field(description="Session identifier")
    timestamp: datetime = Field(default_factory=datetime.now)
    entries: list[MemoryEntry] = Field(default_factory=list)
    is_compacted: bool = Field(default=False, description="Whether this is a compacted file")


class CompactionResult(BaseModel):
    """Result of a memory compaction operation."""

    compacted_file_id: str = Field(description="ID of the new compacted file")
    source_files: list[str] = Field(description="List of source file IDs that were compacted")
    total_entries: int = Field(description="Total number of entries after compaction")
    timestamp: datetime = Field(default_factory=datetime.now)
