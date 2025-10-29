# Chapter 3 Section 6: Asynchronous Batch Processing for LLM Applications

## Project Overview

This project demonstrates a production-ready implementation of **asynchronous batch processing** for LLM applications. It showcases how to efficiently handle large-scale LLM tasks by decoupling request submission from processing, using Redis as a message queue and background workers for parallel execution.

### Purpose

The primary goal is to illustrate best practices for building scalable, fault-tolerant LLM systems that can:
- Handle bulk processing requests without blocking the API
- Scale horizontally by adding more workers
- Provide real-time progress tracking
- Gracefully handle failures at the task level
- Optimize resource utilization and cost efficiency

### Use Case

This implementation focuses on fictional character generation as a representative batch processing use case. Users can submit requests to generate multiple characters with specific attributes (gender, age, personality traits), and the system processes them asynchronously in the background.

## Architecture

### System Components

The architecture follows a microservices pattern with four main components:

```
+---------------+
|   Clients     |
+-------+-------+
        |
        +------------------+---------------------+
        |                  |                     |
+-------v--------+  +------v-------+  +----------v---------+
|  LLM Server    |  | Batch Server |  |   Batch Worker     |
|  (Port 8000)   |  | (Port 8001)  |  |   (Background)     |
+-------+--------+  +------+-------+  +----------+---------+
        |                  |                     |
        +------------------+---------------------+
                           |
                    +------v------+
                    |    Redis    |
                    | (Port 6379) |
                    +-------------+
```

### Component Responsibilities

#### 1. LLM Server (`src/api/llm_server.py`)

**Purpose**: Synchronous API for real-time character generation

**Key Features**:
- FastAPI-based REST API
- Single character generation per request
- Immediate response with generated content
- Health check endpoint

**Endpoints**:
- `GET /health` - Health check
- `POST /generate` - Generate a single character synchronously

**When to Use**: When immediate results are required and latency is critical.

#### 2. Batch Server (`src/api/batch_server.py`)

**Purpose**: Asynchronous API for bulk job submission and management

**Key Features**:
- Job submission with immediate acknowledgment
- Job status tracking
- Result retrieval for completed jobs
- Queue statistics monitoring

**Endpoints**:
- `GET /health` - Health check
- `POST /batch/submit` - Submit a batch job (1-100 tasks)
- `GET /batch/{job_id}/status` - Check job progress
- `GET /batch/{job_id}/result` - Retrieve completed job results
- `GET /batch/queue/stats` - View queue statistics

**Workflow**:
1. Client submits batch request with multiple character specifications
2. Server generates unique job ID
3. Initial job status saved to Redis
4. Job data enqueued to Redis list
5. Immediate response returned to client with job ID
6. Client polls status endpoint to track progress
7. Once complete, client retrieves results

#### 3. Batch Worker (`src/worker/batch_worker.py`)

**Purpose**: Background processor for executing batch jobs

**Key Features**:
- Blocking queue polling with timeout (BLPOP)
- Sequential task processing within each job
- Individual task error handling
- Real-time progress updates
- Graceful shutdown on SIGINT/SIGTERM

**Processing Flow**:
1. Worker polls Redis queue with 5-second timeout
2. When job available, dequeue and parse
3. Update job status to PROCESSING
4. For each task in job:
   - Call LLM API (OpenAI or Gemini)
   - Record success/failure
   - Update job progress in Redis
5. Save final results to Redis
6. Mark job as COMPLETED or FAILED

**Error Handling**:
- Tasks fail independently without affecting other tasks
- Failed tasks recorded with error messages
- Job marked FAILED if any task fails
- Worker continues processing even if job fails

#### 4. Redis

**Purpose**: Message queue and data persistence layer

**Data Structures Used**:

1. **Job Queue** (`llm_batch_jobs`):
   - Type: LIST
   - Operations: RPUSH (enqueue), BLPOP (dequeue)
   - Stores serialized job data

2. **Job Status** (`job:{job_id}:status`):
   - Type: STRING (JSON)
   - TTL: 24 hours
   - Tracks job progress and metadata

