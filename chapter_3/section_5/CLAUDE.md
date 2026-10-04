# Chapter 3 Section 5: LLM API Gateway — One Entry Point for Providers, Keys, and Monitoring

## What This Section Demonstrates

As LLM usage spreads through an organization, every app embedding provider SDKs and API keys becomes an operational liability: keys sprawl, usage is invisible, and provider migrations touch every codebase. This section implements an **LLM API Gateway**: a single HTTP service (`POST /v1/generate`) that fronts all providers, holds all API keys, routes by a `provider` field in the request, and logs every request/response/error with a request ID and per-client attribution.

Client applications depend only on the gateway's provider-neutral contract (via a thin `GatewayClient`), never on provider SDKs. Apply this when multiple applications/teams consume LLMs: it centralizes credentials, cost visibility, provider migrations, and policy enforcement in one deployable.

## Practice Rules

1. **Define a provider-neutral request contract**: `{provider, model, prompt (messages), response_format (schema dict), client_id}` — nothing provider-specific leaks into the API shape.
2. **Keep all provider API keys inside the gateway** (`APIKeyManager`); clients authenticate to the gateway, never to providers. Key rotation becomes a gateway config change.
3. **Route on the `provider` field in one service class** (`GatewayService.process_request`), which owns the per-provider SDK calls and lazily initializes clients.
4. **Assign a `request_id` to every request and return it** — the tracing handle across client logs, gateway logs, and incident reports.
5. **Log request, response (latency + success), and error as separate structured events** (`GatewayMonitor`) with `client_id` — this is where per-team usage/cost accounting comes from.
6. **Ship a thin typed client** (`GatewayClient`) so applications get the gateway contract without hand-writing HTTP.
7. **Expose provider availability in `/health`** (`providers_available: {openai: true, gemini: true}`) so operators see per-provider readiness at a glance.

## Architecture

```
App A ──┐                          ┌──────────── Gateway (:8080) ────────────┐
App B ──┼─ GatewayClient ──POST──▶ │ gateway_server.py   /v1/generate /health│
App C ──┘   /v1/generate           │   │                                     │
                                   │   ▼                                     │
                                   │ GatewayService.process_request          │
                                   │   ├─ GatewayMonitor.log_request         │
                                   │   ├─ APIKeyManager (all provider keys)  │
                                   │   ├─ provider routing:                  │
                                   │   │    openai → _call_openai            │
                                   │   │    gemini → _call_gemini            │
                                   │   └─ log_response / log_error (+ms)     │
                                   └──────────────┬──────────────────────────┘
                                                  ▼
                                     Provider APIs (OpenAI / Gemini)

(docker-compose also runs a demo backend app on :8000 that consumes the gateway)
```

### Directory Structure

```
chapter_3/section_5/
├── src/
│   ├── api_gateway/
│   │   ├── gateway_server.py    # FastAPI app: /v1/generate, /health
│   │   ├── gateway_service.py   # provider routing + timing
│   │   ├── api_key_manager.py   # central key store (Secret[str])
│   │   ├── monitoring.py        # GatewayMonitor: request_id + structured events
│   │   └── models.py            # GatewayRequest/Response/Health/Error
│   ├── client/
│   │   ├── gateway_client.py    # thin client library for apps
│   │   └── llm_client.py
│   ├── api/llm_server.py        # demo backend app consuming the gateway
│   ├── service/request_llm.py / model/model.py / prompt/prompt.py
│   └── config.py / logger.py
├── docker-compose.yml           # gateway:8080 + backend:8000
├── Dockerfile.gateway / Dockerfile.backend
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Provider-neutral contract (`src/api_gateway/models.py`)

```python
class GatewayRequest(BaseModel):
    provider: str = Field(..., description="LLM provider (openai or gemini)")
    model: str = Field(..., description="Model name to use")
    prompt: list[dict[str, str]] = Field(..., description="Prompt messages")
    response_format: dict[str, Any] = Field(..., description="Response format schema")
    client_id: Optional[str] = Field(default=None, description="Client identifier for tracking")

class GatewayResponse(BaseModel):
    content: Any
    provider: str
    model: str
    processing_time_ms: float
    request_id: str          # ← returned to the caller for tracing
