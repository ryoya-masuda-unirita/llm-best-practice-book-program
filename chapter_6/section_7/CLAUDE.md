# Chapter 6 Section 7: Shared Memory Update Strategies for Multi-Agent Systems

## What This Section Demonstrates

When multiple agents share memory (files, records, scratchpads), race conditions are *more* likely than in ordinary web apps — an agent holds its "transaction" open for seconds to tens of seconds of LLM inference. This section implements and compares **four update strategies** over file-based shared memory, coordinated by a pluggable `LockManager`:

- **Conservative (pessimistic) lock** — acquire before read, hold through write. Safest; longest blocking.
- **Optimistic lock** — read freely, validate a version number at write; conflict → retry with fresh data. Best throughput when conflicts are rare (< ~20%), but a conflict wastes an entire LLM inference.
- **Preemptible lock** — priority-based: a higher-priority agent (e.g. emergency handler) can preempt a held lock; the preempted agent gets `PreemptedError` and must re-run.
- **Immutable (append-only) memory** — no locks at all: agents append `MemoryEntry`s; state is derived by folding entries (reducers). Concurrency-safe by construction.

Runnable examples race concurrent agents under each strategy and record a `TimeSeriesLog` so you can see who blocked, who conflicted, and who was preempted. Apply this whenever ≥2 agents (or an agent + human tooling) write the same state.

## Practice Rules

1. **Pick the strategy from your conflict profile, not habit**: rare conflicts → optimistic; frequent conflicts on hot resources → conservative; emergency overrides needed → preemptible; audit/history requirements or high fan-in → immutable/append-only.
2. **Externalize locking behind an abstract `LockManager`** (`acquire/release/version` API; `LocalDictLockManager` in-process here, Redis/DB in production) — strategies must not own lock storage.
3. **Version every mutable document** (`MemoryDocument.version`); optimistic writes compare-and-swap on it and raise `VersionMismatchError` on drift.
4. **Type the failure modes**: `LockAcquisitionError`, `LockNotHeldError`, `VersionMismatchError`, `OptimisticLockConflictError`, `PreemptedError` — each demands a different reaction (wait, retry, re-run, escalate).
5. **Bound optimistic retries** (`max_retries=3`) — each retry re-pays LLM inference; escalate to a pessimistic lock rather than retrying forever.
6. **For preemption, make the preempted side safe**: the resource version increments on preemption so the loser's stale work cannot commit; the loser must catch `PreemptedError` and restart from fresh state.
7. **Prefer append-only when semantics allow**: conflict-free writes, full history, state = `reduce(entries)` — the cost is read-time folding and eventual compaction.

## Architecture

```
Agent A (priority 50)   Agent B (priority 50)   Agent C (priority 100)
        └──────────────┬────────────────────────────┘
                       ▼
        Memory strategy (choose one per resource)
        ├─ ConservativeLockMemory   acquire → read → write → release (LockHandle)
        ├─ OptimisticLockMemory     read (no lock) → write iff version unchanged → retry
        ├─ PreemptibleLockMemory    acquire(priority) → may be preempted by higher priority
        └─ ImmutableMemory          append MemoryEntry → state = reduce(entries)
                       ▼
        LockManager (ABC) — LocalDictLockManager (demo) / Redis-DB (production)
                       ▼
        memory/<resource_id>.json   (+ TimeSeriesLog of the race for analysis)
```

### Directory Structure

```
chapter_6/section_7/
├── src/
│   ├── agent/
│   │   ├── core/                       # agent framework core (as in Chapter 4 Section 8)
│   │   └── extensions/memory/
│   │       ├── lock_manager.py         # LockManager ABC + LocalDictLockManager + error types
│   │       ├── conservative_lock.py    # ConservativeLockMemory + LockHandle
│   │       ├── optimistic_lock.py      # OptimisticLockMemory + OptimisticTransaction
│   │       ├── preemptible_lock.py     # PreemptibleLockMemory + PreemptedError
│   │       ├── immutable_memory.py     # ImmutableMemory + SessionMemory (append-only)
│   │       └── models.py               # MemoryDocument / MemoryEntry / TimeSeriesLog
│   ├── examples.py                     # examples 1–4: concurrent agents per strategy
│   ├── main.py                         # CLI: --agent <example>
│   └── client/ config.py / logger.py
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. The lock abstraction (`src/agent/extensions/memory/lock_manager.py`)

```python
class LockManager(ABC):
    # acquire(resource_id, agent_id, ...) / release / get_version / increment_version
