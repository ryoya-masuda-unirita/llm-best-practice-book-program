# Chapter 3 Section 11: Component-Based RAG System Using Strategy Pattern

## Project Overview

This project demonstrates a production-ready implementation of a **modular RAG (Retrieval-Augmented Generation) system** using the Strategy Pattern. It showcases how to decompose complex LLM workflows into independent, reusable components with standardized interfaces, enabling flexible system composition and easier maintenance.

### Core Concept

As LLM applications grow in complexity, monolithic implementations become difficult to maintain, test, and extend. A typical RAG system involves multiple steps: document loading, text chunking, embedding generation, vector search, and answer generation. Implementing these as one large function creates several problems:

- Difficult to test individual steps in isolation
- Hard to swap implementations (e.g., changing from character-based to semantic chunking)
- Tight coupling makes changes risky
- Code reuse across projects becomes nearly impossible
- Debugging complex workflows is challenging

This implementation solves these challenges by decomposing the RAG pipeline into independent components, each following a common interface. Each component can be developed, tested, and replaced independently without affecting the rest of the system.

### Key Technologies

- **Strategy Pattern**: Behavioral design pattern for defining a family of interchangeable algorithms
- **Generic Types (Python)**: `TypeVar` for type-safe component composition
- **Abstract Base Classes**: Enforce consistent interfaces across components
- **OpenAI Python SDK (v2.4.0+)**: For GPT models and structured outputs
- **Google GenAI Python SDK (v1.45.0+)**: For Gemini models
- **Pydantic**: Type-safe data models with validation
- **NumPy**: Vector operations for cosine similarity
- **Click**: CLI framework for user interface

### Architecture Pattern

The system implements a **Pipeline Architecture** with the **Strategy Pattern**:

```
CLI Layer (main.py)
       |
       v
Pipeline Orchestrator (rag_pipeline.py)
       |
       v
Component Layer (strategy/*)
       |
       +-- DocumentLoader: str -> list[Document]
       +-- SemanticChunker: list[Document] -> list[Chunk]
       +-- Embedder: list[Chunk] -> list[ChunkWithEmbedding]
       +-- Retriever: str -> list[Chunk]
       +-- AnswerGenerator: AnswerGeneratorInput -> RAGAnswer
```

**Key Design Principle**: Each component implements `Component[InputType, OutputType]` with a single `async def process(input_data: InputType) -> OutputType` method. This creates a consistent interface that enables components to be chained together like UNIX pipes.

## Project Status

### What Works

**Component-Based Architecture**
- Base `Component[InputType, OutputType]` interface with generic types
- Five specialized components implementing the base interface
- Type-safe data flow between components
- Async/await support for efficient I/O operations

**Document Loading**
- Load Markdown files from a directory
- Configurable file extension filtering
- Error handling for individual file failures
- UTF-8 encoding support for Japanese text

**Semantic Chunking with LLM**
- LLM-powered semantic segmentation (not fixed-size chunks)
- Provides line numbers to LLM for precise segment identification
- Captures topic and reasoning for each segment
- Supports both OpenAI and Gemini models
- Structured output with Pydantic models

**Vector Embedding**
- OpenAI `text-embedding-3-small` support
- Gemini `text-embedding-004` support
- Parallel embedding generation for multiple chunks
- Error recovery for individual chunk failures

**In-Memory Vector Store**
- Cosine similarity search
- Configurable top-k retrieval
- Simple numpy-based implementation (suitable for development)

**Answer Generation**
- Context construction from retrieved chunks
- Source tracking for citations
- Instruction to use only provided documents
- Support for both OpenAI and Gemini models

**Multi-Provider Support**
- Consistent interface across OpenAI and Gemini
- Provider-specific adapters handle API differences
- Configurable model selection per component

**CLI Interface**
- `index` command for document indexing
- `query` command for question answering
- Rich configuration options (models, top-k, output paths)
- Makefile shortcuts for common operations

### Current Limitations

