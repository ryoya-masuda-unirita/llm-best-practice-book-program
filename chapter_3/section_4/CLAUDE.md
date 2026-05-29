# Chapter 3 Section 1: Controlling LLM Request Volume - Project Status Report

## Project Overview

This project implements a **proxy server architecture for controlling LLM API request volume** to address rate limiting challenges in production LLM applications. The implementation demonstrates a practical approach to managing API rate limits through a dedicated reverse proxy that sits between client applications and LLM API backends.

**Status**: ✅ Implementation Complete

The project consists of two FastAPI-based servers:
1. **LLM API Server** (Port 8000): Provides character generation endpoints using Google Gemini API
2. **Proxy Server** (Port 8080): Implements traffic control mechanisms including rate limiting, circuit breaker, request queuing, and automatic retry

## Problem Statement

LLM APIs impose rate limits (Requests Per Second, Tokens Per Minute) on API keys, which creates operational challenges when:
- Multiple teams or services share a single API contract
- Burst traffic from one consumer affects all other consumers
- Unexpected load spikes cause cascading failures across the system
- 429 (Too Many Requests) errors impact user experience

**Real-world scenarios addressed**:
1. **Multi-team organizations**: Preventing one team's bulk processing from blocking others' development work
2. **E-commerce platforms**: Handling peak traffic during sales events without service degradation
3. **Batch processing**: Ensuring overnight data pipelines complete successfully within rate limits

## Implementation Architecture

### System Architecture

```
Client Applications
        ↓
    [Proxy Server - Port 8080]
        ├── Request Queue (max: 100, timeout: 300s)
        ├── Rate Limiter (Token Bucket: 10 req/sec)
        ├── Circuit Breaker (failure threshold: 5, timeout: 60s)
        └── Retry Logic (max: 3, exponential backoff)
        ↓
    [LLM API Server - Port 8000]
        ├── /generate endpoint
        └── /health endpoint
        ↓
    External LLM APIs
        └── Google Gemini (gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite, gemini-3.5-flash, gemini-3.1-flash-lite)
```

### Component Overview

#### 1. Proxy Server (`src/proxy/proxy_server.py`)

**Purpose**: Central traffic control and coordination layer

**Key Features**:
- Integrates all control mechanisms (queue, rate limiter, circuit breaker, retry)
- Exposes monitoring endpoints (`/metrics`, `/proxy-health`, `/circuit-breaker/reset`)
- Adds proxy metadata to all responses for observability
- Implements background queue processor for async request handling

**Configuration**:
- Backend URL: `http://localhost:8000`
- Max retries: 3
- Retry backoff base: 2.0 seconds

#### 2. Rate Limiter (`src/proxy/rate_limiter.py`)

**Algorithm**: Token Bucket

**Implementation Details**:
- **Capacity**: 10 requests per second (configurable)
- **Refill rate**: Tokens replenished continuously at calculated rate
- **Behavior**: Requests wait (blocking) when tokens unavailable
- **Timeout**: Configurable maximum wait time (default: 30s)

**Key Methods**:
- `acquire()`: Consume one token, wait if unavailable
- `get_available_tokens()`: Return current token count for monitoring

**Code Reference**: `src/proxy/rate_limiter.py:20-98`

#### 3. Circuit Breaker (`src/proxy/circuit_breaker.py`)

**Pattern**: Three-state circuit breaker (CLOSED → OPEN → HALF_OPEN)

**State Transitions**:
- **CLOSED → OPEN**:
  - Consecutive failures reach threshold (5) OR
  - Error rate exceeds 50% (after minimum 10 requests)
- **OPEN → HALF_OPEN**: Timeout period elapses (60 seconds)
- **HALF_OPEN → CLOSED**: Consecutive successes reach threshold (2)
- **HALF_OPEN → OPEN**: Any failure during half-open state

**Metrics Tracked**:
- Total requests and failed requests
- Error rate calculation
- Failure/success counters
- Last failure timestamp

**Code Reference**: `src/proxy/circuit_breaker.py:38-191`

#### 4. Request Queue (`src/proxy/request_queue.py`)

**Purpose**: Absorb burst traffic and prevent request rejection

**Implementation Details**:
- **Queue type**: `asyncio.Queue` for async/await compatibility
- **Max size**: 100 requests
- **Request timeout**: 300 seconds
- **Behavior**: Returns 503 when full, 504 on timeout

**Queueing Mechanism**:
- Uses `asyncio.Future` for async result waiting
- Background processor continuously dequeues and processes requests
- Tracks metrics: total queued, processed, timeouts

**Code Reference**: `src/proxy/request_queue.py:26-132`

#### 5. Retry Logic (`src/proxy/proxy_server.py:100`)

**Library**: `httpx-retries` for robust retry handling

**Retry Policy**:
- **Total attempts**: 3
- **Backoff factor**: 1.0 (results in 1s, 2s, 4s intervals)
- **Status codes triggering retry**:
  - 429 Too Many Requests
  - 500-599 Server Errors

**Implementation**:
```python
retry_policy = Retry(
    total=3,
    backoff_factor=1.0,
    status_forcelist=[429, 500, 501, 502, 503, 504, ...]
)
```

