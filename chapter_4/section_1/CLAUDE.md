# CQRS Knowledge Base Implementation

## Overview

This project implements the **CQRS (Command Query Responsibility Segregation)** pattern for LLM-based knowledge management systems. It separates write operations (Commands) from read operations (Queries), achieving high throughput for writes and low latency for reads.

The system uses Google Gemini for both character generation and embedding creation, with ChromaDB as the vector database for semantic search.

## Architecture

```
+-------------------------------------------------------------+
|                      User Requests                          |
+-------------------------------------------------------------+
              |                           |
              v                           v
+---------------------------+   +---------------------------+
|      LLM Server           |   |   Knowledge Server        |
|      Port 8000            |   |   Port 8001               |
|                           |   |                           |
|  POST /generate           |   |  POST /command/register   |
|   - Character generation  |   |   - Async write (Command) |
|   - Auto-store knowledge  |   |                           |
|                           |   |  POST /query/search       |
|                           |   |   - Sync read (Query)     |
|                           |   |                           |
|                           |   |  GET /query/stats         |
|                           |   |   - Statistics (Query)    |
+-------------+-------------+   +-------------+-------------+
              |                               |
              +---------------+---------------+
                              |
                              v
              +-------------------------------+
              |          ChromaDB             |
              |       Vector Database         |
              |                               |
              |  - Cosine similarity search   |
              |  - Custom Gemini embeddings   |
              |  - Metadata filtering         |
              +---------------+---------------+
                              |
                              v
              +-------------------------------+
              |        Gemini API             |
              |  - gemini-2.5-pro/flash/lite  |
              |  - gemini-3.5-flash           |
              |  - gemini-3.1-flash-lite      |
              |  - gemini-embedding-001       |
              +-------------------------------+
```

### Directory Structure

```
src/
|-- __init__.py              # Package init, shared ThreadPoolExecutor
|-- config.py                # Configuration (GEMINI_API_KEY)
|-- logger.py                # Logging utility
|-- api/
|   |-- __init__.py
|   |-- llm_server.py        # LLM API server (Port 8000)
|   +-- knowledge_server.py  # CQRS API server (Port 8001)
|-- client/
|   |-- __init__.py
|   |-- llm_client.py        # Gemini API client
|   +-- chromadb_client.py   # ChromaDB client (local/remote)
|-- model/
|   |-- __init__.py
|   |-- model.py             # LLM data models (FrozenModel base)
|   +-- knowledge.py         # CQRS models (Command/Query)
|-- service/
|   |-- __init__.py
|   |-- request_llm.py       # Gemini LLM request handler
|   |-- embedding_service.py # Gemini embedding service
|   |-- knowledge_command.py # Command service (async writes)
|   +-- knowledge_query.py   # Query service (sync reads)
+-- prompt/
    |-- __init__.py
    +-- prompt.py            # Prompt generation
```

## Key Components

### CQRS Services

| Component | File | Purpose |
|-----------|------|---------|
| Command Service | `src/service/knowledge_command.py` | Async knowledge registration |
| Query Service | `src/service/knowledge_query.py` | Sync knowledge search |
| Embedding Service | `src/service/embedding_service.py` | Gemini embedding generation |

### Data Models

| Model | File | Purpose |
|-------|------|---------|
| `FrozenModel` | `src/model/model.py` | Base Pydantic model with frozen config |
| `KnowledgeRegisterCommand` | `src/model/knowledge.py` | Command input model |
| `KnowledgeSearchQuery` | `src/model/knowledge.py` | Query input model |
| `KnowledgeSearchResponse` | `src/model/knowledge.py` | Query response with results |

### API Servers

| Server | Port | Endpoints |
|--------|------|-----------|
| LLM Server | 8000 | `GET /health`, `POST /generate` |
| Knowledge Server | 8001 | `GET /health`, `POST /command/register`, `POST /query/search`, `GET /query/stats` |

## Dependencies

```toml
[dependencies]
chromadb = ">=1.3.0"
fastapi = ">=0.119.0"
google-genai = ">=1.45.0"
pydantic = ">=2.12.2"
uvicorn = ">=0.37.0"
```

## Usage

### Setup

1. Set environment variable:
```bash
export GEMINI_API_KEY="your-api-key"
```

2. Install dependencies:
```bash
uv sync
```

### Run

**Local Development:**
```bash
# Terminal 1: LLM Server
uv run python -m src.api.llm_server

# Terminal 2: Knowledge Server
uv run python -m src.api.knowledge_server
```

**Docker Compose:**
```bash
docker-compose up -d
```

### API Examples

**Generate Character:**
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash",
    "character_request": {
      "gender": "female",
      "age": 25,
      "additional_instructions": "brave warrior"
    }
  }'
```

**Search Knowledge:**
```bash
curl -X POST http://localhost:8001/query/search \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "brave warrior",
    "limit": 5
  }'
```

**Get Statistics:**
```bash
curl http://localhost:8001/query/stats
```

### Available Gemini Models

| Model | Use Case |
|-------|----------|
| `gemini-2.5-pro` | High quality generation |
| `gemini-2.5-flash` | Balanced speed/quality |
| `gemini-2.5-flash-lite` | Fastest generation |
| `gemini-3.5-flash` | Next-gen balanced |
| `gemini-3.1-flash-lite` | Next-gen fast generation |

## Development Commands

```bash
# Install dependencies
uv sync

# Run LLM server
uv run python -m src.api.llm_server

# Run Knowledge server
uv run python -m src.api.knowledge_server

# Syntax check all files
python -m py_compile src/**/*.py

# Docker operations
docker-compose up -d      # Start all services
docker-compose ps         # Check status
docker-compose logs -f    # View logs
docker-compose down       # Stop all services
```

## Implementation Notes

### CQRS Pattern

- **Command (Write)**: Async processing via `asyncio.create_task()`, returns job ID immediately
- **Query (Read)**: Sync processing, optimized for low latency (<300ms)
- **Eventual Consistency**: 2-5 second delay between write and read availability

### Embedding Configuration

- Model: `gemini-embedding-001`
- Dimensions: 768
- Distance Metric: Cosine similarity

### ChromaDB Modes

- **Local Mode**: Uses `./data/chromadb` when `CHROMA_HOST` is not set
- **Remote Mode**: Connects via HTTP when `CHROMA_HOST` and `CHROMA_PORT` are set

### Shared Resources

- `src/__init__.py` contains shared `ThreadPoolExecutor(max_workers=4)`
- Used by both Command and Query services for blocking ChromaDB operations

### Error Handling

- All API endpoints return appropriate HTTP status codes
- Background tasks log errors without crashing the main server
- ChromaDB operations wrapped in try-except blocks

### Performance Characteristics

| Operation | Latency |
|-----------|---------|
| Character Generation | 1-2 seconds |
| Background Storage | +2-5 seconds |
| Query Search | 100-300 ms |
| Stats Retrieval | 50-100 ms |
