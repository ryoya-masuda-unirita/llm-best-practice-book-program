# Chapter 2 Section 5: Asynchronous Batch Processing for LLM Applications

## What This Section Demonstrates

This section shows how to run **large, non-latency-sensitive LLM workloads through provider Batch APIs** behind your own asynchronous job service. Instead of firing N synchronous requests, a client submits a job (up to 100 items) and immediately receives a `job_id`; a background worker forwards the job to the provider's batch endpoint (Gemini Batch API / OpenAI Batch API), polls for completion, and stores results in Redis for later retrieval.

Apply this practice for bulk generation/classification/ETL workloads where throughput and cost matter more than latency: provider batch endpoints are ~50% cheaper, and the submit/poll/result HTTP surface decouples your callers from provider processing times (minutes to hours).

## Practice Rules

1. **Accept work asynchronously**: `POST /batch/submit` validates, enqueues to Redis, and returns `job_id` + `PENDING` immediately. Never hold an HTTP connection open for batch work.
2. **Separate API server from worker process.** The server only manipulates the queue and status/result records; the worker owns all provider interaction. They share only Redis.
3. **Run the worker as two concurrent loops**: a pickup loop (blocking dequeue → submit to provider batch API) and a polling loop (check all active provider jobs on an interval, `asyncio.gather` for concurrency).
4. **Track job state machine explicitly** (`JobStatus`: `PENDING → PROCESSING → COMPLETED | FAILED`) and store per-task outcomes (`TaskStatus`) so partial failures are visible, not swallowed.
5. **Give every Redis record a TTL** (24h default) — batch results are transient handoffs, not a database.
6. **Wrap provider batch APIs in three thin functions per provider**: `submit_*_batch`, `get_*_batch_status`, `get_*_batch_results`. Keep provider-specific status strings (e.g. `JOB_STATE_SUCCEEDED`) inside the wrapper.
7. **Expose observability endpoints** (`/batch/queue/stats`, `/batch/jobs`) from day one — queue depth is your primary operational signal.

## Architecture

```
Client ──POST /batch/submit──▶ Batch Server (FastAPI :8001)
   ◀── job_id (immediate)         │ rpush queue / status=PENDING
                                  ▼
                               Redis (:6379)
                                  ▲ blpop
                                  │
                      Batch Worker (no ports)
                      ├─ _job_pickup_loop:    dequeue → submit_gemini_batch()
                      └─ _poll_active_jobs_loop: every 5s → get_*_batch_status()
                                  │ on complete: parse results, set status/result
                                  ▼
Client ──GET /batch/{job_id}/status | /result──▶ Batch Server → Redis
```

`llm-server` (:8000) is a plain synchronous `/generate` endpoint for contrast with the batch path.

### Directory Structure

```
chapter_2/section_5/
├── src/
│   ├── api/
│   │   ├── batch_server.py    # submit/status/result/stats/jobs endpoints
│   │   └── llm_server.py      # synchronous /generate (comparison baseline)
│   ├── worker/batch_worker.py # BatchWorker: pickup + polling loops
│   ├── client/
│   │   ├── redis_client.py    # async Redis wrapper (queue + status/result records)
│   │   └── llm_client.py      # provider clients + model enums
│   ├── model/batch_model.py   # job/task request-response models
│   ├── model/model.py         # CharacterResponse (task output schema)
│   ├── prompt/prompt.py
│   ├── service/request_llm.py # submit/get-status/get-results per provider batch API
│   └── config.py / logger.py
├── docker-compose.yml         # redis / llm-server:8000 / batch-server:8001 / batch-worker
├── Dockerfile
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Submit returns immediately (`src/api/batch_server.py`)

```python
@app.post("/batch/submit", response_model=BatchJobResponse, tags=["Batch"])
# validate BatchJobRequest (1-100 character_requests)
# job_id = uuid; enqueue InternalJobData; set status PENDING
# return BatchJobResponse(job_id=..., status=PENDING, total_tasks=...)
```

### 2. Worker with two cooperating loops (`src/worker/batch_worker.py`)

```python
class BatchWorker:
    async def start(self):
        await asyncio.gather(self._job_pickup_loop(), self._poll_active_jobs_loop())

    async def _job_pickup_loop(self):
        # blpop(queue, timeout=1) → _submit_job → active_jobs[job_id] = ActiveJob(...)

    async def _poll_active_jobs_loop(self):
        # every 5s: asyncio.gather(*[self._check_job_status(j) for j in active_jobs])