**Code Reference**: `src/proxy/proxy_server.py:100-188`

#### 6. LLM API Server (`src/api/llm_server.py`)

**Purpose**: Backend service exposing LLM functionality

**Endpoints**:
- `POST /generate`: Generate character descriptions
- `GET /health`: Health check endpoint

**Supported Models**:
- **Gemini**: gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite, gemini-3.5-flash, gemini-3.1-flash-lite

**Request Model**:
```python
{
    "model": "gemini-2.5-flash",
    "character_request": {
        "gender": "male" | "female",
        "age": 0-100,
        "additional_instructions": "..."
    }
}
```

**Code Reference**: `src/api/llm_server.py:1-92`

## Key Features Implemented

### 1. Multi-Layer Traffic Control

All requests flow through four sequential control layers:
1. **Queue** → Prevents immediate rejection during bursts
2. **Rate Limiter** → Enforces throughput limits
3. **Circuit Breaker** → Protects against cascading failures
4. **Retry Logic** → Handles transient errors automatically

### 2. Comprehensive Monitoring

**Metrics Endpoint** (`GET /metrics`):
```json
{
    "rate_limiter": {
        "available_tokens": 8.5,
        "max_requests": 10,
        "window_seconds": 1.0
    },
    "circuit_breaker": {
        "state": "closed",
        "total_requests": 1523,
        "failed_requests": 12,
        "error_rate": 0.00788
    },
    "request_queue": {
        "current_size": 3,
        "max_size": 100,
        "total_queued": 1523,
        "total_processed": 1520,
        "total_timeouts": 0
    }
}
```

### 3. Response Metadata Enrichment

All proxy responses include metadata for observability:
```json
{
    "_proxy_metadata": {
        "processing_time_ms": 1456.78,
        "circuit_state": "closed",
        "queue_size": 2
    }
}
```

### 4. Structured Logging

Comprehensive logging at all layers:
- Request queuing and dequeuing events
- Token acquisition and waiting
- Circuit state transitions
- Retry attempts with backoff timing
- Error conditions with context

**Example Log Output**:
```
[INFO] Rate limiter initialized: 10 requests per 1.0s (refill rate: 10.00 tokens/s)
[INFO] Request queued. Queue size: 1/100
[INFO] Token acquired. Remaining tokens: 9.00
[INFO] Generate request completed successfully in 1456.78ms (queue size: 0)
```

### 5. Manual Circuit Breaker Control

**Endpoint**: `POST /circuit-breaker/reset`

Allows operators to manually reset circuit breaker to CLOSED state during maintenance or after resolving backend issues.

## Technology Stack

### Core Framework
- **FastAPI**: High-performance async web framework for both servers
- **Uvicorn**: ASGI server for production deployment
- **Pydantic**: Data validation and settings management

### HTTP Client
- **httpx**: Modern async HTTP client
- **httpx-retries**: Automatic retry logic with exponential backoff

### LLM SDKs
- **Google GenAI SDK**: Native Pydantic schema support for structured outputs

### Development Tools
- **python-dotenv**: Environment variable management
- **click**: CLI interface (if needed)
- **pytest**: Testing framework (configured in dev dependencies)

## Data Flow Example

**Scenario**: Client sends character generation request

```
1. Client → POST http://localhost:8080/generate
   {
       "model": "gemini-2.5-flash",
       "character_request": {...}
   }

2. Proxy → Queue.enqueue(request_data)
   - Creates asyncio.Future for result
   - Waits in queue if multiple requests pending

3. Queue Processor → Dequeues next request
   - Background task continuously processes queue

4. Rate Limiter → acquire()
   - Checks token availability
   - Waits if insufficient tokens
   - Consumes 1 token on success

5. Circuit Breaker → call(make_request_with_retry, ...)
   - Checks state (CLOSED/OPEN/HALF_OPEN)
   - Allows request if CLOSED or HALF_OPEN
   - Raises error if OPEN

6. Retry Logic → POST http://localhost:8000/generate
   - Attempts request with exponential backoff on failure
   - Max 3 attempts for 429/5xx errors

7. LLM API Server → request_gemini()
   - Calls Gemini API with structured output
   - Returns CharacterResponse model

8. Response Path (reverse direction)
   - Circuit Breaker records success/failure
   - Queue marks Future as complete
   - Proxy adds metadata
   - Client receives response with proxy_metadata
```

## Configuration

### Environment Variables

For local execution, use `.env`:
```bash
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
```

For Docker execution, use `.envrc`:
```bash
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
```

### Proxy Configuration (`src/proxy/proxy_server.py:20-48`)

```python
# Rate Limiter
max_requests=10          # 10 requests per window
window_seconds=1.0       # 1 second window

# Circuit Breaker
failure_threshold=5      # Open after 5 consecutive failures
success_threshold=2      # Close after 2 consecutive successes in half-open
timeout_seconds=60.0     # Wait 60s before half-open
error_rate_threshold=0.5 # Open if error rate > 50%
min_requests=10          # Minimum requests before error rate check

# Request Queue
max_queue_size=100       # Maximum 100 pending requests
request_timeout=300.0    # 5 minutes maximum wait

# Retry
MAX_RETRIES=3            # Maximum retry attempts
RETRY_BACKOFF_BASE=2.0   # Exponential backoff base
```

