"""LLM API Server - FastAPI application that exposes LLM functionality.

This server implements the CQRS-based pattern with separated storage and execution layers.
"""

import time

from fastapi import FastAPI, HTTPException, status

from src.client.cache_client import redis_client
from src.client.llm_client import GeminiModel, LLMProvider, OpenAIModel
from src.config import CacheBackend, config
from src.logger import make_logger
from src.model.model import HealthResponse, LLMRequest, LLMResponse
from src.prompt.prompt import make_prompt
from src.service import get_llm_service
from src.service.storage import CachedLLMService

logger = make_logger(__name__)

app = FastAPI(
    title="LLM API Server",
    description="API server for generating character descriptions using LLM with CQRS pattern",
    version="2.0.0",
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting up LLM API server...")
    logger.info(f"Cache enabled: {config.cache_enabled}")
    logger.info(f"Cache backend: {config.cache_backend}")

    # Initialize Redis connection if using Redis backend
    if config.cache_enabled and config.cache_backend == CacheBackend.REDIS:
        try:
            await redis_client.connect()
            logger.info("Redis connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            logger.warning("Server will continue without Redis caching")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down LLM API server...")

    # Close Redis connection if it was used
    if config.cache_enabled and config.cache_backend == CacheBackend.REDIS:
        try:
            await redis_client.disconnect()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.post("/generate", response_model=LLMResponse, tags=["LLM"])
async def generate_character(request: LLMRequest):
    """
    Generate a character using the specified LLM provider and model.

    This endpoint uses the CQRS-based pattern with separated storage and execution layers.
    Responses are cached based on configuration to improve performance and reduce API costs.
    """
    start_time = time.time()

    try:
        # Validate model for provider
        if request.provider == LLMProvider.OPENAI and request.model not in OpenAIModel.list_str():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model '{request.model}' for provider '{request.provider.value}'",
            )
        if request.provider == LLMProvider.GEMINI and request.model not in GeminiModel.list_str():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model '{request.model}' for provider '{request.provider.value}'",
            )

        prompt = make_prompt(character_request=request.character_request)

        # Get LLM service instance (uses factory pattern with DI)
        llm_service = get_llm_service()

        # Generate character using the service layer
        # The service will automatically handle caching if enabled
        character = await llm_service.generate_character(
            prompt=prompt, model=request.model, provider=request.provider.value
        )

        processing_time = (time.time() - start_time) * 1000

        logger.info(
            f"Successfully generated character using {request.provider.value}/{request.model} "
            f"in {processing_time:.2f}ms"
        )

        return LLMResponse(
            character=character,
            provider=request.provider.value,
            model=request.model,
            processing_time_ms=processing_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating character: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating character: {str(e)}",
        )


@app.get("/metrics", tags=["Monitoring"])
async def get_cache_metrics():
    """
    Get cache performance metrics.

    Returns statistics about cache hits, misses, and hit rate.
    Only available when caching is enabled.
    """
    try:
        llm_service = get_llm_service()

        # Check if service is CachedLLMService to access metrics
        if isinstance(llm_service, CachedLLMService):
            return llm_service.get_cache_metrics()
        else:
            return {
                "cache_enabled": False,
                "message": "Caching is not enabled",
            }

    except Exception as e:
        logger.error(f"Error retrieving cache metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving cache metrics: {str(e)}",
        )


@app.delete("/cache/{cache_key}", tags=["Cache Management"])
async def invalidate_cache(cache_key: str):
    """
    Invalidate a specific cache entry.

    This endpoint allows manual cache invalidation for specific keys,
    useful when you need to force fresh data retrieval.
    """
    try:
        llm_service = get_llm_service()
        result = await llm_service.invalidate_cache(cache_key)

        return {
            "cache_key": cache_key,
            "invalidated": result,
            "message": "Cache invalidated successfully" if result else "Cache key not found or caching disabled",
        }

    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error invalidating cache: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
