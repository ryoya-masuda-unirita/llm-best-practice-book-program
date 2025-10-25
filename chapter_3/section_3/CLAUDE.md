# Chapter 3 Section 3: LLM API Service Interface Segregation - Project Status Report

## Implementation Summary

This directory contains a complete implementation of an LLM API service applying the **Interface Segregation Principle (ISP)**. By defining two distinct functionalities—text generation and text classification—as independent service interfaces and managing them through a Dependency Injection (DI) pattern, we achieve an architecture with excellent maintainability and extensibility.

## Implementation Details

### Core Features

#### 1. Service Interfaces (Interface Segregation Principle)

**Interface Definitions** (`src/service/interfaces.py`)
- `ITextGenerationService` - Text generation dedicated interface
  - Defines only `generate_character()` method
  - Specialized responsibility for character generation
  - User plan-based model restrictions
- `ITextClassificationService` - Text classification dedicated interface
  - Defines only `classify()` method
  - Specialized responsibility for text classification
  - Category list and structured output
- `get_available_models()` helper function
  - Retrieves available model list based on provider and plan

**User Plan Definition** (`src/model/model.py`)
- `UserPlan.FREE` - Free plan
  - OpenAI: `gpt-4.1-mini` only
  - Gemini: `gemini-2.5-flash-lite` only
- `UserPlan.STANDARD` - Standard plan
  - All models available

#### 2. Concrete Service Implementations

**Text Generation Service** (`src/service/text_generation_service.py`)
- `TextGenerationService` class
- Implements `ITextGenerationService` interface
- Supports both OpenAI/Gemini providers
- Plan restriction validation implementation
- Type safety through structured output (Pydantic)
- Detailed logging output

**Text Classification Service** (`src/service/text_classification_service.py`)
- `TextClassificationService` class
- Implements `ITextClassificationService` interface
- Category list-based classification
- Results include confidence and reasoning
- Strict category validation
- Fallback handling for invalid categories returned

#### 3. Dependency Injection Container

**Service Container** (`src/service/container.py`)
- `ServiceContainer` class
  - Generates service instances for all providers at initialization
  - Centralized management and reuse of LLM client
  - `get_text_generation_service()` method
  - `get_text_classification_service()` method
- Global container instance `service_container`
  - Singleton pattern at module level
  - Shared across entire application

#### 4. LLM Client Management

**Client** (`src/client/llm_client.py`)
- `LLMClient` class
  - OpenAI AsyncClient initialization
  - Google Gemini Client initialization
  - Secure API key management (Secret type)
- `LLMProvider` enumeration
  - OPENAI, GEMINI
- `OpenAIModel` enumeration
  - 8 model definitions (GPT-5, GPT-5-mini, GPT-4.1, etc.)
  - `free_plan_models()` / `standard_plan_models()` methods
- `GeminiModel` enumeration
  - 3 model definitions (2.5-pro, 2.5-flash, 2.5-flash-lite)
  - Plan-based model filtering

#### 5. FastAPI RESTful API

**API Server** (`src/api/llm_server.py`)
- FastAPI application definition
- Endpoints:
  - `GET /health` - Health check
  - `POST /generate` - Character generation (uses ITextGenerationService)
  - `POST /classify` - Text classification (uses ITextClassificationService)
- Service retrieval through dependency injection pattern
- Comprehensive error handling
- Processing time measurement and recording
- User plan validation
- Detailed logging (success/failure/warning)

#### 6. Data Models

**Request/Response Models** (`src/model/model.py`)
- `CharacterRequest` - Character generation request
  - gender, age, additional_instructions
- `CharacterResponse` - Character generation response
  - first_name, last_name, gender, age
  - personalities list (3 personality traits)
- `LLMRequest` - API generation endpoint request
  - provider, model, character_request, user_plan
- `LLMResponse` - API generation endpoint response
  - character, provider, model, processing_time_ms
- `TextClassificationRequest` - Classification request
  - text, categories, provider, model, user_plan
- `ClassificationResult` - Classification result (structured output)
  - category, confidence, reasoning
- `TextClassificationResponse` - API classification endpoint response
  - category, provider, model, processing_time_ms, classification_result
- `HealthResponse` - Health check response
- `UserPlan` - Plan type (FREE/STANDARD)

All models implement strict type definitions and validation with Pydantic

#### 7. Prompt Generation

**Prompt Management** (`src/prompt/prompt.py`)
- `make_generation_prompt()` - Character generation prompt
  - Generates prompt based on CharacterRequest
  - Automatic schema information embedding
  - System and user message composition
