# CLAUDE.md - LLM Adapter and Factory Pattern Implementation

## Project Overview

This project demonstrates **Adapter and Factory design patterns** for managing multiple LLM providers through a unified interface. It showcases best practices for avoiding vendor lock-in while maintaining code maintainability and extensibility.

**Core Objective**: Generate fictional character data (name, gender, age, personality traits) using OpenAI, Anthropic Claude, or Google Gemini APIs through a common interface.

**Key Patterns**:
- **Adapter Pattern**: Abstracts provider-specific API differences
- **Factory Pattern**: Centralizes client instantiation logic
- **Dependency Injection**: Promotes testability and flexibility

## Project Structure

```
src/
├── client/                    # Adapter and Factory implementation
│   ├── base.py               # Abstract base class (LLMClient)
│   ├── adapters.py           # Concrete adapters (OpenAI, Anthropic, Gemini)
│   ├── factory.py            # Factory for creating clients
│   └── model.py              # Provider/model enums
├── model/                    # Domain models
│   └── model.py              # Pydantic data models
├── prompt/                   # Prompt management
│   └── prompt.py             # Prompt generation logic
├── service/                  # Business logic layer
│   └── request_llm.py        # Unified LLM request handling
├── config.py                 # Configuration management
├── logger.py                 # Logging setup
└── main.py                   # CLI entry point

tests/
├── test_adapters.py          # Adapter tests
└── test_factory.py           # Factory tests
```

## Architecture

### Layer Architecture

```
+---------------------------------------------+
|         CLI Layer (main.py)                 |
|  - Command-line argument parsing            |
|  - Output directory management              |
|  - Provider/model validation                |
+-----------------+---------------------------+
                  |
                  v
+-----------------+---------------------------+
|      Service Layer (service/)               |
|  - Unified LLM request processing           |
|  - Prompt generation and response handling  |
+-----------------+---------------------------+
                  |
                  v
+-----------------+---------------------------+
|      Adapter/Factory Layer (client/)        |
|  - LLMClient abstract interface (base.py)   |
|  - Provider-specific adapters (adapters.py) |
|  - Client creation factory (factory.py)     |
+-----------------+---------------------------+
                  |
                  v
+-----------------+---------------------------+
|      Infrastructure Layer                   |
|  - Configuration (config.py)                |
|  - Logging (logger.py)                      |
|  - Data models (model/)                     |
|  - External APIs (OpenAI, Anthropic, Gemini)|
+---------------------------------------------+
```

### Design Patterns in Detail

#### 1. Adapter Pattern (`client/base.py`, `client/adapters.py`)

**Purpose**: Translate different provider APIs into a common interface.

**Abstract Interface** (`base.py`):
```python
class LLMClient(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        response_format: type,
        **kwargs: Any,
    ) -> BaseModel:
        """Generate chat completion with structured output."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider name."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return model identifier."""
        pass

    @abstractmethod
    async def aclose(self) -> None:
        """Close the client and release resources."""
        pass
```

**Key Design Decisions**:
- **Async interface**: All chat methods are async for efficient I/O handling
- **Pydantic integration**: `response_format` ensures type-safe responses
- **Flexible kwargs**: Allows provider-specific parameters without breaking the interface
- **Provider identification**: Methods for runtime introspection
- **Resource management**: `aclose()` method ensures proper cleanup of resources

**OpenAI Adapter** (`adapters.py`):
- Uses `AsyncOpenAI` client
- Leverages latest `responses.parse()` API for structured output
- Returns `result.output_parsed` (Pydantic model)
- Implements `aclose()` to properly close the client

**Anthropic Adapter** (`adapters.py`):
- Uses `AsyncAnthropic` client
- Leverages beta `messages.parse()` API with structured outputs
- Uses `betas=["structured-outputs-2025-11-13"]` for latest features
- Returns `result.parsed_output` (Pydantic model)
- Implements `aclose()` to properly close the client

