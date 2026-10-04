# Chapter 3 Section 2: LLM Request Resilience — Timeouts, Caching, and Fallback Strategies

## What This Section Demonstrates

LLM APIs time out, rate-limit, and go down. This section implements a **fallback coordinator** that wraps every LLM request with a timeout and, on failure, degrades gracefully through a configurable strategy:

- **`parameter_cache`** — exact-match cache lookup (SHA256 of prompt+model)
- **`semantic_cache`** — embedding-similarity cache lookup (cosine ≥ 0.95)
- **`alternative_provider`** — retry the request against a backup provider (OpenAI ⇄ Gemini)

Every request reports which strategy served it, and the coordinator keeps success/timeout/error/fallback statistics for monitoring. Apply this to any user-facing LLM feature with availability requirements — "the model provider had an incident" should degrade your service, not take it down.

## Practice Rules

1. **Put a hard timeout on every primary request** (`asyncio.wait_for(request_func(), timeout=...)`) — a hung request is worse than a failed one.
2. **Make the fallback strategy explicit and configurable** (`FallbackStrategy` enum, chosen per deployment/CLI), not implicit retry spaghetti.
3. **Cache successful responses at the coordinator level** so the cache fills as a side effect of normal traffic and is ready when failures come.
4. **Return the serving strategy with the response** (`(response, strategy, error_reason)` tuple) — callers and logs must know when users got degraded results.
5. **Count everything** (`total_requests`, `primary_success`, `timeout_count`, `error_count`, per-strategy fallback successes) and expose rates; fallback frequency is an SLO signal.
6. **Fail loudly only after all strategies are exhausted** (`_handle_fallback_failure` raises with the accumulated reason).
7. **Give caches TTLs and cleanup paths** (`clear_expired`, `clear_all`); a stale cache serving forever is its own incident.
8. **Semantic cache needs a threshold you've validated** — 0.95 cosine similarity here; too low serves wrong answers, too high never hits.

## Architecture

```
CLI (src/main.py)  -fs parameter_cache | semantic_cache | alternative_provider
  ▼
LLMRequestWrapper (src/client/llm_request_wrapper.py)
  │ builds primary/alternative request closures per provider
  ▼
FallbackCoordinator.request_with_fallback (src/service/fallback_coordinator.py)
  1. _try_primary_request      — asyncio.wait_for(timeout) → success? cache + return (PRIMARY)
  2. _execute_fallback_strategy — dispatch on FallbackStrategy:
       PARAMETER_CACHE   → CacheManager.get(prompt, model)         [exact key]
       SEMANTIC_CACHE    → SemanticCacheManager (embeddings+cosine) [similar prompt]
       ALTERNATIVE_PROVIDER → alternative_request_func()            [other provider]
  3. _handle_fallback_failure  — raise with error_reason
  ▼
(CharacterResponse, FallbackStrategy, error_reason) + stats
```

### Directory Structure

```
chapter_3/section_2/
├── src/
│   ├── main.py                        # CLI (character generation demo + -fs strategy flag)
│   ├── client/
│   │   ├── llm_client.py              # provider clients + model enums
│   │   └── llm_request_wrapper.py     # per-provider request closures fed to the coordinator
│   ├── service/
│   │   ├── fallback_coordinator.py    # FallbackCoordinator / FallbackStrategy / stats
│   │   └── cache_manager.py           # BaseCacheManager / CacheManager / SemanticCacheManager
│   ├── model/model.py                 # CharacterResponse
│   ├── prompt/prompt.py
│   └── config.py / logger.py
├── tests/                             # cache + coordinator tests
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Timeout-guarded primary with fallback dispatch (`src/service/fallback_coordinator.py`)

```python
async def request_with_fallback(self, primary_provider, primary_request_func,
                                alternative_request_func=None, prompt=None, model=None):
    result = await self._try_primary_request(primary_provider, primary_request_func, context)
    if result:
        return result.response, result.strategy, result.error_reason

    error_reason = "timeout" if self.stats["timeout_count"] > 0 else "error"
    result = await self._execute_fallback_strategy(alternative_request_func, context, error_reason)
    if result:
        return result.response, result.strategy, result.error_reason

    self._handle_fallback_failure(error_reason)     # raises
```

```python
async def _try_primary_request(self, provider, request_func, context):
    try:
        response = await asyncio.wait_for(request_func(), timeout=self.timeout)
        await self._cache_response(response, context)          # fill cache on success
        return FallbackResult(response=response, strategy=FallbackStrategy.PRIMARY, error_reason=None)
    except asyncio.TimeoutError:
        self.stats["timeout_count"] += 1
        return None
    except Exception:
        self.stats["error_count"] += 1
        return None
