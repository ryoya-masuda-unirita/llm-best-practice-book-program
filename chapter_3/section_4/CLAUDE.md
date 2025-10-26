# Chapter 3 Section 4: LLM API Gateway

## Overview

This project demonstrates the implementation of an **LLM API Gateway** - a centralized service that manages and routes LLM API requests. The gateway provides secure API key management, unified access to multiple LLM providers (OpenAI and Gemini), structured logging, and monitoring capabilities. This architecture pattern is essential for enterprise environments and microservices architectures where multiple services need to consume LLM capabilities without managing API keys directly.

The implementation showcases how to build a production-ready API gateway that acts as a single point of entry for all LLM interactions, providing benefits such as:
- Centralized API key management and security
- Unified interface across multiple LLM providers
- Request/response logging and monitoring
- Simplified client applications

## Features

- **Centralized API Gateway**: Single entry point for all LLM API requests
- **Multi-Provider Support**: Seamless integration with OpenAI and Gemini APIs
- **Secure API Key Management**: API keys stored and managed only in the gateway
- **Structured Logging**: Comprehensive request/response logging for monitoring
- **Dynamic Schema Conversion**: Automatic conversion of JSON schemas to Pydantic models
- **Health Monitoring**: Built-in health check endpoints
- **Docker Containerization**: Production-ready Docker setup with separate gateway and backend services
- **Gateway Client Library**: Easy-to-use client for consuming the gateway API
- **Error Handling**: Robust error handling and monitoring
- **Type Safety**: Full type safety using Pydantic models throughout

## Project Structure

### Directory Structure

```
chapter_3/section_4/
├── src/
│   ├── __init__.py
│   ├── config.py                     # Configuration management
│   ├── logger.py                     # Logging setup
│   │
│   ├── api_gateway/                  # API Gateway Service
│   │   ├── __init__.py
│   │   ├── gateway_server.py         # FastAPI gateway server
│   │   ├── gateway_service.py        # Core gateway logic
│   │   ├── models.py                 # Gateway request/response models
│   │   ├── api_key_manager.py        # Centralized API key management
│   │   ├── monitoring.py             # Logging and monitoring
│   │   └── example_client.py         # Example usage of gateway
│   │
│   ├── client/                       # Client Library
│   │   ├── __init__.py
│   │   ├── llm_client.py             # Direct LLM client (legacy)
│   │   └── gateway_client.py         # Gateway client library
│   │
│   ├── api/                          # Backend API Service
│   │   ├── __init__.py
│   │   └── llm_server.py             # Backend server using gateway
│   │
│   ├── service/                      # Business Logic
│   │   ├── __init__.py
│   │   └── request_llm.py            # LLM request service
│   │
│   ├── model/                        # Data Models
│   │   ├── __init__.py
│   │   └── model.py                  # Pydantic models
│   │
│   └── prompt/                       # Prompt Management
│       ├── __init__.py
│       └── prompt.py                 # Prompt generation
│
├── docker-compose.yml                # Docker Compose configuration
├── Dockerfile.backend                # Backend service Dockerfile
├── Dockerfile.gateway                # Gateway service Dockerfile
├── Makefile                          # Build and run commands
├── pyproject.toml                    # Project dependencies
├── .envrc.example                    # Environment variables template
├── README.md                         # Project documentation
└── CLAUDE.md                         # This file
```

### Architecture

The project implements a microservices architecture with clear separation between the API Gateway and backend services:

```
+-----------------------------------------------------------+
|                    Client Applications                    |
|           (Frontend, Microservices, etc.)                 |
+---------------------------+-------------------------------+
                            |
                            | HTTP Requests (No API Keys)
                            v
+-----------------------------------------------------------+
|              LLM API Gateway (Port 8080)                  |
|                                                           |
|  +-----------------------------------------------------+  |
|  |       Gateway Server (gateway_server.py)            |  |
|  |  - Request routing                                  |  |
|  |  - Schema conversion                                |  |
|  |  - Error handling                                   |  |
|  +---------------------------+-------------------------+  |
|                              |                            |
|  +---------------------------v-------------------------+  |
|  |      Gateway Service (gateway_service.py)           |  |
|  |  - Provider routing                                 |  |
|  |  - API client management                            |  |
|  +---------------------------+-------------------------+  |
|                              |                            |
|  +---------------------------v-------------------------+  |
|  |      API Key Manager (api_key_manager.py)           |  |
|  |  - Secure key storage                               |  |
|  |  - Provider validation                              |  |
|  +-----------------------------------------------------+  |
|                                                           |
|  +-----------------------------------------------------+  |
|  |          Monitoring (monitoring.py)                 |  |
|  |  - Request/response logging                         |  |
|  |  - Performance metrics                              |  |
|  +-----------------------------------------------------+  |
+---------------------------+-------------------------------+
                            |
                            | API Calls with Keys
                            |
              +-------------+-------------+
              |                           |
              v                           v
      +---------------+           +---------------+
      |  OpenAI API   |           |  Gemini API   |
      +---------------+           +---------------+


+-----------------------------------------------------------+
|             Backend Service (Port 8000)                   |
|                                                           |
|  +-----------------------------------------------------+  |
|  |        Backend Server (llm_server.py)               |  |
|  |  - Business endpoints                               |  |
|  |  - Uses Gateway Client                              |  |
|  +---------------------------+-------------------------+  |
|                              |                            |
|  +---------------------------v-------------------------+  |
|  |      Gateway Client (gateway_client.py)             |  |
|  |  - HTTP client for gateway                          |  |
|  |  - Request/response handling                        |  |
|  +-----------------------------------------------------+  |
+---------------------------+-------------------------------+
                            |
                            | Internal HTTP
                            v
                   (Back to Gateway)
```

### Implementation Details

#### 1. API Gateway Server (`src/api_gateway/gateway_server.py`)

The gateway server is a FastAPI application that exposes REST endpoints for LLM operations:

```python
@app.post("/v1/generate", response_model=GatewayResponse, tags=["Gateway"])
async def generate(request: GatewayRequest):
    """Generate content using LLM through the gateway."""
    # Convert JSON schema to Pydantic model
    response_format_model = json_schema_to_pydantic(request.response_format)

    # Process through gateway service
    content, processing_time_ms = await gateway_service.process_request(
        request_id=request_id,
        provider=request.provider,
        model=request.model,
        prompt=request.prompt,
        response_format=response_format_model,
        client_id=request.client_id,
    )

    return GatewayResponse(...)
```

**Key Features**:
- Dynamic Pydantic model creation from JSON schemas
- Comprehensive error handling with typed error responses
- Health check endpoint for monitoring
- Global exception handler for unhandled errors

**Schema Conversion**:
The gateway receives JSON schemas from clients and converts them to Pydantic models dynamically:
```python
def json_schema_to_pydantic(json_schema: dict[str, Any]) -> type[BaseModel]:
    """Convert a JSON schema to a Pydantic model."""
    # Handles nested models, arrays, enums, and references
    # Recreates the original Pydantic model structure
```

#### 2. Gateway Service (`src/api_gateway/gateway_service.py`)

Core service that routes requests to appropriate LLM providers:

```python
class GatewayService:
    async def process_request(
        self,
        request_id: str,
        provider: str,
        model: str,
        prompt: list[dict],
        response_format: BaseModel,
        client_id: Optional[str] = None,
    ) -> tuple[Any, float]:
        """Process an LLM request through the gateway."""
        # Validate provider
        if not api_key_manager.is_provider_supported(provider):
            raise ValueError(f"Unsupported provider: {provider}")

        # Route to appropriate provider
        if provider.lower() == "openai":
            content = await self._call_openai(...)
        elif provider.lower() == "gemini":
            content = await self._call_gemini(...)
```