**Gemini Adapter** (`adapters.py`):
- Uses `genai.Client` with async methods
- Separates system instructions from user messages (Gemini requirement)
- Supports both tuple `(system, user)` and list message formats
- Uses `GenerateContentConfig` with `response_schema` for structured output
- Returns `result.parsed` directly
- Implements `aclose()` to properly close the async client

**Provider Differences Handled**:
- Message format: OpenAI uses standard chat format; Anthropic uses standard chat format; Gemini separates system/user
- Structured output: OpenAI uses `text_format`; Anthropic uses `output_format` with betas; Gemini uses `response_schema`
- Client initialization: Different SDK patterns and API endpoints
- Resource cleanup: Different close methods across providers

#### 2. Factory Pattern (`client/factory.py`)

**Purpose**: Centralize client creation and validation logic.

**Key Features**:

1. **Provider-Model Mapping**:
```python
PROVIDER_MODELS = {
    LLMProvider.OPENAI: OpenAIModel.list_str(),
    LLMProvider.GEMINI: GeminiModel.list_str(),
    LLMProvider.ANTHROPIC: AnthropicModel.list_str(),
}
```

2. **Validation Before Creation**:
- Checks if provider exists
- Verifies model is supported for that provider
- Raises descriptive `ValueError` with supported options

3. **Client Instantiation**:
- Single source of truth for creating adapters
- Hides concrete adapter classes from business logic
- Enables easy addition of new providers
- Returns appropriate adapter (OpenAI, Anthropic, or Gemini) based on provider parameter

**Benefits**:
- **Single Responsibility**: One place to manage client creation
- **Open/Closed Principle**: Add new providers without modifying existing code
- **Validation**: Catch errors early with clear messages
- **Testability**: Easy to mock factory in tests

#### 3. Service Layer (`service/request_llm.py`)

**Purpose**: Provide business logic abstraction over adapters.

**Implementation** (`request_llm.py`):
```python
async def request_llm(
    client: LLMClient,
    model: str,
) -> CharacterResponse:
    # Get prompt
    prompt = make_prompt()

    # Make request using unified interface
    result = await client.chat(
        messages=prompt,
        response_format=CharacterResponse,
    )

    return result
```

**Key Points**:
- **Provider-agnostic**: Same code works for any provider (OpenAI, Anthropic, Gemini)
- **Dependency injection**: Client is injected, promoting testability
- **Separation of concerns**: Prompt generation separate from API calls
- **Error handling**: Propagates exceptions with context
- **Clean interface**: Service layer doesn't need to know about factory or provider details

## Data Models

### Character Models (`model/model.py`)

**Design Philosophy**: Strict validation, immutability, type safety.

```python
class Gender(StrEnum):
    FEMALE = "female"
    MALE = "male"

class CharacterPersonality(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,  # Validate on assignment
        frozen=True,               # Immutable after creation
        extra="ignore",            # Ignore unknown fields
    )

    short_personality: str
    description: str

class CharacterResponse(BaseModel):
    first_name: str
    last_name: str
    gender: Gender
    age: int = Field(ge=0, le=100)  # Constrained integer
    personalities: list[CharacterPersonality]
```

**Pydantic Features Used**:
- **Field constraints**: `ge=0, le=100` ensures valid age range
- **Frozen models**: Prevents accidental mutations
- **StrEnum**: Type-safe gender values
- **Nested models**: Complex structures with validation
- **Extra ignore**: Robust against API response changes

## Provider and Model Enums (`client/model.py`)

**Purpose**: Type-safe provider and model identifiers.

```python
class LLMProvider(StrEnum):
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"

class OpenAIModel(StrEnum):
    GPT_5_5 = "gpt-5.5"
    GPT_5_4 = "gpt-5.4"
    GPT_5_4_MINI = "gpt-5.4-mini"
    GPT_5_4_NANO = "gpt-5.4-nano"
    GPT_5_2 = "gpt-5.2"
    GPT_5_1 = "gpt-5.1"
    GPT_5 = "gpt-5"
    GPT_5_MINI = "gpt-5-mini"
    GPT_5_NANO = "gpt-5-nano"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in OpenAIModel]

class AnthropicModel(StrEnum):
    CLAUDE_SONNET_4_6 = "claude-sonnet-4-6"
    CLAUDE_OPUS_4_7 = "claude-opus-4-7"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in AnthropicModel]
```

