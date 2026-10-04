"""Gateway models for LLM API Gateway requests and responses."""

import time
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class GatewayRequest(BaseModel):
    """Request model for LLM API Gateway."""

    provider: str = Field(..., description="LLM provider (openai or anthropic)")
    model: str = Field(..., description="Model name to use")
    prompt: list[dict[str, str]] = Field(..., description="Prompt messages")
    response_format: dict[str, Any] = Field(..., description="Response format schema")
    client_id: Optional[str] = Field(default=None, description="Client identifier for tracking")


class GatewayResponse(BaseModel):
    """Response model for LLM API Gateway."""

    content: Any = Field(..., description="Generated content from LLM")
    provider: str = Field(..., description="LLM provider used")
    model: str = Field(..., description="Model used")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    request_id: str = Field(..., description="Unique request ID for tracking")


class GatewayHealthResponse(BaseModel):
    """Health check response for gateway."""

    status: Literal["healthy"] = "healthy"
    timestamp: float = Field(default_factory=time.time)
    providers_available: dict[str, bool] = Field(default_factory=dict, description="Provider availability status")


class GatewayErrorResponse(BaseModel):
    """Error response model for gateway."""

    error: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Error type")
    request_id: Optional[str] = Field(default=None, description="Request ID if available")
    timestamp: float = Field(default_factory=time.time)
