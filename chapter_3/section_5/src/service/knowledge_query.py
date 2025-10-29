"""Query side of CQRS - Handles knowledge base read operations synchronously."""

import asyncio
import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from src.client.chromadb_client import get_knowledge_collection
from src.logger import make_logger
from src.model.knowledge import (
    KnowledgeItem,
    KnowledgeSearchQuery,
    KnowledgeSearchResponse,
    KnowledgeStatsResponse,
)
from src.model.model import CharacterRequest, CharacterResponse
from src.service.embedding_service import get_embedding

logger = make_logger(__name__)

# Thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=4)


def _search_chromadb(query_embedding: list[float], query: KnowledgeSearchQuery) -> dict:
    """
    Search ChromaDB for knowledge items using custom query embedding.

    This is a blocking operation that runs in a thread pool.

    Args:
        query_embedding: Pre-generated embedding vector for the query
        query: Search query parameters

    Returns:
        ChromaDB query results
    """
    try:
        collection = get_knowledge_collection()

        # Prepare where clause for metadata filtering
        where_clause = None
        if query.filter_metadata:
            where_clause = query.filter_metadata

        # Query the collection using custom embedding
        results = collection.query(
            query_embeddings=[query_embedding],  # Use custom embedding instead of query_texts
            n_results=query.limit,
            where=where_clause,
        )

        return results

    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        raise


def _parse_search_results(results: dict) -> list[KnowledgeItem]:
    """Parse ChromaDB search results into KnowledgeItem objects."""
    items = []

    if not results or not results.get("ids") or not results["ids"][0]:
        return items

    ids = results["ids"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for i, item_id in enumerate(ids):
        try:
            metadata = metadatas[i]

            # Extract full data from JSON
            full_data_json = metadata.get("full_data_json", "{}")
            full_data = json.loads(full_data_json)

            # Parse character data
            character_request = CharacterRequest(**full_data.get("character_request", {}))
            character_response = CharacterResponse(**full_data.get("character_response", {}))

            # Convert distance to similarity score (ChromaDB returns cosine distance)
            # Similarity = 1 - distance for cosine
            similarity_score = 1.0 - distances[i]

            item = KnowledgeItem(
                id=item_id,
                character_request=character_request,
                character_response=character_response,
                provider=metadata.get("provider", ""),
                model=metadata.get("model", ""),
                processing_time_ms=metadata.get("processing_time_ms", 0.0),
                similarity_score=similarity_score,
                created_at=metadata.get("created_at", 0.0),
            )
            items.append(item)

        except Exception as e:
            logger.warning(f"Error parsing search result item {item_id}: {e}")
            continue

    return items


async def search_knowledge(query: KnowledgeSearchQuery) -> KnowledgeSearchResponse:
    """
    Search knowledge base synchronously using custom embeddings.

    This is optimized for low-latency reads and returns results immediately.
    It generates a query embedding using the specified provider's API and then
    searches ChromaDB using vector similarity.

    Args:
        query: Search query parameters

    Returns:
        Search results with similarity scores
    """
    start_time = time.time()

    logger.info(
        f"Searching knowledge base with query: {query.query_text[:50]}... using {query.embedding_provider} embeddings"
    )

    # Generate embedding for the query text
    query_embedding = await get_embedding(query.query_text, query.embedding_provider)
    logger.debug(f"Generated query embedding with dimension: {len(query_embedding)}")

    # Execute the blocking ChromaDB operation in a thread pool
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(executor, _search_chromadb, query_embedding, query)

    # Parse results
    items = _parse_search_results(results)

    query_time = (time.time() - start_time) * 1000

    logger.info(f"Search completed in {query_time:.2f}ms, found {len(items)} results")

    return KnowledgeSearchResponse(
        results=items,
        total_count=len(items),
        query_time_ms=query_time,
    )


def _get_stats_from_chromadb() -> dict:
    """
    Get statistics from ChromaDB.

    This is a blocking operation that runs in a thread pool.
    """
    try:
        collection = get_knowledge_collection()

        # Get all items (or use count if available)
        results = collection.get(include=["metadatas"])

        return results

    except Exception as e:
        logger.error(f"Error getting knowledge base stats: {e}")
        raise


async def get_knowledge_stats() -> KnowledgeStatsResponse:
    """
    Get knowledge base statistics.

    Returns aggregate information about stored knowledge items.

    Returns:
        Statistics including total count and distribution by provider/model
    """
    logger.info("Retrieving knowledge base statistics")

    # Execute the blocking ChromaDB operation in a thread pool
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(executor, _get_stats_from_chromadb)

    # Calculate statistics
    total_items = len(results.get("ids", []))
    metadatas = results.get("metadatas", [])

    providers = [m.get("provider", "unknown") for m in metadatas]
    models = [m.get("model", "unknown") for m in metadatas]

    providers_distribution = dict(Counter(providers))
    models_distribution = dict(Counter(models))

    logger.info(f"Retrieved stats: {total_items} total items")

    return KnowledgeStatsResponse(
        total_items=total_items,
        providers_distribution=providers_distribution,
        models_distribution=models_distribution,
    )