**Benefits**:
- **Autocomplete**: IDE suggestions for valid values
- **Type checking**: Catch typos at development time
- **String compatibility**: `StrEnum` works with string comparisons
- **Enumeration**: `list_str()` provides all valid values

## Configuration Management (`config.py`)

Expected structure:
```python
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    openai_api_key: str
    gemini_api_key: str
    anthropic_api_key: str

    class Config:
        env_file = ".env"

config = Config()
```

**Best Practices**:
- Use `pydantic-settings` for type-safe environment variables
- Never commit `.env` files
- Provide `.envrc.example` as template
- Validate required keys at startup

## Testing Strategy

### Test Coverage

#### Adapter Tests (`tests/test_adapters.py`)

**What to Test**:
1. **Interface compliance**: Verify adapters implement `LLMClient`
2. **Initialization**: Check correct client and model setup for OpenAI, Anthropic, and Gemini
3. **Chat functionality**: Mock API calls and verify response parsing for all three providers
4. **Error handling**: Test API failures, invalid responses
5. **Provider/model metadata**: Verify `get_provider_name()`, `get_model_name()`
6. **Resource cleanup**: Test `aclose()` method for proper resource release

**Example Test Pattern**:
```python
@pytest.mark.asyncio
async def test_openai_chat_success(self, mocker):
    # Mock the API client
    mock_client = mocker.patch('openai.AsyncOpenAI')
    mock_response = mocker.Mock()
    mock_response.output_parsed = CharacterResponse(...)

    # Test the adapter
    adapter = OpenAIAdapter(model="gpt-5.4")
    result = await adapter.chat(messages, CharacterResponse)

    # Verify
    assert isinstance(result, CharacterResponse)
    mock_client.responses.parse.assert_called_once()

@pytest.mark.asyncio
async def test_anthropic_chat_success(self, mocker):
    # Mock the API client
    mock_client = mocker.patch('anthropic.AsyncAnthropic')
    mock_response = mocker.Mock()
    mock_response.parsed_output = CharacterResponse(...)

    # Test the adapter
    adapter = AnthropicAdapter(model="claude-sonnet-4-6")
    result = await adapter.chat(messages, CharacterResponse)

    # Verify
    assert isinstance(result, CharacterResponse)
    mock_client.beta.messages.parse.assert_called_once()
```

#### Factory Tests (`tests/test_factory.py`)

**What to Test**:
1. **Provider enumeration**: `get_supported_providers()`
2. **Model enumeration**: `get_supported_models(provider)`
3. **Validation**: `is_valid_combination(provider, model)`
4. **Client creation**: Correct adapter type returned
5. **Error cases**: Invalid provider, invalid model, wrong combination
6. **Case insensitivity**: Provider names should work regardless of case

**Example Test Pattern**:
```python
def test_create_client_openai(self):
    client = LLMClientFactory.create_client(
        provider=LLMProvider.OPENAI,
        model=OpenAIModel.GPT_5_4
    )
    assert isinstance(client, OpenAIAdapter)
    assert client.get_provider_name() == LLMProvider.OPENAI

def test_invalid_combination(self):
    with pytest.raises(ValueError):
        LLMClientFactory.create_client(
            provider=LLMProvider.OPENAI,
            model=GeminiModel.GEMINI_2_5_PRO  # Wrong!
        )

def test_create_client_anthropic(self):
    client = LLMClientFactory.create_client(
        provider=LLMProvider.ANTHROPIC,
        model=AnthropicModel.CLAUDE_SONNET_4_6
    )
    assert isinstance(client, AnthropicAdapter)
    assert client.get_provider_name() == LLMProvider.ANTHROPIC
```

### Testing Best Practices

1. **Mock external APIs**: Never call real APIs in unit tests
2. **Test boundaries**: Validate input validation logic
3. **Test both paths**: Success and failure scenarios
4. **Async tests**: Use `pytest-asyncio` for async code
5. **Fixtures**: Share common setup (mock clients, sample data)