3. **Job Results** (`job:{job_id}:result`):
   - Type: STRING (JSON)
   - TTL: 24 hours
   - Stores completed job results

**Persistence**:
- AOF (Append-Only File) enabled for durability
- Data persists across Redis restarts
- Jobs in queue survive worker crashes

## Data Models

### Core Models (`src/model/model.py`)

#### CharacterRequest
```python
class CharacterRequest(BaseModel):
    gender: Gender              # "male" or "female"
    age: int                    # 0-100
    additional_instructions: Optional[str]
```

Request model for specifying character generation parameters.

#### CharacterResponse
```python
class CharacterResponse(BaseModel):
    first_name: str
    last_name: str
    gender: Gender
    age: int
    personalities: list[CharacterPersonality]  # Exactly 3
```

Response model containing generated character information.

#### LLMRequest/LLMResponse
```python
class LLMRequest(BaseModel):
    provider: LLMProvider       # "openai" or "gemini"
    model: str
    character_request: CharacterRequest

class LLMResponse(BaseModel):
    character: CharacterResponse
    provider: str
    model: str
    processing_time_ms: float
```

Models for synchronous API requests and responses.

### Batch Models (`src/model/batch_model.py`)

#### JobStatus
```python
class JobStatus(StrEnum):
    PENDING = "pending"         # Queued, not started
    PROCESSING = "processing"   # Currently being processed
    COMPLETED = "completed"     # All tasks successful
    FAILED = "failed"          # One or more tasks failed
```

#### BatchJobRequest
```python
class BatchJobRequest(BaseModel):
    provider: str                           # LLM provider
    model: str                              # Model name
    character_requests: list[CharacterRequest]  # 1-100 requests
```

Client submits this to create a batch job.

#### BatchJobResponse
```python
class BatchJobResponse(BaseModel):
    job_id: str                 # UUID for tracking
    status: JobStatus           # PENDING initially
    total_tasks: int
    submitted_at: float         # Unix timestamp
```

Immediate response after job submission.

#### TaskStatus
```python
class TaskStatus(BaseModel):
    task_index: int                         # 0-based index
    status: JobStatus                       # Task-level status
    character: Optional[CharacterResponse]  # Result if successful
    error: Optional[str]                   # Error message if failed
    processing_time_ms: Optional[float]
```

Status and result for individual task within a job.

#### BatchJobStatusResponse
```python
class BatchJobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus               # Overall job status
    total_tasks: int
    completed_tasks: int            # Count of completed
    failed_tasks: int               # Count of failed
    pending_tasks: int              # Count of pending
    submitted_at: float
    started_at: Optional[float]
    completed_at: Optional[float]
```

Real-time progress information returned by status endpoint.

#### BatchJobResultResponse
```python
class BatchJobResultResponse(BaseModel):
    job_id: str
    status: JobStatus
    provider: str
    model: str
    tasks: list[TaskStatus]         # All task results
    submitted_at: float
    completed_at: Optional[float]
```

Complete results for a finished job.

#### InternalJobData
```python
class InternalJobData(BaseModel):
    job_id: str
    provider: str
    model: str
    character_requests: list[dict]  # Serialized as dicts for JSON
    submitted_at: float
```

Internal representation stored in Redis queue.

## Implementation Details

### Redis Client (`src/client/redis_client.py`)

**Design Pattern**: Async wrapper around redis-py

**Key Methods**:

```python
async def enqueue_job(queue_name: str, job_data: dict) -> None
```
- Adds job to queue using RPUSH
- Jobs serialized as JSON strings
- Atomic operation ensures consistency

```python
async def dequeue_job(queue_name: str, timeout: int) -> Optional[dict]
```
- Blocks waiting for job using BLPOP
- Returns None if timeout expires
- Automatically deserializes JSON
- Efficient polling without busy-waiting

```python
async def set_job_status(job_id: str, status_data: dict, ttl: int) -> None
```
- Stores job status with SETEX
- TTL ensures automatic cleanup (default 24 hours)
- Key pattern: `job:{job_id}:status`

