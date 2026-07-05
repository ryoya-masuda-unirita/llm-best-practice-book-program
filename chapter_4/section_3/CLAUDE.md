# Chapter 4 Section 3: Component-Based RAG with the Strategy Pattern

## What This Section Demonstrates

A RAG system is a pipeline of distinct steps — load → chunk → embed → store → retrieve → generate. This section implements each step as a **swappable component behind one generic interface** (`Component[InputType, OutputType]` with a single `async process()` method), composed by a thin `RAGPipeline` orchestrator.

The payoff of the Strategy pattern here: any stage can be replaced without touching the others (semantic chunking → fixed-size chunking, in-memory vector store → ChromaDB, Gemini → another provider), each stage is testable in isolation, and the pipeline itself is just composition code. Apply this to any multi-stage LLM workflow — RAG is the canonical example, but the decomposition works for any load/transform/generate chain.

## Practice Rules

1. **Define one generic component interface** — `Component[InputType, OutputType]` with `async process(input_data) -> output` — and make every pipeline stage implement it. Types document the pipeline contract.
2. **Chain components by type compatibility**: loader `str → list[Document]`, chunker `list[Document] → list[Chunk]`, embedder `list[Chunk] → list[ChunkWithEmbedding]`, retriever `str → list[Chunk]`, generator `AnswerGeneratorInput → RAGAnswer`.
3. **Keep the pipeline a pure orchestrator** — `RAGPipeline` constructs components (models/top_k injectable) and calls them in order; no stage logic lives in the pipeline.
4. **Separate indexing from querying** as two pipeline methods (`index_documents()` / `query()`), guarded by an `_is_indexed` flag with a clear error.
5. **Let stages degrade per item, not per batch** — the chunker catches per-document failures and continues, logging what was skipped.
6. **Use an LLM for semantic chunking when structure matters**: `SemanticChunker` asks Gemini (structured output → `ChunkingResponse`) to split by meaning, instead of fixed character windows.
7. **Keep the vector store behind the retriever** — `VectorStore` (in-memory, cosine similarity) is an implementation detail of `Retriever`; swapping to a real vector DB changes one class.

## Architecture

```
Indexing:  data_directory
   ▼ DocumentLoader   (str → list[Document])
   ▼ SemanticChunker  (list[Document] → list[Chunk])       ← LLM-driven chunking
   ▼ Embedder         (list[Chunk] → list[ChunkWithEmbedding])   gemini-embedding-001
   ▼ VectorStore.store()

Query:     question
   ▼ Retriever        (str → list[Chunk])    query embed + cosine top-k
   ▼ AnswerGenerator  (AnswerGeneratorInput → RAGAnswer)   context-grounded generation
   ▼ RAGAnswer (answer + source chunks)
```

### Directory Structure

```
chapter_4/section_3/
├── src/
│   ├── strategy/
│   │   ├── base.py         # Component[InputType, OutputType] ABC
│   │   ├── loader.py       # DocumentLoader (md/txt file discovery)
│   │   ├── chunker.py      # SemanticChunker (LLM structured-output chunking)
│   │   ├── embedder.py     # Embedder (gemini-embedding-001)
│   │   ├── retriever.py    # VectorStore (in-memory cosine) + Retriever
│   │   └── generator.py    # AnswerGenerator (+ AnswerGeneratorInput)
│   ├── service/rag_pipeline.py   # RAGPipeline: composition + index/query
│   ├── model/rag_model.py        # Document/Chunk/ChunkWithEmbedding/RAGAnswer...
│   ├── client/llm_client.py      # Gemini client + model enums
│   ├── main.py                   # CLI: `index` and `query` subcommands
│   └── config.py / logger.py
├── data/                         # source documents to index
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. The generic component interface (`src/strategy/base.py`)

```python
InputType = TypeVar("InputType")
OutputType = TypeVar("OutputType")

class Component(ABC, Generic[InputType, OutputType]):
    """Base class for all pipeline components following the strategy pattern."""

    @abstractmethod
    async def process(self, input_data: InputType) -> OutputType:
        pass
