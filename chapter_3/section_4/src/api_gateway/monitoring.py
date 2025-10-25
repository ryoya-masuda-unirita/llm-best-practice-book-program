"""Monitoring and logging module for LLM API Gateway.

This module provides structured logging and monitoring capabilities
to track API usage, performance metrics, and errors.
"""

import uuid
from typing import Optional

from src.logger import make_logger

logger = make_logger(__name__)


class GatewayMonitor:
    """Monitors and logs gateway operations for observability.

    This provides centralized monitoring so that all LLM API usage can be
    tracked, analyzed, and optimized from a single point.
    """

    def __init__(self):
        """Initialize the gateway monitor."""
        logger.info("Gateway Monitor initialized")

    def generate_request_id(self) -> str:
        """Generate a unique request ID for tracking.

        Returns:
            A unique request identifier
        """
        return str(uuid.uuid4())

    def log_request(
        self,
        request_id: str,
        provider: str,
        model: str,
        client_id: Optional[str] = None,
    ) -> None:
        """Log an incoming gateway request.

        Args:
            request_id: Unique request identifier
            provider: LLM provider name
            model: Model name
            client_id: Client identifier
        """
        logger.info(f"[REQUEST] id={request_id} | provider={provider} | model={model} | client={client_id}")

    def log_response(
        self,
        request_id: str,
        provider: str,
        model: str,
        processing_time_ms: float,
        success: bool,
        cached: bool = False,
        error: Optional[str] = None,
    ) -> None:
        """Log a gateway response.

        Args:
            request_id: Unique request identifier
            provider: LLM provider name
            model: Model name
            processing_time_ms: Processing time in milliseconds
            success: Whether the request was successful
            cached: Whether response was served from cache
            error: Error message if request failed
        """
        status = "SUCCESS" if success else "FAILURE"
        cache_status = "CACHED" if cached else "FRESH"

        log_msg = (
            f"[RESPONSE] id={request_id} | status={status} | "
            f"provider={provider} | model={model} | "
            f"time={processing_time_ms:.2f}ms | cache={cache_status}"
        )

        if error:
            log_msg += f" | error={error}"

        if success:
            logger.info(log_msg)
        else:
            logger.error(log_msg)

    def log_cache_hit(self, request_id: str, provider: str, model: str) -> None:
        """Log a cache hit event.

        Args:
            request_id: Unique request identifier
            provider: LLM provider name
            model: Model name
        """
        logger.info(f"[CACHE HIT] id={request_id} | provider={provider} | model={model}")

    def log_cache_miss(self, request_id: str, provider: str, model: str) -> None:
        """Log a cache miss event.

        Args:
            request_id: Unique request identifier
            provider: LLM provider name
            model: Model name
        """
        logger.debug(f"[CACHE MISS] id={request_id} | provider={provider} | model={model}")

    def log_error(
        self,
        request_id: str,
        error_type: str,
        error_message: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        """Log an error event.

        Args:
            request_id: Unique request identifier
            error_type: Type of error
            error_message: Error message
            provider: LLM provider name (if applicable)
            model: Model name (if applicable)
        """
        log_msg = f"[ERROR] id={request_id} | type={error_type} | message={error_message}"

        if provider:
            log_msg += f" | provider={provider}"
        if model:
            log_msg += f" | model={model}"

        logger.error(log_msg)

    def log_authentication_failure(self, client_id: Optional[str] = None) -> None:
        """Log an authentication failure.

        Args:
            client_id: Client identifier (if available)
        """
        logger.warning(f"[AUTH FAILURE] client={client_id or 'unknown'}")

    def log_rate_limit_exceeded(
        self,
        client_id: str,
        limit: int,
        current: int,
    ) -> None:
        """Log a rate limit exceeded event.

        Args:
            client_id: Client identifier
            limit: Rate limit threshold
            current: Current request count
        """
        logger.warning(f"[RATE LIMIT] client={client_id} | limit={limit} | current={current}")


# Global monitor instance
gateway_monitor = GatewayMonitor()
