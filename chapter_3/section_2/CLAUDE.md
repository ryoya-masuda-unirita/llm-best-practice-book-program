# Chapter 3 Section 2: Separating Storage and Execution Layers in LLM Systems

## Overview

This project demonstrates a **Bridge Pattern-based architecture** that separates storage (caching) and execution (LLM API calls) layers in an LLM system. By decoupling cache/database access from LLM API invocation, we achieve high component independence, flexibility, testability, and maintainability.

The implementation provides a FastAPI-based REST API server supporting multiple OpenAI models (GPT-4o, GPT-4.1, GPT-5 series). It offers flexible cache backend switching between in-memory and Redis storage based on environment configuration.

## Features

- **Storage-Execution Separation**: Clear separation of concerns using the Bridge Pattern
- **Dual Cache Backends**: Support for both in-memory and Redis-based caching
- **OpenAI Support**: Compatible with OpenAI GPT models (GPT-5, GPT-4.1, GPT-4o series)
- **Model Validation**: Automatic validation of model compatibility with providers
- **Dependency Injection**: Flexible service instance management via Factory Pattern
- **REST API Server**: High-performance FastAPI endpoints
- **Cache Metrics**: Monitoring capabilities for cache hit rate and performance
- **Cache Invalidation**: Manual cache key invalidation functionality
- **Async Operations**: Efficient API calls using async/await patterns
- **Type Safety**: Strict type validation and verification with Pydantic
- **Environment Management**: Secure API key handling with Secret[str] type
- **Docker Support**: Easy deployment with Docker Compose

## Architecture Overview

### Design Patterns

The project employs three core design patterns to achieve separation of concerns:

#### 1. Bridge Pattern Implementation

The Bridge Pattern separates the abstraction (`ILLMService` interface) from its implementations (`CachedLLMService` and `ExecutionLLMService`).

**Benefits**:
- Storage and execution layers can be developed, tested, and modified independently
- New implementations can be added without changing existing code
- Enhanced code reusability
- Easy mocking for unit tests

**Structure**:
```python
# Abstraction
class ILLMService(ABC):
    @abstractmethod
    async def generate_character(...) -> CharacterResponse: pass

# Storage Implementation
class CachedLLMService(ILLMService):
    def __init__(self, execution_service: ILLMService):
        self._execution_service = execution_service  # Dependency Injection

    async def generate_character(...):
        # Check cache → Delegate to execution → Store in cache

# Execution Implementation
class ExecutionLLMService(ILLMService):
    async def generate_character(...):
        # Direct LLM API invocation
```

#### 2. Factory Pattern for Service Creation

`LLMServiceFactory` manages service instantiation based on environment configuration.

**Benefits**:
- Centralized object creation logic
- Easy switching of implementations via configuration
- Simplified testing with mock services

**Implementation**:
```python
class LLMServiceFactory:
    @staticmethod
    def create_service() -> ILLMService:
        execution_service = ExecutionLLMService()
        if config.cache_enabled:
            return CachedLLMService(execution_service)
        return execution_service
```

#### 3. Singleton Pattern for Service Management

`get_llm_service()` ensures only one service instance exists application-wide.

**Benefits**:
- Prevents redundant service instantiation
- Efficient resource utilization
- Consistent cache metrics across requests

**Note**: Includes `reset_llm_service()` for testing scenarios

#### 4. Decorator Pattern Application

`CachedLLMService` wraps `ExecutionLLMService` to add caching functionality, following the Decorator pattern.

**Benefits**:
- Adds features without modifying existing implementations
- Follows the Open/Closed Principle (open for extension, closed for modification)

### Request Processing Flow

```
1. Client Request
   ↓ POST /generate
2. FastAPI Endpoint (llm_server.py)
   ↓ Request validation & model validation
3. get_llm_service() → Factory
   ↓ Service instance retrieval
4. CachedLLMService (Storage Layer)
   ↓ Cache lookup
5. Cache Check
     HIT → Return cached data (fast path)
     MISS → Proceed to execution
6. ExecutionLLMService (Execution Layer)
   ↓ OpenAI API call
7. LLM API Invocation
     OpenAI: responses.parse()
8. CachedLLMService
   ↓ Store result in cache with TTL
9. FastAPI Endpoint
   ↓ Format response with processing time
10. Client Response
   ↓ JSON response with metrics
```

