"""Knowledge Base API Server - CQRS implementation with separate Command and Query endpoints."""

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from src.logger import make_logger
from src.model.knowledge import (
    KnowledgeRegisterCommand,
    KnowledgeRegisterResponse,
    KnowledgeSearchQuery,
    KnowledgeSearchResponse,
    KnowledgeStatsResponse,
)
from src.model.model import HealthResponse
from src.service.knowledge_command import register_knowledge_async
from src.service.knowledge_query import get_knowledge_stats, search_knowledge

logger = make_logger(__name__)

app = FastAPI(
    title="Knowledge Base API Server (CQRS)",
    description="Separate Command and Query endpoints for knowledge base operations",
    version="1.0.0",
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.post(
    "/command/register",
    response_model=KnowledgeRegisterResponse,
    tags=["Command"],
    summary="Register knowledge (async)",
    description="""
    Register new knowledge to the knowledge base asynchronously.

    This is a Command operation that accepts the request immediately
    and processes it in the background without blocking.

    **Characteristics:**
    - High throughput
    - Eventual consistency
    - Returns immediately with job ID
    - Optimized for write operations
    """,
)
async def register_knowledge(command: KnowledgeRegisterCommand, background_tasks: BackgroundTasks):
    """Register knowledge asynchronously."""
    try:
        job_id = await register_knowledge_async(command)

        logger.info(f"Knowledge registration command accepted with job_id: {job_id}")

        return KnowledgeRegisterResponse(
            job_id=job_id,
            status="accepted",
            message="Knowledge registration queued for processing",
        )

    except Exception as e:
        logger.error(f"Error accepting knowledge registration command: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error accepting command: {str(e)}",
        )


@app.post(
    "/query/search",
    response_model=KnowledgeSearchResponse,
    tags=["Query"],
    summary="Search knowledge (sync)",
    description="""
    Search the knowledge base for similar items synchronously.

    This is a Query operation optimized for low latency reads.

    **Characteristics:**
    - Low latency
    - Immediate results
    - Read-only operation
    - Optimized for search performance
    """,
)
async def search_knowledge_endpoint(query: KnowledgeSearchQuery):
    """Search knowledge base synchronously."""
    try:
        results = await search_knowledge(query)

        logger.info(f"Search query completed: found {results.total_count} results in {results.query_time_ms:.2f}ms")

        return results

    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching knowledge: {str(e)}",
        )


@app.get(
    "/query/stats",
    response_model=KnowledgeStatsResponse,
    tags=["Query"],
    summary="Get knowledge base statistics",
    description="""
    Get aggregate statistics about the knowledge base.

    This is a Query operation that provides insights into
    the stored knowledge without modifying any data.

    **Characteristics:**
    - Read-only
    - Aggregate data
    - Performance metrics
    """,
)
async def get_stats():
    """Get knowledge base statistics."""
    try:
        stats = await get_knowledge_stats()

        logger.info(f"Stats retrieved: {stats.total_items} total items")

        return stats

    except Exception as e:
        logger.error(f"Error getting knowledge base stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting stats: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