**Provider Implementations**:

OpenAI:
```python
async def _call_openai(self, model, prompt, response_format):
    client = self._get_openai_client()
    result = await client.beta.chat.completions.parse(
        model=model,
        messages=prompt,
        response_format=response_format,
    )
    return result.choices[0].message.parsed
```

Gemini:
```python
async def _call_gemini(self, model, prompt, response_format):
    client = self._get_gemini_client()
    result = await client.aio.models.generate_content(
        model=model,
        contents=user_content,
        config=GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_format,
        ),
    )
    return result.parsed
```

#### 3. API Key Manager (`src/api_gateway/api_key_manager.py`)

Centralized management of API keys for different providers:

```python
class APIKeyManager:
    """Manages API keys for different LLM providers."""

    def __init__(self):
        self._provider_keys: Dict[str, Secret[str]] = {
            "openai": config.openai_api_key,
            "gemini": config.gemini_api_key,
        }

    def get_api_key(self, provider: str) -> str:
        """Get the API key for a specific provider."""
        if provider_lower not in self._provider_keys:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        return self._provider_keys[provider_lower]
```

**Benefits**:
- Single source of truth for API keys
- Easy key rotation (update in one place)
- Provider validation
- Keys never exposed to client applications

#### 4. Monitoring (`src/api_gateway/monitoring.py`)

Structured logging for all gateway operations:

```python
class GatewayMonitor:
    def log_request(self, request_id, provider, model, client_id):
        """Log an incoming gateway request."""
        logger.info(
            f"[REQUEST] id={request_id} | provider={provider} | "
            f"model={model} | client={client_id}"
        )

    def log_response(self, request_id, provider, model,
                     processing_time_ms, success, error=None):
        """Log a gateway response."""
        status = "SUCCESS" if success else "FAILURE"
        log_msg = (
            f"[RESPONSE] id={request_id} | status={status} | "
            f"provider={provider} | model={model} | "
            f"time={processing_time_ms:.2f}ms"
        )
```

**Monitoring Features**:
- Unique request ID generation (UUID)
- Request tracking across the system
- Performance metrics (processing time)
- Error logging and categorization

#### 5. Gateway Client (`src/client/gateway_client.py`)

Client library for applications to consume the gateway:

```python
class GatewayClient:
    async def generate(
        self,
        provider: str,
        model: str,
        prompt: list[dict],
        temperature: float = 1.0,
        response_format: Optional[dict] = None,
        client_id: Optional[str] = None,
    ) -> tuple[Any, float, str]:
        """Generate content via the gateway."""
        response = await self.client.post(
            f"{self.gateway_url}/v1/generate",
            json={
                "provider": provider,
                "model": model,
                "prompt": prompt,
                "temperature": temperature,
                "response_format": response_format,
                "client_id": client_id,
            },
        )
        result = response.json()
        return (
            result["content"],
            result["processing_time_ms"],
            result["request_id"],
        )
```

#### 6. Data Models (`src/api_gateway/models.py`)

Type-safe request and response models:

```python
class GatewayRequest(BaseModel):
    provider: str
    model: str
    prompt: list[dict[str, str]]
    response_format: dict[str, Any]
    client_id: Optional[str] = None

class GatewayResponse(BaseModel):
    content: Any
    provider: str
    model: str
    processing_time_ms: float
    request_id: str

class GatewayHealthResponse(BaseModel):
    status: Literal["healthy"] = "healthy"
    timestamp: float
    providers_available: dict[str, bool]
```

## Usage

### Environment Setup

**Requirements**:
- Python 3.13.2 or higher
- Docker and Docker Compose (for containerized deployment)
- OpenAI API key
- Google Gemini API key

**Dependencies**:
- fastapi>=0.115.12
- uvicorn>=0.34.0
- httpx>=0.28.5
- openai>=2.4.0
- google-genai>=1.45.0
- pydantic>=2.12.2
- python-dotenv>=1.1.1