### Cache Key Generation

**Key Formula**:
```python
key_data = f"{provider}:{model}:{str(prompt)}"
cache_key = hashlib.sha256(key_data.encode()).hexdigest()
```

**Cache Hit Flow**:
- Log: `Cache hit for {provider}/{model} (hits: X, misses: Y, hit_rate: Z%)`
- Metrics: `_cache_hits += 1`
- No API call
- Response time: ~10-100ms (in-memory), ~50-200ms (Redis)

**Cache Miss Flow**:
- Log: `Cache miss for {provider}/{model} (hits: X, misses: Y, hit_rate: Z%)`
- Metrics: `_cache_misses += 1`
- Execute LLM API call
- Store result with TTL
- Response time: ~1000-3000ms (includes API latency)

## Project Structure

### Directory Layout

```
chapter_3/section_2/
├── src/
│   ├── __init__.py                # Package initialization
│   ├── config.py                  # Configuration management (API keys, cache settings)
│   ├── logger.py                  # Logging configuration
│   ├── api/
│   │   ├── __init__.py
│   │   └── llm_server.py          # FastAPI server implementation
│   ├── client/
│   │   ├── __init__.py
│   │   ├── llm_client.py          # LLM client initialization (OpenAI)
│   │   └── cache_client.py        # Cache backends (InMemoryCache, RedisClient)
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py               # Pydantic data models
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py              # Prompt generation logic
│   └── service/
│       ├── __init__.py
│       ├── interface.py           # ILLMService interface (Bridge)
│       ├── storage.py             # Storage layer (CachedLLMService)
│       ├── execution.py           # Execution layer (ExecutionLLMService)
│       └── factory.py             # Factory pattern implementation
├── .env.example                    # Environment variables template
├── .envrc.example                  # direnv configuration template
├── docker-compose.yml              # Docker Compose configuration
├── Dockerfile.web                  # Web server Dockerfile
├── Makefile                        # Development commands
├── pyproject.toml                  # Project dependencies
├── README.md                       # User documentation (Japanese)
└── CLAUDE.md                       # This file (technical design doc)
```

### Component Details

#### 1. Bridge Interface (`src/service/interface.py`)

**Abstract Interface**:
- `ILLMService` base class
- `generate_character()` method signature
- `invalidate_cache()` method signature
- Enables polymorphism

**Key Points**:
- All service implementations must implement both methods
- Provides consistent interface for storage and execution layers
- Allows transparent switching between implementations

#### 2. Storage Layer (`src/service/storage.py`)

**CachedLLMService Implementation**:
- Wraps execution service via dependency injection
- Supports both Redis and in-memory caching
- SHA256 hash-based cache key generation
- Automatic cache hit/miss tracking
- TTL-based cache expiration
- Cache metrics collection (hits, misses, hit rate)

**Key Features**:
```python
class CachedLLMService(ILLMService):
    def __init__(self, execution_service: ILLMService):
        self._execution_service = execution_service
        # Initialize cache backend based on config
        if config.cache_backend == CacheBackend.MEMORY:
            self._cache = InMemoryCache()
        else:
            self._cache = redis_client
```

#### 3. Execution Layer (`src/service/execution.py`)

**ExecutionLLMService Implementation**:
- Direct OpenAI API invocation
- Structured output with `responses.parse()`
- No cache awareness (single responsibility)

**Implementation**:
```python
async def generate_character(...):
    if provider != LLMProvider.OPENAI:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    result = await openai_client.responses.parse(
        model=model,
        input=prompt,
        text_format=CharacterResponse,
    )
    return result.output_parsed
```

#### 4. Factory Pattern (`src/service/factory.py`)