**Scalability Constraints**
- In-memory vector store doesn't persist across runs
- No support for incremental indexing (must reindex all documents)
- Linear search doesn't scale beyond ~10,000 chunks
- No distributed processing for large document sets

**Missing Production Features**
- No vector database integration (Pinecone, Weaviate, Milvus)
- No chunk overlap strategy for preserving context
- No hybrid search (combining vector and keyword search)
- No re-ranking of retrieved chunks
- No query expansion or reformulation

**Limited Chunking Strategies**
- Only semantic chunking via LLM (no character-based, sentence-based, or paragraph-based)
- No recursive chunking for very long documents
- No metadata preservation (headers, sections, etc.)
- LLM-based chunking is expensive for large document sets

**Testing Coverage**
- No unit tests for individual components
- No integration tests for full pipeline
- No performance benchmarks
- No test fixtures for common scenarios

**Observability Gaps**
- No metrics on retrieval quality (precision, recall)
- No tracking of chunk usage frequency
- No cost estimation for LLM operations
- No performance profiling for bottleneck identification

## Architecture Deep Dive

### 1. Component Interface Design

The foundation of this architecture is the `Component[InputType, OutputType]` base class defined in `src/strategy/base.py`:

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

InputType = TypeVar("InputType")
OutputType = TypeVar("OutputType")

class Component(ABC, Generic[InputType, OutputType]):
    """Base class for all pipeline components following the strategy pattern."""

    @abstractmethod
    async def process(self, input_data: InputType) -> OutputType:
        """
        Process input data and return output.

        Args:
            input_data: The input data to process

        Returns:
            The processed output data
        """
        pass
```

**Design Decisions**:

| Decision | Rationale | Alternative Considered |
|----------|-----------|------------------------|
| Abstract Base Class | Enforce interface contract at import time | Protocol (duck typing) |
| Generic types | Type safety and IDE autocomplete | No typing (Any -> Any) |
| Async by default | Non-blocking I/O for API calls | Sync (would need thread pools) |
| Single `process` method | Simplicity, composition | Multiple methods (fit/transform) |

**Benefits of This Design**:
1. **Type Safety**: `Component[str, list[Document]]` ensures correct chaining
2. **Testability**: Each component can be tested in isolation
3. **Composability**: Components can be rearranged without code changes
4. **Extensibility**: New components added without modifying existing ones
5. **Clarity**: Input/output types serve as documentation

#### Type Flow Example

```python
# This composition is type-safe:
loader: Component[str, list[Document]]
chunker: Component[list[Document], list[Chunk]]
embedder: Component[list[Chunk], list[ChunkWithEmbedding]]

# Flow:
dir_path: str = "data/"
docs: list[Document] = await loader.process(dir_path)
chunks: list[Chunk] = await chunker.process(docs)
embedded: list[ChunkWithEmbedding] = await embedder.process(chunks)
```

Type checker (mypy) validates that output types match input types.

### 2. Document Loader Component

The loader is the entry point to the pipeline (implemented in `src/strategy/loader.py`):

```python
class DocumentLoader(Component[str, list[Document]]):
    """Component for loading documents from a directory."""

    def __init__(self, file_extensions: list[str] | None = None):
        self.file_extensions = file_extensions or [".md"]

    async def process(self, input_data: str) -> list[Document]:
        directory = Path(input_data)
        if not directory.exists() or not directory.is_dir():
            raise ValueError(f"Invalid directory path: {directory}")

        documents = []
        for file_path in directory.iterdir():
            if file_path.is_file() and file_path.suffix in self.file_extensions:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    document = Document(file_path=str(file_path), content=content)
                    documents.append(document)
                except Exception as e:
                    logger.error(f"Failed to load document {file_path}: {e}")
                    continue

        return documents
