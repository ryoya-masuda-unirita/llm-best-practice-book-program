# Chapter 3 Section 6: Asynchronous Batch Processing for LLM Applications

## Overview

This project demonstrates a production-ready implementation of **asynchronous batch processing** for LLM applications. It showcases how to efficiently handle large-scale LLM tasks by decoupling request submission from processing, using Redis as a message queue and background workers for parallel execution.

### Purpose

The primary goal is to illustrate best practices for building scalable, fault-tolerant LLM systems that can:
- Handle bulk processing requests without blocking the API
- Scale horizontally by adding more workers
- Provide real-time progress tracking
- Gracefully handle failures at the task level
- Optimize resource utilization and cost efficiency

### Use Case

This implementation focuses on fictional character generation as a representative batch processing use case. Users can submit requests to generate multiple characters with specific attributes (gender, age, personality traits), and the system processes them asynchronously via Gemini Batch API.

## Architecture

### System Components

```
+------------------+
|     Clients      |
+--------+---------+
         |
         +------------------+----------------------+
         |                  |                      |
+--------v--------+  +------v-------+  +-----------v----------+
|   LLM Server    |  | Batch Server |  |    Batch Worker      |
|   (Port 8000)   |  | (Port 8001)  |  |    (Background)      |
|                 |  |              |  |                      |
| POST /generate  |  | POST /submit |  | - Job Pickup Loop    |
|                 |  | GET /status  |  | - Polling Loop       |
|                 |  | GET /result  |  | - Gemini Batch API   |
+--------+--------+  +------+-------+  +-----------+----------+
         |                  |                      |
         +------------------+----------------------+
                            |
                     +------v------+
                     |    Redis    |
                     | (Port 6379) |
                     |             |
                     | - Job Queue |
                     | - Status    |
                     | - Results   |
                     +-------------+
```

### Directory Structure

```
chapter_3/section_5/
|-- src/
|   |-- api/
|   |   |-- batch_server.py     # Batch job management API (port 8001)
|   |   +-- llm_server.py       # Synchronous LLM API (port 8000)
|   |-- worker/
|   |   +-- batch_worker.py     # Background worker with concurrent polling
|   |-- client/
|   |   |-- llm_client.py       # Gemini client initialization
|   |   +-- redis_client.py     # Async Redis wrapper with decorators
|   |-- model/
|   |   |-- model.py            # Character request/response models
|   |   +-- batch_model.py      # Batch job models (status, result)
|   |-- service/
|   |   +-- request_llm.py      # Gemini Batch API functions
|   |-- prompt/
|   |   +-- prompt.py           # Prompt generation with schema embedding
|   |-- config.py               # Pydantic config with Secret types
|   +-- logger.py               # Logging configuration
|-- docker-compose.yml
|-- Dockerfile
|-- Makefile
|-- pyproject.toml
+-- .env.example
```

## Key Components

### Batch Server (`src/api/batch_server.py`)

FastAPI server for batch job management:
- `POST /batch/submit` - Submit batch job, returns job_id immediately
- `GET /batch/{job_id}/status` - Poll job progress
- `GET /batch/{job_id}/result` - Get completed results
- `GET /batch/queue/stats` - View queue statistics
- `GET /batch/jobs` - List all job IDs

Uses helper functions `raise_not_found()` and `raise_internal_error()` for consistent error handling, and Pydantic response models (`QueueStatsResponse`, `JobListResponse`).

### Batch Worker (`src/worker/batch_worker.py`)

Background processor with two concurrent async loops:

1. **Job Pickup Loop** (`_job_pickup_loop`):
   - Dequeues jobs from Redis using BLPOP (1s timeout)
   - Immediately submits to Gemini Batch API
   - Tracks active jobs in `active_jobs` dict

2. **Polling Loop** (`_poll_active_jobs_loop`):
   - Polls all active Gemini batch jobs every 5 seconds
   - Uses `asyncio.gather()` for concurrent status checks
   - Processes results when jobs complete

Helper functions:
- `build_status_response()` - Constructs BatchJobStatusResponse
- `build_task_results()` - Converts batch results to TaskStatus list
- `prepare_prompts()` - Prepares prompts from character requests

### Redis Client (`src/client/redis_client.py`)