```

### 2. Strategy dispatch table

```python
strategy_handlers = {
    FallbackStrategy.PARAMETER_CACHE: self._try_parameter_cache,
    FallbackStrategy.SEMANTIC_CACHE: self._try_semantic_cache,
    FallbackStrategy.ALTERNATIVE_PROVIDER: lambda ctx, err: self._try_alternative_provider(
        alternative_func, ctx, err),
}
```

### 3. Exact vs semantic caching (`src/service/cache_manager.py`)

```python
class CacheManager(BaseCacheManager):                 # exact match
    def _generate_cache_key(self, prompt: list, model: str) -> str:
        # SHA256(prompt + model) → .cache/<key>.json

class SemanticCacheManager(BaseCacheManager):         # similarity match
    def __init__(self, cache_dir=".semantic_cache", ttl=None,
                 similarity_threshold: float = 0.95, embedding_func=None): ...
    # embeds the prompt; serves the best entry with cosine ≥ threshold
```

Both inherit TTL handling, expiry cleanup, and file storage from `BaseCacheManager`.

### 4. Observable outcomes

```python
coordinator.get_stats()   # totals + per-strategy successes + computed rates
coordinator.log_stats()   # human-readable summary (Errors / Fallback Rate ...)
```

## Data Models

| Model | Purpose |
|-------|---------|
| `FallbackStrategy` | `primary` / `parameter_cache` / `semantic_cache` / `alternative_provider` |
| `RequestContext` | prompt + model carried through the fallback chain |
| `FallbackResult` | response + serving strategy + error_reason |
| `CharacterResponse` | Demo task structured output |

## Setup & Run

```bash
cp .envrc.example .envrc     # OPENAI_API_KEY / GEMINI_API_KEY
uv sync

# Canonical example (alternative-provider fallback: Gemini primary → OpenAI backup)
uv run python -m src.main -g FEMALE -a 25 -lp ANTHROPIC -m CLAUDE_HAIKU_4_5 -am GPT_5_4

# Cache-based strategies
uv run python -m src.main -g FEMALE -a 25 -lp ANTHROPIC -m CLAUDE_HAIKU_4_5 -fs parameter_cache
uv run python -m src.main -g FEMALE -a 25 -lp ANTHROPIC -m CLAUDE_HAIKU_4_5 -fs semantic_cache
```

### CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--gender` / `--age` / `--additional-instructions` | `-g` / `-a` / `-ai` | Character request |
| `--llm-provider` / `--model` | `-lp` / `-m` | Primary provider/model |
| `--alternative-model` | `-am` | Backup model (alternative-provider strategy) |
| `--fallback-strategy` | `-fs` | `parameter_cache` / `semantic_cache` / `alternative_provider` |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
uv run pytest tests/ -v      # cache + coordinator tests (LLM mocked)
```

## Implementation Notes

- **Strategy choice is a product decision.** Cache strategies return *stale or approximate* answers instantly and free; alternative-provider returns *fresh* answers at latency+cost with a second dependency. Deterministic tasks favor caching; personalized/generative ones favor provider failover.
- **Cache-on-success is what makes cache fallback real** — without it, the cache is empty exactly when you need it. Note the write happens after primary success, off the failure path.
- **Semantic cache cost**: each lookup needs an embedding call (see `embedding_func`); it trades a cheap embedding request for avoiding an expensive/broken generation request.
- **The stats module doubles as the alerting contract** — a rising fallback rate with steady traffic is your early warning of provider degradation.
- **Combine with retries carefully**: this coordinator intentionally does *not* retry the primary before falling back; if you add retries (exponential backoff), keep the total worst-case latency budget in mind — timeout × attempts + fallback time is what users experience.

## How to Apply This Practice to Your Own Project

1. Wrap your provider calls as zero-arg async closures and route every call through one coordinator — resilience must not be per-call-site.
2. Pick a default timeout from your latency SLO (not the provider's worst case), and expose it via config.
3. Enable exact-match caching first (cheapest win), with TTLs matched to content freshness; add semantic caching only where paraphrased repeats are common.
4. Configure the alternative provider using the adapter/factory pattern (Chapter 3 Section 1) so both providers share one interface.
5. Propagate the serving strategy to logs/metrics; alert on fallback rate.
6. Decide the end-of-chain behavior explicitly: raise (this implementation), or add a static/template response tier if your product needs a never-fail answer.
