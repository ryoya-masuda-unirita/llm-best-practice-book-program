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

    Provides centralized monitoring so all LLM API usage can be tracked and analyzed.
    """

    def __init__(self):
        logger.info("Gateway Monitor initialized")

    def generate_request_id(self) -> str:
        """Generate a unique request ID for tracking."""
        return str(uuid.uuid4())

    def log_request(
        self,
        request_id: str,
        provider: str,
        model: str,
        client_id: Optional[str] = None,
    ) -> None:
        """Log an incoming gateway request."""
        logger.info(f"[REQUEST] id={request_id} | provider={provider} | model={model} | client={client_id}")

    def log_response(
        self,
        request_id: str,
        provider: str,
        model: str,
        processing_time_ms: float,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Log a gateway response."""
        status = "SUCCESS" if success else "FAILURE"

        log_msg = (
            f"[RESPONSE] id={request_id} | status={status} | "
            f"provider={provider} | model={model} | "
            f"time={processing_time_ms:.2f}ms"
        )

        if error:
            log_msg += f" | error={error}"

        if success:
            logger.info(log_msg)
        else:
            logger.error(log_msg)

    def log_error(
        self,
        request_id: str,
        error_type: str,
        error_message: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        """Log an error event."""
        log_msg = f"[ERROR] id={request_id} | type={error_type} | message={error_message}"

        if provider:
            log_msg += f" | provider={provider}"
        if model:
            log_msg += f" | model={model}"

        logger.error(log_msg)


# Global monitor instance
gateway_monitor = GatewayMonitor()
