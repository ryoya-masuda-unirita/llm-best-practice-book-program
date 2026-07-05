# Chapter 3 Section 3: Concurrent LLM Requests — Retry with Backoff, Jitter, and Semaphore Control

## What This Section Demonstrates

This section implements the client-side reliability kit for **making many LLM requests at once without melting your rate limits**:

- **Exponential backoff with jitter** — failed requests retry at 1s → 2s → 4s… (capped at 60s) plus 10–50% random jitter to avoid the thundering-herd effect of synchronized retries.
- **Retryable-error classification** — rate limits (429/ResourceExhausted) and transient server errors (5xx) retry; everything else fails immediately.
- **Semaphore-bounded concurrency** — a YAML file of N generation requests is processed with `asyncio.gather`, limited to `-p` concurrent in-flight requests.
- **Partial-failure tolerance** — `gather(return_exceptions=True)`; failures are logged with their indices, successes are kept.

Apply this to any bulk LLM workload driven from your own process (as opposed to provider batch APIs — Chapter 2 Section 5): dataset generation, backfills, evaluations, migrations.

## Practice Rules

1. **Never retry blindly.** Classify errors first (`should_retry_error`): retry rate limits and transient 5xx (`RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}`); fail fast on auth/validation errors.
2. **Exponential backoff must have jitter.** `min(base * 2^attempt, MAX) + uniform jitter` — without jitter, all failed clients retry in lockstep and re-trigger the rate limit.
3. **Honor `Retry-After` when the API provides it** — an explicit server hint beats your own schedule.
4. **Cap both attempts and backoff** (`MAX_RETRIES`, `MAX_BACKOFF_SECONDS = 60`); unbounded retries hide outages.
5. **Bound concurrency with a semaphore**, not chunked loops — `asyncio.Semaphore(parallelism)` keeps exactly N requests in flight while others queue, maximizing throughput within the limit.
6. **Use `gather(return_exceptions=True)` and triage results** — one bad item must not abort the batch; report failed indices for reprocessing.
7. **Implement retry as a decorator** (`@retry_with_exponential_backoff()`) so the policy is declared once and applied to any request function.

## Architecture

```
character_requests.yaml (N requests)
  ▼
CLI (src/main.py)  -rf file -m model -p parallelism
  ▼
batch_request_gemini (src/service/request_llm.py)
  semaphore = asyncio.Semaphore(parallelism)
  tasks = [request_with_semaphore(req) for req in requests]
  results = await asyncio.gather(*tasks, return_exceptions=True)
        │ each task:
        ▼
  @retry_with_exponential_backoff()          ← retry policy as decorator
  request_gemini(...)                         ← structured output call
        │ wrapped in LLMOps logging (Chapter 2 Section 4's logger)
  ▼
outputs/gemini_<index>_<id>.json (per success) + failed-indices report
```

### Directory Structure

```
chapter_3/section_3/
├── character_requests.yaml        # batch input: gender/age/instructions per item
├── src/
│   ├── main.py                    # CLI: request file, model, parallelism, user, storage
│   ├── service/
│   │   ├── request_llm.py         # backoff/jitter/retry decorator + semaphore batch
│   │   ├── llmops_logger.py       # per-request structured logging (metadata/content split)
│   │   └── prompt_storage.py      # stored prompt content (by prompt_id)
│   ├── model/                     # model.py / llmops_log.py / prompt_data.py
│   ├── prompt/prompt.py
│   ├── client/llm_client.py       # Gemini client + model enum
│   └── config.py / logger.py
├── tests/test_request_llm.py      # backoff & retry-classification tests
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Backoff with jitter (`src/service/request_llm.py`)

```python
MAX_BACKOFF_SECONDS = 60
BASE_BACKOFF_SECONDS = 1
JITTER_MIN, JITTER_MAX = 0.1, 0.5
RETRYABLE_STATUS_CODES = {429, 500, 503, 502, 504}

def calculate_backoff_with_jitter(attempt: int, base: float = BASE_BACKOFF_SECONDS) -> float:
    backoff = min(base * (2**attempt), MAX_BACKOFF_SECONDS)
    jitter_range = backoff * (JITTER_MAX - JITTER_MIN)
    jitter = random.uniform(backoff * JITTER_MIN, backoff * JITTER_MIN + jitter_range)
    return backoff + jitter