```

**Design Choices**:
1. **Configurable Extensions**: Supports multiple file types without code changes
2. **Graceful Degradation**: Individual file failures don't stop the entire load
3. **UTF-8 Encoding**: Explicit encoding for international text
4. **Immutable Output**: `Document` model is frozen (Pydantic `frozen=True`)

**Extension Points**: To add PDF support, create a `PDFDocumentLoader` class and swap it in the pipeline without changing other components.

### 3. Semantic Chunker Component

The chunker splits documents into meaningful segments using an LLM (implemented in `src/strategy/chunker.py`).

**Why Semantic Chunking?**

Traditional chunking strategies have limitations:

| Strategy | Limitation |
|----------|------------|
| Fixed character count | Splits mid-sentence, mid-concept |
| Fixed line count | No regard for semantic boundaries |
| Paragraph-based | Paragraphs may cover multiple topics |
| Sentence-based | Related sentences get separated |

Semantic chunking uses the LLM's understanding to identify topic boundaries.

**Implementation Approach**:
1. Number all lines in the document (1-indexed)
2. Send numbered text to LLM with instructions to identify semantic boundaries
3. LLM returns structured output with `start_line`, `end_line`, `topic`, `reason` for each segment
4. Extract text for each segment based on line numbers

**Data Model for Chunking**:

```python
class ChunkSegment(BaseModel):
    start_line: int  # Starting line number (1-indexed)
    end_line: int    # Ending line number (1-indexed)
    topic: str       # Main topic or theme of this segment
    reason: str      # Reason for this segmentation

class ChunkingResponse(BaseModel):
    segments: list[ChunkSegment]
```

The chunker sends the document to the LLM with a detailed system instruction (in Japanese) that requests semantic segmentation based on topic boundaries. The LLM responds with structured JSON containing segment boundaries.

**Trade-offs**:

| Aspect | Benefit | Cost |
|--------|---------|------|
| LLM-based | High-quality semantic boundaries | Expensive (API calls per document) |
| Structured output | Reliable parsing | Requires supported LLM |
| Line-based indexing | Precise extraction | Sensitive to newlines |

### 4. Embedder Component

The embedder converts text chunks into vector representations (implemented in `src/strategy/embedder.py`):

```python
class Embedder(Component[list[Chunk], list[ChunkWithEmbedding]]):
    """Component for creating embeddings from text chunks."""

    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self.openai_client = AsyncOpenAI(api_key=config.openai_api_key)

    async def process(self, input_data: list[Chunk]) -> list[ChunkWithEmbedding]:
        chunks_with_embeddings = []
        for chunk in input_data:
            try:
                embedding = await self._create_embedding(chunk.text)
                chunk_with_embedding = ChunkWithEmbedding(
                    chunk=chunk,
                    embedding=embedding
                )
                chunks_with_embeddings.append(chunk_with_embedding)
            except Exception as e:
                logger.error(f"Failed to embed chunk: {e}")
                continue
        return chunks_with_embeddings
