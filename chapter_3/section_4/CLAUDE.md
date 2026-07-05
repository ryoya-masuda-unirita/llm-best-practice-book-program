# Chapter 3 Section 4: Controlling LLM Request Volume — Proxy with Rate Limiter, Queue, and Circuit Breaker

## What This Section Demonstrates

Provider rate limits are a shared, org-wide resource; letting every client hit the LLM API directly guarantees 429 storms. This section builds a **traffic-control proxy** that sits between clients and an LLM backend and composes three classic mechanisms:

- **Token-bucket rate limiter** — smooths outbound request rate to a configured requests/window.
- **Request queue** — absorbs bursts: requests wait (bounded queue + future-based completion) instead of failing when the bucket is empty.
- **Circuit breaker** — CLOSED → OPEN on consecutive failures/error rate, rejecting fast while the backend is unhealthy; OPEN → HALF_OPEN probes recovery.

The proxy exposes the same `/generate` surface as the backend plus `/metrics` and `/proxy-health`, so clients switch by changing one base URL. Apply this pattern whenever multiple consumers share one LLM quota, or when a flaky upstream must not cascade into your app.

## Practice Rules

1. **Centralize volume control in one process** (the proxy). Client-side politeness doesn't compose across services; one choke point does.
2. **Order the mechanisms: queue → rate limiter → circuit breaker → backend.** The queue absorbs bursts, the limiter paces dequeues, the breaker guards the actual call.
3. **Use a token bucket for pacing** (`tokens = max_requests`, refilled at `max_requests / window_seconds` per second) — it allows short bursts up to bucket size while enforcing the average rate.
4. **Bound the queue and fail explicitly when full** (`RequestQueueFullError` → HTTP 503) — unbounded queues convert overload into latency and memory pressure.
5. **Complete queued requests via futures**: the enqueuer awaits a future; the worker loop dequeues, executes, and resolves it — decoupling client connections from execution pacing.
6. **Trip the breaker on both consecutive failures and error rate** (`failure_threshold`, `error_rate_threshold`), and auto-probe recovery after `timeout_seconds` via HALF_OPEN.
7. **Expose metrics for all three mechanisms** (`/metrics`: available tokens, queue size, breaker state/counters) — you cannot tune what you cannot see.

## Architecture

```
Clients ──POST /generate──▶ Proxy Server (:8080, src/proxy/proxy_server.py)
                              │ enqueue → await future
                              ▼
                        RequestQueue (bounded)          ← 503 when full
                              │ worker loop dequeues
                              ▼
                        TokenBucketRateLimiter.acquire(timeout=30s)
                              ▼
                        CircuitBreaker.call(forward_to_backend)
                              │ CLOSED/HALF_OPEN → forward; OPEN → fast fail
                              ▼
                        LLM Backend (:8000, src/api/llm_server.py) → Gemini
Monitoring:
  GET /proxy-health  GET /metrics  POST /circuit-breaker/reset
```

### Directory Structure

```
chapter_3/section_4/
├── src/
│   ├── proxy/
│   │   ├── proxy_server.py      # FastAPI proxy: queue worker, endpoints, wiring
│   │   ├── rate_limiter.py      # TokenBucketRateLimiter + RateLimiterConfig
│   │   ├── request_queue.py     # RequestQueue + QueueConfig + RequestQueueFullError
│   │   └── circuit_breaker.py   # CircuitBreaker + CircuitBreakerConfig + states
│   ├── api/llm_server.py        # backend: /generate (Gemini structured output), /health
│   ├── client/llm_client.py / service/request_llm.py
│   ├── model/model.py / prompt/prompt.py / config.py / logger.py
├── docker-compose.yml           # llm-server:8000 + proxy-server:8080
├── Dockerfile.web / Dockerfile.proxy
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Token bucket (`src/proxy/rate_limiter.py`)

```python
@dataclass
class RateLimiterConfig:
    max_requests: int = 10        # bucket size
    window_seconds: float = 1.0   # refill window

class TokenBucketRateLimiter:
    def __init__(self, config):
        self.tokens = float(config.max_requests)
        self.refill_rate = config.max_requests / config.window_seconds

    async def acquire(self, timeout: float | None = None) -> bool:
        # refill tokens by elapsed_time * refill_rate (capped at bucket size),
        # consume one, or wait until available / timeout