```python
async def get_job_status(job_id: str) -> Optional[dict]
```
- Retrieves job status with GET
- Returns None if expired or not found

**Connection Management**:
- Singleton pattern with global instance
- Explicit connect/disconnect methods
- FastAPI lifespan events handle connections
- Connection pooling managed by redis-py

### LLM Integration (`src/service/request_llm.py`)

#### OpenAI Integration

```python
async def request_openai(model: str, prompt: list[dict]) -> CharacterResponse:
    result = await openai_client.responses.parse(
        model=model,
        input=prompt,
        text_format=CharacterResponse,
    )
    return result.output_parsed
```

**Features**:
- Uses OpenAI's `responses.parse()` method
- Direct Pydantic model support via `text_format`
- Automatic validation and parsing
- Async/await for non-blocking execution

**Supported Models**:
- gpt-5, gpt-5-mini, gpt-5-nano
- gpt-4.1, gpt-4.1-mini, gpt-4.1-nano
- gpt-4o, gpt-4o-mini

#### Gemini Integration

```python
async def request_gemini(model: str, prompt: list[dict]) -> CharacterResponse:
    result = await google_genai_client.aio.models.generate_content(
        model=model,
        contents=prompt[-1]["content"],
        config=GenerateContentConfig(
            system_instruction=prompt[0]["content"],
            response_mime_type="application/json",
            response_schema=CharacterResponse,
        ),
    )
    return result.parsed
```

**Features**:
- Uses Google's async client (`aio`)
- Separates system instruction from user content
- Forces JSON output with `response_mime_type`
- Pydantic model validation via `response_schema`

**Supported Models**:
- gemini-2.5-pro
- gemini-2.5-flash
- gemini-2.5-flash-lite

### Prompt Engineering (`src/prompt/prompt.py`)

**Strategy**: Schema-aware prompt generation

The prompt contains Japanese text that instructs the LLM to act as a creative character generator, embedding the Pydantic model schema directly into the system message to enforce structured output.

**Design Decisions**:
1. **Schema Embedding**: Pydantic model schema embedded in system prompt
2. **Explicit Constraints**: Clear validation rules stated upfront
3. **Structured Format**: JSON-only output enforced
4. **Parameterization**: Gender, age, and instructions dynamically injected

### Configuration (`src/config.py`)

**Pattern**: Pydantic-based configuration with environment variables

```python
class Config(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    gemini_api_key: Secret[str] = Field(default=os.environ["GEMINI_API_KEY"])
    openai_api_key: Secret[str] = Field(default=os.environ["OPENAI_API_KEY"])
    redis_host: str = Field(default=os.environ.get("REDIS_HOST", "localhost"))
    redis_port: int = Field(default=int(os.environ.get("REDIS_PORT", "6379")))
    redis_db: int = Field(default=int(os.environ.get("REDIS_DB", "0")))
```

**Security Features**:
- `Secret[str]` type masks API keys in logs
- Environment variables loaded from `.env` or `.envrc`
- Validation ensures required vars are present
- Immutable config with `frozen=True`

## Deployment

### Docker Configuration

**Dockerfile**:
- Multi-stage build (if optimized)
- Python 3.13.2 base image
- Dependencies installed via pip/uv
- Application code copied to `/app`
- Exposed ports: 8000 (LLM), 8001 (Batch)

**docker-compose.yml**:

```yaml
services:
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    command: redis-server --appendonly yes
    volumes: [redis-data:/data]
    healthcheck: redis-cli ping

  llm-server:
    image: shibui/llm-best-practice:chapter3_section6
    ports: ["8000:8000"]
    depends_on: [redis]
    command: uvicorn src.api.llm_server:app --host 0.0.0.0 --port 8000

  batch-server:
    image: shibui/llm-best-practice:chapter3_section6
    ports: ["8001:8001"]
    depends_on: [redis]
    command: uvicorn src.api.batch_server:app --host 0.0.0.0 --port 8001

  batch-worker:
    image: shibui/llm-best-practice:chapter3_section6
    depends_on: [redis]
    command: python -m src.worker.batch_worker
```

