# Chapter 4 Section 1: CQRS for an LLM Knowledge Base

## What This Section Demonstrates

This section applies **CQRS (Command Query Responsibility Segregation)** to an LLM-backed knowledge base with a vector database. Writes (registering generated knowledge, which require embedding computation) and reads (semantic search) have opposite performance profiles, so they are split:

- **Command side** — `POST /command/register` accepts a write, returns a `job_id` immediately, and computes the embedding + stores into ChromaDB in a background task (async, high-throughput, eventually consistent).
- **Query side** — `POST /query/search` embeds the query and runs a synchronous vector search optimized for low latency; `GET /query/stats` reports collection statistics.

An LLM server (`/generate`, Gemini character generation) demonstrates the producer side: generated content is auto-registered as knowledge. Apply CQRS when your LLM system both ingests content (slow, embedding-heavy) and serves search (fast), and you don't want ingestion spikes to degrade query latency.

## Practice Rules

1. **Separate command and query code paths entirely** — different service modules (`knowledge_command.py` / `knowledge_query.py`), different endpoints, independently tunable.
2. **Commands return immediately with a `job_id`**; the actual embedding + store runs via `asyncio.create_task`. Never make a writer wait for vector indexing.
3. **Be explicit about eventual consistency** — written knowledge becomes searchable seconds later; document it and provide a sync variant (`register_knowledge_sync`) for tests/consistency-critical paths.
4. **Build the embedding text deliberately** (`_generate_embedding_text` concatenates the salient fields) — what you embed defines what search can find.
5. **Use one embedding model for both write and query sides** (`gemini-embedding-001`, cosine distance) — mixed embedding models silently break retrieval.
6. **Wrap blocking vector-DB calls in a shared `ThreadPoolExecutor`** so the async servers never block the event loop.
7. **Type both sides' contracts** as Pydantic models (`KnowledgeRegisterCommand` vs `KnowledgeSearchQuery` etc.) — command and query models evolve independently; don't share one "Knowledge" DTO.

## Architecture

```
             User / LLM apps
        ┌──────────┴─────────────┐
        ▼                        ▼
LLM Server (:8000)        Knowledge Server (:8001)
  POST /generate            POST /command/register   [Command: async write]
  (Gemini generation,       POST /query/search       [Query: sync read]
   auto-registers            GET  /query/stats        [Query]
   generated knowledge)          │
        │                        │
        ▼                        ▼
   knowledge_command.py     knowledge_query.py
   embed → job_id now,      embed query → ChromaDB
   store via create_task    similarity search
        └──────────┬─────────────┘
                   ▼
           ChromaDB (:8002→8000)   gemini-embedding-001 / cosine / 768-dim
```

### Directory Structure

```
chapter_4/section_1/
├── src/
│   ├── api/
│   │   ├── llm_server.py          # /generate (+ auto knowledge registration)
│   │   └── knowledge_server.py    # /command/register, /query/search, /query/stats
│   ├── service/
│   │   ├── knowledge_command.py   # async/sync registration (Command side)
│   │   ├── knowledge_query.py     # search + stats (Query side)
│   │   ├── embedding_service.py   # gemini-embedding-001 wrapper
│   │   └── request_llm.py         # Gemini generation
│   ├── client/
│   │   ├── chromadb_client.py     # local / remote (CHROMA_HOST) modes
│   │   └── llm_client.py
│   ├── model/knowledge.py         # command/query request-response models
│   ├── model/model.py / prompt/prompt.py / config.py / logger.py
│   └── __init__.py                # shared ThreadPoolExecutor(max_workers=4)
├── docker-compose.yml             # chromadb:8002 / llm-server:8000 / knowledge-server:8001
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Fire-and-return command (`src/service/knowledge_command.py`)

```python
async def register_knowledge_async(command: KnowledgeRegisterCommand) -> str:
    job_id = str(uuid.uuid4())
    asyncio.create_task(_store_in_chromadb_async(command, job_id))   # background
    return job_id                                                     # immediate ack