**LLMServiceFactory Class**:
- `create_service()` - Configuration-based instantiation
- `create_execution_service()` - Direct execution service
- `create_cached_service()` - Explicit cached service with custom execution layer

**Singleton Management**:
- `get_llm_service()` - Returns singleton instance
- `reset_llm_service()` - Resets singleton for testing

#### 5. Cache Client Implementation (`src/client/cache_client.py`)

**InMemoryCache Class**:
- Simple dictionary-based storage
- TTL support with expiration checking
- Automatic cleanup on access
- Ideal for development and testing
- Methods: `get()`, `set()`, `delete()`, `exists()`

**RedisClient Class**:
- Async Redis operations with `redis.asyncio`
- Connection management with automatic reconnect
- JSON serialization/deserialization
- TTL support via `setex()`
- Error handling with fallback
- Methods: `connect()`, `disconnect()`, `get()`, `set()`, `delete()`, `exists()`

**Global Instance**:
```python
redis_client = RedisClient()  # Singleton instance
```

#### 6. LLM Client Module (`src/client/llm_client.py`)

**Supported Models**:
- **OpenAI**: GPT-5 series (gpt-5, gpt-5-mini, gpt-5-nano), GPT-4.1 series (gpt-4.1, gpt-4.1-mini, gpt-4.1-nano), GPT-4o series (gpt-4o, gpt-4o-mini)

**Client Initialization**:
```python
openai_client = AsyncOpenAI(api_key=config.openai_api_key)
```

**Model Enums**:
- `LLMProvider` - Enum for providers (openai)
- `OpenAIModel` - Enum with `list_str()` method

#### 7. REST API Layer (`src/api/llm_server.py`)

**FastAPI Application**:
- Title: "LLM API Server"
- Version: "2.0.0"
- Auto-generated OpenAPI documentation

**Endpoints**:

1. **POST /generate** - Character generation
   - Request: `LLMRequest` (provider, model, character_request)
   - Response: `LLMResponse` (character, provider, model, processing_time_ms)
   - Validates model compatibility with provider
   - Tracks processing time
   - Automatic caching via service layer

2. **GET /health** - Health check
   - Response: `HealthResponse` (status, timestamp)
   - Always returns "healthy"

3. **GET /metrics** - Cache metrics
   - Response: Cache statistics (hits, misses, hit_rate, backend type)
   - Returns `{"cache_enabled": false}` if caching disabled

4. **DELETE /cache/{cache_key}** - Cache invalidation
   - Parameter: cache_key (string)
   - Response: Invalidation result and message

**Lifecycle Events**:
- `startup_event()` - Initializes Redis connection if using Redis backend
- `shutdown_event()` - Gracefully closes Redis connection

**Error Handling**:
- Model validation errors → HTTP 400
- API errors → HTTP 500 with error details
- Comprehensive logging for all operations

#### 8. Data Models (`src/model/model.py`)

**Enums**:
- `Gender` - FEMALE, MALE

**Request Models**:
- `CharacterRequest` - gender, age (0-100), additional_instructions
- `LLMRequest` - provider, model, character_request

**Response Models**:
- `CharacterPersonality` - short_personality, description
- `CharacterResponse` - first_name, last_name, gender, age, personalities (list of 3)
- `LLMResponse` - character, provider, model, processing_time_ms
- `HealthResponse` - status, timestamp

**Pydantic Configuration**:
- `validate_assignment=True` - Validates on assignment
- `frozen=True` - Immutable models
- `extra="ignore"` - Ignores extra fields

**Helper Methods**:
- `CharacterResponse.detailed_model()` - Returns schema for prompt generation
- `CharacterResponse.save_as_json()` - Saves to JSON file

#### 9. Prompt Generation (`src/prompt/prompt.py`)

**make_prompt() Function**:
- Accepts `CharacterRequest` parameter
- Generates structured system and user messages
- Uses `CharacterResponse.detailed_model()` for schema
- Japanese language prompts
- JSON structure enforcement

**Prompt Structure**:
```python
[
    {"role": "system", "content": "System instructions with JSON schema..."},
    {"role": "user", "content": "Character generation request..."}
]
```

