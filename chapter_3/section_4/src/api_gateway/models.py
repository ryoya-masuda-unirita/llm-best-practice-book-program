"""Gateway models for LLM API Gateway requests and responses."""

import time
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class GatewayRequest(BaseModel):
    """Request model for LLM API Gateway."""

    provider: str = Field(..., description="LLM provider (openai or gemini)")
    model: str = Field(..., description="Model name to use")
    prompt: list[dict[str, str]] = Field(..., description="Prompt messages")
    temperature: Optional[float] = Field(default=1.0, description="Temperature for generation", ge=0.0, le=2.0)
    response_format: Optional[dict[str, Any]] = Field(default=None, description="Response format schema")
    client_id: Optional[str] = Field(default=None, description="Client identifier for tracking and rate limiting")
    api_token: str = Field(..., description="API token for gateway authentication")


class GatewayResponse(BaseModel):
    """Response model for LLM API Gateway."""

    content: Any = Field(..., description="Generated content from LLM")
    provider: str = Field(..., description="LLM provider used")
    model: str = Field(..., description="Model used")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    request_id: str = Field(..., description="Unique request ID for tracking")
    cached: bool = Field(default=False, description="Whether response was served from cache")


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