**Key Design Choices**:
1. **Shared Image**: Same Docker image for all services, different commands
2. **Health Checks**: Redis health check ensures dependencies ready
3. **Volume Persistence**: Redis data persisted in Docker volume
4. **Network Isolation**: Services communicate via Docker network
5. **Scaling Ready**: Worker can be scaled with `--scale batch-worker=N`

### Makefile Commands

```makefile
make docker-build     # Build Docker image
make docker-up        # Start all services
make docker-down      # Stop all services
make docker-logs      # View service logs
make docker-restart   # Restart all services
```

## Design Decisions and Trade-offs

### 1. Redis vs. Alternative Queue Systems

**Decision**: Use Redis as message queue

**Alternatives Considered**:
- RabbitMQ
- Apache Kafka
- Amazon SQS
- PostgreSQL with SKIP LOCKED

**Rationale**:
- ✅ Simple to deploy and operate
- ✅ Low latency for job submission/retrieval
- ✅ Built-in TTL for automatic data cleanup
- ✅ Single technology for queue + status storage
- ✅ Sufficient for most batch processing needs
- ❌ Limited guarantees vs. dedicated message brokers
- ❌ No built-in DLQ (Dead Letter Queue)
- ❌ Horizontal scaling more complex than Kafka

**When to Reconsider**:
- Need for strong message delivery guarantees
- Multi-region, geo-distributed deployments
- High-throughput streaming use cases (millions of messages/sec)
- Advanced routing/filtering requirements

### 2. Synchronous Task Processing in Worker

**Decision**: Process tasks sequentially within each job

**Alternative**: Process all tasks in parallel using asyncio.gather()

**Rationale**:
- ✅ Simpler error handling and state management
- ✅ Predictable resource consumption
- ✅ Easier to implement rate limiting per worker
- ✅ Clear progress tracking (task N of M)
- ❌ Slower for jobs with many tasks
- ❌ Underutilizes async capabilities

**When to Reconsider**:
- Jobs typically contain 50+ tasks
- LLM API has high latency (>2 seconds per request)
- Cost of additional workers exceeds benefit of parallel processing

**Mitigation**: Scale horizontally by running multiple workers

### 3. Job Status Storage in Redis

**Decision**: Store status and results in Redis with 24-hour TTL

**Alternative**: Use PostgreSQL or S3 for persistent storage

**Rationale**:
- ✅ Fast reads for status polling
- ✅ Automatic cleanup reduces storage costs
- ✅ Co-located with queue simplifies architecture
- ✅ Sufficient for most batch job use cases
- ❌ Data lost after 24 hours
- ❌ Not suitable for long-term audit trails
- ❌ Redis memory can become bottleneck

**When to Reconsider**:
- Need to retain job history for compliance/audit
- Results accessed weeks/months after completion
- Result payloads very large (>1MB per job)

**Enhancement**: Dual-write results to both Redis (short-term) and PostgreSQL/S3 (long-term)

### 4. No Built-in Retry Logic

**Decision**: Failed tasks are not automatically retried

**Alternative**: Implement exponential backoff retry within worker

**Rationale**:
- ✅ Simpler implementation
- ✅ Avoids cascading failures
- ✅ Clear distinction between transient and permanent failures
- ✅ Client can resubmit if desired
- ❌ Requires manual intervention for transient failures
- ❌ Lower success rate for flaky API calls

**When to Reconsider**:
- LLM API has frequent transient errors (rate limits, timeouts)
- Manual resubmission operationally expensive
- High value of individual task completion

**Enhancement**: Add retry configuration per job (max_retries, backoff_factor)

### 5. No Authentication/Authorization

**Decision**: APIs are unauthenticated

**Rationale**:
- ✅ Simplifies example code
- ✅ Suitable for internal, trusted networks
- ✅ Focuses on batch processing patterns
- ❌ Not production-ready for public APIs
- ❌ No rate limiting per user
- ❌ No access control