class LocalDictLockManager(LockManager):
    # in-process dict implementation — swap for Redis/DB in production
class LockAcquisitionError(Exception): ...
class VersionMismatchError(Exception): ...
```

### 2. Optimistic compare-and-swap (`src/agent/extensions/memory/optimistic_lock.py`)

```python
class OptimisticLockMemory:
    """Reads without locking; validates version at write time.
    Best when conflict rate < 20% — a conflict wastes an LLM inference."""
    def __init__(self, memory_dir, agent_id, lock_manager=None, max_retries: int = 3): ...
    # write: load fresh → apply change → commit iff version unchanged → else retry
```

### 3. Priority preemption (`src/agent/extensions/memory/preemptible_lock.py`)

```python
class PreemptibleLockMemory:
    def acquire_lock(self, resource_id, priority, ...):
        # higher priority may preempt a held lock; loser raises PreemptedError
    # version incremented on preemption → stale work cannot commit
```

### 4. Lock-free append-only memory (`src/agent/extensions/memory/immutable_memory.py`)

```python
class ImmutableMemory:
    # append(entry) — concurrency-safe; version = len(entries)
    # state via reducers, e.g.:
def conversation_stats_reducer(acc: dict, entry: MemoryEntry) -> dict: ...
```

## Data Models

| Model | Purpose |
|-------|---------|
| `MemoryDocument` | Versioned mutable document (lock strategies) |
| `MemoryEntry` | Append-only record (immutable strategy) |
| `LockHandle` / `OptimisticTransaction` | Strategy-specific write scopes |
| `TimeSeriesLog` | Recorded race timeline (who read/wrote/blocked/conflicted when) |

## Setup & Run

```bash
cp .envrc.example .envrc     # set GEMINI_API_KEY
uv sync

# Canonical example
uv run python -m src.main --agent example_1_agent_with_conservative_lock

# The strategy comparison
uv run python -m src.main --agent example_2_with_optimistic_lock
uv run python -m src.main --agent example_3_with_preemptive_lock
uv run python -m src.main --agent example_4_with_immutable_memory
```

Each example races concurrent writers and prints the `TimeSeriesLog` table (agent / operation / resource / outcome).

### CLI Options

| Option | Description |
|--------|-------------|
| `--agent` | Example to run (1–4, above) |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
```

## Implementation Notes

- **LLM latency changes the trade-off math**: in classic systems, optimistic locking wins because transactions are milliseconds. With seconds-long "transactions" (inference), conflicts are both more likely and far more expensive to retry — pessimistic and append-only strategies deserve more weight than web-app intuition suggests.
- **Preemption models real multi-agent priorities** (an emergency responder shouldn't queue behind a batch summarizer), but it pushes complexity to the preempted side — every preemptible agent needs restart-from-fresh logic.
- **Immutable memory is the quiet winner** where semantics fit: no locks, natural audit trail, and reducers reconstruct any view. Costs: growing storage (compaction needed eventually) and read-time computation.
- **`TimeSeriesLog` output is the pedagogical core** — run examples 1 and 2 back-to-back and compare blocking time vs wasted-conflict work under the same workload.
- **The demo's `LocalDictLockManager` is single-process**: multi-process/multi-host deployments need Redis (`SET NX PX` + version keys) or a DB row lock behind the same ABC.

## How to Apply This Practice to Your Own Project

1. Inventory shared resources your agents write; estimate conflict rates per resource (log first, guess second).
2. Put a `LockManager` ABC in front of your lock store from day one; start with the local implementation, swap in Redis/DB unchanged.
3. Default mapping: append-only for logs/dialogue/metrics; optimistic for rarely-contended documents; conservative for hot documents; preemptible only where priorities genuinely differ.
4. Version all mutable documents and type your failure modes; each error class gets a distinct recovery path.
5. Cap optimistic retries and escalate to pessimistic on repeated conflict — don't burn inference on retry storms.
6. Record a per-run operation timeline (your `TimeSeriesLog`) in staging; choose strategies from observed contention, then re-verify after topology changes.
