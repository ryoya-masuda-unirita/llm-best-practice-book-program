"""Reverse Proxy Server with rate limiting, circuit breaker, retry, and queueing."""

import asyncio
import time

import httpx
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from httpx_retries import Retry, RetryTransport
from pydantic import BaseModel, ConfigDict, Field

from src.config import config
from src.logger import make_logger
from src.model.model import LLMRequest, LLMResponse
from src.proxy.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenError
from src.proxy.rate_limiter import RateLimiterConfig, TokenBucketRateLimiter
from src.proxy.request_queue import QueueConfig, RequestQueue, RequestQueueFullError

logger = make_logger(__name__)

rate_limiter = TokenBucketRateLimiter(
    RateLimiterConfig(
        max_requests=10,  # 10 requests per second
        window_seconds=1.0,
    )
)

circuit_breaker = CircuitBreaker(
    CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=2,
        timeout_seconds=30.0,
        error_rate_threshold=0.5,
        min_requests=10,
    )
)

request_queue = RequestQueue(
    QueueConfig(
        max_queue_size=100,
        request_timeout=300.0,
    )
)

app = FastAPI(
    title="LLM Proxy Server",
    description="Reverse proxy with rate limiting, circuit breaker, retry, and queueing",
    version="1.0.0",
)


class ProxyMetrics(BaseModel):
    """Proxy server metrics."""

    rate_limiter: dict = Field(..., description="Rate limiter metrics")
    circuit_breaker: dict = Field(..., description="Circuit breaker metrics")
    request_queue: dict = Field(..., description="Request queue metrics")
    timestamp: float = Field(default_factory=time.time)


class ProxyHealthResponse(BaseModel):
    """Proxy server health check response."""

    status: str = Field(..., description="Health status")
    backend_url: str = Field(..., description="Backend LLM API URL")
    timestamp: float = Field(default_factory=time.time)


class ProxyMetadata(BaseModel):
    """Metadata added by proxy to track request processing."""

    processing_time_ms: float = Field(..., description="Total processing time through proxy in milliseconds")
    circuit_state: str = Field(..., description="Circuit breaker state when request was processed")
    queue_size: int = Field(..., description="Queue size after processing request")


class BackendHealthResponse(BaseModel):
    """Backend health check response with proxy metadata."""

    model_config = ConfigDict(populate_by_name=True)

    status: str = Field(..., description="Health status from backend")
    timestamp: float = Field(..., description="Timestamp from backend")
    proxy_metadata: ProxyMetadata = Field(..., description="Proxy processing metadata", alias="_proxy_metadata")


class ProxiedLLMResponse(LLMResponse):
    """LLM response with proxy metadata."""

    model_config = ConfigDict(populate_by_name=True)

    proxy_metadata: ProxyMetadata = Field(..., description="Proxy processing metadata", alias="_proxy_metadata")


async def make_request_with_retry(
    method: str,
    url: str,
    json_data: dict | None = None,
    max_retries: int = config.proxy_max_retries,
) -> dict:
    """
    Make HTTP request with exponential backoff retry logic.

    Raises:
        HTTPException: If all retries fail or on client errors (4xx except 429)
    """
    retry_policy = Retry(
        total=max_retries,
        backoff_factor=config.proxy_retry_backoff / 2,  # Divide by 2 because formula is backoff_factor * (2 ** n)
        status_forcelist=[429] + list(range(500, 600)),
    )
    retry_transport = RetryTransport(transport=httpx.AsyncHTTPTransport(), retry=retry_policy)

    try:
        async with httpx.AsyncClient(transport=retry_transport, timeout=60.0) as client:
            if method == "GET":
                response = await client.get(url)
            elif method == "POST":
                response = await client.post(url, json=json_data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()

            return response.json()

    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code

        if status_code == 429:
            logger.error(f"Rate limit exceeded after {max_retries} retries")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded after {max_retries} retries",
            )
        elif 500 <= status_code < 600:
            logger.error(f"Server error {status_code} after {max_retries} retries: {e}")
            raise HTTPException(
                status_code=status_code,
                detail=f"Backend server error after retries: {str(e)}",
            )
        else:
            logger.error(f"Client error {status_code}: {e}")
            raise HTTPException(
                status_code=status_code,
                detail=f"Backend client error: {str(e)}",
            )

    except httpx.RequestError as e:
        logger.error(f"Request error after {max_retries} retries: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to backend after {max_retries} retries: {str(e)}",
        )


async def process_queued_request(queue_item: dict):
    """Process a request from the queue."""
    request_data = queue_item["data"]
    future = queue_item["future"]

    try:
        acquired = await rate_limiter.acquire(timeout=30.0)
        if not acquired:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit timeout",
            )

        result = await circuit_breaker.call(
            make_request_with_retry,
            method=request_data["method"],
            url=request_data["url"],
            json_data=request_data.get("json"),
        )

        request_queue.complete_request(future, result=result)

    except Exception as e:
        logger.error(f"Error processing queued request: {e}")
        request_queue.complete_request(future, exception=e)


@app.on_event("startup")
async def startup_event():
    """Start background task for processing queue."""
    asyncio.create_task(queue_processor())
    logger.info("Proxy server started. Queue processor running.")