**Production Recommendations**:
- Add API key authentication (custom header)
- Integrate JWT for user identity
- Implement rate limiting (per-user quotas)
- Add role-based access control (RBAC)

### 6. Single Worker Instance by Default

**Decision**: Default docker-compose runs one worker

**Rationale**:
- ✅ Minimal resource usage for development
- ✅ Predictable behavior for testing
- ✅ Clear logs without interleaving
- ❌ Slow processing for large backlogs
- ❌ Single point of failure

**Scaling**:
```bash
docker-compose up -d --scale batch-worker=5
```

**Production Recommendation**: Run 3-10 workers depending on throughput needs

## Performance Characteristics

### Latency

**Synchronous API** (`/generate`):
- API overhead: ~10ms
- LLM API call: 1-3 seconds (varies by model)
- Total: 1-3 seconds

**Batch API** (`/batch/submit`):
- API overhead: ~10ms
- Redis enqueue: ~1ms
- Total: ~11ms (immediate response)

**Status Check** (`/batch/{job_id}/status`):
- API overhead: ~10ms
- Redis GET: ~1ms
- Total: ~11ms

**Result Retrieval** (`/batch/{job_id}/result`):
- API overhead: ~10ms
- Redis GET: ~1-5ms (depends on result size)
- Total: ~11-15ms

### Throughput

**Single Worker**:
- ~1 task per 1-3 seconds (LLM dependent)
- ~1,200-3,600 tasks per hour
- Bottleneck: LLM API latency

**Multiple Workers (N)**:
- Linear scaling: N × single worker throughput
- 5 workers: ~6,000-18,000 tasks/hour
- Bottleneck: LLM API rate limits

**Queue Performance**:
- Redis RPUSH/BLPOP: 10,000+ ops/sec
- Queue is not the bottleneck

### Resource Usage

**Per Worker**:
- Memory: ~100-200MB (depends on result caching)
- CPU: Minimal (waiting on I/O)
- Network: ~1-10 KB per task

**Redis**:
- Memory: ~1KB per queued job + ~10-50KB per result (depends on payload)
- 1000 active jobs: ~10-50MB
- TTL automatically reclaims memory

## Error Handling Patterns

### Task-Level Errors

**Scenario**: LLM API call fails for one task

**Behavior**:
1. Exception caught in `_process_task()`
2. Task marked as FAILED with error message
3. Processing continues with next task
4. Failed task included in final results

**Example Error Response**:
```json
{
  "task_index": 2,
  "status": "failed",
  "character": null,
  "error": "Rate limit exceeded. Please retry after 60 seconds.",
  "processing_time_ms": 234.56
}
```

### Job-Level Errors

**Scenario**: Critical error before any task processing

**Behavior**:
1. Exception caught in `_process_job()`
2. Job status updated to FAILED
3. Error logged
4. Worker continues with next job

**Scenario**: Some tasks succeed, some fail

**Behavior**:
1. All tasks attempted
2. Job status set to FAILED (conservative)
3. Both successful and failed tasks included in results
4. Client can retry only failed tasks

### Worker Crash

**Scenario**: Worker process crashes mid-job

**Behavior**:
1. Job remains in PROCESSING state (stale)
2. Partial results may be saved
3. Job never marked as COMPLETED
4. No automatic recovery

**Mitigation**:
- Health check monitors worker status
- Watchdog process can restart worker
- Jobs stuck in PROCESSING for >1 hour could be requeued (requires custom logic)

### Redis Connection Loss

**Scenario**: Network partition between worker and Redis

**Behavior**:
1. Worker's BLPOP call fails
2. Exception caught in main loop
3. Worker sleeps 1 second and retries
4. Processing resumes when connection restored

## Monitoring and Observability

### Logging

**Standard Format**:
```
[timestamp] [level] [module] [message]
```