```

### 2. Bounded queue with future completion (`src/proxy/request_queue.py`)

```python
async def enqueue(self, request_data) -> Any:
    if self.is_full():
        raise RequestQueueFullError(...)
    future = asyncio.get_event_loop().create_future()
    await self.queue.put({"data": request_data, "future": future})
    return await future                      # caller waits here

def complete_request(self, future, result=None, exception=None):
    exception and future.set_exception(exception) or future.set_result(result)
```

### 3. Worker loop pacing dequeues (`src/proxy/proxy_server.py`)

```python
async def process_queue_worker():
    while True:
        queue_item = await request_queue.dequeue()
        acquired = await rate_limiter.acquire(timeout=30.0)     # pace here
        result = await circuit_breaker.call(forward_request, queue_item["data"])
        request_queue.complete_request(queue_item["future"], result=result)
```

### 4. Circuit breaker state machine (`src/proxy/circuit_breaker.py`)

```python
async def call(self, func, *args, **kwargs):
    async with self.lock:
        await self._check_state()                    # OPEN → HALF_OPEN after timeout
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(...)
    try:
        result = await func(*args, **kwargs)
        await self._on_success()                     # HALF_OPEN successes → CLOSED
        return result
    except Exception:
        await self._on_failure()                     # threshold/error-rate → OPEN
        raise
```

## Data Models

| Model | Purpose |
|-------|---------|
| `RateLimiterConfig` / `QueueConfig` / `CircuitBreakerConfig` | Tunables per mechanism |
| `CircuitState` | `CLOSED` / `OPEN` / `HALF_OPEN` |
| `ProxyMetrics` / `ProxyHealthResponse` | Monitoring payloads (tokens, queue size, breaker counters) |
| `LLMRequest` / `ProxiedLLMResponse` | Passthrough request/response incl. circuit_state + queue_size metadata |

## Setup & Run

```bash
cp .envrc.example .envrc     # set GEMINI_API_KEY

# Canonical (docker)
make docker-build && make docker-up
curl -s http://localhost:8000/health          # backend direct
curl -s http://localhost:8080/proxy-health    # via proxy
curl -s http://localhost:8080/metrics         # limiter/queue/breaker state
make docker-down

# Generate through the proxy
curl -X POST http://localhost:8080/generate -H "Content-Type: application/json" \
  -d '{"gender": "female", "age": 25}'
```

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
make docker-build / make docker-up / make docker-down / make docker-logs
```

## Implementation Notes

- **Why proxy-level control beats client-side**: quotas are per-organization; a proxy makes the quota a single managed resource with global visibility, and lets you change policy without redeploying N clients.
- **Token bucket vs fixed window**: fixed windows allow 2× bursts at boundaries; token bucket enforces the average while still permitting controlled bursts up to bucket size.
- **Backpressure semantics**: queue full → 503 immediately (client should back off); queue accepted → client waits up to the limiter/queue latency. Both outcomes are explicit, never silent queuing forever — `acquire(timeout=30)` caps wait time.
- **Breaker protects both sides**: OPEN state spares the failing backend from hammering *and* gives clients fast failures instead of timeouts. `POST /circuit-breaker/reset` exists for operator override after a known fix.
- **These mechanisms compose but measure differently**: watch `available_tokens` for pacing pressure, `queue_size` for sustained overload, breaker `state`/failure counts for upstream health — three different alerts.

## How to Apply This Practice to Your Own Project

1. Deploy the proxy pattern when ≥2 consumers share an LLM quota; keep the backend API unchanged and move clients over by base-URL switch.
2. Size the token bucket from your provider tier: `max_requests/window` ≈ 80% of the documented RPM; leave headroom for retries.
3. Bound the queue at (acceptable wait seconds × dequeue rate); return 503 + `Retry-After` beyond it.
4. Start the breaker with `failure_threshold=5`, `timeout_seconds=30`, `error_rate_threshold=0.5`, then tune from incident data.
5. Ship `/metrics` into your monitoring stack and alert on queue growth and breaker opens.
6. If you need per-tenant fairness, shard the token bucket per tenant key in the proxy — the composition order stays the same.