- `make_classification_prompt()` - Classification prompt
  - Generates prompt including category list
  - Structured output schema description
  - Polite instructions in Japanese

#### 8. Configuration Management

**Environment Configuration** (`src/config.py`)
- `Config` Pydantic model
  - OpenAI API key (Secret type)
  - Gemini API key (Secret type)
- Auto-loading from .envrc file
- Immutability (frozen=True)
- Validation enabled (validate_assignment=True)

#### 9. Logging Management

**Logging Configuration** (`src/logger.py`)
- Structured log format
- Includes timestamp, level, module, file, function name
- `make_logger()` helper function

#### 10. Infrastructure

**Docker Configuration**
- `Dockerfile.web` - Web server container
  - Efficient uv-based image
  - Multi-stage build
- `docker-compose.yml` - Service composition
  - llm-server service (API)
  - proxy-server service (Proxy)
  - llm-network network

**Development Tools**
- `Makefile` - Development command collection
  - run-llm-server, docker-build, docker-up, etc.
- `pyproject.toml` - Dependency definitions
  - fastapi, uvicorn, openai, google-genai, etc.

**Documentation**
- `README.md` - Comprehensive usage instructions and architecture explanation
- `CLAUDE.md` - This file (project status report)

### Not Yet Implemented or Future Extensions

#### Testing
- Unit tests (recommended implementation)
  - Service interface mock tests
  - Plan restriction validation tests
  - ServiceContainer tests
- Integration tests
  - E2E tests including actual API calls
  - Comprehensive error case validation

#### Monitoring Features
- Metrics collection (Prometheus, etc.)
- Distributed tracing (OpenTelemetry)
- Request rate and latency visualization

#### Additional Service Interfaces
- `IEmbeddingService` - Embedding vector generation
- `IChatService` - Chat functionality
- `ISummarizationService` - Summarization functionality
- `ITranslationService` - Translation functionality

#### Authentication & Authorization
- API key authentication
- JWT token authentication
- Enhanced plan-based feature restrictions

## Architectural Design Principles

### 1. Application of Interface Segregation Principle (ISP)

The key feature of this implementation is the segregation of LLM services into independent interfaces by functionality.

**Benefits**:
- Each client depends only on necessary functionality
- Easy to create tests and mocks
- Minimal impact range when adding features
- Different teams can develop independently

**Implementation Example**:
```python
# Bad example: Single monolithic interface
class ILLMService(ABC):
    @abstractmethod
    def generate_character(...): pass
    @abstractmethod
    def classify(...): pass
    @abstractmethod
    def embed(...): pass
    @abstractmethod
    def chat(...): pass
    # Many more methods...

# Good example: Segregated by functionality
class ITextGenerationService(ABC):
    @abstractmethod
    def generate_character(...): pass

class ITextClassificationService(ABC):
    @abstractmethod
    def classify(...): pass
```

### 2. Dependency Injection Pattern

Through the `ServiceContainer` class, we centralize the creation and management of service instances.

**Benefits**:
- Loosely coupled design
- Easy to inject mocks during testing
- Service lifecycle management
- Efficient reuse of LLM client

**Implementation Example**:
```python
class ServiceContainer:
    def __init__(self):
        self._llm_client = LLMClient()  # Share one client
        self._initialize_services()

    def get_text_generation_service(self, provider: LLMProvider):
        return self._text_generation_services[provider]
```

### 3. Application of Factory Pattern

ServiceContainer itself acts as a Factory that generates service instances for each provider.

**Benefits**:
- Encapsulation of object creation logic
- Flexible switching based on configuration
- Centralized initialization processing

### 4. Single Responsibility Principle (SRP)

Each service class has only a single responsibility.

**Examples**:
- `TextGenerationService` - Character generation only
- `TextClassificationService` - Text classification only
- `ServiceContainer` - Service management only
- `LLMClient` - LLM client initialization only

### Data Flow

#### Character Generation Request Flow

```
1. Client
   ↓ POST /generate {provider, model, user_plan, character_request}
2. FastAPI Endpoint (llm_server.py)
   ↓ Request validation and parsing
3. ServiceContainer
   ↓ get_text_generation_service(provider) call
4. ITextGenerationService instance retrieval
   ↓ (for OpenAI or Gemini)
5. TextGenerationService
   ↓ generate_character() call
6. Plan restriction validation
   ↓ Check with get_available_models()
7. Prompt generation
   ↓ make_generation_prompt() call
8. LLM API call
   ↓ OpenAI: beta.chat.completions.parse()
   ↓ Gemini: aio.models.generate_content()
9. Structured output parsing
   ↓ CharacterResponse object creation
10. FastAPI Endpoint
   ↓ Wrap in LLMResponse and return
11. Client
   ↓ Receive JSON response
```

