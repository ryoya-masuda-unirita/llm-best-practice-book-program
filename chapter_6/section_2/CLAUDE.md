# Chapter 6 Section 2: Thin Wrapper Library for LLM SDKs — Transparent Observability

## What This Section Demonstrates

This section wraps the official OpenAI, Gemini, and Anthropic SDKs in a **thin, transparent proxy layer** that records every call (request parameters, token usage, latency) to JSON log files — *without changing the SDK's interface*. Application code keeps writing `client.messages.create(...)` / `client.chat.completions.parse(...)` exactly as documented; the wrapper intercepts the methods it cares about and delegates everything else via `__getattr__`.

The practice targets a real adoption problem: teams already using SDKs directly can't afford a rewrite to gain observability. A drop-in wrapper client (`AnthropicWrapperClient`, `OpenAIWrapperClient`, `GenAIWrapperClient`) delivers usage tracking, cost attribution, and performance measurement with a one-line constructor swap. Contrast with the adapter pattern (Chapter 3 Section 1), which unifies interfaces at the cost of adopting a new one.

## Practice Rules

1. **Preserve the SDK interface exactly.** Wrap only the namespaces you instrument (`messages`, `chat.completions`, `models`); forward every other attribute with `def __getattr__(self, name): return getattr(self._inner, name)`.
2. **Intercept at the method level**: wrapped `create`/`parse`/`count_tokens` record start time → delegate to the real SDK → log metadata → return the untouched response.
3. **Log requests and usage defensively** — read response fields with `getattr(..., None)` / `hasattr` so SDK version bumps degrade logs, not calls.
4. **Capture full cost telemetry**: input/output tokens, cache-related token counts (`cache_creation_input_tokens`, `cache_read_input_tokens`), duration_ms, model, and request parameters.
5. **Wrap sync and async variants both** (`MessagesWrapper` / `AsyncMessagesWrapper`, `ModelsWrapper` / `AsyncModelsWrapper`) — real apps use both.
6. **Wrap nested/beta namespaces you actually use** (`BetaMessagesWrapper`, Gemini `AioWrapper`) — coverage should follow usage, not SDK completeness.
7. **Write logs as JSON files in a configured directory** (`config.usage_log_directory`) — a stand-in for your log pipeline; one file per call keeps writes atomic.

## Architecture

```
Application code (unchanged SDK usage)
   │  client.messages.create(...)          ← same call as with the raw SDK
   ▼
AnthropicWrapperClient / OpenAIWrapperClient / GenAIWrapperClient
   ├─ instrumented namespaces: MessagesWrapper / ChatCompletionsWrapper / ModelsWrapper
   │     start_time → delegate → _log_usage() → return response
   └─ everything else: __getattr__ → original SDK object
   ▼
Official SDK → Provider API

usage_logs/*.json   ← timestamp, method, duration_ms, request params, token usage
```

### Directory Structure

```
chapter_6/section_2/
├── src/
│   ├── client/
│   │   ├── anthropic_wrapper_client.py  # Messages/AsyncMessages/BetaMessages wrappers
│   │   ├── openai_wrapper_client.py     # ChatCompletions wrappers
│   │   ├── gemini_wrapper_client.py     # Models/AsyncModels/Aio wrappers (subclasses genai.Client)
│   │   └── llm_client.py                # provider/model enums + wrapper client instances
│   ├── service/request_llm.py           # normal SDK-style calls through the wrappers
│   ├── model/model.py / prompt/prompt.py
│   ├── main.py                          # CLI demo (character generation)
│   └── config.py / logger.py            # incl. usage_log_directory
├── tests/test_wrapper_client.py
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Intercept-and-delegate (`src/client/anthropic_wrapper_client.py`)

```python
class MessagesWrapper:
    def __init__(self, messages, log_dir: str = config.usage_log_directory):
        self._messages = messages

    def create(self, *args, **kwargs):
        start_time = datetime.now()
        response = self._messages.create(*args, **kwargs)   # delegate to the real SDK
        self._log_usage(method="messages.create", args=args, kwargs=kwargs,
                        response=response, start_time=start_time)
        return response                                      # untouched response

    def __getattr__(self, name):
        return getattr(self._messages, name)                 # everything else passes through
