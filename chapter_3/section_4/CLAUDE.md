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
|-- src/
|   |-- __init__.py
|   |-- config.py                     # Configuration management
|   |-- logger.py                     # Logging setup
|   |
|   |-- api_gateway/                  # API Gateway Service
|   |   |-- __init__.py
|   |   |-- gateway_server.py         # FastAPI gateway server
|   |   |-- gateway_service.py        # Core gateway logic
|   |   |-- models.py                 # Gateway request/response models
|   |   |-- api_key_manager.py        # Centralized API key management
|   |   +-- monitoring.py             # Logging and monitoring
|   |
|   |-- client/                       # Client Library
|   |   |-- __init__.py
|   |   |-- llm_client.py             # LLM provider enums
|   |   +-- gateway_client.py         # Gateway client library
|   |
|   |-- api/                          # Backend API Service
|   |   |-- __init__.py
|   |   +-- llm_server.py             # Backend server using gateway
|   |
|   |-- service/                      # Business Logic
|   |   |-- __init__.py
|   |   +-- request_llm.py            # LLM request service
|   |
|   |-- model/                        # Data Models
|   |   |-- __init__.py
|   |   +-- model.py                  # Pydantic models
|   |
|   +-- prompt/                       # Prompt Management
|       |-- __init__.py
|       +-- prompt.py                 # Prompt generation
|
|-- docker-compose.yml                # Docker Compose configuration
|-- Dockerfile.backend                # Backend service Dockerfile
|-- Dockerfile.gateway                # Gateway service Dockerfile
|-- Makefile                          # Build and run commands
|-- pyproject.toml                    # Project dependencies
|-- .envrc.example                    # Environment variables template
|-- README.md                         # Project documentation
+-- CLAUDE.md                         # This file
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
|                              v                            |
|  +-----------------------------------------------------+  |
|  |      Gateway Service (gateway_service.py)           |  |
|  |  - Provider routing                                 |  |
|  |  - API client management                            |  |
|  +---------------------------+-------------------------+  |
|                              |                            |
|                              v                            |
|  +-----------------------------------------------------+  |
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
|                              v                            |
|  +-----------------------------------------------------+  |
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

### Key Components

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
        provider_lower = provider.lower()
        if provider_lower not in self._provider_keys:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        return self._provider_keys[provider_lower]
```

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

#### 5. Gateway Client (`src/client/gateway_client.py`)

Client library for applications to consume the gateway:

```python
class GatewayClient:
    async def generate(
        self,
        provider: str,
        model: str,
        prompt: list[dict],
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

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | >=0.119.0 | Web framework for API endpoints |
| uvicorn | >=0.37.0 | ASGI server |
| httpx | >=0.28.1 | Async HTTP client |
| openai | >=2.4.0 | OpenAI API client |
| google-genai | >=1.45.0 | Google Gemini API client |
| pydantic | >=2.12.2 | Data validation and models |
| python-dotenv | >=1.1.1 | Environment variable management |
| click | >=8.3.0 | CLI utilities |

## Usage

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

### Run

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
uv run uvicorn src.api_gateway.gateway_server:app --host 0.0.0.0 --port 8080 --reload
```

**Terminal 2 - Start Backend**:
```bash
uv run uvicorn src.api.llm_server:app --host 0.0.0.0 --port 8000 --reload
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Gateway health check |
| `/v1/generate` | POST | Generate content via LLM |
| `/docs` | GET | Swagger UI documentation |
| `/redoc` | GET | ReDoc documentation |

### Example Requests

**Health Check**:
```bash
curl http://localhost:8080/health
```

**Generate Content**:
```bash
curl -X POST http://localhost:8080/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "prompt": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Say hello!"}
    ],
    "response_format": {
      "type": "object",
      "properties": {"message": {"type": "string"}},
      "required": ["message"]
    },
    "client_id": "test-client"
  }'
```

## Development Commands

| Command | Description |
|---------|-------------|
| `make fmt` | Format code with ruff |
| `make lint` | Run linter |
| `make fix` | Run both lint and format |
| `make mypy` | Run type checking |
| `make docker-build` | Build all Docker images |
| `make docker-build-gateway` | Build gateway image only |
| `make docker-build-backend` | Build backend image only |
| `make docker-up` | Start all services |
| `make docker-down` | Stop all services |
| `make docker-logs` | View service logs |
| `make docker-restart` | Restart all services |

## Implementation Notes

### Security Considerations
- API keys are stored using `Secret[str]` type for automatic masking in logs
- Keys are never exposed to client applications
- All requests are logged with unique request IDs for auditing

### Error Handling
- Centralized error handling via `_handle_gateway_error()` function
- Typed error responses using `GatewayErrorResponse` model
- Provider validation before processing requests

### Performance
- Lazy initialization of LLM clients (created on first use)
- Processing time tracked and returned in responses
- Async/await throughout for non-blocking I/O

### Extensibility
- Adding new providers requires only:
  1. Add key to `APIKeyManager`
  2. Add routing case in `GatewayService.process_request()`
  3. Implement provider-specific call method

### Trade-offs
- **Single Point of Failure**: Gateway downtime affects all services
  - Mitigation: Deploy multiple instances with load balancing
- **Additional Latency**: Extra network hop adds ~10-50ms
  - Negligible for LLM calls (typically seconds)
- **Operational Complexity**: Another service to maintain
  - Mitigated by containerization and monitoring