```

**Embedding Model Comparison**:

| Model | Dimensions | Cost/1M tokens | Quality | Use Case |
|-------|-----------|----------------|---------|----------|
| text-embedding-3-small | 1536 | $0.02 | Good | Development, large-scale |
| text-embedding-3-large | 3072 | $0.13 | Better | Production, high-quality |
| text-embedding-004 (Gemini) | 768 | $0.025 | Good | Gemini ecosystem |

### 5. Retriever Component with Vector Store

The retriever finds relevant chunks for a query (implemented in `src/strategy/retriever.py`).

**Vector Store Implementation**:

```python
class VectorStore:
    """In-memory vector store for storing and searching embeddings."""

    def __init__(self):
        self.chunks_with_embeddings: list[ChunkWithEmbedding] = []

    def store(self, chunks_with_embeddings: list[ChunkWithEmbedding]) -> None:
        self.chunks_with_embeddings.extend(chunks_with_embeddings)

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[Chunk]:
        if not self.chunks_with_embeddings:
            return []

        query_array = np.array(query_embedding)
        similarities = []

        for chunk_with_embedding in self.chunks_with_embeddings:
            chunk_array = np.array(chunk_with_embedding.embedding)
            similarity = self._cosine_similarity(query_array, chunk_array)
            similarities.append((similarity, chunk_with_embedding.chunk))

        similarities.sort(reverse=True, key=lambda x: x[0])
        return [chunk for _, chunk in similarities[:top_k]]

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
```

**Why Cosine Similarity?**

For text embeddings, cosine similarity is preferred over Euclidean distance because:
1. Normalized to [-1, 1] range
2. Magnitude-invariant (focuses on direction)
3. Standard in NLP and semantic search

**Production Considerations**: The in-memory vector store is suitable for development but not production. For production, consider: Pinecone (managed, scalable), Weaviate (open-source, GraphQL), Milvus (high performance), Qdrant (Rust-based, fast), or Chroma (developer-friendly).

### 6. Answer Generator Component

The generator creates answers based on retrieved chunks (implemented in `src/strategy/generator.py`):

```python
class AnswerGenerator(Component[AnswerGeneratorInput, RAGAnswer]):
    """Component for generating answers based on retrieved chunks."""

    def __init__(self, model: str = "gemini-2.5-flash"):
        self.model = model

    async def process(self, input_data: AnswerGeneratorInput) -> RAGAnswer:
        question = input_data.question
        chunks = input_data.chunks

        if not chunks:
            return RAGAnswer(
                question=question,
                answer="No relevant information found.",
                source_chunks=[],
            )

        context = self._build_context(chunks)
        answer = await self._generate_answer(question, context)
        source_files = list(set([chunk.source_file for chunk in chunks]))

        return RAGAnswer(
            question=question,
            answer=answer,
            source_chunks=source_files
        )
```

**Context Construction Strategy**: The system builds context by numbering each chunk (e.g., "[Document 1]", "[Document 2]") and including the source file path. This enables:
- Easy reference in the answer
- Source traceability
- Visual separation of chunks

**Prompt Engineering for RAG**: The system instruction (in Japanese) enforces critical RAG principles:
1. Ground answers in provided documents only
2. Explicitly state when information is missing
3. Cite sources for verification
4. Provide concise answers

### 7. Pipeline Orchestrator

The orchestrator chains components together (implemented in `src/service/rag_pipeline.py`):

```python
class RAGPipeline:
    """Pipeline that orchestrates the RAG workflow."""

    def __init__(
        self,
        data_directory: str,
        chunker_model: str = "gemini-2.5-flash",
        embedding_model: str = "text-embedding-3-small",
        generator_model: str = "gemini-2.5-flash",
        top_k: int = 5,
    ):
        self.data_directory = data_directory
        self.vector_store = VectorStore()

        # Initialize components
        self.loader = DocumentLoader()
        self.chunker = SemanticChunker(model=chunker_model)
        self.embedder = Embedder(model=embedding_model)
        self.retriever = Retriever(
            vector_store=self.vector_store,
            top_k=top_k,
            embedding_model=embedding_model
        )
        self.generator = AnswerGenerator(model=generator_model)

        self._is_indexed = False

    async def index_documents(self) -> None:
        """Index all documents in the data directory."""
        documents = await self.loader.process(self.data_directory)
        chunks = await self.chunker.process(documents)
        chunks_with_embeddings = await self.embedder.process(chunks)
        self.vector_store.store(chunks_with_embeddings)
        self._is_indexed = True

    async def query(self, question: str) -> RAGAnswer:
        """Query the RAG system with a question."""
        if not self._is_indexed:
            raise RuntimeError("Documents must be indexed first")

        relevant_chunks = await self.retriever.process(question)
        generator_input = AnswerGeneratorInput(
            question=question,
            chunks=relevant_chunks
        )
        answer = await self.generator.process(generator_input)
        return answer
