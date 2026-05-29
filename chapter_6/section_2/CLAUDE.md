# Chapter 3 Section 9: Thin Wrapper Library for LLM SDKs

## Project Overview

This project demonstrates a production-ready implementation of a **thin wrapper library** for LLM SDKs. It wraps the official OpenAI, Google Gemini, and Anthropic Python SDKs to provide transparent logging, token usage tracking, and performance measurement without altering the original SDK interfaces.

### Core Concept

When integrating LLMs into production systems, teams often face challenges around observability, cost tracking, and consistent error handling across different providers. Direct use of official SDKs is simple initially, but quickly becomes problematic when you need to:

- Track API usage across departments for cost allocation
- Monitor performance metrics for SLA compliance
- Implement consistent retry logic for transient failures
- Switch between LLM providers without refactoring application code

This implementation solves these challenges by creating a transparent wrapper layer that intercepts SDK calls, logs comprehensive metadata, and delegates actual functionality to the official SDKs.

### Key Technologies

- **OpenAI Python SDK (v2.4.0+)**: Official SDK for GPT models with structured outputs
- **Google GenAI Python SDK (v1.45.0+)**: Official SDK for Gemini models
- **Anthropic Python SDK (v0.74.1+)**: Official SDK for Claude models with structured outputs
- **Pydantic**: Data validation and settings management with type safety
- **Python `__getattr__`**: Dynamic method delegation for transparent wrapping
- **JSON Logging**: Structured logs for analysis and monitoring

### Architecture Pattern

The system implements a **Transparent Proxy pattern** with decorator-style wrapping:

```
Application Code
       |
       v
Wrapper Client (OpenAIWrapperClient, GenAIWrapperClient, AnthropicWrapperClient)
       | (intercepts method calls)
       v
Logging Layer (records metadata)
       | (delegates to original)
       v
Official SDK (OpenAI, Google GenAI, Anthropic)
       |
       v
LLM API (OpenAI, Google, Anthropic)
```

**Key Design Principle**: The wrapper maintains 100% interface compatibility. Applications using the wrapper can replace `from openai import AsyncOpenAI` with `from src.client.openai_wrapper_client import AsyncOpenAIWrapperClient` without changing any other code.

## Directory Structure

```
chapter_3/section_9/
+-- src/
|   +-- __init__.py                  # Package initialization
|   +-- config.py                    # Configuration management (API keys, log directory)
|   +-- logger.py                    # Logging configuration
|   +-- main.py                      # CLI entry point
|   +-- client/
|   |   +-- __init__.py
|   |   +-- llm_client.py            # Wrapper client initialization
|   |   +-- openai_wrapper_client.py     # OpenAI wrapper implementation
|   |   +-- gemini_wrapper_client.py     # Gemini wrapper implementation
|   |   +-- anthropic_wrapper_client.py  # Anthropic wrapper implementation
|   +-- model/
|   |   +-- __init__.py
|   |   +-- model.py                 # Pydantic data models
|   +-- prompt/
|   |   +-- __init__.py
|   |   +-- prompt.py                # Prompt generation logic
|   +-- service/
|       +-- __init__.py
|       +-- request_llm.py           # LLM request processing
+-- tests/
|   +-- __init__.py
|   +-- test_wrapper_client.py       # Wrapper unit tests
+-- outputs/                          # Generated output files (auto-created)
+-- usage_logs/                       # Usage logs (auto-created)
+-- .envrc.example                    # Environment variable template
+-- Makefile                          # Development commands
+-- pyproject.toml                    # Project dependencies
+-- README.md                         # User documentation (Japanese)
+-- CLAUDE.md                         # This file
```

## Key Components

### Wrapper Clients

| File | Class | Description |
|------|-------|-------------|
| `openai_wrapper_client.py` | `OpenAIWrapperClient` | Sync wrapper for OpenAI SDK |
| `openai_wrapper_client.py` | `AsyncOpenAIWrapperClient` | Async wrapper for OpenAI SDK |
| `gemini_wrapper_client.py` | `GenAIWrapperClient` | Wrapper for Google GenAI SDK |
| `anthropic_wrapper_client.py` | `AnthropicWrapperClient` | Sync wrapper for Anthropic SDK |
| `anthropic_wrapper_client.py` | `AsyncAnthropicWrapperClient` | Async wrapper for Anthropic SDK |

