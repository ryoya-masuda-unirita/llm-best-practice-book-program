# Chapter 2 Section 4: Structured Logging for LLMOps

## What This Section Demonstrates

This section implements a **dual-layer structured logging architecture for LLM operations**. Traditional logging fails for LLM apps: prompts/responses are too long for log streams, unstructured text can't be aggregated, and sensitive prompt content needs special handling.

The practice separates the two concerns:
- **Metadata layer** — one machine-readable JSON log line per request (`LLMOpsLogEntry`): request ID, prompt ID, model, latency, status, user, level. Small, aggregatable, greppable.
- **Content layer** — the full prompt/response stored separately (`PromptStorage`, date-partitioned files), referenced from the log line by `prompt_id`.

Apply this to any LLM feature that runs in production: it gives you request traceability (`request_id`), cost/latency dashboards from JSON logs, and post-hoc debugging (fetch the exact prompt by `prompt_id`) without bloating your log pipeline.

## Practice Rules

1. **Never log prompt/response bodies into the log stream.** Log a `prompt_id` reference; store the content in a dedicated store keyed by that ID.
2. **Emit one structured JSON log entry per LLM request** with at minimum: `timestamp` (UTC ISO 8601), `request_id`, `prompt_id`, `model`, `latency_ms`, `status_code`, `level`, and optional `user_id` / `error_message` / `metadata`.
3. **Wrap every LLM call in a tracking context manager** (`track_llm_request`) that measures latency, catches exceptions, sets the status/level, and always logs in `finally` — success and failure paths share one code path.
4. **Define the log entry as a Pydantic model**, not a dict — field constraints (`ge=0.0`) and `exclude_none=True` serialization keep entries clean and consistent.
5. **Abstract the content store behind an interface** (`PromptStorage` ABC with `save_prompt` / `retrieve_prompt`) so local files can be swapped for S3/GCS/DB without touching call sites. Construct via factory (`get_prompt_storage(storage_type)`).
6. **Partition stored prompts by date** (`prompt_storage/YYYY/MM/DD/<prompt_id>.json`) for retention policies and fast lookup.
7. **Store prompts asynchronously** so logging never adds user-visible latency; support sensitive-data masking at save time (`mask_sensitive=True`).

## Architecture

```
CLI (src/main.py)
  ▼
async with llmops_logger.track_llm_request(model=..., prompt_content=...) as tracking:
    response = await request_llm(...)        # any provider call
    tracking["response"] = response
  │
  ├── on exit (finally):
  │     latency measured, status/level decided
  │     ├── PromptStorage.save_prompt(PromptData)   → prompt_storage/YYYY/MM/DD/<prompt_id>.json
  │     └── logger emits LLMOpsLogEntry.to_json_string()  → stdout/log pipeline
  ▼
outputs/<provider>_<uuid>.json  (the actual app output)
```

### Directory Structure

```
chapter_2/section_4/
├── src/
│   ├── main.py                    # CLI (Click, async) — provider/model/user/storage options
│   ├── config.py / logger.py
│   ├── client/llm_client.py       # LLMProvider + OpenAI/Gemini/Anthropic model enums & clients
│   ├── model/
│   │   ├── llmops_log.py          # LLMOpsLogEntry, LogLevel, StorageType
│   │   ├── prompt_data.py         # PromptData (stored content record)
│   │   └── model.py               # CharacterResponse (the demo task's output schema)
│   ├── prompt/prompt.py
│   └── service/
│       ├── llmops_logger.py       # LLMOpsLogger + track_llm_request + factory
│       ├── prompt_storage.py      # PromptStorage ABC, LocalFilePromptStorage, factory
│       └── request_llm.py         # per-provider request functions
├── tests/                         # pytest: log entry, logger, storage
├── prompt_storage/                # date-partitioned stored prompts (runtime)
├── outputs/
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. The tracking context manager (`src/service/llmops_logger.py`)

```python
@asynccontextmanager
async def track_llm_request(self, model, prompt_content, ...) -> AsyncGenerator[dict, None]:
    request_id = request_id or str(uuid4())
    prompt_id = prompt_id or str(uuid4())
    tracking = {"request_id": request_id, "prompt_id": prompt_id, "response": None, "error": None}

    start_time = time.time()
    try:
        yield tracking
        status_code = 200
    except Exception as e:
        error_message, status_code, level = str(e), 500, LogLevel.ERROR
        raise
    finally:
        latency_ms = (time.time() - start_time) * 1000
        await self.log_llm_request(request_id=request_id, prompt_id=prompt_id, model=model,
                                   latency_ms=latency_ms, status_code=status_code, ...)