## Extending the System

### Adding a New Provider

This project already includes three providers (OpenAI, Anthropic, Gemini). Here's how Anthropic was added as an example:

**Example: How Anthropic Claude Was Added**

1. **Define model enum** (`client/model.py`):
```python
class AnthropicModel(StrEnum):
    CLAUDE_SONNET = "claude-sonnet-4-6"
    CLAUDE_HAIKU = "claude-haiku-4-5"

    @staticmethod
    def list_str() -> list[str]:
        return [model for model in AnthropicModel]
```

2. **Create adapter** (`client/adapters.py`):
```python
class AnthropicAdapter(LLMClient):
    def __init__(self, model: str):
        self._client = AsyncAnthropic(api_key=config.anthropic_api_key)
        self._model = model

    async def chat(
        self,
        messages: list[dict[str, str]],
        response_format: type,
        **kwargs: Any,
    ) -> BaseModel:
        # Use beta structured outputs API
        result = await self._client.beta.messages.parse(
            model=self._model,
            max_tokens=kwargs.get("max_tokens", 1024),
            betas=["structured-outputs-2025-11-13"],
            messages=messages,
            output_format=response_format,
            **{k: v for k, v in kwargs.items() if k != "max_tokens"},
        )
        return result.parsed_output

    def get_provider_name(self) -> str:
        return LLMProvider.ANTHROPIC

    def get_model_name(self) -> str:
        return self._model

    async def aclose(self) -> None:
        await self._client.close()
```

3. **Update factory** (`client/factory.py`):
```python
PROVIDER_MODELS = {
    LLMProvider.OPENAI: OpenAIModel.list_str(),
    LLMProvider.GEMINI: GeminiModel.list_str(),
    LLMProvider.ANTHROPIC: AnthropicModel.list_str(),  # Add this
}

# In create_client method:
elif provider_lower == LLMProvider.ANTHROPIC:
    return AnthropicAdapter(model=model)
```

4. **Update configuration** (`config.py`):
```python
class Config(BaseSettings):
    openai_api_key: str
    gemini_api_key: str
    anthropic_api_key: str  # Add this
```

5. **Write tests** (`tests/test_adapters.py`, `tests/test_factory.py`):
- Add `TestAnthropicAdapter` class
- Test all interface methods
- Add factory tests for Anthropic

**That's it!** Minimal changes needed to:
- Service layer (`service/request_llm.py`) - already uses dependency injection, no changes needed
- CLI layer (`main.py`) - update to include Anthropic in choices
- Data models (`model/model.py`) - no changes needed

### Adding a New Model to Existing Provider

Simply add to the appropriate enum:
```python
class OpenAIModel(StrEnum):
    # Existing models...
    GPT_6 = "gpt-6"  # New model
```

The factory's `PROVIDER_MODELS` mapping will automatically include it.

## Common Pitfalls and Solutions

### 1. API Key Management

**Pitfall**: Hardcoding API keys or committing them to git.

**Solution**:
- Use environment variables
- Add `.env` to `.gitignore`
- Provide `.envrc.example` template
- Use `pydantic-settings` for validation

### 2. Error Handling

**Pitfall**: Generic exception catching loses context.

**Solution**:
```python
try:
    result = await client.chat(messages, response_format)
except Exception as e:
    logger.error(f"LLM request failed: {provider}/{model} - {str(e)}")
    raise
```

### 3. Async/Await Confusion

**Pitfall**: Forgetting `await` on async methods.

**Solution**:
- Always mark functions that call async code as `async`
- Use `await` when calling async methods
- Use `asyncio.run()` for top-level entry points
- Type hints help: `async def chat(...) -> BaseModel`

### 4. Type Safety

**Pitfall**: Using strings for providers/models leads to typos.

**Solution**:
- Use `StrEnum` for all identifiers
- Leverage type hints: `provider: LLMProvider`
- Factory validates combinations

### 5. Testing Real APIs

**Pitfall**: Tests calling real APIs are slow and flaky.