async def register_knowledge_sync(command: KnowledgeRegisterCommand) -> str:
    job_id = str(uuid.uuid4())
    await _store_in_chromadb_async(command, job_id)                   # for tests / strict consistency
    return job_id
```

### 2. Deliberate embedding text construction

```python
def _generate_embedding_text(command: KnowledgeRegisterCommand) -> str:
    # concatenates name/attributes/description into the string that gets embedded —
    # this string IS the search surface
```

### 3. Low-latency query path (`src/service/knowledge_query.py`)

```python
async def search_knowledge(query: KnowledgeSearchQuery) -> KnowledgeSearchResponse:
    query_embedding = await get_embedding(query.query)
    results = _search_chromadb(query_embedding, query)     # top-k cosine search
    return KnowledgeSearchResponse(items=_parse_search_results(results), ...)
```

### 4. One embedding function for both sides (`src/service/embedding_service.py`)

```python
GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"

async def get_embedding(text: str) -> list[float]:
    # runs _get_gemini_embedding_sync in the shared ThreadPoolExecutor
```

## Data Models

| Model | Purpose |
|-------|---------|
| `KnowledgeRegisterCommand` / `KnowledgeRegisterResponse` | Write contract: content + metadata → job_id |
| `KnowledgeSearchQuery` / `KnowledgeSearchResponse` / `KnowledgeItem` | Read contract: query + top_k → ranked items with distances |
| `KnowledgeStatsQuery` / `KnowledgeStatsResponse` | Collection statistics |

## Setup & Run

```bash
cp .envrc.example .envrc     # set GEMINI_API_KEY

# Canonical (docker: chromadb + llm-server + knowledge-server)
make docker-build && make docker-up
curl -s http://localhost:8000/health
make docker-down

# Write (returns job_id immediately)
curl -X POST http://localhost:8001/command/register -H "Content-Type: application/json" \
  -d '{"name": "...", "description": "...", ...}'

# Read (seconds later — eventual consistency)
curl -X POST http://localhost:8001/query/search -H "Content-Type: application/json" \
  -d '{"query": "brave knight", "top_k": 3}'
curl -s http://localhost:8001/query/stats
```

ChromaDB runs remote via `CHROMA_HOST`/`CHROMA_PORT` in docker; without them, the client falls back to local mode (`./data/chromadb`).

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
make docker-build / make docker-up / make docker-down / make docker-logs
```

## Implementation Notes

- **Why CQRS here**: embedding computation makes writes much slower than reads. Coupling them means ingestion bursts inflate search P99. Splitting lets you scale the query path (stateless, CPU-light) separately from the command path (embedding-bound).
- **Eventual consistency window** is embedding time + index update (~2–5s here). Surface `job_id` so callers can build "is it indexed yet?" checks if needed.
- **`asyncio.create_task` is the minimal async-write implementation** — sufficient for a single process. For durability across restarts, replace it with a real queue (the Redis worker pattern from Chapter 2 Section 5) without touching the API contract.
- **The shared `ThreadPoolExecutor` (in `src/__init__.py`)** exists because ChromaDB and the embedding SDK expose blocking calls; both sides funnel through it to keep FastAPI's event loop responsive.
- **The LLM server auto-registering its outputs** shows the natural producer integration: generation results become searchable knowledge with no extra client work.

## How to Apply This Practice to Your Own Project

1. Split your knowledge service into `*_command.py` and `*_query.py` modules with separate Pydantic contracts before optimizing anything.
2. Make writes acknowledge with a job identifier and move embedding+indexing off the request path.
3. Define `_generate_embedding_text` for your domain deliberately — include the fields users search by, exclude noise.
4. Pin one embedding model + distance metric in one module; never let the two sides drift.
5. State your consistency window in the API docs; add a sync write variant for tests.
6. When write volume grows, swap `create_task` for a durable queue + worker; when read volume grows, replicate the query service — the split makes both moves independent.