```

### 2. Routing + timing + monitoring in one place (`src/api_gateway/gateway_service.py`)

```python
async def process_request(self, request_id, provider, model, prompt, response_format, client_id=None):
    gateway_monitor.log_request(request_id, provider, model, client_id)
    if not api_key_manager.is_provider_supported(provider):
        gateway_monitor.log_error(request_id, "UnsupportedProvider", ...)
        raise ValueError(f"Unsupported provider: {provider}")

    start_time = time.time()
    try:
        if provider.lower() == "openai":
            content = await self._call_openai(model=model, prompt=prompt, response_format=response_format)
        elif provider.lower() == "gemini":
            content = await self._call_gemini(model=model, prompt=prompt, response_format=response_format)
        processing_time_ms = (time.time() - start_time) * 1000
        gateway_monitor.log_response(request_id, provider, model, processing_time_ms, True)
        return content, processing_time_ms
    except Exception as e:
        gateway_monitor.log_error(request_id, type(e).__name__, str(e), provider, model)
        gateway_monitor.log_response(request_id, provider, model, ..., False, error=str(e))
        raise
```

### 3. Centralized key custody (`src/api_gateway/api_key_manager.py`)

```python
class APIKeyManager:
    def __init__(self):
        self._provider_keys: Dict[str, Secret[str]] = {
            "openai": config.openai_api_key,
            "gemini": config.gemini_api_key,
        }
    def get_api_key(self, provider: str) -> str: ...        # raises on unsupported
    def is_provider_supported(self, provider: str) -> bool: ...
```

Keys are `Secret[str]` (masked in logs); clients never see them.

### 4. Thin app-side client (`src/client/gateway_client.py`)

```python
class GatewayClient:
    async def generate(self, provider, model, prompt, response_format=None, client_id=None):
        response = await self.client.post(f"{self.gateway_url}/v1/generate", json={...})
        result = response.json()
        return result["content"], result["processing_time_ms"], result["request_id"]
```

## Data Models

| Model | Purpose |
|-------|---------|
| `GatewayRequest` / `GatewayResponse` | The provider-neutral wire contract |
| `GatewayHealthResponse` | status + `providers_available` map |
| `GatewayErrorResponse` | error, error_type, request_id, timestamp |

## Setup & Run

```bash
cp .envrc.example .envrc     # OPENAI_API_KEY / GEMINI_API_KEY (gateway-side only!)

# Canonical (docker)
make docker-build && make docker-up
curl -s http://localhost:8080/health
# → {"status":"healthy","providers_available":{"openai":true,"gemini":true}}
make docker-down

# Call the gateway directly
curl -X POST http://localhost:8080/v1/generate -H "Content-Type: application/json" \
  -d '{"provider": "gemini", "model": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
       "prompt": [{"role": "user", "content": "..."}],
       "response_format": {...}, "client_id": "team-a"}'
```

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
make docker-build / make docker-up / make docker-down / make docker-logs
```

## Implementation Notes

- **Gateway vs proxy (Chapter 3 Section 4)**: the proxy controls *volume* to one backend (rate limit/queue/breaker); the gateway unifies *access* across providers (contract, keys, monitoring). Production setups often compose both — gateway in front, volume controls inside it.
- **`response_format` crosses the wire as a JSON schema dict**, not a Pydantic class — the gateway reconstructs provider-specific structured-output bindings server-side. Clients stay dependency-free.
- **`client_id` is the accounting axis**: with structured request/response logs keyed by client_id, per-team cost dashboards are a log query, not new code.
- **Lazy provider-client initialization** (`_get_openai_client`) means the gateway boots even if one provider's key is absent — `/health` shows which providers are actually available.
- **What to add for production**: gateway-level authn (API keys/JWT for callers), per-client rate limits, response caching, and budget alerts — all natural extensions at this choke point, listed as future work in the code comments.

## How to Apply This Practice to Your Own Project

1. Stand up the gateway with your providers in `GatewayService` and keys in `APIKeyManager`; deploy it before the second LLM-consuming app appears.
2. Freeze the wire contract early (`provider/model/prompt/response_format/client_id`) — every field you add later must be optional.
3. Require `client_id` (or derive it from caller auth) so usage attribution exists from day one.
4. Distribute the thin client as an internal package; forbid direct provider SDK usage in app code via lint/review policy.
5. Ship the monitor's structured events to your log pipeline; build per-provider latency and per-client volume dashboards.
6. Layer volume controls (Section 4) and caching into the gateway as usage grows — the choke point is already in place.
