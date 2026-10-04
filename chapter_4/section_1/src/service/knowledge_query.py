"""Query side of CQRS - Handles knowledge base read operations synchronously."""

import asyncio
import json
import time
from collections import Counter

from src import executor
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


def _search_chromadb(query_embedding: list[float], query: KnowledgeSearchQuery) -> dict:
    """Search ChromaDB for knowledge items using custom query embedding."""
    try:
        collection = get_knowledge_collection()

        where_clause = None
        if query.filter_metadata:
            where_clause = query.filter_metadata

        results = collection.query(
            query_embeddings=[query_embedding],
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

            full_data_json = metadata.get("full_data_json", "{}")
            full_data = json.loads(full_data_json)

            character_request = CharacterRequest(**full_data.get("character_request", {}))
            character_response = CharacterResponse(**full_data.get("character_response", {}))

            similarity_score = 1.0 - distances[i]

            item = KnowledgeItem(
                id=item_id,
                character_request=character_request,
                character_response=character_response,
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
    """Search knowledge base using Anthropic embeddings."""
    start_time = time.time()

    logger.info(f"Searching knowledge base with query: {query.query_text[:50]}...")

    query_embedding = await get_embedding(query.query_text)
    logger.debug(f"Generated query embedding with dimension: {len(query_embedding)}")

    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(executor, _search_chromadb, query_embedding, query)

    items = _parse_search_results(results)

    query_time = (time.time() - start_time) * 1000

    logger.info(f"Search completed in {query_time:.2f}ms, found {len(items)} results")

    return KnowledgeSearchResponse(
        results=items,
        total_count=len(items),
        query_time_ms=query_time,
    )


def _get_stats_from_chromadb() -> dict:
    """Get statistics from ChromaDB."""
    try:
        collection = get_knowledge_collection()

        results = collection.get(include=["metadatas"])

        return results

    except Exception as e:
        logger.error(f"Error getting knowledge base stats: {e}")
        raise


async def get_knowledge_stats() -> KnowledgeStatsResponse:
    """Get knowledge base statistics."""
    logger.info("Retrieving knowledge base statistics")

    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(executor, _get_stats_from_chromadb)

    total_items = len(results.get("ids", []))
    metadatas = results.get("metadatas", [])

    models = [m.get("model", "unknown") for m in metadatas]
    models_distribution = dict(Counter(models))

    logger.info(f"Retrieved stats: {total_items} total items")

    return KnowledgeStatsResponse(
        total_items=total_items,
        models_distribution=models_distribution,
    )