```

**Pipeline Pattern Benefits**:
1. Separation of concerns (indexing vs querying)
2. State management (prevents queries before indexing)
3. Component composition (easy reconfiguration)
4. Error propagation (component errors bubble up naturally)

**Data Flow Visualization**:

```
Indexing Pipeline:
  directory path (str)
        |
        v
  DocumentLoader.process()
        |
        v
  list[Document]
        |
        v
  SemanticChunker.process()
        |
        v
  list[Chunk]
        |
        v
  Embedder.process()
        |
        v
  list[ChunkWithEmbedding]
        |
        v
  VectorStore.store()

Query Pipeline:
  question (str)
        |
        v
  Retriever.process()
        |
        v
  list[Chunk]
        |
        v
  AnswerGenerator.process()
        |
        v
  RAGAnswer
```

### 8. Data Models

Pydantic models ensure type safety and data validation (defined in `src/model/rag_model.py`):

```python
class Document(BaseModel):
    model_config = ConfigDict(frozen=True, validate_assignment=True)
    file_path: str
    content: str

class Chunk(BaseModel):
    model_config = ConfigDict(frozen=True, validate_assignment=True)
    text: str
    source_file: str
    chunk_index: int

class ChunkWithEmbedding(BaseModel):
    model_config = ConfigDict(frozen=False, validate_assignment=True)
    chunk: Chunk
    embedding: list[float]

class RAGAnswer(BaseModel):
    model_config = ConfigDict(frozen=True, validate_assignment=True)
    question: str
    answer: str
    source_chunks: list[str]
```

**Model Design Principles**:

| Principle | Rationale | Implementation |
|-----------|-----------|----------------|
| Immutability | Thread safety, prevents bugs | `frozen=True` |
| Validation | Catch errors early | `validate_assignment=True` |
| Documentation | Self-documenting code | Field descriptions |
| Serialization | Easy persistence | Pydantic `.model_dump()` |

### 9. CLI Application

Click-based CLI provides user interface (implemented in `src/main.py`):

The CLI provides two main commands:
- `index`: Loads documents from a directory and creates the vector index
- `query`: Asks a question and retrieves an answer from indexed documents

**CLI Options**:
- `--llm-provider` / `-lp`: Choose OpenAI or Gemini
- `--data-directory` / `-d`: Directory containing documents
- `--chunker-model` / `-cm`: Model for semantic chunking
- `--embedding-model` / `-em`: Model for embeddings
- `--generator-model` / `-gm`: Model for answer generation
- `--top-k` / `-k`: Number of chunks to retrieve
- `--output-file` / `-o`: Save answer to JSON file

**Validation**: The CLI validates that selected models are compatible with the chosen provider (e.g., can't use GPT models with Gemini provider).

## Best Practices Demonstrated

### 1. Strategy Pattern for Interchangeable Algorithms

Each component is a "strategy" that can be swapped:

```python
# Original pipeline
pipeline = RAGPipeline(
    chunker_model="gemini-2.5-flash",
    embedding_model="text-embedding-3-small",
)

# Swap to different strategy
pipeline = RAGPipeline(
    chunker_model="gpt-5-mini",
    embedding_model="text-embedding-004",
)
```

No code changes to pipeline logic required.

### 2. Composition Over Inheritance

Components are composed, not inherited:

```python
class RAGPipeline:
    def __init__(self):
        self.loader = DocumentLoader()     # Composition
        self.chunker = SemanticChunker()   # Composition
        self.embedder = Embedder()         # Composition
```

**Why Composition Wins**:
- Easier to test (inject mocks)
- Flexible (combine any compatible components)
- Maintainable (no diamond problem)
- Clear (explicit dependencies)

### 3. Dependency Injection

Components receive dependencies explicitly:

```python
class Retriever(Component[str, list[Chunk]]):
    def __init__(self, vector_store: VectorStore, top_k: int):
        self.vector_store = vector_store  # Injected dependency
        self.top_k = top_k
```

**Benefits**:
- Testable (inject mock vector store)
- Configurable (different stores for dev/prod)
- Explicit (dependencies visible in constructor)

### 4. Type Safety with Generics

Generic types catch errors at type-check time:

```python
loader: Component[str, list[Document]]
chunker: Component[int, str]  # Wrong input type!

