"""LLM API Gateway Server - FastAPI application that centralizes LLM API access.

This gateway provides:
- Centralized API key management
- Authentication and authorization
- Retry logic with exponential backoff
- Structured logging and monitoring
- Response caching (optional)
- Unified interface for multiple LLM providers
"""

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from src.api_gateway.auth import verify_api_token
from src.api_gateway.gateway_service import gateway_service
from src.api_gateway.middleware import RequestTrackingMiddleware
from src.api_gateway.models import (
    GatewayErrorResponse,
    GatewayHealthResponse,
    GatewayRequest,
    GatewayResponse,
)
from src.api_gateway.monitoring import gateway_monitor
from src.logger import make_logger

logger = make_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title="LLM API Gateway",
    description="Centralized gateway for managing and routing LLM API requests",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add middleware
app.add_middleware(RequestTrackingMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {type(exc).__name__}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=GatewayErrorResponse(
            error=str(exc),
            error_type=type(exc).__name__,
        ).model_dump(),
    )


@app.get("/health", response_model=GatewayHealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint for the gateway.

    Returns the health status of the gateway and availability of LLM providers.
    """
    # In production, you would check actual provider availability
    providers_available = {
        "openai": True,
        "gemini": True,
    }

    return GatewayHealthResponse(providers_available=providers_available)


@app.post("/v1/generate", response_model=GatewayResponse, tags=["Gateway"])
async def generate(
    request: GatewayRequest,
    client_id: str = Depends(verify_api_token),
):
    """Generate content using LLM through the gateway.

    This endpoint centralizes all LLM API calls, providing:
    - Secure API key management (keys never exposed to clients)
    - Automatic retry with exponential backoff
    - Request/response logging and monitoring
    - Optional response caching
    - Consistent error handling

    Args:
        request: Gateway request with LLM parameters
        client_id: Authenticated client identifier (from token)

    Returns:
        Gateway response with generated content and metadata

    Raises:
        HTTPException: If request fails or provider is not supported
    """
    # Generate unique request ID
    request_id = gateway_monitor.generate_request_id()

    try:
        # Process the request through the gateway
        content, processing_time_ms, cached = await gateway_service.process_request(
            request_id=request_id,
            provider=request.provider,
            model=request.model,
            prompt=request.prompt,
            temperature=request.temperature,
            response_format=request.response_format,
            client_id=client_id,
        )

        return GatewayResponse(
            content=content,
            provider=request.provider,
            model=request.model,
            processing_time_ms=processing_time_ms,
            request_id=request_id,
            cached=cached,
        )

    except ValueError as e:
        # Invalid provider or configuration
        gateway_monitor.log_error(
            request_id,
            "ValidationError",
            str(e),
            request.provider,
            request.model,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=GatewayErrorResponse(
                error=str(e),
                error_type="ValidationError",
                request_id=request_id,
            ).model_dump(),
        )

    except Exception as e:
        # Other errors (network issues, API errors, etc.)
        gateway_monitor.log_error(
            request_id,
            type(e).__name__,
            str(e),
            request.provider,
            request.model,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=GatewayErrorResponse(
                error=str(e),
                error_type=type(e).__name__,
                request_id=request_id,
            ).model_dump(),
        )


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting LLM API Gateway Server...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info",
    )