#### 10. Configuration Management (`src/config.py`)

**Config Class Fields**:
- `openai_api_key: Secret[str]` - OpenAI API key
- `cache_enabled: bool` - Enable/disable caching (default: true)
- `cache_backend: CacheBackend` - memory or redis (default: memory)
- `cache_ttl: int` - TTL in seconds (default: 3600)
- `redis_host: str` - Redis host (default: localhost)
- `redis_port: int` - Redis port (default: 6379)
- `redis_db: int` - Redis database number (default: 0)
- `redis_password: Secret[str] | None` - Optional Redis password

**Security Features**:
- `Secret[str]` type prevents logging sensitive data
- Environment variable loading
- Pydantic validation for all fields

#### 11. Logging (`src/logger.py`)

**Logger Configuration**:
- Structured logging setup
- Module-based logger creation
- `make_logger(__name__)` factory function
- Configurable log levels

#### 12. Deployment

**Docker Configuration**:
- `Dockerfile.web` - Multi-stage build with uv package manager
- `docker-compose.yml` - Orchestrates API server + Redis
- Platform: linux/amd64
- Base image: Python 3.13

**Makefile Commands**:
- `make run-llm-server` - Start local development server
- `make docker-build` - Build Docker images
- `make docker-up` - Start Docker Compose services
- `make docker-down` - Stop Docker Compose services
- `make docker-logs` - View container logs
- `make lint` - Run ruff linter with import sorting
- `make fmt` - Format code with ruff
- `make fix` - Run lint + format
- `make mypy` - Type checking with mypy

**Environment Files**:
- `.env.example` - Template for environment variables
- `.envrc.example` - Template for direnv configuration

## Best Practices & Design Decisions

### Why This Architecture?

#### 1. Bridge Pattern Benefits

This project's core strength lies in the separation between `ILLMService` abstraction and its implementations (`CachedLLMService` and `ExecutionLLMService`).

**Advantages**:
- Independent development, testing, and modification of storage and execution layers
- Easy addition of new cache backends (e.g., Memcached, DynamoDB)
- Enhanced code reusability
- Simple unit testing with mocks (no need for actual LLM API or cache)

**Example**:
```python
# Abstract interface
class ILLMService(ABC):
    @abstractmethod
    async def generate_character(...) -> CharacterResponse: pass

# Storage implementation
class CachedLLMService(ILLMService):
    def __init__(self, execution_service: ILLMService):
        self._execution_service = execution_service  # DI

    async def generate_character(...):
        # Cache check → Delegate to execution → Cache storage

# Execution implementation
class ExecutionLLMService(ILLMService):
    async def generate_character(...):
        # LLM API invocation
```

#### 2. Factory Pattern for Flexible DI

`LLMServiceFactory` enables configuration-driven service instantiation.

**Advantages**:
- Centralized creation logic complexity
- Configuration-based implementation switching
- Enhanced testability

**Example**:
```python
class LLMServiceFactory:
    @staticmethod
    def create_service() -> ILLMService:
        execution_service = ExecutionLLMService()
        if config.cache_enabled:
            return CachedLLMService(execution_service)
        return execution_service
```

#### 3. Singleton Pattern for Resource Management

`get_llm_service()` ensures a single service instance application-wide.

**Advantages**:
- Prevents redundant service initialization
- Efficient resource utilization
- Consistent cache metrics

**Note**: Includes `reset_llm_service()` for testing

#### 4. Decorator Pattern Implementation

`CachedLLMService` decorates `ExecutionLLMService` to add caching without modification.

**Advantages**:
- Adds functionality without changing existing code
- Enables multiple decorators to be stacked
- Follows the Open/Closed Principle

### Cache Configuration Modes

#### Development Mode
```bash
# .env
CACHE_ENABLED=true
CACHE_BACKEND=memory  # In-memory cache
CACHE_TTL=3600
```

**Use Cases**:
- No Redis dependency
- Fast startup
- Ideal for local development
- Testing scenarios requiring fresh data

