"""Examples demonstrating the AI Agent memory lock strategies.

This module provides comprehensive examples of using different memory
locking strategies for multi-agent systems:

1. Conservative Lock (Pessimistic Lock): Acquires locks before operations
2. Optimistic Lock: Version-based conflict detection at write time
3. Preemptible Lock: Priority-based lock acquisition with shadow copies
4. Immutable Memory: Append-only storage without locks

Each strategy has different tradeoffs between consistency, throughput,
and complexity. Choose based on your system's requirements.
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.agent.extensions.memory import (
    ConservativeLockMemory,
    ImmutableMemory,
    LocalDictLockManager,
    LockAcquisitionError,
    MemoryEntry,
    MemoryEntryType,
    OptimisticLockConflictError,
    OptimisticLockMemory,
    PreemptibleLockMemory,
    SessionMemory,
)
from src.logger import make_logger

logger = make_logger(__name__)


@dataclass
class TimeSeriesEvent:
    """Single event in the time series log."""

    timestamp: datetime
    elapsed_ms: float
    agent_id: str
    event_type: str
    resource_id: str
    details: str
    version: int | None = None
    success: bool = True


@dataclass
class TimeSeriesLog:
    """Time series log for memory operations."""

    strategy_name: str
    events: list[TimeSeriesEvent] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)

    def log(
        self,
        agent_id: str,
        event_type: str,
        resource_id: str,
        details: str,
        version: int | None = None,
        success: bool = True,
    ) -> None:
        """Add an event to the log."""
        now = datetime.now()
        elapsed_ms = (now - self.start_time).total_seconds() * 1000
        event = TimeSeriesEvent(
            timestamp=now,
            elapsed_ms=elapsed_ms,
            agent_id=agent_id,
            event_type=event_type,
            resource_id=resource_id,
            details=details,
            version=version,
            success=success,
        )
        self.events.append(event)

    def print_log(self) -> None:
        """Print the time series log in a formatted table."""
        logger.info(f"\n{'=' * 100}")
        logger.info(f"TIME SERIES LOG: {self.strategy_name}")
        logger.info(f"{'=' * 100}")
        logger.info(
            f"{'Time(ms)':>10} | {'Agent':<20} | {'Event':<15} | {'Resource':<20} | {'Ver':>4} | {'Status':<7} | Details"
        )
        logger.info(f"{'-' * 100}")

        for event in self.events:
            status = "OK" if event.success else "FAIL"
            version_str = str(event.version) if event.version is not None else "-"
            logger.info(
                f"{event.elapsed_ms:>10.1f} | {event.agent_id:<20} | {event.event_type:<15} | "
                f"{event.resource_id:<20} | {version_str:>4} | {status:<7} | {event.details}"
            )

        logger.info(f"{'=' * 100}\n")


def example_1_agent_with_conservative_lock(memory_directory: str) -> TimeSeriesLog:
    """Example 1: Basic agent with Conservative lock.

    Conservative locking (pessimistic locking) acquires an exclusive lock
    before any operation and holds it until completion. This is the safest
    approach for data integrity but can cause blocking.

    Use cases:
    - Multi-file transactions (e.g., item trading between agents)
    - Critical data requiring strict consistency
    - Operations where conflicts are expensive to resolve
    """
    logger.info("\n=== Example 1: Basic Agent with conservative memory lock ===\n")

    ts_log = TimeSeriesLog(strategy_name="Conservative Lock (Pessimistic)")

    memory_dir = os.path.join(memory_directory, "conservative")
    lock_manager = LocalDictLockManager()

    agent_a = ConservativeLockMemory(
        memory_dir=memory_dir,
        agent_id="agent_a",
        lock_manager=lock_manager,
        lock_ttl_seconds=60,
    )

    agent_b = ConservativeLockMemory(
        memory_dir=memory_dir,
        agent_id="agent_b",
        lock_manager=lock_manager,
        lock_ttl_seconds=60,
    )

    ts_log.log("agent_a", "LOCK_REQUEST", "shared_task_list", "Requesting exclusive lock")
    with agent_a.acquire_lock("shared_task_list"):
        ts_log.log("agent_a", "LOCK_ACQUIRED", "shared_task_list", "Lock acquired successfully")

        doc = agent_a.read("shared_task_list")
        ts_log.log("agent_a", "READ", "shared_task_list", f"Read document with {len(doc.entries)} entries")

        time.sleep(0.3)
        ts_log.log("agent_a", "PROCESSING", "shared_task_list", "Simulating LLM inference (300ms)")

        agent_a.add_entry(
            "shared_task_list",
            MemoryEntryType.ACTION,
            "Task added by Agent A: Analyze customer feedback",
        )
        version = lock_manager.get_version("shared_task_list")
        ts_log.log("agent_a", "WRITE", "shared_task_list", "Added new task entry", version=version)

    ts_log.log("agent_a", "LOCK_RELEASED", "shared_task_list", "Lock released")

    ts_log.log("agent_b", "LOCK_REQUEST", "shared_task_list", "Requesting exclusive lock")
    with agent_b.acquire_lock("shared_task_list"):
        ts_log.log("agent_b", "LOCK_ACQUIRED", "shared_task_list", "Lock acquired successfully")

        doc = agent_b.read("shared_task_list")
        ts_log.log("agent_b", "READ", "shared_task_list", f"Read document with {len(doc.entries)} entries")

        agent_b.add_entry(
            "shared_task_list",
            MemoryEntryType.ACTION,
            "Task marked complete by Agent B",
        )
        version = lock_manager.get_version("shared_task_list")
        ts_log.log("agent_b", "WRITE", "shared_task_list", "Marked task as complete", version=version)

    ts_log.log("agent_b", "LOCK_RELEASED", "shared_task_list", "Lock released")

    logger.info("\n--- Multi-resource locking (prevents deadlock) ---")
    ts_log.log("agent_a", "MULTI_LOCK_REQ", "inventory_a,inventory_b", "Requesting locks in sorted order")

    with agent_a.acquire_multiple_locks(["inventory_a", "inventory_b"]):
        ts_log.log("agent_a", "LOCK_ACQUIRED", "inventory_a", "First lock acquired")
        ts_log.log("agent_a", "LOCK_ACQUIRED", "inventory_b", "Second lock acquired")

        agent_a.add_entry("inventory_a", MemoryEntryType.ACTION, "Transferred item: Sword -> B")
        ts_log.log("agent_a", "WRITE", "inventory_a", "Updated inventory A")

        agent_a.add_entry("inventory_b", MemoryEntryType.ACTION, "Received item: Sword from A")
        ts_log.log("agent_a", "WRITE", "inventory_b", "Updated inventory B")

    ts_log.log("agent_a", "LOCK_RELEASED", "inventory_b", "Released in reverse order")
    ts_log.log("agent_a", "LOCK_RELEASED", "inventory_a", "Released in reverse order")

    logger.info("\n--- Demonstrating lock contention ---")

    def agent_task(agent: ConservativeLockMemory, task_name: str) -> None:
        ts_log.log(agent.agent_id, "LOCK_REQUEST", "contested", f"Requesting lock for {task_name}")
        try:
            with agent.acquire_lock("contested", wait=True, timeout_seconds=2.0):
                ts_log.log(agent.agent_id, "LOCK_ACQUIRED", "contested", "Lock acquired")
                time.sleep(0.2)
                ts_log.log(agent.agent_id, "PROCESSING", "contested", f"Processing {task_name}")
                agent.add_entry("contested", MemoryEntryType.OBSERVATION, f"Processed: {task_name}")
                ts_log.log(agent.agent_id, "WRITE", "contested", f"Completed {task_name}")
        except LockAcquisitionError:
            ts_log.log(agent.agent_id, "LOCK_TIMEOUT", "contested", "Lock acquisition timed out", success=False)

    ts_log.log("agent_a", "LOCK_REQUEST", "contested", "Lock released after task")
    ts_log.log("agent_b", "LOCK_WAIT", "contested", "Waiting for lock (blocked by agent_a)")

    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(agent_task, agent_a, "Task X")
        time.sleep(0.05)
        executor.submit(agent_task, agent_b, "Task Y")

    time.sleep(1)

    logger.info("Conservative lock example completed!")
    return ts_log


def example_2_with_optimistic_lock(memory_directory: str) -> TimeSeriesLog:
    """Example 2: Agent with Optimistic lock.

    Optimistic locking reads without locking, then validates the version
    at write time. If the version has changed, the write fails and must
    be retried. Best when conflicts are rare (< 20% of operations).

    Use cases:
    - Collaborative editing with low conflict rate
    - High-throughput systems
    - Independent operations on shared data
    """
    logger.info("\n=== Example 2: Agent with optimistic memory lock ===\n")

    ts_log = TimeSeriesLog(strategy_name="Optimistic Lock (Version-based)")

    memory_dir = os.path.join(memory_directory, "optimistic")
    lock_manager = LocalDictLockManager()

    agent_a = OptimisticLockMemory(
        memory_dir=memory_dir,
        agent_id="agent_a",
        lock_manager=lock_manager,
        max_retries=3,
    )

    agent_b = OptimisticLockMemory(
        memory_dir=memory_dir,
        agent_id="agent_b",
        lock_manager=lock_manager,
        max_retries=3,
    )

    ts_log.log("agent_a", "READ", "spec_document", "Reading without lock")
    doc_a, version_a = agent_a.read("spec_document")
    ts_log.log("agent_a", "READ_COMPLETE", "spec_document", f"Got {len(doc_a.entries)} entries", version=version_a)

    ts_log.log("agent_b", "READ", "spec_document", "Reading without lock (concurrent)")
    doc_b, version_b = agent_b.read("spec_document")
    ts_log.log("agent_b", "READ_COMPLETE", "spec_document", f"Got {len(doc_b.entries)} entries", version=version_b)

    ts_log.log("agent_a", "PROCESSING", "spec_document", "Simulating LLM inference...")
    ts_log.log("agent_b", "PROCESSING", "spec_document", "Simulating LLM inference...")
    time.sleep(0.1)

    doc_b.add_entry(
        MemoryEntry(
            id="entry_b1",
            type=MemoryEntryType.OBSERVATION,
            content="Chapter 2 written by Agent B",
            agent_id="agent_b",
        )
    )
    ts_log.log("agent_b", "WRITE_ATTEMPT", "spec_document", f"Writing with version {version_b}", version=version_b)
    new_version = agent_b.write("spec_document", doc_b, version_b)
    ts_log.log("agent_b", "WRITE_SUCCESS", "spec_document", "Version check passed", version=new_version)

    doc_a.add_entry(
        MemoryEntry(
            id="entry_a1",
            type=MemoryEntryType.OBSERVATION,
            content="Chapter 1 written by Agent A",
            agent_id="agent_a",
        )
    )

    ts_log.log("agent_a", "WRITE_ATTEMPT", "spec_document", f"Writing with version {version_a}", version=version_a)
    try:
        agent_a.write("spec_document", doc_a, version_a)
    except OptimisticLockConflictError as e:
        ts_log.log(
            "agent_a",
            "CONFLICT",
            "spec_document",
            f"Version mismatch: expected {e.read_version}, actual {e.current_version}",
            version=e.current_version,
            success=False,
        )

        ts_log.log("agent_a", "RETRY_READ", "spec_document", "Re-reading for retry")
        doc_a_fresh, version_a_fresh = agent_a.read("spec_document")
        ts_log.log("agent_a", "READ_COMPLETE", "spec_document", "Got fresh data", version=version_a_fresh)

        doc_a_fresh.add_entry(
            MemoryEntry(
                id="entry_a1",
                type=MemoryEntryType.OBSERVATION,
                content="Chapter 1 written by Agent A",
                agent_id="agent_a",
            )
        )
        ts_log.log(
            "agent_a",
            "WRITE_ATTEMPT",
            "spec_document",
            f"Retry with version {version_a_fresh}",
            version=version_a_fresh,
        )
        new_version = agent_a.write("spec_document", doc_a_fresh, version_a_fresh)
        ts_log.log("agent_a", "WRITE_SUCCESS", "spec_document", "Retry successful", version=new_version)

    logger.info("\n--- Simulating concurrent writes ---")

    results: list[tuple[str, bool]] = []

    def concurrent_write(agent: OptimisticLockMemory, content: str) -> None:
        ts_log.log(agent.agent_id, "READ", "concurrent_test", "Reading for concurrent write")
        doc, version = agent.read("concurrent_test")
        ts_log.log(agent.agent_id, "READ_COMPLETE", "concurrent_test", "Read complete", version=version)

        time.sleep(0.05)
        ts_log.log(agent.agent_id, "PROCESSING", "concurrent_test", "Processing...")

        doc.add_entry(
            MemoryEntry(
                id=f"entry_{agent.agent_id}",
                type=MemoryEntryType.OBSERVATION,
                content=content,
                agent_id=agent.agent_id,
            )
        )

        ts_log.log(agent.agent_id, "WRITE_ATTEMPT", "concurrent_test", f"Writing version {version}", version=version)
        try:
            new_ver = agent.write("concurrent_test", doc, version)
            ts_log.log(agent.agent_id, "WRITE_SUCCESS", "concurrent_test", "Write succeeded", version=new_ver)
            results.append((agent.agent_id, True))
        except OptimisticLockConflictError as e:
            ts_log.log(
                agent.agent_id,
                "CONFLICT",
                "concurrent_test",
                f"Conflict: had v{e.read_version}, now v{e.current_version}",
                version=e.current_version,
                success=False,
            )
            results.append((agent.agent_id, False))

    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(concurrent_write, agent_a, "Content from A")
        executor.submit(concurrent_write, agent_b, "Content from B")

    time.sleep(0.5)

    successes = sum(1 for _, success in results if success)
    logger.info(f"Concurrent writes: {successes}/2 succeeded (expected: 1 due to conflict)")
    logger.info("Optimistic lock example completed!")
    return ts_log


def example_3_with_preemptive_lock(memory_directory: str) -> TimeSeriesLog:
    """Example 3: Agent with Preemptive lock.

    Preemptive (priority-based) locking allows higher-priority agents
    to force-acquire locks from lower-priority holders. Shadow copies
    preserve preempted data for later reconciliation.

    Use cases:
    - Emergency response systems
    - Real-time applications with SLA requirements
    - Hierarchical agent systems
    """
    logger.info("\n=== Example 3: Agent with preemptive memory lock ===\n")

    ts_log = TimeSeriesLog(strategy_name="Preemptible Lock (Priority-based)")

    memory_dir = os.path.join(memory_directory, "preemptible")
    lock_manager = LocalDictLockManager()

    normal_agent = PreemptibleLockMemory(
        memory_dir=memory_dir,
        agent_id="normal_agent",
        priority=PreemptibleLockMemory.PRIORITY_NORMAL,
        lock_manager=lock_manager,
    )

    emergency_agent = PreemptibleLockMemory(
        memory_dir=memory_dir,
        agent_id="emergency_agent",
        priority=PreemptibleLockMemory.PRIORITY_CRITICAL,
        lock_manager=lock_manager,
    )

    low_priority_agent = PreemptibleLockMemory(
        memory_dir=memory_dir,
        agent_id="low_priority_agent",
        priority=PreemptibleLockMemory.PRIORITY_LOW,
        lock_manager=lock_manager,
    )

    ts_log.log("normal_agent", "LOCK_REQUEST", "customer_tickets", "Priority=50, requesting lock")
    with normal_agent.acquire_lock("customer_tickets"):
        ts_log.log("normal_agent", "LOCK_ACQUIRED", "customer_tickets", "Lock acquired (priority=50)")

        normal_agent.add_entry(
            "customer_tickets",
            MemoryEntryType.OBSERVATION,
            "Processing routine ticket #1234",
        )
        ts_log.log("normal_agent", "WRITE", "customer_tickets", "Processing routine ticket")

        time.sleep(0.1)
        ts_log.log("normal_agent", "PROCESSING", "customer_tickets", "Simulating work...")

    ts_log.log("normal_agent", "LOCK_RELEASED", "customer_tickets", "Lock released normally")

    ts_log.log("emergency_agent", "LOCK_REQUEST", "customer_tickets", "Priority=100, force_preempt=True")
    with emergency_agent.acquire_lock("customer_tickets", force_preempt=True):
        ts_log.log("emergency_agent", "LOCK_ACQUIRED", "customer_tickets", "Lock acquired (priority=100)")

        emergency_agent.add_entry(
            "customer_tickets",
            MemoryEntryType.ACTION,
            "URGENT: Critical customer issue resolved",
        )
        ts_log.log("emergency_agent", "WRITE", "customer_tickets", "Handled critical issue")

    ts_log.log("emergency_agent", "LOCK_RELEASED", "customer_tickets", "Lock released")

    shadow_copies = emergency_agent.list_shadow_copies("customer_tickets")
    ts_log.log(
        "system",
        "SHADOW_CHECK",
        "customer_tickets",
        f"Shadow copies created: {len(shadow_copies)}",
    )

    logger.info("\n--- Low priority cannot preempt higher priority ---")

    ts_log.log("normal_agent", "LOCK_REQUEST", "important_resource", "Priority=50, requesting lock")
    with normal_agent.acquire_lock("important_resource"):
        ts_log.log("normal_agent", "LOCK_ACQUIRED", "important_resource", "Lock held with priority=50")

        normal_agent.add_entry(
            "important_resource",
            MemoryEntryType.OBSERVATION,
            "Working on important task",
        )
        ts_log.log("normal_agent", "WRITE", "important_resource", "Processing...")

        ts_log.log("low_priority_agent", "LOCK_REQUEST", "important_resource", "Priority=10, attempting preempt")
        try:
            with low_priority_agent.acquire_lock("important_resource"):
                ts_log.log("low_priority_agent", "LOCK_ACQUIRED", "important_resource", "Unexpected!")
        except LockAcquisitionError:
            ts_log.log(
                "low_priority_agent",
                "PREEMPT_DENIED",
                "important_resource",
                "Priority 10 < 50, cannot preempt",
                success=False,
            )

    ts_log.log("normal_agent", "LOCK_RELEASED", "important_resource", "Lock released")

    logger.info("\n--- Simulating preemption scenario ---")

    def normal_task() -> None:
        ts_log.log("normal_agent", "LOCK_REQUEST", "shared_resource", "Starting long task (priority=50)")
        try:
            with normal_agent.acquire_lock("shared_resource"):
                ts_log.log("normal_agent", "LOCK_ACQUIRED", "shared_resource", "Lock acquired")
                for i in range(3):
                    time.sleep(0.1)
                    ts_log.log("normal_agent", "PROCESSING", "shared_resource", f"Step {i + 1}/3")
                normal_agent.add_entry("shared_resource", MemoryEntryType.ACTION, "Normal task completed")
                ts_log.log("normal_agent", "WRITE", "shared_resource", "Task completed")
        except Exception as e:
            ts_log.log("normal_agent", "PREEMPTED", "shared_resource", str(e), success=False)

    def emergency_task() -> None:
        time.sleep(0.15)
        ts_log.log("emergency_agent", "LOCK_REQUEST", "shared_resource", "URGENT! Priority=100")
        with emergency_agent.acquire_lock("shared_resource", force_preempt=True):
            ts_log.log("emergency_agent", "LOCK_ACQUIRED", "shared_resource", "Preempted lower priority")
            emergency_agent.add_entry("shared_resource", MemoryEntryType.ACTION, "Emergency handled")
            ts_log.log("emergency_agent", "WRITE", "shared_resource", "Emergency resolved")
        ts_log.log("emergency_agent", "LOCK_RELEASED", "shared_resource", "Lock released")

    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(normal_task)
        executor.submit(emergency_task)

    time.sleep(1)

    logger.info("Preemptive lock example completed!")
    return ts_log


def example_4_with_immutable_memory(memory_directory: str) -> TimeSeriesLog:
    """Example 4: Agent with Immutable memory.

    Immutable memory never modifies existing data - all changes are
    appended as new timestamped files. The current state is reconstructed
    by reducing all files in order. No locks required.

    Use cases:
    - Conversation history / chat logs
    - Action/behavior audit trails
    - Time-series data
    - Event sourcing patterns
    """
    logger.info("\n=== Example 4: Agent with immutable memory ===\n")

    ts_log = TimeSeriesLog(strategy_name="Immutable Memory (Append-only)")

    memory_dir = os.path.join(memory_directory, "immutable")

    agent_a = ImmutableMemory(
        memory_dir=memory_dir,
        agent_id="chatbot_a",
        session_id="session_001",
    )

    agent_b = ImmutableMemory(
        memory_dir=memory_dir,
        agent_id="chatbot_b",
        session_id="session_002",
    )

    ts_log.log("chatbot_a", "APPEND", "session_001", "User: Hello, how can you help me?")
    agent_a.append(MemoryEntryType.OBSERVATION, "User: Hello, how can you help me?")

    ts_log.log("chatbot_a", "APPEND", "session_001", "Bot: I can help with product inquiries.")
    agent_a.append(MemoryEntryType.ACTION, "Bot: I can help with product inquiries.")

    ts_log.log("chatbot_b", "APPEND", "session_002", "User: I have a complaint. (concurrent)")
    agent_b.append(MemoryEntryType.OBSERVATION, "User: I have a complaint.")

    ts_log.log("chatbot_a", "APPEND", "session_001", "User: What's the price of item X?")
    agent_a.append(MemoryEntryType.OBSERVATION, "User: What's the price of item X?")

    ts_log.log("chatbot_b", "APPEND", "session_002", "Bot: I'm sorry. How can I help?")
    agent_b.append(MemoryEntryType.ACTION, "Bot: I'm sorry to hear that. How can I help?")

    ts_log.log("chatbot_a", "APPEND", "session_001", "Bot: Item X costs $99.")
    agent_a.append(MemoryEntryType.ACTION, "Bot: Item X costs $99.")

    ts_log.log("chatbot_b", "APPEND", "session_002", "User: My order was damaged.")
    agent_b.append(MemoryEntryType.OBSERVATION, "User: My order was damaged.")

    ts_log.log("chatbot_b", "APPEND", "session_002", "Bot: I've initiated a replacement.")
    agent_b.append(MemoryEntryType.ACTION, "Bot: I've initiated a replacement.")

    ts_log.log("chatbot_a", "FLUSH", "session_001", "Writing buffered entries to file")
    file_a = agent_a.flush()
    ts_log.log("chatbot_a", "FILE_CREATED", "session_001", f"Created: {file_a.name if file_a else 'None'}")

    ts_log.log("chatbot_b", "FLUSH", "session_002", "Writing buffered entries to file")
    file_b = agent_b.flush()
    ts_log.log("chatbot_b", "FILE_CREATED", "session_002", f"Created: {file_b.name if file_b else 'None'}")

    ts_log.log("system", "REDUCE", "all_sessions", "Reading all entries (Reducer operation)")
    all_entries = agent_a.read_all()
    ts_log.log("system", "REDUCE_COMPLETE", "all_sessions", f"Total entries: {len(all_entries)}")

    logger.info("\n--- Filtering and reducing ---")

    ts_log.log("system", "FILTER", "chatbot_a", "Filtering by agent")
    agent_a_entries = agent_a.read_by_agent("chatbot_a")
    ts_log.log("system", "FILTER_COMPLETE", "chatbot_a", f"Found {len(agent_a_entries)} entries")

    def conversation_stats_reducer(acc: dict[str, Any], entry: MemoryEntry) -> dict[str, Any]:
        if "message_count" not in acc:
            acc["message_count"] = 0
            acc["agents"] = set()
            acc["by_type"] = {}

        acc["message_count"] += 1
        if entry.agent_id:
            acc["agents"].add(entry.agent_id)
        acc["by_type"][entry.type.value] = acc["by_type"].get(entry.type.value, 0) + 1
        return acc

    ts_log.log("system", "REDUCE_CUSTOM", "all_sessions", "Applying custom reducer")
    stats = agent_a.reduce(conversation_stats_reducer)
    ts_log.log(
        "system",
        "REDUCE_RESULT",
        "all_sessions",
        f"Messages: {stats['message_count']}, Agents: {len(stats.get('agents', set()))}",
    )

    logger.info("\n--- SessionMemory with context manager ---")

    ts_log.log("session_agent", "SESSION_START", "session_003", "Opening session")
    with SessionMemory(memory_dir, "session_agent", "session_003") as session:
        ts_log.log("session_agent", "APPEND", "session_003", "Starting analysis task...")
        session.append(MemoryEntryType.THOUGHT, "Starting analysis task...")

        ts_log.log("session_agent", "APPEND", "session_003", "Fetching data from API")
        session.append(MemoryEntryType.ACTION, "Fetching data from API")

        ts_log.log("session_agent", "APPEND", "session_003", "Received 100 records")
        session.append(MemoryEntryType.OBSERVATION, "Received 100 records")

        ts_log.log("session_agent", "APPEND", "session_003", "Analysis complete")
        session.append(MemoryEntryType.ACTION, "Analysis complete")

    ts_log.log("session_agent", "SESSION_END", "session_003", "Session closed, auto-flushed")

    logger.info("\n--- Compaction ---")

    for i in range(5):
        temp_agent = ImmutableMemory(memory_dir, f"temp_agent_{i}", f"temp_session_{i}")
        temp_agent.append(MemoryEntryType.OBSERVATION, f"Temporary entry {i}")
        temp_agent.flush()
        ts_log.log(f"temp_agent_{i}", "FLUSH", f"temp_session_{i}", "Created temp file")

    pre_stats = agent_a.get_stats()
    ts_log.log("system", "STATS", "all_files", f"Before compaction: {pre_stats['total_files']} files")

    ts_log.log("system", "COMPACT_START", "all_files", "Starting compaction")
    result = agent_a.compact(keep_recent_files=3, min_files_for_compaction=5)
    if result:
        ts_log.log(
            "system",
            "COMPACT_COMPLETE",
            "all_files",
            f"Compacted {len(result.source_files)} files -> 1 file",
        )

    post_stats = agent_a.get_stats()
    ts_log.log("system", "STATS", "all_files", f"After compaction: {post_stats['total_files']} files")

    logger.info("Immutable memory example completed!")
    return ts_log