```

Pickup latency and provider polling are independent concerns; two loops keep both responsive.

### 3. Provider batch wrappers (`src/service/request_llm.py`)

```python
def submit_gemini_batch(model, prompts) -> str:
    inline_batch_job = google_genai_client.batches.create(...)   # returns job name

def get_gemini_batch_status(batch_job_name: str) -> str:
    return google_genai_client.batches.get(name=batch_job_name).state.name

def get_gemini_batch_results(batch_job_name: str) -> list[CharacterResponse | None]:
    # parse response.candidates[0].content.parts[0].text per task → CharacterResponse
```

The OpenAI equivalents (`submit_openai_batch` builds a JSONL file for `openai_client.batches.create`) live in the same module — same three-function shape.

### 4. Redis as the only shared state (`src/client/redis_client.py`)

```python
@ensure_connected
async def enqueue_job(self, queue_name, job_data): await self.redis.rpush(queue_name, job_json)
async def dequeue_job(self, queue_name, timeout=0): await self.redis.blpop(queue_name, timeout=timeout)
async def set_job_status(self, job_id, status_data, ttl=DEFAULT_TTL): ...   # key: batch:status:<job_id>
async def set_job_result(self, job_id, result_data, ttl=DEFAULT_TTL): ...  # key: batch:result:<job_id>
```

## Data Models

| Model | Purpose |
|-------|---------|
| `JobStatus` | `PENDING` / `PROCESSING` / `COMPLETED` / `FAILED` |
| `BatchJobRequest` | Input: provider, model, `character_requests` (1–100) |
| `BatchJobResponse` | Immediate ack: `job_id`, status, `total_tasks` |
| `BatchJobStatusResponse` | Progress: completed / failed / pending task counts |
| `BatchJobResultResponse` / `TaskStatus` | Final per-task outcomes |
| `InternalJobData` | Queue payload incl. `submitted_at` |

## Setup & Run

```bash
cp .envrc.example .envrc     # GEMINI_API_KEY (and OPENAI_API_KEY for OpenAI batches)

# Docker (canonical)
make docker-build && make docker-up
curl -s http://localhost:8001/batch/queue/stats     # → {"queue_name":"llm_batch_jobs","pending_jobs":0}
make docker-down

# Submit → poll → fetch
curl -X POST http://localhost:8001/batch/submit -H "Content-Type: application/json" \
  -d '{"llm_provider": "gemini", "model": "gemini-2.5-flash",
       "character_requests": [{"gender": "female", "age": 25}]}'
curl http://localhost:8001/batch/<job_id>/status
curl http://localhost:8001/batch/<job_id>/result
```

Local (three terminals): `redis-server` / `uv run uvicorn src.api.batch_server:app --port 8001` / `uv run python -m src.worker.batch_worker`.

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
make docker-build / make docker-up / make docker-down
```

## Implementation Notes

- **Provider Batch APIs are half price** but completion is minutes-to-hours; the job service absorbs that variance so callers never block.
- **Graceful shutdown**: the worker traps SIGINT/SIGTERM (`signal_handler` → `worker.stop()`) and drains in-flight polling before exit.
- **Partial failure model**: a job completes even when individual tasks fail — `TaskStatus` records per-task success/error, and counts surface in the status endpoint. Don't fail whole jobs for one bad item.
- **In-memory `active_jobs` is a single-worker simplification**: if the worker restarts, submitted-but-unfinished provider jobs are orphaned. For production, persist the provider job name in Redis at submit time and rebuild `active_jobs` on startup.
- **Redis key patterns**: queue `llm_batch_jobs`, status `batch:status:<job_id>`, result `batch:result:<job_id>`, all with 24h TTL.

## How to Apply This Practice to Your Own Project

1. Start from the three-process topology: stateless API server, stateless worker, Redis (or your queue of choice) in between.
2. Define the job state machine and per-task result model first; every endpoint and worker transition maps to it.
3. Wrap each provider's batch API in the submit/status/results triple; normalize provider states to your `JobStatus` inside the wrapper.
4. Enforce job-size limits at the API boundary (here 1–100 tasks) to match provider constraints and keep polling cheap.
5. Add `queue/stats` and job-listing endpoints before you need them — they're your ops dashboard.
6. Decide result retention (TTL) and idempotency (client-supplied job keys) before production traffic.