#### Text Classification Request Flow

```
1. Client
   ↓ POST /classify {provider, model, user_plan, text, categories}
2. FastAPI Endpoint (llm_server.py)
   ↓ Request validation
3. ServiceContainer
   ↓ get_text_classification_service(provider) call
4. ITextClassificationService instance retrieval
5. TextClassificationService
   ↓ classify() call
6. Plan restriction validation
7. Classification prompt generation
   ↓ make_classification_prompt() call
8. LLM API call (structured output)
9. Result validation
   ↓ Verify category is in the list
10. ClassificationResult return
   ↓ category, confidence, reasoning
11. FastAPI Endpoint
   ↓ Wrap in TextClassificationResponse
12. Client
   ↓ Receive JSON response
```

### Plan Restriction Mechanism

**Model Restriction Implementation**:
```python
# For OpenAI models
class OpenAIModel(StrEnum):
    @staticmethod
    def free_plan_models() -> list[str]:
        return [OpenAIModel.GPT_4_1_MINI]

    @staticmethod
    def standard_plan_models() -> list[str]:
        return OpenAIModel.list_str()  # All models

# Validation in service
def generate_character(..., user_plan: UserPlan):
    available_models = get_available_models(self.provider, user_plan)
    if model not in available_models:
        raise ValueError(f"Model '{model}' is not available for {user_plan.value} plan")
```

**Available Models by Plan**:

| Plan | OpenAI | Gemini |
|------|--------|--------|
| FREE | gpt-4.1-mini only | gemini-2.5-flash-lite only |
| STANDARD | All models (GPT-5, GPT-5-mini, GPT-4.1, etc.) | All models (2.5-pro, 2.5-flash, 2.5-flash-lite) |

## Operating Environment

### Required Components
- **Python**: 3.13.2 or higher
- **FastAPI**: 0.119.0+ - High-performance async web framework
- **Pydantic**: 2.12.2+ - Data validation and configuration management
- **Uvicorn**: 0.37.0+ - ASGI server

### LLM SDKs
- **OpenAI Python SDK**: 2.4.0+ - Structured output support
- **Google Gemini SDK**: 1.45.0+ - Structured output support

### Development Tools
- **uv**: Python package manager (recommended)
- **Docker**: Containerization
- **Docker Compose**: Multi-service orchestration
- **Make**: Task runner

### Other Libraries
- **python-dotenv**: 1.1.1+ - Environment variable management
- **click**: 8.3.0+ - CLI tool building (for future extensions)
- **httpx**: 0.28.1+ - HTTP client

## Expected Behavior

### Behavior by Endpoint

#### 1. Health Check (`GET /health`)

**Request Example**:
```bash
curl http://localhost:8000/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "timestamp": 1698765432.123
}
```

#### 2. Character Generation (`POST /generate`)

**Success Example with Free Plan**:
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4.1-mini",
    "user_plan": "free",
    "character_request": {
      "gender": "female",
      "age": 25,
      "additional_instructions": "Adventurous and brave"
    }
  }'
```

**Expected Behavior**:
- HTTP Status: 200
- processing_time_ms: approximately 1000-3000ms
- Complete character information in character field
- Includes 3 personality traits

**Plan Restriction Error Example**:
```bash
# Using premium model with Free Plan
curl -X POST http://localhost:8000/generate \
  -d '{"provider": "openai", "model": "gpt-5", "user_plan": "free", ...}'
```

**Expected Error**:
- HTTP Status: 400
- detail: "Model 'gpt-5' is not available for free plan. Available models: gpt-4.1-mini"

#### 3. Text Classification (`POST /classify`)

**Success Example**:
```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "user_plan": "standard",
    "text": "This product is excellent!",
    "categories": ["Positive", "Negative", "Neutral"]
  }'