### Setup

1. **Create environment file**:

```bash
# Copy the example file
cp .envrc.example .envrc

# Edit .envrc with your API keys
# .envrc
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
GATEWAY_URL=http://localhost:8080
BACKEND_URL=http://localhost:8000
GATEWAY_TIMEOUT=30.0
```

2. **Install dependencies**:

```bash
# Using uv (recommended)
uv sync

# Using pip
pip install -e .
```

### Running the Services

#### Option 1: Docker Compose (Recommended)

```bash
# Build Docker images
make docker-build

# Start all services
make docker-up

# View logs
make docker-logs

# Stop all services
make docker-down
```

This starts:
- Gateway service on http://localhost:8080
- Backend service on http://localhost:8000

#### Option 2: Local Development

**Terminal 1 - Start Gateway**:
```bash
make run-api-gateway
# Or directly:
uv run uvicorn src.api_gateway.gateway_server:app --host 0.0.0.0 --port 8080 --reload
```

**Terminal 2 - Start Backend**:
```bash
make run-llm-server
# Or directly:
uv run uvicorn src.api.llm_server:app --host 0.0.0.0 --port 8000 --reload
```

### Using the Gateway

#### 1. Health Check

```bash
curl http://localhost:8080/health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": 1729234567.123,
  "providers_available": {
    "openai": true,
    "gemini": true
  }
}
```

#### 2. Generate Content via Gateway

```bash
curl -X POST http://localhost:8080/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "prompt": [
      {
        "role": "system",
        "content": "You are a helpful assistant."
      },
      {
        "role": "user",
        "content": "Say hello!"
      }
    ],
    "response_format": {
      "type": "object",
      "properties": {
        "message": {"type": "string"}
      },
      "required": ["message"]
    },
    "client_id": "test-client"
  }'
```

#### 3. Using the Gateway Client Library

```python
from src.client.gateway_client import GatewayClient
from src.model.model import CharacterResponse

async def example():
    client = GatewayClient()

    # Prepare request
    prompt = [
        {"role": "system", "content": "Generate a character"},
        {"role": "user", "content": "Create a fictional character"}
    ]

    # Get schema from Pydantic model
    schema = CharacterResponse.model_json_schema()

    # Call gateway
    content, processing_time, request_id = await client.generate(
        provider="openai",
        model="gpt-4o-mini",
        prompt=prompt,
        response_format=schema,
        client_id="my-service"
    )

    print(f"Request ID: {request_id}")
    print(f"Processing time: {processing_time:.2f}ms")
    print(f"Content: {content}")
```

#### 4. Run Example Client

```bash
make run-gateway-client
# Or directly:
uv run python -m src.api_gateway.example_client
```

### Output Examples

**Gateway Logs**:
```
[2025-10-26 10:30:45] [INFO] [Gateway Monitor initialized]
[2025-10-26 10:30:45] [INFO] [API Key Manager initialized with 2 providers]
[2025-10-26 10:30:47] [INFO] [REQUEST] id=a1b2c3d4-e5f6-7890-abcd-ef1234567890 | provider=openai | model=gpt-4o-mini | client=test-client
[2025-10-26 10:30:49] [INFO] [RESPONSE] id=a1b2c3d4-e5f6-7890-abcd-ef1234567890 | status=SUCCESS | provider=openai | model=gpt-4o-mini | time=1234.56ms
```

**API Response**:
```json
{
  "content": {
    "first_name": "Aoi",
    "last_name": "Amemiya",
    "gender": "male",
    "age": 28,
    "personalities": [
      {
        "short_personality": "Introverted Thinker",
        "description": "Always thinks deeply and prefers quiet places."
      }
    ]
  },
  "provider": "openai",
  "model": "gpt-4o-mini",
  "processing_time_ms": 1234.56,
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### API Documentation

Once the gateway is running, interactive API documentation is available at:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

## Testing

### Manual Testing

1. **Test Gateway Health**:
```bash
curl http://localhost:8080/health
```

2. **Test OpenAI Provider**:
```bash
curl -X POST http://localhost:8080/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "prompt": [{"role": "user", "content": "Hello"}],
    "response_format": {"type": "object", "properties": {"msg": {"type": "string"}}, "required": ["msg"]}
  }'