Async wrapper around redis-py with:
- `@ensure_connected` decorator for automatic connection
- `_status_key()` / `_result_key()` static methods for key generation
- `DEFAULT_TTL = 86400` (24 hours) for automatic cleanup
- Methods: `enqueue_job`, `dequeue_job`, `set_job_status`, `get_job_status`, `set_job_result`, `get_job_result`, `get_queue_length`, `list_job_ids`

### Gemini Batch API (`src/service/request_llm.py`)

Three synchronous functions for Gemini Batch API:
- `submit_gemini_batch(model, prompts)` - Creates batch job, returns job name
- `get_gemini_batch_status(batch_job_name)` - Returns state name (JOB_STATE_SUCCEEDED, etc.)
- `get_gemini_batch_results(batch_job_name)` - Parses results into CharacterResponse list

Result parsing handles nested structure: `response.candidates[0].content.parts[0].text`

### Data Models

**JobStatus** enum: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`

**Key models**:
- `BatchJobRequest` - Input: provider, model, character_requests (1-100)
- `BatchJobResponse` - Immediate response: job_id, status, total_tasks
- `BatchJobStatusResponse` - Progress: completed_tasks, failed_tasks, pending_tasks
- `BatchJobResultResponse` - Final: tasks list with TaskStatus entries
- `InternalJobData` - Queue storage: includes submitted_at timestamp

## Dependencies

- `redis>=7.0.0` - Async Redis client
- `fastapi>=0.115.0` - Web framework
- `uvicorn>=0.30.0` - ASGI server
- `pydantic>=2.10.0` - Data validation
- `google-genai>=1.0.0` - Gemini API client

## Usage

### Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API key
# GEMINI_API_KEY=<your_key>

# Install dependencies
uv sync
```

### Run with Docker

```bash
make docker-build    # Build image
make docker-up       # Start all services
make docker-logs     # View logs
make docker-down     # Stop services
```

### Run Locally

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Batch Server
uvicorn src.api.batch_server:app --host 0.0.0.0 --port 8001

# Terminal 3: Worker
python -m src.worker.batch_worker
```

### API Examples

```bash
# Submit batch job
curl -X POST http://localhost:8001/batch/submit \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "character_requests": [
      {"gender": "female", "age": 25, "additional_instructions": "cheerful"},
      {"gender": "male", "age": 30, "additional_instructions": "intellectual"}
    ]
  }'

# Check status
curl http://localhost:8001/batch/{job_id}/status

# Get results
curl http://localhost:8001/batch/{job_id}/result

# List all jobs
curl http://localhost:8001/batch/jobs

# Queue stats
curl http://localhost:8001/batch/queue/stats
```

## Development Commands

| Command | Description |
|---------|-------------|
| `make lint` | Run ruff linter with auto-fix |
| `make fmt` | Format code with ruff |
| `make fix` | Run lint + fmt |
| `make mypy` | Type checking |
| `make docker-build` | Build Docker image |
| `make docker-up` | Start services |
| `make docker-down` | Stop services |
| `make docker-logs` | View logs |
| `make docker-restart` | Restart services |

## Implementation Notes

### Worker Architecture

The worker uses two concurrent loops instead of sequential processing:
1. Jobs are submitted to Gemini immediately upon dequeue
2. Multiple Gemini batch jobs can be in-flight simultaneously
3. All active jobs are polled in parallel every 5 seconds

This design maximizes throughput when processing many concurrent jobs.

### Redis Key Patterns

- Queue: `llm_batch_jobs` (LIST)
- Status: `job:{job_id}:status` (STRING with 24h TTL)
- Result: `job:{job_id}:result` (STRING with 24h TTL)

### Error Handling

- Task-level failures don't affect other tasks
- Job marked FAILED if any task fails
- Worker continues processing after job failures
- Gemini failed states: `JOB_STATE_FAILED`, `JOB_STATE_CANCELLED`, `JOB_STATE_EXPIRED`

### Supported Models

- `gemini-2.5-pro`
- `gemini-2.5-flash`
- `gemini-2.5-flash-lite`
- `gemini-3.5-flash`
- `gemini-3.1-flash-lite`

### Security Notes

This is example code without production security controls:
- No authentication/authorization
- No rate limiting
- API keys in environment variables

For production, add API key auth, JWT, rate limiting, and secrets management.