```

### 2. Defensive telemetry extraction

```python
usage_info = {}
if hasattr(response, "usage") and response.usage:
    usage_info = {
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
        "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", None),
        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", None),
    }
```

New/renamed SDK fields yield `None`s in logs — never broken requests.

### 3. Subclass where the SDK supports it (`src/client/gemini_wrapper_client.py`)

```python
class GenAIWrapperClient(genai.Client):
    def __init__(self, *args, log_dir=config.usage_log_directory, **kwargs):
        super().__init__(*args, **kwargs)
        # replace .models / .aio with instrumented wrappers
    def __getattr__(self, name): ...
```

### 4. Zero-diff adoption (`src/service/request_llm.py`)

Service code is written exactly as against raw SDKs — `await anthropic_client.beta.messages.parse(...)` etc. Only the client construction site knows about wrappers.

## Data Models

| Item | Purpose |
|------|---------|
| `LLMProvider` / `OpenAIModel` / `GeminiModel` / `AnthropicModel` | Enums (Anthropic: claude-opus-4-7, claude-sonnet-4-6, claude-haiku-4-5, claude-sonnet-5, claude-opus-4-8) |
| `CharacterResponse` | Demo task structured output |
| usage log JSON | timestamp, method, duration_ms, request params, usage tokens per call |

## Setup & Run

```bash
cp .envrc.example .envrc     # OPENAI_API_KEY / GEMINI_API_KEY / ANTHROPIC_API_KEY
uv sync

# Canonical example (Anthropic through the wrapper)
uv run python -m src.main -lp ANTHROPIC -m CLAUDE_SONNET_4_6

# Then inspect the captured telemetry
ls usage_logs/
```

### CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--llm-provider` | `-lp` | `OPENAI` / `GEMINI` / `ANTHROPIC` |
| `--model` | `-m` | Model enum name |
| `--output-directory` | `-od` | Output directory |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
uv run pytest tests/ -v      # wrapper delegation + logging tests
```

## Implementation Notes

- **Wrapper vs adapter**: the wrapper keeps each SDK's native interface (zero migration, provider-specific features intact); the adapter (Chapter 3 Section 1) unifies interfaces (portability, but a new API to adopt). Wrappers suit brownfield observability; adapters suit greenfield multi-provider design. They compose: wrap the SDKs, then adapt the wrappers.
- **`__getattr__` is the load-bearing trick** — it makes the wrapper future-proof: SDK methods you didn't wrap keep working, so upgrading the SDK never blocks on the wrapper.
- **Logging must never break the call**: telemetry extraction uses defensive access, and log-write failures should be caught and logged, not raised into application code.
- **Streaming caveat**: wrapping `create(stream=True)` requires wrapping the returned iterator to capture usage at stream end — the current implementation logs the non-streaming path; extend the wrapper if you stream.
- **File-per-call JSON logs** are the demo sink; in production point `_log_usage` at your structured-logging pipeline (the Chapter 2 Section 4 logger slots in directly).

## How to Apply This Practice to Your Own Project

1. Identify the SDK namespaces your code actually calls (`messages`, `chat.completions`, …) and write one wrapper class per namespace with intercepted hot methods + `__getattr__` passthrough.
2. Swap client construction to the wrapper class — grep shows this is typically 1–3 lines per codebase.
3. Extract telemetry defensively; include token usage, cache tokens, duration, model, and enough request params for cost attribution.
4. Route logs to your real pipeline instead of files once validated; add department/team tags at the constructor.
5. Add wrapper tests that assert delegation (unwrapped methods still work) and log content (wrapped methods record correctly).
6. Revisit coverage when adopting new SDK features (streaming, batches) — wrap them the day you start using them.