**Key Log Events**:
- Job submission: `[batch_server] Batch job {job_id} submitted with {n} tasks`
- Job dequeue: `[redis_client] Dequeued job from {queue}: {job_id}`
- Task completion: `[batch_worker] Task {idx} of job {job_id} completed in {ms}ms`
- Job completion: `[batch_worker] Job {job_id} completed. Completed: {n}, Failed: {m}`

### Metrics to Monitor

**Queue Depth**:
- Endpoint: `GET /batch/queue/stats`
- Metric: `pending_jobs`
- Alert: Queue depth > 1000 (backlog building)

**Worker Health**:
- Monitor worker process uptime
- Check last job processed timestamp
- Alert: No jobs processed in 5 minutes (worker stuck)

**Job Success Rate**:
- Metric: `completed_jobs / total_jobs`
- Alert: Success rate < 95% (systemic issues)

**Processing Time**:
- Metric: `completed_at - submitted_at` per job
- Alert: P95 processing time > 5 minutes (congestion)

**Task Failure Rate**:
- Metric: `failed_tasks / total_tasks`
- Alert: Failure rate > 5% (API issues)

### Recommended Integrations

**Prometheus**:
- Export queue depth, worker count, job metrics
- Scrape `/metrics` endpoint (requires implementation)

**Grafana**:
- Dashboard showing queue depth over time
- Job completion rate
- Task processing latency histogram

**Sentry**:
- Capture exceptions from worker
- Track error rates and unique errors

**DataDog/New Relic**:
- APM for request tracing
- Distributed tracing across services

## Testing Strategy

### Unit Tests (Not Implemented)

**Recommended Coverage**:
- Redis client methods (mock Redis)
- Pydantic model validation
- Prompt generation logic
- Status state transitions

### Integration Tests

**Manual Testing**:
1. Start services with `make docker-up`
2. Submit test jobs via curl
3. Verify status updates in real-time
4. Confirm results match expectations
5. Check logs for errors

**Automated Testing**:
```python
async def test_batch_job_lifecycle():
    # Submit job
    response = await client.post("/batch/submit", json=job_request)
    job_id = response.json()["job_id"]

    # Poll until complete
    while True:
        status = await client.get(f"/batch/{job_id}/status")
        if status.json()["status"] == "completed":
            break
        await asyncio.sleep(1)

    # Verify results
    result = await client.get(f"/batch/{job_id}/result")
    assert len(result.json()["tasks"]) == expected_count
```

### Load Testing

**Tools**: Apache Bench, Locust, k6

**Scenario**: Submit 100 batch jobs, each with 10 tasks

```bash
# Example using Apache Bench
ab -n 100 -c 10 -p job_payload.json -T application/json \
   http://localhost:8001/batch/submit
```

**Metrics to Collect**:
- Job submission latency (should be <100ms)
- Queue depth over time
- Worker throughput (tasks/second)
- End-to-end job completion time

### Failure Testing

**Scenarios**:
1. **Redis Failure**: Stop Redis, verify graceful degradation
2. **Worker Failure**: Kill worker mid-job, verify job remains in queue
3. **LLM API Failure**: Mock API errors, verify task-level error handling
4. **Rate Limiting**: Trigger rate limits, verify backoff behavior (if implemented)

## Future Enhancements

### 1. Priority Queue

**Use Case**: Process urgent jobs before older jobs

**Implementation**:
- Use Redis sorted sets (ZADD/ZPOPMIN)
- Score = priority × 1e9 + timestamp (higher priority = lower score)
- Worker uses ZPOPMIN instead of BLPOP

### 2. Scheduled Jobs

**Use Case**: Execute batch job at specific time

**Implementation**:
- Accept `scheduled_at` parameter in BatchJobRequest
- Store in Redis sorted set with timestamp score
- Scheduler process moves due jobs to main queue

### 3. Webhooks

**Use Case**: Notify client when job completes

**Implementation**:
- Accept `webhook_url` in BatchJobRequest
- Worker sends POST to webhook after job completion
- Include job_id and status in webhook payload

### 4. Result Streaming

**Use Case**: Get results as they complete, not just at end

