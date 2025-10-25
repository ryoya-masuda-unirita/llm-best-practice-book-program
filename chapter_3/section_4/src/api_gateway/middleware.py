"""Middleware for LLM API Gateway.

This module provides middleware components for request/response tracking,
logging, and monitoring.
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.logger import make_logger

logger = make_logger(__name__)


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware to track all requests and responses through the gateway.

    This provides visibility into all traffic flowing through the gateway,
    helping with debugging, monitoring, and optimization.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and track its lifecycle.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler

        Returns:
            The HTTP response
        """
        start_time = time.time()

        # Log incoming request
        logger.info(
            f"Incoming request: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

        try:
            # Process the request
            response = await call_next(request)

            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"status={response.status_code} time={processing_time:.2f}ms"
            )

            # Add custom headers for observability
            response.headers["X-Processing-Time-Ms"] = str(round(processing_time, 2))
            response.headers["X-Gateway-Version"] = "1.0.0"

            return response

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"error={type(e).__name__}: {str(e)} time={processing_time:.2f}ms"
            )
            raise


class CORSMiddleware:
    """CORS middleware for gateway (if needed for frontend access)."""

    # This would be configured based on specific requirements
    # For now, we'll let FastAPI's built-in CORS handle this
    pass
