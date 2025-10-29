"""Embedding service using OpenAI and Google Gemini APIs."""

import asyncio

from src.client.llm_client import google_genai_client, openai_client
from src.logger import make_logger

logger = make_logger(__name__)


async def get_openai_embedding(text: str) -> list[float]:
    """
    Get embedding vector from OpenAI API.

    Args:
        text: Text to embed

    Returns:
        Embedding vector as list of floats
    """
    logger.debug(f"Generating OpenAI embedding for text: {text[:50]}...")

    response = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )

    # Extract embedding vector from response
    embedding = response.data[0].embedding

    logger.debug(f"Generated OpenAI embedding with dimension: {len(embedding)}")

    return embedding


def get_gemini_embedding(text: str) -> list[float]:
    """
    Get embedding vector from Google Gemini API.

    Note: This is a synchronous operation as the Google client doesn't support async.

    Args:
        text: Text to embed

    Returns:
        Embedding vector as list of floats
    """
    logger.debug(f"Generating Gemini embedding for text: {text[:50]}...")

    result = google_genai_client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
    )

    # Extract embedding vector from response
    embedding = result.embeddings[0].values

    logger.debug(f"Generated Gemini embedding with dimension: {len(embedding)}")

    return embedding


async def get_embedding(text: str, provider: str) -> list[float]:
    """
    Get embedding vector using the specified provider.

    Args:
        text: Text to embed
        provider: Provider name ("openai" or "gemini")

    Returns:
        Embedding vector as list of floats

    Raises:
        ValueError: If provider is not supported
    """
    if provider.lower() == "openai":
        return await get_openai_embedding(text)
    elif provider.lower() == "gemini":
        # Gemini API is synchronous, but we wrap it for consistency

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, get_gemini_embedding, text)
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")


def get_embedding_dimension(provider: str) -> int:
    """
    Get the embedding dimension for the specified provider.

    Args:
        provider: Provider name ("openai" or "gemini")

    Returns:
        Embedding dimension as integer
    """
    if provider.lower() == "openai":
        return 1536
    elif provider.lower() == "gemini":
        return 768
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")