## Testing and Validation

### Manual Testing Approaches

**1. Rate Limiting Test**:
```bash
# Send 20 requests rapidly (limit: 10/sec)
for i in {1..20}; do
  curl -X POST http://localhost:8080/generate ... &
done

# Expected: First 10 process immediately, remaining 10 queue and process over ~2 seconds
```

**2. Circuit Breaker Test**:
```bash
# Stop backend server
# Send 10 requests

# Expected:
# - First 5 requests fail
# - Circuit opens
# - Remaining 5 get immediate 503 errors
# - After 60s, circuit moves to half-open
```

**3. Queue Overflow Test**:
```bash
# Send 150 requests simultaneously (queue max: 100)

# Expected:
# - First 100 queue successfully
# - Remaining 50 receive 503 Queue Full errors
```

### Metrics Validation

Monitor real-time metrics during testing:
```bash
watch -n 1 'curl -s http://localhost:8080/metrics | jq'
```

Observe:
- Token depletion and replenishment
- Queue size fluctuations
- Circuit state transitions
- Error rate calculations

## Current Limitations and Future Work

### Current Limitations

1. **No Caching**: Repeated identical requests all hit the backend
2. **Single Instance**: No horizontal scaling or load balancing
3. **No Priority Queuing**: All requests treated equally (FIFO)
4. **Fixed Configuration**: Rate limits hard-coded, not dynamic
5. **Limited Metrics**: No Prometheus/Grafana integration

### Potential Enhancements

1. **Response Caching**:
   - Implement Redis-based cache for identical prompts
   - Configurable TTL based on use case
   - Cache invalidation mechanisms

2. **Distributed Deployment**:
   - Multiple proxy instances with shared state (Redis)
   - Distributed rate limiting using Redis sorted sets
   - Load balancer in front of proxy cluster

3. **Priority Queuing**:
   - Multiple queues with different priorities
   - User/service tier-based queue assignment
   - Weighted fair queuing algorithm

4. **Dynamic Rate Limiting**:
   - Auto-adjust limits based on backend performance
   - Per-user/service rate limits
   - Time-based limit schedules (higher during off-peak)

5. **Advanced Monitoring**:
   - Prometheus metrics export
   - Grafana dashboards
   - Alerting on high error rates or queue backlog
   - Distributed tracing with OpenTelemetry

6. **Cost Optimization**:
   - Token usage tracking per user/service
   - Budget-based throttling
   - Cost attribution and chargebacks

## Running the Project

### Setup

```bash
# Install dependencies
uv sync

# Configure environment (choose one)
cp .env.example .env           # For local execution
cp .envrc.example .envrc       # For Docker execution
# Edit the file with your API key

# Start servers locally (two terminals)
uv run uvicorn src.api.llm_server:app --host 0.0.0.0 --port 8000 --reload
uv run uvicorn src.proxy.proxy_server:app --host 0.0.0.0 --port 8080 --reload

# Or use Docker Compose
make docker-build && make docker-up
```

### API Usage

**Generate Character**:
```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash",
    "character_request": {
      "gender": "male",
      "age": 25,
      "additional_instructions": "Make them adventurous"
    }
  }'
```

**Check Metrics**:
```bash
curl http://localhost:8080/metrics
```

**View API Docs**:
- Proxy: http://localhost:8080/docs
- Backend: http://localhost:8000/docs

## Key Learnings

### Architectural Insights

1. **Separation of Concerns**: Proxy handles all traffic control; backend focuses on LLM integration
2. **Defense in Depth**: Multiple layers (queue → rate limit → circuit breaker → retry) provide robust protection
3. **Observability First**: Rich metrics and metadata enable effective operations

### Implementation Decisions

1. **Token Bucket over Leaky Bucket**: Allows burst traffic within limits, better UX
2. **Async Queue over Synchronous**: Enables non-blocking operations, better scalability
3. **httpx-retries over Manual Retry**: Leverages battle-tested library, reduces bugs
4. **Pydantic Throughout**: Type safety from API to LLM response parsing

### Operational Considerations

1. **Circuit Breaker Tuning**: Balance between protection and availability
2. **Queue Size**: Trade-off between memory usage and burst absorption
3. **Timeout Values**: Coordinate queue timeout, rate limiter timeout, and HTTP timeout
4. **Logging Volume**: Detailed logs help debugging but increase storage costs

## Conclusion

This implementation demonstrates a production-ready pattern for controlling LLM API request volume through a proxy architecture. The combination of rate limiting, circuit breaking, queuing, and automatic retry provides robust protection against rate limit errors while maintaining good user experience during burst traffic.

The modular design allows each component to be tuned independently based on specific requirements, and the comprehensive monitoring enables data-driven optimization. While current implementation is single-instance, the architecture can be extended to distributed deployment with shared state for larger-scale applications.

**Status**: Ready for educational use and adaptation to production environments with appropriate hardening and scaling considerations.