### Wrapped Methods

**OpenAI**:
- `client.chat.completions.create()` - Chat completions
- `client.responses.create()` - Responses API
- `client.responses.parse()` - Structured output parsing

**Gemini**:
- `client.models.generate_content()` - Sync content generation
- `client.aio.models.generate_content()` - Async content generation

**Anthropic**:
- `client.messages.create()` - Message creation
- `client.messages.count_tokens()` - Token counting
- `client.beta.messages.create()` - Beta messages
- `client.beta.messages.parse()` - Structured output parsing

### Available Models

**OpenAI**: gpt-5.5, gpt-5.4, gpt-5.4-mini, gpt-5.4-nano, gpt-5.2, gpt-5.1, gpt-5, gpt-5-mini, gpt-5-nano

**Gemini**: gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite, gemini-3.5-flash, gemini-3.1-flash-lite

**Anthropic**: claude-sonnet-4-6, claude-opus-4-7

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| anthropic | >=0.74.1 | Anthropic Claude SDK |
| click | >=8.3.0 | CLI framework |
| google-genai | >=1.45.0 | Google Gemini SDK |
| openai | >=2.4.0 | OpenAI SDK |
| pydantic | >=2.12.2 | Data validation |
| pytest | >=8.4.2 | Testing framework |
| pytest-asyncio | >=1.2.0 | Async test support |
| pytest-mock | >=3.15.1 | Mocking utilities |
| python-dotenv | >=1.1.1 | Environment variable loading |

## Usage

### Setup

1. Create environment file:
```bash
cp .envrc.example .envrc
```

2. Edit `.envrc` with your API keys:
```bash
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
GOOGLE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
```

3. Install dependencies:
```bash
uv sync
```

### Run

```bash
# OpenAI
uv run python -m src.main -lp openai -m gpt-5.4-mini

# Gemini
uv run python -m src.main -lp gemini -m gemini-2.5-flash

# Anthropic
uv run python -m src.main -lp anthropic -m claude-sonnet-4-6

# With custom output directory
uv run python -m src.main -lp openai -m gpt-5.4 -od ./custom_output
```

### CLI Options

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| --llm-provider | -lp | Yes | gemini | LLM provider (openai, gemini, anthropic) |
| --model | -m | Yes | - | Model name to use |
| --output-directory | -od | No | outputs | Directory for output files |
| --help | - | No | - | Show help message |

## Development Commands

```bash
# Run linter (ruff)
make lint

# Run formatter (ruff)
make fmt

# Run both linter and formatter
make fix

# Run type checker (mypy)
make mypy

# Run tests
pytest

# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/test_wrapper_client.py
```

## Implementation Notes

### Design Principles

1. **Thin by Default**: The wrapper does not hide SDK functionality. All original SDK methods remain accessible via `__getattr__` delegation.

2. **Transparent Operation**: Application code requires only import changes - no behavioral modifications needed.

3. **Cross-Cutting Concerns Only**: The wrapper handles logging, performance measurement, and token tracking. Business logic stays in application code.

### Wrapper Hierarchy

```
AsyncOpenAIWrapperClient (inherits AsyncOpenAI)
    +-- .chat (property) -> ChatWrapper
    |       +-- .completions (property) -> AsyncChatCompletionsWrapper
    |               +-- .create() -> [WRAPPED WITH LOGGING]
    +-- .responses (property) -> AsyncResponsesWrapper
            +-- .create() -> [WRAPPED WITH LOGGING]
            +-- .parse() -> [WRAPPED WITH LOGGING]

GenAIWrapperClient (inherits genai.Client)
    +-- .models (property) -> ModelsWrapper
    |       +-- .generate_content() -> [WRAPPED WITH LOGGING]
    +-- .aio (property) -> AioWrapper
            +-- .models (property) -> AsyncModelsWrapper
                    +-- .generate_content() -> [WRAPPED WITH LOGGING]

AsyncAnthropicWrapperClient (inherits AsyncAnthropic)
    +-- .messages (property) -> AsyncMessagesWrapper
    |       +-- .create() -> [WRAPPED WITH LOGGING]
    |       +-- .count_tokens() -> [WRAPPED WITH LOGGING]
    +-- .beta (property) -> BetaWrapper
            +-- .messages (property) -> AsyncBetaMessagesWrapper
                    +-- .create() -> [WRAPPED WITH LOGGING]
                    +-- .parse() -> [WRAPPED WITH LOGGING]
```

