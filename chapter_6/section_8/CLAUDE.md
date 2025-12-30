# AI Agent Memory Update Strategies

## Overview

This project implements four memory update strategies for multi-agent AI systems where agents share file-based memory. Since LLM inference takes seconds to tens of seconds, race conditions are more likely than in traditional web applications. This implementation provides exclusive control using an external "Lock Manager" and an append-only data structure approach.

## Architecture

```
+-------------------------------------------------------------------------+
|                          AI Agent System                                |
+-------------------------------------------------------------------------+
|                                                                         |
|  +---------------+  +---------------+  +---------------+                |
|  |   Agent A     |  |   Agent B     |  |   Agent C     |                |
|  | (priority=50) |  | (priority=50) |  | (priority=100)|                |
|  +-------+-------+  +-------+-------+  +-------+-------+                |
|          |                  |                  |                        |
|          +--------+---------+------------------+                        |
|                   |                                                     |
|                   v                                                     |
|         +------------------------+                                      |
|         |    Memory Strategy     |                                      |
|         +------------------------+                                      |
|         | +--------------------+ |                                      |
|         | | Conservative Lock  | |  Safest, long blocking               |
|         | +--------------------+ |                                      |
|         | +--------------------+ |                                      |
|         | | Optimistic Lock    | |  High concurrency, retry on conflict |
|         | +--------------------+ |                                      |
|         | +--------------------+ |                                      |
|         | | Preemptible Lock   | |  Priority-based, emergency handling  |
|         | +--------------------+ |                                      |
|         | +--------------------+ |                                      |
|         | | Immutable Memory   | |  Append-only, no locks needed        |
|         | +--------------------+ |                                      |
|         +-----------+------------+                                      |
|                     |                                                   |
|                     v                                                   |
|         +------------------------+                                      |
|         |    Lock Manager        |                                      |
|         |   (LocalDict/Redis)    |                                      |
|         +-----------+------------+                                      |
|                     |                                                   |
|                     v                                                   |
|         +------------------------+                                      |
|         |   File System / JSON   |                                      |
|         |      (memory/*.json)   |                                      |
|         +------------------------+                                      |
|                                                                         |
+-------------------------------------------------------------------------+
```

### Directory Structure

```
chapter_6/section_8/
|-- src/
|   |-- __init__.py
|   |-- main.py                    # CLI entry point (Click-based)
|   |-- examples.py                # Demo implementations for each strategy
|   |-- config.py                  # Configuration management (Pydantic)
|   |-- logger.py                  # Logging setup
|   |-- client/
|   |   +-- llm_client.py          # LLM client abstraction
|   +-- agent/
|       |-- core/                  # Agent core functionality
|       |   |-- agent.py           # Base agent implementation
|       |   |-- base.py            # Abstract base classes
|       |   |-- controller.py      # Agent controller
|       |   |-- mediator.py        # Agent mediator pattern
|       |   |-- memory.py          # Core memory interface
|       |   |-- states.py          # Agent states
|       |   +-- toolbox.py         # Tool management
|       +-- extensions/
|           |-- factory.py         # Agent factory
|           |-- memory/            # Memory strategy implementations
|           |   |-- models.py              # Data models (Pydantic)
|           |   |-- lock_manager.py        # Lock management abstraction
|           |   |-- conservative_lock.py   # Pessimistic locking
|           |   |-- optimistic_lock.py     # Version-based locking
|           |   |-- preemptible_lock.py    # Priority-based locking
|           |   +-- immutable_memory.py    # Append-only memory
|           |-- handlers/          # Safety handlers
|           |-- mediators/         # Mediator implementations
|           |-- nodes/             # Graph nodes for agents
|           |-- strategies/        # Reasoning strategies (ReAct, CoT, ToT)
|           +-- tools/             # Tool implementations
|-- memory/                        # Runtime-generated memory files
|-- pyproject.toml                 # Project configuration (uv)
|-- Makefile                       # Development commands
+-- README.md                      # Japanese documentation
```

## Key Components

### Memory Strategies

| Strategy | Class | Use Case |
|----------|-------|----------|
| Conservative Lock | `ConservativeLockMemory` | Multi-file transactions, critical data |
| Optimistic Lock | `OptimisticLockMemory` | High-throughput, low conflict rate (<20%) |
| Preemptible Lock | `PreemptibleLockMemory` | Emergency response, SLA requirements |
| Immutable Memory | `ImmutableMemory`, `SessionMemory` | Chat logs, audit trails, event sourcing |

### Lock Manager

- `LockManager` (ABC): Abstract interface for lock management
- `LocalDictLockManager`: In-memory implementation for testing/single-process
- Supports TTL-based auto-release, version tracking, shadow copies for preemption

### Data Models

- `MemoryDocument`: Container for memory entries with metadata
- `MemoryEntry`: Individual memory entry with type, content, agent_id
- `MemoryEntryType`: OBSERVATION, THOUGHT, ACTION
- `LockInfo`: Lock metadata including holder, priority, expiration
- `ShadowCopy`: Preserved data when lock is preempted

## Dependencies

| Package | Purpose |
|---------|---------|
| anthropic | Anthropic Claude API client |
| google-genai | Google Gemini API client |
| openai | OpenAI API client |
| click | CLI framework |
| pydantic | Data validation and settings |
| polars | Data processing |
| python-dotenv | Environment variable loading |

## Usage

### Setup

```bash
# Copy environment template
cp .envrc.example .envrc

# Edit .envrc and set API keys
export GEMINI_API_KEY="your-gemini-api-key-here"

# Install dependencies
uv sync
```

### Run

```bash
# Show CLI help
python -m src.main --help

# Run specific strategy demo
python -m src.main --agent example_1_agent_with_conservative_lock
python -m src.main --agent example_2_with_optimistic_lock
python -m src.main --agent example_3_with_preemptive_lock
python -m src.main --agent example_4_with_immutable_memory

# Run all strategies
python -m src.main --agent all

# Specify custom memory directory
python -m src.main --agent all --memory-directory ./custom_memory
```

### CLI Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--agent` | `-a` | Choice | Required | Agent workflow to run |
| `--memory-directory` | `-md` | Path | `memory` | Directory for memory files |

## Development Commands

```bash
# Lint code with ruff
make lint

# Format code with ruff
make fmt

# Run both lint and format
make fix

# Type check with mypy
make mypy
```

## Implementation Notes

### Strategy Selection Guide

| Criteria | Conservative | Optimistic | Preemptible | Immutable |
|----------|-------------|------------|-------------|-----------|
| Data Integrity | High | Medium | Medium | High |
| Throughput | Low | High | Medium | High |
| Complexity | Low | Medium | High | Medium |

### Deadlock Prevention

- `acquire_multiple_locks()` acquires locks in sorted order
- TTL-based auto-release prevents indefinite blocking

### Conflict Handling

- Optimistic lock: Re-read and retry on `OptimisticLockConflictError`
- Preemptible lock: Shadow copies preserve preempted data for reconciliation

### Performance Considerations

- Conservative lock: Other agents blocked during LLM inference (seconds)
- Optimistic lock: Retry costs (tokens, time) increase with conflict rate
- Immutable memory: Run compaction periodically to prevent file proliferation
