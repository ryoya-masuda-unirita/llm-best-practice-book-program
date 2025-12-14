"""Models for knowledge base operations (CQRS pattern)."""

import time
from typing import Optional

from pydantic import BaseModel, Field

from src.model.model import CharacterRequest, CharacterResponse


# Command Models (Write Operations)
class KnowledgeRegisterCommand(BaseModel):
    """Command to register knowledge asynchronously."""

    character_request: CharacterRequest = Field(..., description="Original character request")
    character_response: CharacterResponse = Field(..., description="Generated character response")
    model: str = Field(..., description="Model used")
    prompt: list[dict] = Field(..., description="Prompt used for generation")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    metadata: Optional[dict] = Field(default=None, description="Additional metadata")


class KnowledgeRegisterResponse(BaseModel):
    """Response for knowledge registration command."""

    job_id: str = Field(..., description="Background job ID for tracking")
    status: str = Field(default="accepted", description="Command acceptance status")
    message: str = Field(default="Knowledge registration queued for processing")


# Query Models (Read Operations)
class KnowledgeSearchQuery(BaseModel):
    """Query to search knowledge base."""

    query_text: str = Field(..., description="Search query text")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    filter_metadata: Optional[dict] = Field(default=None, description="Metadata filters")


class KnowledgeItem(BaseModel):
    """Single knowledge item in search results."""

    id: str = Field(..., description="Unique identifier")
    character_request: CharacterRequest = Field(..., description="Original character request")
    character_response: CharacterResponse = Field(..., description="Generated character response")
    model: str = Field(..., description="Model used")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    created_at: float = Field(..., description="Timestamp of creation")


class KnowledgeSearchResponse(BaseModel):
    """Response for knowledge search query."""

    results: list[KnowledgeItem] = Field(..., description="Search results")
    total_count: int = Field(..., description="Total number of results returned")
    query_time_ms: float = Field(..., description="Query processing time in milliseconds")


class KnowledgeStatsQuery(BaseModel):
    """Query to get knowledge base statistics."""

    include_samples: bool = Field(default=False, description="Include sample items")


class KnowledgeStatsResponse(BaseModel):
    """Response for knowledge statistics query."""

    total_items: int = Field(..., description="Total number of knowledge items")
    models_distribution: dict[str, int] = Field(..., description="Distribution by model")
    timestamp: float = Field(default_factory=time.time, description="Stats generation timestamp")