### Lazy Initialization

Wrappers are created on-demand to minimize overhead:

```python
@property
def chat(self):
    if self._chat_wrapper is None:
        self._chat_wrapper = ChatWrapper(super().chat, self._log_dir, is_async=True)
    return self._chat_wrapper
```

### Log Format

Each API call generates a JSON log file with:

```json
{
  "timestamp": "2025-11-01T10:17:39.694420",
  "method": "chat.completions.create",
  "duration_ms": 3247.82,
  "request": {
    "model": "gpt-5.4-mini",
    "messages": [...],
    "temperature": 1.0
  },
  "response": {
    "id": "chatcmpl-ABC123",
    "usage": {
      "prompt_tokens": 156,
      "completion_tokens": 243,
      "total_tokens": 399
    }
  }
}
```

### Log File Naming

| Provider | Pattern |
|----------|---------|
| OpenAI (sync) | `openai_YYYYMMDD_HHMMSS_ffffff.json` |
| OpenAI (async) | `async_openai_YYYYMMDD_HHMMSS_ffffff.json` |
| OpenAI Responses | `openai_responses_YYYYMMDD_HHMMSS_ffffff.json` |
| Gemini (sync) | `genai_YYYYMMDD_HHMMSS_ffffff.json` |
| Gemini (async) | `async_genai_YYYYMMDD_HHMMSS_ffffff.json` |
| Anthropic (sync) | `anthropic_YYYYMMDD_HHMMSS_ffffff.json` |
| Anthropic (async) | `async_anthropic_YYYYMMDD_HHMMSS_ffffff.json` |
| Anthropic Beta | `anthropic_beta_YYYYMMDD_HHMMSS_ffffff.json` |

### Configuration

API keys are managed via Pydantic with `Secret[str]` for security:

```python
class Config(BaseModel):
    google_api_key: Secret[str] = Field(default=os.environ.get("GOOGLE_API_KEY", ""))
    openai_api_key: Secret[str] = Field(default=os.environ.get("OPENAI_API_KEY", ""))
    anthropic_api_key: Secret[str] = Field(default=os.environ["ANTHROPIC_API_KEY"])
    usage_log_directory: str = Field(default="usage_logs")
```

### Token Usage Tracking

Provider-specific token field mapping:

| Provider | Input Tokens | Output Tokens | Total Tokens |
|----------|--------------|---------------|--------------|
| OpenAI | `prompt_tokens` | `completion_tokens` | `total_tokens` |
| Gemini | `prompt_token_count` | `candidates_token_count` | `total_token_count` |
| Anthropic | `input_tokens` | `output_tokens` | (computed) |

### Log Analysis Examples

```bash
# Total tokens by OpenAI
cat usage_logs/async_openai_*.json | jq -s 'map(.response.usage.total_tokens) | add'

# Total tokens by Gemini
cat usage_logs/async_genai_*.json | jq -s 'map(.response.usage_metadata.total_token_count) | add'

# Total tokens by Anthropic
cat usage_logs/async_anthropic_*.json | jq -s 'map(.response.usage.input_tokens + .response.usage.output_tokens) | add'

# Average processing time
cat usage_logs/*.json | jq -s 'map(.duration_ms) | add / length'

# Requests per model
cat usage_logs/*.json | jq -s 'group_by(.request.model) | map({model: .[0].request.model, count: length})'
```

## Current Limitations

- No automatic retry logic for transient errors
- No request/response caching
- No streaming response support
- Synchronous file writes (may add latency in high-volume scenarios)
- File-based logging only (no centralized log aggregation)

## Testing

Unit tests use mocking to validate wrapper behavior without real API calls:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

Test coverage includes:
- Sync and async wrappers for all providers
- Log file creation and format validation
- Token usage extraction
- Duration measurement
- `__getattr__` delegation