async def queue_processor():
    """Background task to process queued requests."""
    logger.info("Queue processor started")

    while True:
        try:
            queue_item = await request_queue.dequeue()
            asyncio.create_task(process_queued_request(queue_item))

        except Exception as e:
            logger.error(f"Error in queue processor: {e}")
            await asyncio.sleep(0.1)


@app.get("/proxy-health", response_model=ProxyHealthResponse, tags=["Proxy Monitoring"])
async def proxy_health_check():
    """
    Proxy server health check endpoint.

    This checks the proxy server's own health and its ability to reach the backend.
    This endpoint does NOT go through rate limiting or circuit breaker.
    For controlled access to backend health, use GET /health instead.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{config.backend_url}/health")
            response.raise_for_status()

        return ProxyHealthResponse(
            status="healthy",
            backend_url=config.backend_url,
        )
    except Exception as e:
        logger.error(f"Proxy health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "backend_url": config.backend_url,
                "error": str(e),
                "timestamp": time.time(),
            },
        )


@app.get("/metrics", response_model=ProxyMetrics, tags=["Monitoring"])
async def get_metrics():
    """Get proxy server metrics."""
    return ProxyMetrics(
        rate_limiter={
            "available_tokens": await rate_limiter.get_available_tokens(),
            "max_requests": rate_limiter.config.max_requests,
            "window_seconds": rate_limiter.config.window_seconds,
        },
        circuit_breaker=await circuit_breaker.get_metrics(),
        request_queue=await request_queue.get_metrics(),
    )


@app.post("/circuit-breaker/reset", tags=["Monitoring"])
async def reset_circuit_breaker():
    """Manually reset the circuit breaker."""
    await circuit_breaker.reset()
    return {"message": "Circuit breaker reset to CLOSED state"}


@app.get("/health", response_model=BackendHealthResponse, tags=["Backend API"])
async def backend_health_check():
    """
    Backend health check endpoint with full access control.

    This endpoint proxies the backend's /health endpoint and applies:
    - Request queueing for handling bursts
    - Rate limiting with token bucket algorithm
    - Circuit breaker for preventing cascading failures
    - Automatic retry with exponential backoff
    """
    start_time = time.time()

    try:
        backend_url = f"{config.backend_url}/health"
        request_data = {
            "method": "GET",
            "url": backend_url,
            "json": None,
        }

        logger.info(f"Proxying GET request to {backend_url} (with access controls)")

        try:
            result = await request_queue.enqueue(request_data)

            processing_time = (time.time() - start_time) * 1000

            logger.info(
                f"Health check completed successfully in {processing_time:.2f}ms "
                f"(queue size: {request_queue.get_size()})"
            )

            response_model = BackendHealthResponse(
                status=result.get("status", "unknown"),
                timestamp=result.get("timestamp", time.time()),
                _proxy_metadata=ProxyMetadata(
                    processing_time_ms=processing_time,
                    circuit_state=(await circuit_breaker.get_state()).value,
                    queue_size=request_queue.get_size(),
                ),
            )

            return response_model

        except RequestQueueFullError as e:
            logger.error(f"Request queue full: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e),
            )

        except CircuitBreakerOpenError as e:
            logger.error(f"Circuit breaker open: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Backend health check unavailable (circuit breaker open)",
            )

        except asyncio.TimeoutError:
            logger.error("Health check request timeout in queue")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Health check request timeout",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in health check proxy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Proxy error: {str(e)}",
        )


@app.post("/generate", response_model=ProxiedLLMResponse, tags=["Backend API"])
async def backend_generate_character(request: LLMRequest):
    """
    Backend character generation endpoint with full access control.

    This endpoint proxies the backend's /generate endpoint and applies:
    - Request queueing for handling bursts
    - Rate limiting with token bucket algorithm
    - Circuit breaker for preventing cascading failures
    - Automatic retry with exponential backoff
    """
    start_time = time.time()

    try:
        backend_url = f"{config.backend_url}/generate"
        request_body = request.model_dump()
        request_data = {
            "method": "POST",
            "url": backend_url,
            "json": request_body,
        }

        logger.info(f"Proxying POST request to {backend_url} (with access controls)")

        try:
            result = await request_queue.enqueue(request_data)

            processing_time = (time.time() - start_time) * 1000

            logger.info(
                f"Generate request completed successfully in {processing_time:.2f}ms "
                f"(queue size: {request_queue.get_size()})"
            )

            backend_response = LLMResponse(**result)

            response_model = ProxiedLLMResponse(
                character=backend_response.character,
                provider=backend_response.provider,
                model=backend_response.model,
                processing_time_ms=backend_response.processing_time_ms,
                _proxy_metadata=ProxyMetadata(
                    processing_time_ms=processing_time,
                    circuit_state=(await circuit_breaker.get_state()).value,
                    queue_size=request_queue.get_size(),
                ),
            )

            return response_model

        except RequestQueueFullError as e:
            logger.error(f"Request queue full: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e),
            )

        except CircuitBreakerOpenError as e:
            logger.error(f"Circuit breaker open: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable (circuit breaker open)",
            )

        except asyncio.TimeoutError:
            logger.error("Generate request timeout in queue")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request timeout",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate proxy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Proxy error: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