# This won't type-check:
result = await chunker.process(await loader.process("data/"))
# Mypy error: Expected int, got list[Document]
```

### 5. Async/Await for I/O-Bound Operations

All components use async for non-blocking I/O:

```python
async def index_documents(self):
    documents = await self.loader.process(self.data_directory)  # File I/O
    chunks = await self.chunker.process(documents)              # API call
    embeddings = await self.embedder.process(chunks)            # API call
```

### 6. Error Isolation

Component failures don't cascade:

```python
for chunk in input_data:
    try:
        embedding = await self._create_embedding(chunk.text)
        chunks_with_embeddings.append(ChunkWithEmbedding(...))
    except Exception as e:
        logger.error(f"Failed to embed chunk: {e}")
        continue  # Skip this chunk, process others
```

### 7. Immutable Data Models

Pydantic models are frozen to prevent mutations:

```python
doc = Document(file_path="test.md", content="Hello")
doc.content = "World"  # Raises FrozenInstanceError
```

**Benefits**: Thread safety, predictability, easier debugging.

## Production Deployment Considerations

### 1. Vector Database Migration

Replace `VectorStore` with production database like Pinecone:

```python
class PineconeVectorStore(VectorStoreAdapter):
    def __init__(self, index_name: str):
        import pinecone
        pinecone.init(api_key=os.environ["PINECONE_API_KEY"])
        self.index = pinecone.Index(index_name)

    async def store(self, chunks_with_embeddings):
        vectors = [(str(i), chunk.embedding, {...}) 
                   for i, chunk in enumerate(chunks_with_embeddings)]
        self.index.upsert(vectors=vectors, batch_size=100)

    async def search(self, query_embedding, top_k):
        results = self.index.query(vector=query_embedding, top_k=top_k)
        return [...]
```

Then update pipeline: `self.vector_store = PineconeVectorStore("production-rag")`

### 2. Incremental Indexing

Support adding/updating individual documents without full reindex:

```python
class IncrementalRAGPipeline(RAGPipeline):
    async def index_new_document(self, file_path: str):
        document = Document(...)
        chunks = await self.chunker.process([document])
        embeddings = await self.embedder.process(chunks)
        self.vector_store.store(embeddings)

    async def update_document(self, file_path: str):
        await self.vector_store.delete_by_source(file_path)
        await self.index_new_document(file_path)
