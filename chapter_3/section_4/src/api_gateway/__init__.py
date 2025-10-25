"""LLM API Gateway package.

This package implements the API Gateway pattern for LLM API access,
providing centralized management, security, and observability.
"""

from src.api_gateway.auth import GatewayAuthenticator, verify_api_token
from src.api_gateway.gateway_service import GatewayService, gateway_service
from src.api_gateway.models import (
    GatewayErrorResponse,
    GatewayHealthResponse,
    GatewayRequest,
    GatewayResponse,
)
from src.api_gateway.monitoring import GatewayMonitor, gateway_monitor

__all__ = [
    "GatewayAuthenticator",
    "verify_api_token",
    "GatewayService",
    "gateway_service",
    "GatewayRequest",
    "GatewayResponse",
    "GatewayHealthResponse",
    "GatewayErrorResponse",
    "GatewayMonitor",
    "gateway_monitor",
]