**Implementation**:
- WebSocket endpoint: `/batch/{job_id}/stream`
- Worker publishes task results to Redis pub/sub
- Server subscribes and forwards to WebSocket clients

### 5. Idempotency Keys

**Use Case**: Prevent duplicate job submission

**Implementation**:
- Accept `idempotency_key` in BatchJobRequest
- Check Redis for existing job with same key
- Return existing job_id if found, otherwise create new

### 6. Dead Letter Queue

**Use Case**: Isolate permanently failed tasks

**Implementation**:
- After N retries, move task to DLQ
- Separate Redis list: `llm_batch_jobs:dlq`
- Admin endpoint to inspect and reprocess DLQ tasks

### 7. Cost Tracking

**Use Case**: Monitor LLM API costs per job

**Implementation**:
- Track token usage per task
- Store cumulative cost in job results
- Dashboard showing cost per provider/model

### 8. Multi-tenancy

**Use Case**: Support multiple clients with isolation

**Implementation**:
- Add `tenant_id` to job metadata
- Separate Redis keys per tenant
- Rate limiting per tenant
- Cost allocation per tenant

## Security Considerations

### Current State (Example Code)

⚠️ **Warning**: This implementation is not production-ready from a security standpoint.

**Missing Security Controls**:
- No authentication (anyone can submit jobs)
- No authorization (anyone can view any job)
- No rate limiting (susceptible to abuse)
- No input sanitization (potential injection risks)
- API keys in plaintext environment variables

### Production Hardening

**1. Authentication**:
```python
# Add API key authentication
@app.post("/batch/submit")
async def submit_batch_job(
    request: BatchJobRequest,
    api_key: str = Header(..., alias="X-API-Key")
):
    if not verify_api_key(api_key):
        raise HTTPException(401, "Invalid API key")
```

**2. Authorization**:
```python
# Ensure users can only access their own jobs
@app.get("/batch/{job_id}/result")
async def get_batch_job_result(
    job_id: str,
    user: User = Depends(get_current_user)
):
    job_owner = get_job_owner(job_id)
    if job_owner != user.id:
        raise HTTPException(403, "Forbidden")
```

**3. Rate Limiting**:
```python
from slowapi import Limiter
limiter = Limiter(key_func=lambda: request.headers.get("X-API-Key"))

@app.post("/batch/submit")
@limiter.limit("10/minute")
async def submit_batch_job(...):
    ...
```

**4. Input Validation**:
- Pydantic models already provide basic validation
- Add max length constraints on string fields
- Sanitize user-provided instructions to prevent prompt injection

**5. Secrets Management**:
- Use AWS Secrets Manager, HashiCorp Vault, or GCP Secret Manager
- Rotate API keys regularly
- Never log sensitive data

## Conclusion

This project demonstrates a robust, scalable architecture for asynchronous batch processing of LLM tasks. Key takeaways:

1. **Separation of Concerns**: Decouple job submission from execution
2. **Horizontal Scalability**: Add workers to increase throughput
3. **Fault Tolerance**: Task-level error handling prevents cascading failures
4. **Observability**: Real-time status tracking and comprehensive logging
5. **Trade-offs**: Simplicity vs. advanced features (retries, DLQ, etc.)

The implementation prioritizes clarity and educational value over production-hardening. For real-world deployment, implement the security controls, monitoring, and enhancements outlined above.

**When to Use This Pattern**:
- ✅ Batch processing of 10-10,000+ items
- ✅ Each item takes 1-60 seconds to process
- ✅ Results not needed immediately
- ✅ Occasional failures acceptable at task level
- ✅ Cost efficiency more important than latency

**When Not to Use**:
- ❌ Real-time user-facing requests
- ❌ Strong message delivery guarantees required
- ❌ Complex workflow orchestration needed
- ❌ Sub-second latency required
- ❌ Strict ordering requirements

For those scenarios, consider alternatives like synchronous APIs, dedicated message brokers (RabbitMQ, Kafka), or workflow engines (Temporal, Airflow).
