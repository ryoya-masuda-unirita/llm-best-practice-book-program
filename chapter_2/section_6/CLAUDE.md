# Chapter 2 Section 6: Streaming LLM Responses over HTTP (SSE with FastAPI)

## What This Section Demonstrates

This section shows how to **relay LLM streaming output to HTTP clients** so users see tokens as they are generated instead of waiting for the full completion. The server exposes two endpoints over the same request model — `/stream` (Server-Sent Events style chunked response) and `/completions` (blocking, for comparison) — and an async client consumes the stream chunk by chunk.

Apply this practice to any user-facing generation feature (chat, drafting, summarization): perceived latency drops from "seconds until anything appears" to "first token in well under a second", and long generations stop hitting client/proxy timeouts.

## Practice Rules

1. **Wrap the provider's streaming API in an async generator** (`AsyncIterator[str]`) that yields plain text chunks. This is the seam between provider SDK and web framework.
2. **Return `StreamingResponse` with `media_type="text/event-stream"`** and disable buffering along the path: `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no` (the last one stops nginx-style proxies from batching chunks).
3. **Keep a non-streaming endpoint alongside** the streaming one, sharing the same request model — batch/tool callers don't want SSE.
4. **Handle errors inside the generator**: once streaming starts you can no longer change the HTTP status, so yield an error marker (`data: [ERROR] ...`) into the stream and log server-side.
5. **Consume with an async HTTP client** (`aiohttp` here), iterating `response.content.iter_any()` and flushing each chunk to the display immediately.
6. **Validate requests with a Pydantic model** (`StreamRequest`: prompt with `min_length=1`, provider enum, optional model) before starting any stream.

## Architecture

```
example_client.py (aiohttp)
  │ POST /stream {prompt, provider, model?}
  ▼
FastAPI app (src/api/app.py)
  ├─ /stream      → StreamingResponse(stream_openai_response(...), text/event-stream)
  ├─ /completions → await get_openai_response(...)   (blocking, same request model)
  └─ /health
        ▼
Streaming service (src/service/streaming_service.py)
  stream_openai_response(): openai chat.completions.create(stream=True)
  → async for chunk → yield delta.content
```

### Directory Structure

```
chapter_2/section_6/
├── run_server.py              # uvicorn launcher (host/port/reload options)
├── example_client.py          # async client: stream & completion modes (Click CLI)
├── src/
│   ├── api/app.py             # FastAPI app: /stream, /completions, /health
│   ├── service/streaming_service.py  # async generator + non-streaming call
│   ├── client/llm_client.py   # OpenAIModel enum + async client
│   ├── model/model.py         # StreamRequest / CompletionResponse / HealthResponse
│   └── config.py / logger.py
├── tests/                     # test_api / test_models / test_streaming_service
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Async generator over the provider stream (`src/service/streaming_service.py`)

```python
async def stream_openai_response(prompt: str, model: str = OpenAIModel.GPT_5_4_MINI) -> AsyncIterator[str]:
    try:
        stream = await openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        logger.error(f"Error in OpenAI streaming: {e}")
        yield f"data: [ERROR] {str(e)}\n\n"     # error must go INTO the stream
```

### 2. StreamingResponse with anti-buffering headers (`src/api/app.py`)

```python
@app.post("/stream")
async def stream_response(request: StreamRequest):
    return StreamingResponse(
        stream_openai_response(request.prompt, model=request.model or OpenAIModel.GPT_5_4_MINI),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

### 3. Blocking twin endpoint for non-interactive callers (`src/api/app.py`)

```python
@app.post("/completions", response_model=CompletionResponse)
async def get_completion(request: StreamRequest):
    content = await get_openai_response(request.prompt, model=model)
    return CompletionResponse(content=content, model=str(model), provider="openai")
```

### 4. Chunk-by-chunk client consumption (`example_client.py`)

```python
async with aiohttp.ClientSession() as session:
    async with session.post(url, json=payload) as response:
        async for chunk in response.content.iter_any():
            if chunk:
                print(chunk.decode("utf-8"), end="", flush=True)   # flush per chunk
```

## Data Models

| Model | Purpose |
|-------|---------|
| `StreamRequest` | prompt (`min_length=1`), provider enum, optional `OpenAIModel` — shared by both endpoints |
| `CompletionResponse` | Non-streaming result: content, model, provider |
| `HealthResponse` | `/health` payload |

## Setup & Run

```bash
cp .envrc.example .envrc     # set OPENAI_API_KEY
uv sync

# Terminal 1: server
uv run python run_server.py            # default 127.0.0.1:8000

# Terminal 2: client
uv run python example_client.py --prompt 'こんにちは'                    # streaming (default)
uv run python example_client.py --prompt 'こんにちは' --mode completion  # blocking comparison
```

### example_client.py Options

| Option | Default | Description |
|--------|---------|-------------|
| `--prompt` | — | User prompt (required) |
| `--mode` | `stream` | `stream` (SSE) or `completion` (blocking) |
| `--model` | server default (`GPT_5_4_MINI`) | Model override |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
uv run pytest tests/ -v      # API, model, and streaming-service tests
```

## Implementation Notes

- **Status codes vs streams**: HTTP status is committed when the first chunk is sent. Validation errors (bad provider, empty prompt) are raised *before* returning `StreamingResponse` so clients still get 4xx; mid-stream provider failures degrade to in-band error text.
- **`X-Accel-Buffering: no` matters in real deployments** — without it, nginx/ALB-style intermediaries buffer the response and users see nothing until completion, silently defeating streaming.
- **The service layer knows nothing about HTTP.** `stream_openai_response` yields plain strings; the same generator could feed a WebSocket, gRPC stream, or CLI without change.
- **Test strategy** (`tests/`): the streaming service is tested by collecting the generator's chunks; the API is tested with FastAPI's test client, asserting content type and chunked delivery.
- **Extending to other providers**: add a `stream_<provider>_response` generator with the same signature and branch on `request.provider` — the endpoint shape doesn't change.

## How to Apply This Practice to Your Own Project

1. Write the async-generator wrapper for your provider's `stream=True` API first; test it standalone.
2. Expose it via `StreamingResponse` with the three anti-buffering headers; keep validation before the stream starts.
3. Provide the blocking twin endpoint from the same request model for programmatic consumers.
4. Define an in-band error convention (`[ERROR] ...` marker or SSE `event: error`) and make clients detect it.
5. Verify end-to-end through your real proxy/load-balancer chain — buffering bugs only appear there.
6. For chat UIs, accumulate chunks client-side into the transcript as they render; keep the raw text exactly as received.