#### Production Mode
```bash
# .env
CACHE_ENABLED=true
CACHE_BACKEND=redis  # Redis cache
CACHE_TTL=3600

REDIS_HOST=redis  # Docker Compose service name or localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_secure_password  # Optional
```

**Use Cases**:
- Distributed, persistent caching
- Cache sharing across multiple instances
- Production-ready scaling
- Built-in Redis monitoring

#### No-Cache Mode
```bash
# .env
CACHE_ENABLED=false  # Disable caching
```

**Use Cases**:
- Every request directly hits LLM API
- Testing actual LLM behavior
- Debugging cache-related issues

## Technology Stack

### Core Dependencies
- **Python**: 3.13.2
- **FastAPI**: 0.119.0+ - Modern async web framework
- **Pydantic**: 2.12.2+ - Data validation and settings management
- **Uvicorn**: 0.37.0+ - ASGI server implementation

### LLM SDKs
- **OpenAI Python SDK**: 2.4.0+ - Async client with structured outputs

### Caching
- **redis-py**: 7.0.0+ - Async Redis client (`redis.asyncio`)
- **Redis Server**: 7.x - In-memory data structure store

### Development Tools
- **uv**: Fast Python package installer and resolver
- **Docker**: Container runtime
- **Docker Compose**: Multi-container orchestration
- **Make**: Task automation

### Additional Libraries
- **python-dotenv**: 1.1.1+ - Environment variable management
- **click**: 8.3.0+ - CLI framework
- **httpx**: 0.28.1+ - HTTP client library
- **streamlit**: 1.50.0+ - Web app framework (for future UI)

### Development Dependencies
- **pytest**: 8.4.2+ - Testing framework
- **pytest-asyncio**: 1.2.0+ - Async test support
- **pytest-mock**: 3.15.1+ - Mocking utilities

## Performance Characteristics

### Cache Performance Impact

**First Request (Cache Miss)**:
- Response time: 1,000 - 3,000 ms
- LLM API call: Yes
- Cache storage: Yes

**Subsequent Requests (Cache Hit)**:
- Response time: 10 - 100 ms (in-memory), 50 - 200 ms (Redis)
- LLM API call: No
- Performance gain: 10-100x faster

**Cache Hit Rate**:
- Typical production: 70% - 90%
- Impact: Higher hit rate = lower API costs
- Variability: Depends on request diversity

### Cost Optimization

OpenAI GPT-4o-mini pricing (as of January 2025):
- Input: $0.150 / 1M tokens
- Output: $0.600 / 1M tokens

Example calculation for 500 tokens/request (300 input + 200 output):
- Per request cost: $0.0002
- 1,000 requests/day at 80% cache hit rate over 30 days:
  - Without cache: $0.20/day × 30 days = $6.00/month
  - With cache: $0.04/day × 30 days = $1.20/month
  - **Savings: $4.80/month (80% reduction)**

## Security Considerations

### Current Implementation

1. **API Key Protection**
   - `Secret[str]` type prevents accidental logging
   - Environment variable loading
   - .env files excluded from version control

2. **Input Validation**
   - Pydantic model validation
   - Field constraints (age: 0-100)
   - Type checking at runtime
   - Model compatibility validation

3. **Error Handling**
   - Comprehensive try-except blocks
   - Appropriate HTTP status codes
   - No sensitive data in error messages
   - Detailed logging for debugging

4. **Redis Security**
   - Optional password authentication
   - Connection timeout settings
   - Graceful error handling on connection failure

### Recommended Enhancements

1. **Authentication & Authorization**
   - API key authentication per client
   - JWT token-based auth
   - Request rate limiting per IP/client

2. **Network Security**
   - HTTPS/TLS enforcement
   - CORS configuration for web clients
   - Redis authentication and TLS

3. **Monitoring**
   - Request/response logging
   - Cache metrics tracking
   - Distributed tracing with OpenTelemetry
   - Prometheus metrics export

## Getting Started

### Prerequisites