**Solution**:
- Mock all external calls with `pytest-mock`
- Separate integration tests from unit tests
- Use fixtures for common mocks

## Best Practices Demonstrated

### 1. SOLID Principles

- **Single Responsibility**: Each class has one job
  - `LLMClient`: Define interface
  - `OpenAIAdapter`: Implement OpenAI integration
  - `LLMClientFactory`: Create clients
  - `request_llm`: Business logic

- **Open/Closed**: Open for extension, closed for modification
  - Add new providers without changing existing code
  - Factory pattern enables this

- **Liskov Substitution**: Any `LLMClient` can replace another
  - Same interface for all providers
  - Polymorphism enables provider swapping

- **Interface Segregation**: Minimal interface
  - Only three methods required
  - No unnecessary dependencies

- **Dependency Inversion**: Depend on abstractions
  - Service layer depends on `LLMClient` interface, not concrete adapters
  - Factory injects appropriate implementation

### 2. Type Safety

- **Pydantic models**: Runtime validation and type checking
- **StrEnum**: Type-safe identifiers
- **Type hints**: `-> CharacterResponse`, `list[dict[str, str]]`
- **Generic types**: `response_format: type`

### 3. Separation of Concerns

- **Layers**: CLI -> Service -> Adapter -> Infrastructure
- **Prompt management**: Separate module for prompt logic
- **Configuration**: Centralized in `config.py`
- **Logging**: Consistent across all modules

### 4. Testability

- **Dependency injection**: Factory provides clients
- **Async support**: Full async/await for better performance
- **Mocking**: All external dependencies mockable
- **Comprehensive tests**: Full test coverage for all three providers

### 5. Documentation

- **Docstrings**: All public methods documented
- **Type hints**: Self-documenting interfaces
- **Examples**: README with usage examples
- **This file**: Architectural documentation

## Performance Considerations

### Async I/O

All LLM calls are async, enabling:
- Concurrent requests to different providers
- Efficient I/O handling
- Better resource utilization

Example concurrent usage:
```python
async def compare_providers():
    # Create clients
    openai_client = LLMClientFactory.create_client(
        LLMProvider.OPENAI, OpenAIModel.GPT_5_4
    )
    anthropic_client = LLMClientFactory.create_client(
        LLMProvider.ANTHROPIC, AnthropicModel.CLAUDE_SONNET_4_6
    )
    gemini_client = LLMClientFactory.create_client(
        LLMProvider.GEMINI, GeminiModel.GEMINI_2_5_PRO
    )

    # Run requests concurrently
    openai_task = request_llm(openai_client, "gpt-5.4")
    anthropic_task = request_llm(anthropic_client, "claude-sonnet-4-6")
    gemini_task = request_llm(gemini_client, "gemini-2.5-pro")

    results = await asyncio.gather(
        openai_task, anthropic_task, gemini_task
    )

    # Clean up
    await asyncio.gather(
        openai_client.aclose(),
        anthropic_client.aclose(),
        gemini_client.aclose()
    )

    return results
```

### Caching Considerations

For production systems, consider:
- **Client reuse**: Don't recreate clients for each request
- **Response caching**: Cache identical prompts (with TTL)
- **Connection pooling**: Reuse HTTP connections

Example client singleton:
```python
class LLMClientFactory:
    _clients: dict[tuple[str, str], LLMClient] = {}

    @classmethod
    def create_client(cls, provider, model):
        key = (provider, model)
        if key not in cls._clients:
            # Create client as before
            cls._clients[key] = new_client
        return cls._clients[key]
```

## Security Considerations

1. **API Key Protection**:
   - Never log API keys
   - Use environment variables
   - Rotate keys regularly

2. **Input Validation**:
   - Validate all user inputs (CLI args)
   - Use Pydantic for automatic validation
   - Sanitize prompts if user-generated

3. **Output Validation**:
   - Pydantic models ensure valid responses
   - Handle parsing errors gracefully
   - Log validation failures

4. **Rate Limiting**:
   - Implement retry logic with backoff
   - Respect provider rate limits
   - Consider async semaphores for concurrency control