```

### 3. Caching for Expensive Operations

Cache LLM-based chunking results:

```python
class CachedSemanticChunker(SemanticChunker):
    def __init__(self, model, cache_dir=".cache/chunks"):
        super().__init__(model)
        self.cache_dir = Path(cache_dir)

    async def _chunk_document(self, document):
        cache_key = hashlib.sha256(document.content.encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            return self._load_from_cache(cache_file)

        chunks = await super()._chunk_document(document)
        self._save_to_cache(cache_file, chunks)
        return chunks
```

### 4. Monitoring and Observability

Add metrics collection with Prometheus:

```python
from prometheus_client import Counter, Histogram

rag_queries_total = Counter('rag_queries_total', 'Total RAG queries')
rag_query_duration = Histogram('rag_query_duration_seconds', 'Query duration')

class ObservableRAGPipeline(RAGPipeline):
    @rag_query_duration.time()
    async def query(self, question: str):
        rag_queries_total.inc()
        return await super().query(question)
```

### 5. Error Handling and Retry Logic

Add resilience with retry logic:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class ResilientSemanticChunker(SemanticChunker):
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _chunk_document(self, document):
        return await super()._chunk_document(document)
```

## Future Enhancements

### 1. Hybrid Search (Vector + Keyword)

Combine semantic and keyword search for better retrieval:

```python
class HybridRetriever(Component[str, list[Chunk]]):
    def __init__(self, vector_retriever, keyword_retriever, alpha=0.7):
        self.vector_retriever = vector_retriever
        self.keyword_retriever = keyword_retriever
        self.alpha = alpha  # Weight for vector search

    async def process(self, input_data: str):
        vector_chunks = await self.vector_retriever.process(input_data)
        keyword_chunks = await self.keyword_retriever.process(input_data)
        return self._merge_results(vector_chunks, keyword_chunks)
```

### 2. Query Expansion

Improve retrieval with query reformulation:

```python
class QueryExpandingRetriever(Retriever):
    async def process(self, input_data: str):
        expanded_queries = await self._expand_query(input_data)
        all_chunks = []
        for query in expanded_queries:
            chunks = await super().process(query)
            all_chunks.extend(chunks)
        return self._deduplicate_and_rerank(all_chunks)
```

### 3. Multi-Hop Reasoning

For complex questions requiring multiple retrieval steps:

```python
class MultiHopRAGPipeline(RAGPipeline):
    async def query(self, question: str, max_hops: int = 3):
        context_chunks = []
        current_question = question

        for hop in range(max_hops):
            chunks = await self.retriever.process(current_question)
            context_chunks.extend(chunks)

            if await self._has_sufficient_context(question, context_chunks):
                break

            current_question = await self._generate_followup(question, context_chunks)

        return await self.generator.process(
            AnswerGeneratorInput(question, context_chunks)
        )
```

### 4. Adaptive Chunking

Adjust chunk size based on document characteristics:

```python
class AdaptiveChunker(Component[list[Document], list[Chunk]]):
    async def process(self, input_data: list[Document]):
        all_chunks = []
        for doc in input_data:
            doc_type = self._classify_document(doc)
            
            if doc_type == "code":
                chunker = CodeAwareChunker()
            elif doc_type == "table":
                chunker = TablePreservingChunker()
            else:
                chunker = SemanticChunker()

            chunks = await chunker.process([doc])
            all_chunks.extend(chunks)
        return all_chunks
```

## Lessons Learned

### What Worked Well

1. **Generic Type System**: Caught many bugs at type-check time, not runtime
2. **Component Abstraction**: Made testing and swapping implementations trivial
3. **Async Throughout**: Enabled efficient I/O without complex threading
4. **Pydantic Models**: Self-documenting, validated data structures
5. **Pipeline Pattern**: Clear separation between indexing and querying

### What Could Be Improved

1. **No Persistence**: Vector store doesn't survive restarts
2. **Sequential Processing**: Could parallelize document chunking/embedding
3. **No Metrics**: Can't measure retrieval quality or system performance
4. **Fixed Pipeline**: No runtime reconfiguration of components
5. **Cost Blindness**: No tracking of API costs

### Design Trade-offs

| Decision | Benefit | Cost |
|----------|---------|------|
| In-memory vector store | Simple, no dependencies | Not production-ready |
| LLM-based chunking | High-quality boundaries | Expensive, slow |
| Async by default | Non-blocking I/O | More complex code |
| Frozen data models | Thread-safe | Can't mutate |
| Component abstraction | Flexible, testable | More code layers |

## Conclusion

This component-based RAG system demonstrates a production-grade architecture for complex LLM workflows. The core insight is that **complex systems should be composed of simple, independent parts** rather than implemented as monolithic functions.

The system successfully achieves:
- **Modularity**: Each component has a single responsibility
- **Flexibility**: Components can be swapped without affecting others
- **Testability**: Each component can be tested in isolation
- **Type Safety**: Generic types ensure correct composition
- **Extensibility**: New components can be added without modification

For teams building production RAG systems, this architecture provides:
- **Experimentation**: Easy to try different strategies
- **Debugging**: Clear boundaries make it easy to isolate problems
- **Scalability**: Components can be replaced with production implementations
- **Maintenance**: Changes localized to individual components
- **Testing**: Each component testable independently

The component-based approach is particularly valuable as RAG systems evolve. Initial implementations can use simple components (in-memory vector store, basic chunking) that are later upgraded to production components (Pinecone, semantic chunking) without changing the overall architecture.