```

Callers put the response into `tracking["response"]`; logging happens in `finally`, so failures are logged with the same fidelity as successes.

### 2. Metadata/content separation (`src/model/llmops_log.py`, `src/model/prompt_data.py`)

```python
class LLMOpsLogEntry(BaseModel):        # goes to the log stream
    timestamp: str                       # UTC ISO 8601, default_factory
    request_id: str
    prompt_id: str                       # ← the join key
    model: str
    latency_ms: Optional[float] = Field(None, ge=0.0)
    status_code: Optional[int]
    level: LogLevel = LogLevel.INFO
    metadata: Optional[dict[str, Any]]

class PromptData(BaseModel):             # goes to the prompt store
    prompt_id: str                       # ← same join key
    prompt_content: Any
    response_content: Optional[Any]
```

### 3. Swappable storage backend (`src/service/prompt_storage.py`)

```python
class PromptStorage(ABC):
    @abstractmethod
    async def save_prompt(self, prompt_data: PromptData, mask_sensitive: bool = True) -> str: ...
    @abstractmethod
    async def retrieve_prompt(self, prompt_id: str) -> Optional[PromptData]: ...

class LocalFilePromptStorage(PromptStorage):
    def _get_storage_path(self, prompt_id, date=None) -> Path:
        # prompt_storage/2026/07/04/<prompt_id>.json  — date-partitioned
```

`get_prompt_storage(StorageType.LOCAL)` is the only place that knows concrete classes.

### 4. Emitting the JSON log line

```python
def to_json_string(self) -> str:
    return json.dumps(self.model_dump(exclude_none=True), ensure_ascii=False)
```

Example emitted line:

```json
{"timestamp": "2026-07-04T22:16:48+00:00", "request_id": "c027…", "prompt_id": "544c…",
 "user_id": "default_user", "model": "global.anthropic.claude-haiku-4-5-20251001-v1:0", "latency_ms": 2522.0,
 "status_code": 200, "level": "INFO", "metadata": {"provider": "gemini", "response_format": "CharacterResponse"}}
```

## Data Models

| Model | Purpose |
|-------|---------|
| `LLMOpsLogEntry` | Structured per-request log record (metadata only) |
| `PromptData` | Stored content record: prompt + response + metadata, keyed by `prompt_id` |
| `LogLevel` | `INFO` / `DEBUG` / `ERROR` / `WARNING` |
| `StorageType` | Storage backend selector (currently `local`) |
| `CharacterResponse` | Demo task output schema (character generation) |

## Setup & Run

```bash
cp .envrc.example .envrc     # OPENAI_API_KEY / GEMINI_API_KEY / ANTHROPIC_API_KEY
uv sync

# Canonical example
uv run python -m src.main -lp ANTHROPIC -m CLAUDE_HAIKU_4_5

# With user attribution and explicit storage type
uv run python -m src.main -lp ANTHROPIC -m CLAUDE_SONNET_4_6 -u user123 -st local -od ./outputs
```

### CLI Options

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--llm-provider` | `-lp` | Yes | `gemini` | `OPENAI` / `GEMINI` / `ANTHROPIC` |
| `--model` | `-m` | Yes | — | Model enum name for the chosen provider |
| `--output-directory` | `-od` | No | `outputs` | Directory for app output files |
| `--user-id` | `-u` | No | `default_user` | User ID recorded in log entries |
| `--storage-type` | `-st` | No | `local` | Prompt storage backend |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy

# Tests (log entry, logger, storage)
uv run pytest tests/ -v
```

## Implementation Notes

- **Why a context manager, not decorators or manual calls**: the `finally` block guarantees a log entry even when the provider call raises, and latency measurement brackets exactly the user-perceived call.
- **`request_id` vs `prompt_id`**: `request_id` traces one end-to-end request (join across services); `prompt_id` locates content in the store. Keep both — a retried request may reuse a prompt.
- **Debugging flow**: user reports issue with `request_id` → grep JSON logs for the entry → take its `prompt_id` → `retrieve_prompt(prompt_id)` → replay the exact prompt.
- **Masking is a storage concern** (`mask_sensitive=True` on `save_prompt`), not a logging concern — the log stream never sees content at all.
- **Tests** stub the storage layer; run them to see the expected contract for custom backends (S3, DB) before writing one.

## How to Apply This Practice to Your Own Project

1. Copy `llmops_log.py` (log entry model) and `prompt_storage.py` (ABC + local impl + factory); adjust fields to your telemetry needs (add `cost_usd`, `input_tokens`, `output_tokens` if you have them).
2. Instantiate one `LLMOpsLogger` per process via `create_llmops_logger()` and wrap every provider call in `track_llm_request(...)`.
3. Put the provider response into `tracking["response"]` inside the block — that's what gets persisted with the prompt.
4. Ship the JSON lines to your log pipeline (CloudWatch/Datadog/BigQuery); build dashboards on `model`, `latency_ms`, `status_code`, `level`.
5. Implement a production `PromptStorage` (object storage with lifecycle rules) behind the existing ABC; select it via the factory.
6. Define a retention/masking policy for stored prompts before launch — that's where the sensitive data lives.
