"""Data models for RAG pipeline."""

from pydantic import BaseModel, ConfigDict, Field


class Document(BaseModel):
    """Represents a loaded document."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    file_path: str = Field(..., description="Path to the document file")
    content: str = Field(..., description="Content of the document")


class Chunk(BaseModel):
    """Represents a text chunk from a document."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    text: str = Field(..., description="The text content of the chunk")
    source_file: str = Field(..., description="Source file path")
    chunk_index: int = Field(..., description="Index of the chunk in the source document")


class ChunkWithEmbedding(BaseModel):
    """Represents a chunk with its embedding vector."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=False,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    chunk: Chunk = Field(..., description="The text chunk")
    embedding: list[float] = Field(..., description="Embedding vector for the chunk")


class ChunkSegment(BaseModel):
    """Represents a segment suggestion from LLM for chunking."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    start_line: int = Field(..., description="Starting line number (1-indexed)")
    end_line: int = Field(..., description="Ending line number (1-indexed)")
    topic: str = Field(..., description="Main topic or theme of this segment")
    reason: str = Field(..., description="Reason for this segmentation")


class ChunkingResponse(BaseModel):
    """Response from LLM for semantic chunking."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    segments: list[ChunkSegment] = Field(..., description="List of suggested text segments")


class RAGAnswer(BaseModel):
    """Final answer from the RAG system."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    question: str = Field(..., description="The original question")
    answer: str = Field(..., description="The generated answer")
    source_chunks: list[str] = Field(..., description="Source file paths of chunks used")
