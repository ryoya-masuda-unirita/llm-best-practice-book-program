# Chapter 3 Section 7: Priority-based Request Handling

## Overview

Production-ready implementation of priority-based request handling for LLM applications. Manages requests with varying business importance through a multi-tier queue system backed by Redis, ensuring fair resource allocation while maintaining service quality guarantees for premium users.

## Architecture

```
+-------------+     +---------------+     +------------------+
|   Client    | --> |  FastAPI API  | --> | Redis Priority   |
| (REST API)  |     |  (Producer)   |     | Queues (3 tiers) |
+-------------+     +---------------+     +------------------+
                                                    |
                                                    v
                                          +------------------+
                                          | Background Worker|
                                          | (Weighted Sched) |
                                          +------------------+
                                                    |
                                                    v
                                          +------------------+
                                          |   OpenAI API     |
                                          +------------------+
```

**Priority Mapping:**
- ENTERPRISE -> HIGH (70% processing capacity)
- PREMIUM -> MEDIUM (20% processing capacity)
- FREE -> LOW (10% processing capacity)

### Directory Structure

```
src/
  api/
    llm_server.py    # FastAPI endpoints for queue operations
  client/
    llm_client.py    # LLM provider client definitions
  model/
    model.py         # Pydantic models (Priority, UserTier, QueuedTask, etc.)
  prompt/
    prompt.py        # Prompt generation utilities
  service/
    queue_manager.py # Redis-based priority queue management
    worker.py        # Background worker with weighted scheduling
    request_llm.py   # LLM API request handlers
  config.py          # Configuration with environment variables
  logger.py          # Structured logging setup
```

## Key Components

| Component | File | Purpose |
|-----------|------|---------|
| PriorityQueueManager | `queue_manager.py` | Redis Sorted Set-based priority queues |
| WeightedPriorityScheduler | `worker.py` | Weighted random selection to prevent starvation |
| PriorityWorker | `worker.py` | Task processing loop with retry logic |
| QueuedTask | `model.py` | Task lifecycle model with state tracking |

## Dependencies

- **fastapi**: REST API framework
- **redis**: Priority queue storage using Sorted Sets
- **openai**: LLM provider for character generation
- **pydantic**: Data validation and configuration
- **uvicorn**: ASGI server

## Usage

### Setup

```bash
# Copy environment file and add API keys
cp .envrc.example .envrc
# Set OPENAI_API_KEY in .envrc
```

### Run with Docker

```bash
# Start all services (Redis, API server, Worker)
make docker-up

# View logs
make docker-logs

# Stop services
make docker-down
```

### Run Locally

```bash
# Terminal 1: Start Redis
docker run -p 6379:6379 redis:8-alpine

# Terminal 2: Start API server
uvicorn src.api.llm_server:app --host 0.0.0.0 --port 8000

# Terminal 3: Start worker
python -m src.service.worker
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/generate/queue` | Queue task with priority based on user_tier |
| GET | `/task/{task_id}` | Get task status and result |
| GET | `/queue/stats` | Get queue statistics |
| POST | `/generate` | Synchronous generation (bypass queue) |
| GET | `/health` | Health check |

### Example Request

```bash
# Submit a task (enterprise user = high priority)
curl -X POST http://localhost:8000/generate/queue \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-5.4-mini",
    "character_request": {
      "gender": "female",
      "age": 25,
      "additional_instructions": "A brave warrior"
    },
    "user_tier": "enterprise"
  }'

# Check task status
curl http://localhost:8000/task/{task_id}

# View queue statistics
curl http://localhost:8000/queue/stats
```

## Development Commands

| Command | Description |
|---------|-------------|
| `make lint` | Run ruff linter with auto-fix |
| `make fmt` | Format code with ruff |
| `make fix` | Run lint and format |
| `make mypy` | Type check with mypy |
| `make docker-build` | Build Docker image |
| `make docker-up` | Start Docker Compose services |
| `make docker-down` | Stop Docker Compose services |
| `make docker-logs` | View all service logs |
| `make docker-logs-server` | View API server logs |
| `make docker-logs-worker` | View worker logs |

## Implementation Notes

### Redis Data Structures

- **Priority Queues**: Sorted Sets (`llm:queue:high`, `llm:queue:medium`, `llm:queue:low`)
  - Score = Unix timestamp for FIFO within priority
- **Task Storage**: Key-Value (`llm:task:{task_id}`)
- **Processing Set**: Set (`llm:processing`) for crash recovery

### Weighted Scheduling Algorithm

Uses `random.choices()` with weights [0.7, 0.2, 0.1] to select which priority queue to process. This ensures:
- HIGH priority gets ~70% of processing capacity
- LOW priority still gets ~10% (prevents starvation)
- Long-term convergence to configured ratios

### Task State Transitions

```
PENDING -> PROCESSING -> COMPLETED
                     -> FAILED (after max_retry_attempts)
                     -> PENDING (retry on transient error)
```

### Configuration (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (required) | OpenAI API key |
| `REDIS_HOST` | localhost | Redis server host |
| `REDIS_PORT` | 6379 | Redis server port |
| `REDIS_DB` | 0 | Redis database number |

### Priority Ratios (config.py)

| Priority | Default Ratio | Description |
|----------|---------------|-------------|
| HIGH | 0.7 | Enterprise users |
| MEDIUM | 0.2 | Premium users |
| LOW | 0.1 | Free users |