```

### 2. Error classification

```python
def should_retry_error(error: Exception) -> tuple[bool, int | None]:
    if isinstance(error, google_exceptions.ResourceExhausted):        # 429
        return True, None
    if isinstance(error, (google_exceptions.ServiceUnavailable,       # 503
                          google_exceptions.InternalServerError,      # 500
                          google_exceptions.DeadlineExceeded)):       # timeout
        return True, None
    return False, None            # auth/validation → fail immediately
```

### 3. Retry policy as a decorator

```python
def retry_with_exponential_backoff(max_retries: int = MAX_RETRIES):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    should_retry, retry_after = should_retry_error(e)
                    if not should_retry or attempt == max_retries:
                        raise
                    backoff_time = retry_after if retry_after is not None \
                                   else calculate_backoff_with_jitter(attempt)
                    await asyncio.sleep(backoff_time)
        return wrapper
    return decorator

@retry_with_exponential_backoff()
async def request_gemini(character_request, model, llmops_logger, ...): ...
```

### 4. Semaphore-bounded batch with partial-failure triage

```python
semaphore = asyncio.Semaphore(parallelism)

async def request_with_semaphore(req: CharacterRequest) -> CharacterResponse:
    async with semaphore:
        return await request_gemini(character_request=req, model=model, ...)

results = await asyncio.gather(*(request_with_semaphore(r) for r in character_requests),
                               return_exceptions=True)
for i, result in enumerate(results):
    if isinstance(result, Exception):
        failed_requests.append(i)        # keep going; report indices at the end
```

## Data Models

| Model | Purpose |
|-------|---------|
| `CharacterRequest` / `CharacterResponse` | Batch item input/output |
| `LLMOpsLogEntry` / `PromptData` | Structured logging + prompt storage (see Chapter 2 Section 4) |

## Setup & Run

```bash
cp .envrc.example .envrc     # set GEMINI_API_KEY
uv sync

# Canonical example: 33-request batch, 2 concurrent
uv run python -m src.main -rf character_requests.yaml -m GEMINI_2_5_FLASH -p 2
```

### CLI Options

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--request-file` | `-rf` | Yes | — | YAML batch file (`requests:` list) |
| `--model` | `-m` | Yes | — | Gemini model enum name |
| `--parallelism` | `-p` | No | 5 | Max concurrent requests |
| `--user-id` | `-u` | No | `default_user` | For LLMOps logs |
| `--storage-type` | `-st` | No | `local` | Prompt storage backend |
| `--output-directory` | `-od` | No | `outputs` | Output directory |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
uv run pytest tests/ -v      # backoff math + retry classification (no API)
```

## Implementation Notes

- **Choosing parallelism**: start at (provider RPM limit × safety factor 0.5) ÷ (60 / average request seconds). Too high converts your own traffic into 429s that the retry layer then has to absorb — the semaphore is cheaper than the retry.
- **Why decorator + semaphore compose well**: the decorator handles *temporal* spreading of one request's retries; the semaphore handles *spatial* limiting across requests. Each retry re-acquires nothing — it holds its semaphore slot, guaranteeing in-flight count never exceeds `-p` even during retry storms.
- **`return_exceptions=True` semantics**: exceptions arrive as values, preserving index alignment with inputs — that's what makes "reprocess failed indices" trivial.
- **Client-side batch vs provider Batch API**: this pattern gives immediate results and full control at standard pricing; Chapter 2 Section 5's provider batch endpoints give 50% cost savings at multi-minute latency. Choose per workload.
- **Every request still flows through LLMOps logging** (Chapter 2 Section 4 pattern), so batch runs produce per-request latency/status records for analysis.

## How to Apply This Practice to Your Own Project

1. Copy `calculate_backoff_with_jitter`, `should_retry_error`, and the decorator; extend `should_retry_error` with your provider's exception types (OpenAI `RateLimitError`, Anthropic `APIStatusError` 5xx, httpx timeouts).
2. Decorate your request function — one line — and keep the function itself policy-free.
3. Wrap batch fan-out in a semaphore closure + `gather(return_exceptions=True)`; log failed indices and write a reprocessing path for them.
4. Honor `Retry-After` headers where your SDK exposes them.
5. Make `parallelism` a CLI/config knob and tune it against your actual rate-limit tier.
6. Keep per-request observability on — throughput problems are diagnosed from the per-request records, not the batch summary.
