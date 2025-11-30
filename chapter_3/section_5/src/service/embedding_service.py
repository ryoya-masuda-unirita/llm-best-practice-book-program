"""Embedding service using Google Gemini API."""

import asyncio

from src.client.llm_client import google_genai_client
from src.logger import make_logger

logger = make_logger(__name__)

GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
GEMINI_EMBEDDING_DIMENSION = 768


def _get_gemini_embedding_sync(text: str) -> list[float]:
    """Get embedding vector from Google Gemini API (synchronous)."""
    logger.debug(f"Generating Gemini embedding for text: {text[:50]}...")

    result = google_genai_client.models.embed_content(
        model=GEMINI_EMBEDDING_MODEL,
        contents=text,
    )
    embedding = result.embeddings[0].values

    logger.debug(f"Generated Gemini embedding with dimension: {len(embedding)}")
    return embedding


async def get_embedding(text: str) -> list[float]:
    """
    Get embedding vector using Gemini API.

    Args:
        text: Text to embed

    Returns:
        Embedding vector as list of floats
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_gemini_embedding_sync, text)


def get_embedding_dimension() -> int:
    """
    Get the embedding dimension for Gemini.

    Returns:
        Embedding dimension as integer (768)
    """
    return GEMINI_EMBEDDING_DIMENSION