```

3. **Test Gemini Provider**:
```bash
curl -X POST http://localhost:8080/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gemini",
    "model": "gemini-2.0-flash-exp",
    "prompt": [{"role": "user", "content": "Hello"}],
    "response_format": {"type": "object", "properties": {"msg": {"type": "string"}}, "required": ["msg"]}
  }'
```

4. **Test Error Handling**:
```bash
# Invalid provider
curl -X POST http://localhost:8080/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "invalid",
    "model": "test",
    "prompt": [{"role": "user", "content": "test"}],
    "response_format": {"type": "object", "properties": {}}
  }'
```

### Verifying Logs

Check Docker logs to verify monitoring is working:
```bash
# Gateway logs
docker logs llm-gateway

# Backend logs
docker logs llm-backend

# Or use make command
make docker-logs
```

## Key Benefits

### 1. Security
- API keys are never exposed to client applications
- Centralized key management enables easy rotation
- All requests go through a single, auditable entry point

### 2. Consistency
- Unified interface across multiple LLM providers
- Standardized error handling and logging
- Consistent request/response format

### 3. Observability
- All LLM API calls are logged with request IDs
- Performance metrics tracked centrally
- Easy to identify usage patterns and optimize costs

### 4. Maintainability
- Changes to API keys require updating only the gateway
- Adding new LLM providers is centralized
- Client applications are decoupled from LLM API details

### 5. Scalability
- Gateway can be scaled independently
- Load balancing and rate limiting can be added at gateway level
- Cache layer can be introduced without client changes

## Trade-offs and Considerations

### Advantages
- **Centralized Management**: API keys, logging, and monitoring in one place
- **Security**: API keys never leave the gateway
- **Flexibility**: Easy to switch providers or add new ones
- **Observability**: Complete visibility into LLM usage

### Disadvantages
- **Single Point of Failure**: Gateway downtime affects all dependent services
  - Mitigation: Deploy multiple gateway instances with load balancing
- **Additional Latency**: Extra network hop adds ~10-50ms overhead
  - Impact: Negligible for most use cases (LLM calls typically take seconds)
- **Operational Complexity**: Another service to deploy and monitor
  - Mitigation: Use managed services or container orchestration (Kubernetes)

### When to Use
- Multiple services consuming LLM APIs
- Need for centralized API key management
- Requirement for comprehensive logging and monitoring
- Frontend applications need to call LLM APIs
- Planning to switch between LLM providers

### When Not to Use
- Single application with simple LLM usage
- Extremely latency-sensitive applications (< 100ms requirements)
- Prototype/PoC stage where simplicity is paramount

## Development Workflow

### Code Formatting and Linting

```bash
# Format code
make fmt

# Run linter
make lint

# Fix all issues
make fix

# Type checking
make mypy
```

### Docker Workflow

```bash
# Build images
make docker-build

# Build only gateway
make docker-build-gateway

# Build only backend
make docker-build-backend

# Restart services
make docker-restart
```

## Summary

This LLM API Gateway implementation demonstrates a production-ready architecture for managing LLM API access in enterprise environments. By centralizing API key management, providing unified access to multiple providers, and implementing comprehensive monitoring, the gateway significantly improves security, observability, and maintainability of LLM-powered systems.

The gateway pattern is especially valuable in microservices architectures where multiple services need LLM capabilities, or when frontend applications need to safely consume LLM APIs without exposing API keys. While it introduces a small amount of latency and operational complexity, the benefits in terms of security, consistency, and governance typically far outweigh these costs in production environments.