## Monitoring and Observability

### Logging Strategy

Current implementation logs:
- Adapter initialization (`adapters.py:38, 92`)
- Request start/completion (`request_llm.py:41, 52`)
- Factory client creation (`factory.py:66`)

**Recommended additions**:
- Request latency metrics
- Error rates by provider
- Token usage tracking
- Cost monitoring

### Example Enhanced Logging:
```python
import time

async def request_llm(provider, model):
    start_time = time.time()
    try:
        client = LLMClientFactory.create_client(provider, model)
        result = await client.chat(messages, response_format)

        duration = time.time() - start_time
        logger.info(
            f"LLM request completed",
            extra={
                "provider": provider,
                "model": model,
                "duration_ms": duration * 1000,
                "status": "success"
            }
        )
        return result
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"LLM request failed",
            extra={
                "provider": provider,
                "model": model,
                "duration_ms": duration * 1000,
                "error": str(e),
                "status": "error"
            }
        )
        raise
```

## Deployment Considerations

### Environment-Specific Configuration

Use different configurations for dev/staging/prod:
```python
class Config(BaseSettings):
    env: str = "development"
    openai_api_key: str
    gemini_api_key: str
    anthropic_api_key: str
    log_level: str = "INFO"

    class Config:
        env_file = f".env.{os.getenv('ENV', 'development')}"
```

### Docker Deployment

Example `Dockerfile`:

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install -e .

COPY src src/
COPY .env .env

CMD ["python", "-m", "src.main"]
```

### Health Checks

Add health check endpoint for monitoring:
```python
async def health_check() -> dict:
    """Verify all configured providers are accessible."""
    results = {}
    for provider in LLMProvider:
        try:
            # Simple test request
            results[provider] = "healthy"
        except Exception as e:
            results[provider] = f"unhealthy: {str(e)}"
    return results
```

## Future Enhancements

### 1. Retry Logic with Exponential Backoff

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def chat_with_retry(client, messages, response_format):
    return await client.chat(messages, response_format)
```

### 2. Response Streaming

Support streaming for real-time responses:
```python
class LLMClient(ABC):
    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream chat completion chunks."""
        pass
```

### 3. Cost Tracking

Track token usage and costs:
```python
class UsageMetrics(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float

class LLMClient(ABC):
    @abstractmethod
    async def chat(
        self, ...
    ) -> tuple[BaseModel, UsageMetrics]:
        pass
```

### 4. Multi-Model Ensemble

Combine responses from multiple providers:
```python
async def ensemble_request(prompt, provider_configs):
    """
    provider_configs: list of (provider, model) tuples
    e.g., [(LLMProvider.OPENAI, "gpt-5.4"),
           (LLMProvider.ANTHROPIC, "claude-sonnet-4-6"),
           (LLMProvider.GEMINI, "gemini-2.5-pro")]
    """
    clients = [
        LLMClientFactory.create_client(provider, model)
        for provider, model in provider_configs
    ]

    tasks = [
        request_llm(client, model)
        for client, (_, model) in zip(clients, provider_configs)
    ]

    results = await asyncio.gather(*tasks)

    # Clean up clients
    await asyncio.gather(*[client.aclose() for client in clients])

    return consensus(results)  # Voting or averaging logic
```

## Conclusion

This implementation demonstrates production-ready practices for LLM integration:

**Key Takeaways**:
1. **Abstraction**: Hide provider differences behind common interface
2. **Flexibility**: Easily swap or add providers
3. **Type Safety**: Leverage Python's type system and Pydantic
4. **Testability**: Comprehensive test coverage with mocking
5. **Maintainability**: Clear separation of concerns
6. **Extensibility**: Open/closed principle enables growth

**When to Use This Pattern**:
- Multi-provider LLM applications
- Systems requiring provider flexibility
- Production applications needing reliability
- Projects with long-term maintenance needs

**When NOT to Use**:
- Simple scripts with single provider
- Prototypes with no production plans
- Provider-specific feature requirements (may need custom logic)

This architecture balances pragmatism with best practices, providing a solid foundation for production LLM applications.