- Python 3.13.2 or higher
- Docker and Docker Compose (for containerized deployment)
- Redis Server (for Redis cache backend)
- OpenAI API key

### Local Development

**Step 1: Install Dependencies**
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

**Step 2: Configure Environment**
```bash
# Copy example file
cp .env.example .env

# Edit .env and add your API keys
# Required:
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx

# Optional (defaults shown):
CACHE_ENABLED=true
CACHE_BACKEND=memory
CACHE_TTL=3600
```

**Step 3: Start Server**
```bash
# Using Makefile
make run-llm-server

# Or directly with uvicorn
uv run uvicorn src.api.llm_server:app --host 0.0.0.0 --port 8000 --reload
```

**Step 4: Access API Documentation**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Docker Deployment

**Step 1: Build Images**
```bash
make docker-build
```

**Step 2: Start Services**
```bash
make docker-up
```

**Step 3: View Logs**
```bash
make docker-logs
```

**Step 4: Stop Services**
```bash
make docker-down
```

### API Usage Examples

**1. Generate Character (OpenAI)**
```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "character_request": {
      "gender": "male",
      "age": 28,
      "additional_instructions": "ファンタジー世界の魔法使い"
    }
  }'
```

**2. Health Check**
```bash
curl http://localhost:8000/health
```

**3. Cache Metrics**
```bash
curl http://localhost:8000/metrics
```

**4. Invalidate Cache**
```bash
curl -X DELETE "http://localhost:8000/cache/{cache_key}"
```

### Testing

**Manual Testing**:

1. **Cache Hit/Miss Testing**:
```bash
# Enable in-memory cache
# Send same request twice
# First request: Cache miss (slow)
# Second request: Cache hit (fast)
```

2. **Model Validation Testing**:
```bash
# Invalid model for OpenAI
curl -X POST "http://localhost:8000/generate" \
  -d '{"provider": "openai", "model": "invalid-model", ...}'
# Expected: HTTP 400 Bad Request
```

3. **Redis Cache Testing**:
```bash
# Start Redis
docker run -d -p 6379:6379 redis:latest

# Update .env
CACHE_BACKEND=redis

# Restart server and test
# Check Redis directly
docker exec -it <redis_container> redis-cli
> KEYS *
> GET <cache_key>
```

### Common Troubleshooting

**Issue: Low Cache Hit Rate**
- Cause: Diverse requests, short TTL
- Solution: Increase TTL, review cache key generation

**Issue: Redis Connection Failure**
- Cause: Redis not running, incorrect connection settings
- Solution: Check `docker-compose ps`, verify REDIS_HOST and REDIS_PORT

**Issue: LLM API Errors**
- Cause: Invalid API keys, rate limits, network issues
- Solution: Verify API keys in .env, check rate limits, review error logs

**Issue: Model Validation Errors**
- Cause: Using incompatible model for provider
- Solution: Check `OpenAIModel` enum in `src/client/llm_client.py`

**Issue: Stale Cache Data**
- Cause: Long TTL with updated requirements
- Solution: Use DELETE /cache/{cache_key} endpoint, or adjust CACHE_TTL

## Summary

This project demonstrates how to build a production-ready LLM system with proper separation of concerns using the Bridge Pattern. The architecture effectively decouples storage (caching) and execution (LLM API calls) layers, enabling:

### Key Achievements

1. **Maintainability**
   - Clear separation between storage and execution
   - Independent development and testing
   - Easy to understand and modify

2. **Flexibility**
   - Configuration-driven service instantiation
   - Easy cache backend switching (memory/Redis)
   - Simple model addition

3. **Extensibility**
   - Clean interface-based design
   - Type-safe implementations
   - Well-documented components

4. **Performance**
   - Significant response time improvements (10-100x)
   - 80%+ reduction in LLM API costs
   - Efficient resource utilization

5. **Developer Experience**
   - Comprehensive API documentation
   - Docker support for easy deployment
   - Makefile commands for common tasks
   - Clear error messages and logging

This implementation serves as a foundation for building scalable, maintainable LLM applications with proper architectural patterns and best practices.