```

**Expected Response**:
```json
{
  "category": "Positive",
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "processing_time_ms": 567.89,
  "classification_result": {
    "category": "Positive",
    "confidence": "high",
    "reasoning": "Contains clearly positive expressions such as 'excellent'"
  }
}
```

### Log Output Examples

**Success Logs**:
```
[2025-10-25 10:30:45] [INFO] [src.service.text_generation_service] Generating character using OpenAI model: gpt-4.1-mini
[2025-10-25 10:30:47] [INFO] [src.api.llm_server] Successfully generated character using openai/gpt-4.1-mini for free plan in 1234.56ms
```

**Classification Success Logs**:
```
[2025-10-25 10:31:12] [INFO] [src.service.text_classification_service] Classifying text using Gemini model: gemini-2.5-flash
[2025-10-25 10:31:13] [INFO] [src.service.text_classification_service] Classification result: Positive (confidence: high) - Contains positive expressions such as 'excellent'
[2025-10-25 10:31:13] [INFO] [src.api.llm_server] Successfully classified text using gemini/gemini-2.5-flash for standard plan in 789.12ms. Result: Positive
```

**Plan Restriction Error Logs**:
```
[2025-10-25 10:32:00] [WARNING] [src.api.llm_server] Validation error: Model 'gpt-5' is not available for free plan. Available models: gpt-4.1-mini
```

## Security and Quality

### Implemented Measures

1. **API Key Protection**
   - Automatic masking via `Secret[str]` type
   - Loading from environment variables
   - .gitignore registration of .env files

2. **Input Validation**
   - Strict type checking with Pydantic models
   - Age range constraints (0-100)
   - Category list validity validation

3. **Error Handling**
   - Comprehensive try-except blocks
   - Appropriate HTTP status codes
   - Detailed error messages

### Recommended Future Enhancements

1. **Authentication & Authorization**
   - API key-based authentication
   - JWT token authentication
   - Rate limiting per plan

2. **Security Hardening**
   - Enforce HTTPS/TLS communication
   - Proper CORS configuration
   - Input sanitization

3. **Monitoring**
   - Request/response audit logs
   - Anomaly detection and alerting
   - Performance metrics

## Startup Methods

### Local Development

**Minimal Configuration (Python environment only)**:
```bash
# Install dependencies
uv sync

# Start development server (hot reload enabled)
make run-llm-server

# Or directly
uv run uvicorn src.api.llm_server:app --host 0.0.0.0 --port 8000 --reload
```

**Production Configuration (Docker Compose)**:
```bash
# Build image
make docker-build

# Start containers
make docker-up

# View logs
make docker-logs

# Stop
make docker-down
```

### Verification

1. **Health Check**
   - Endpoint: `GET /health`
   - Expected: `{"status": "healthy", ...}`
   - Frequency: Every 30 seconds (for monitoring)

2. **API Documentation**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Interactive testing available

3. **Processing Time**
   - Check `processing_time_ms` field in response
   - Guideline: 1000-3000ms (first request), similar afterwards

4. **Error Rate**
   - Monitor HTTP 5xx errors
   - Target: < 0.1%

### Troubleshooting

**Problem: API Key Error**
- Cause: Environment variables not set
- Solution: Check `.envrc` file and set API keys

**Problem: Plan Restriction Error**
- Cause: Attempting to use premium model with Free Plan
- Solution: Change `user_plan` to "standard" or use available models

**Problem: Port Conflict**
- Cause: Port 8000 already in use
- Solution: Stop other processes or specify different port

**Problem: LLM API Error**
- Cause: Invalid API key or rate limiting
- Solution: Verify API key validity, adjust request frequency

## Summary

This project is a practical implementation example of applying the Interface Segregation Principle to LLM services. By combining the following design patterns, we achieve an architecture with excellent maintainability and extensibility.

### Achieved Design Goals

1. **Loose Coupling**
   - Each interface has independent responsibilities
   - Changes to one feature don't affect others
   - Easy testing and mocking

2. **Extensibility**
   - Easy to add new service interfaces
   - Minimal impact on existing code
   - Simple to add providers or models

3. **Maintainability**
   - Clear separation of responsibilities
   - Consistent design patterns
   - Comprehensive documentation and logs

4. **Flexibility**
   - Plan-based model restrictions
   - Flexible configuration through dependency injection
   - Behavior switching via environment settings

### Best Practices

Key patterns practiced in this project:

1. **Interface Segregation**: Define minimal interfaces per functionality to minimize client dependencies

2. **Dependency Injection**: Centralized management via ServiceContainer improves testability and flexibility

3. **Structured Output**: Type-safe LLM responses through Pydantic models ensure reliability

4. **Environment-Specific Configuration**: Easy switching between development/production/test configurations

This architecture can serve as a reference implementation for leveraging LLMs in production environments. It's particularly useful for enterprise applications with multiple features or startups gradually expanding functionality.