```

### 2. Pipeline as pure composition (`src/service/rag_pipeline.py`)

```python
class RAGPipeline:
    def __init__(self, data_directory, chunker_model=..., embedding_model=..., generator_model=..., top_k=5):
        self.vector_store = VectorStore()
        self.loader = DocumentLoader()
        self.chunker = SemanticChunker(model=chunker_model)
        self.embedder = Embedder(model=embedding_model)
        self.retriever = Retriever(vector_store=self.vector_store, top_k=top_k, embedding_model=embedding_model)
        self.generator = AnswerGenerator(model=generator_model)

    async def index_documents(self) -> None:
        documents = await self.loader.process(self.data_directory)
        chunks = await self.chunker.process(documents)
        chunks_with_embeddings = await self.embedder.process(chunks)
        self.vector_store.store(chunks_with_embeddings)
        self._is_indexed = True

    async def query(self, question: str) -> RAGAnswer:
        if not self._is_indexed:
            raise RuntimeError("Documents must be indexed before querying. Call index_documents() first.")
        relevant_chunks = await self.retriever.process(question)
        return await self.generator.process(AnswerGeneratorInput(question=question, chunks=relevant_chunks))
```

### 3. Per-item degradation in batch stages (`src/strategy/chunker.py`)

```python
for document in input_data:
    try:
        chunks = await self._chunk_document(document)
        all_chunks.extend(chunks)
    except Exception as e:
        logger.error(f"Failed to chunk document {document.file_path}: {e}")
        continue      # one bad document doesn't sink the index
```

### 4. Retriever hides the store (`src/strategy/retriever.py`)

```python
class VectorStore:
    def store(self, chunks_with_embeddings: list[ChunkWithEmbedding]) -> None: ...
    def search(self, query_embedding: list[float], top_k: int = 5) -> list[Chunk]: ...
    # cosine similarity over numpy vectors

class Retriever(Component[str, list[Chunk]]):
    async def process(self, input_data: str) -> list[Chunk]:
        query_embedding = await self._create_query_embedding(input_data)
        return self.vector_store.search(query_embedding, top_k=self.top_k)
```

## Data Models

| Model | Purpose |
|-------|---------|
| `Document` | Loaded file: path + content |
| `Chunk` / `ChunkWithEmbedding` | Semantic chunk (± embedding vector) |
| `ChunkSegment` / `ChunkingResponse` | Structured output schema for LLM-driven chunking |
| `RAGAnswer` | Final answer + source chunks (grounding) |

## Setup & Run

```bash
cp .envrc.example .envrc     # set GEMINI_API_KEY
uv sync

# Canonical example: index + answer in one query command
uv run python -m src.main query -q 'What is structured output?'

# Explicit subcommands
uv run python -m src.main index -dd data/
uv run python -m src.main query -q '質問...' --data-directory data/
```

### CLI (click group)

| Command | Key options | Description |
|---------|-------------|-------------|
| `index` | `--data-directory`, `--chunker-model`, `--embedding-model` | Build the vector index |
| `query` | `--question/-q`, `--data-directory`, model options | Index (if needed) and answer a question |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
```

## Implementation Notes

- **Semantic chunking trades tokens for retrieval quality**: each document costs one LLM call at indexing time, but chunks follow meaning boundaries, which improves retrieval precision over fixed windows. Swap in a character/token chunker (same `Component` interface) when indexing cost dominates.
- **The in-memory `VectorStore` is deliberately naive** — a numpy cosine scan. It keeps the section focused on the composition pattern; the ChromaDB client from Chapter 4 Section 1 is the drop-in production replacement (change only `VectorStore`/`Retriever`).
- **Embedding-model consistency**: `Retriever` takes the same `embedding_model` used by `Embedder`; the pipeline constructor enforces this by wiring both from one parameter.
- **Grounded answers**: `AnswerGenerator` builds the context block from retrieved chunks and returns them in `RAGAnswer`, so callers can render citations and detect empty-retrieval cases.
- **Every stage is independently unit-testable** with plain fixtures (documents in, chunks out) — the Strategy decomposition is what makes RAG testing tractable.

## How to Apply This Practice to Your Own Project

1. Draw your workflow as stages with typed inputs/outputs first; then define the `Component[In, Out]` ABC and one class per stage.
2. Keep orchestration in a pipeline class whose constructor takes the components (or their config) — composition over inheritance.
3. Start with the naive in-memory vector store; swap to a real vector DB by reimplementing only the store/retriever.
4. Choose chunking per corpus: semantic (LLM) for structure-heavy documents, fixed-size for uniform text; the interface makes A/B testing trivial.
5. Guard query-before-index with an explicit error; separate index and query CLI commands for operational control.
6. Return sources with every answer — grounding data is a product feature and a debugging tool.
