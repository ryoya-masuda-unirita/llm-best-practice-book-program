# Chapter 3 Section 3: LLM API Service Interface Segregation

## Overview

This project demonstrates the **Interface Segregation Principle (ISP)** applied to LLM API services. It implements two distinct functionalities - text generation and text classification - as independent service interfaces, managed through a Dependency Injection (DI) pattern using Anthropic Claude API.

## Architecture

```
+----------------------------------------------------------+
|                    FastAPI Server                         |
|  +------------------+    +---------------------------+   |
|  | POST /generate   |    | POST /classify            |   |
|  +--------+---------+    +-------------+-------------+   |
+-----------|-----------------------------|----------------+
            |                             |
            v                             v
+----------------------------------------------------------+
|                  ServiceContainer (DI)                    |
|  +------------------------+  +-------------------------+ |
|  | get_text_generation_   |  | get_text_classification_| |
|  | service()              |  | service()               | |
|  +-----------+------------+  +------------+------------+ |
+--------------|----------------------------|--------------+
               |                            |
               v                            v
+---------------------------+  +----------------------------+
| ITextGenerationService    |  | ITextClassificationService |
| (Abstract Interface)      |  | (Abstract Interface)       |
+-----------+---------------+  +-------------+--------------+
            |                                |
            v                                v
+---------------------------+  +----------------------------+
| TextGenerationService     |  | TextClassificationService  |
| (Concrete Implementation) |  | (Concrete Implementation)  |
+-----------+---------------+  +-------------+--------------+
            |                                |
            +---------------+----------------+
                            |
                            v
              +---------------------------+
              |    Anthropic Client       |
              |    (AsyncAnthropic)       |
              +---------------------------+
```

### Directory Structure

```
chapter_3/section_3/
|-- src/
|   |-- __init__.py
|   |-- config.py              # Configuration (API keys)
|   |-- logger.py              # Logging setup
|   |-- api/
|   |   |-- __init__.py
|   |   +-- llm_server.py      # FastAPI application
|   |-- client/
|   |   |-- __init__.py
|   |   +-- llm_client.py      # Anthropic client setup
|   |-- model/
|   |   |-- __init__.py
|   |   +-- model.py           # Pydantic data models
|   |-- prompt/
|   |   |-- __init__.py
|   |   +-- prompt.py          # Prompt generation
|   +-- service/
|       |-- __init__.py
|       |-- interfaces.py      # Service interfaces (ISP)
|       |-- container.py       # DI container
|       |-- text_generation_service.py
|       +-- text_classification_service.py
|-- .env.example
|-- docker-compose.yml
|-- Dockerfile.web
|-- Makefile
|-- pyproject.toml
+-- README.md
```

## Key Components

### Service Interfaces (`src/service/interfaces.py`)

- `ITextGenerationService` - Abstract interface for text generation
  - `generate_character()` - Generate character with structured output
- `ITextClassificationService` - Abstract interface for text classification
  - `classify()` - Classify text into categories
- `get_available_models()` - Helper to get models by user plan

### Service Implementations

- `TextGenerationService` - Implements character generation using Anthropic
- `TextClassificationService` - Implements text classification using Anthropic

### DI Container (`src/service/container.py`)

- `ServiceContainer` - Manages service instances
  - `get_text_generation_service()` - Returns ITextGenerationService
  - `get_text_classification_service()` - Returns ITextClassificationService

### LLM Client (`src/client/llm_client.py`)

- `AnthropicModel` - Enum of available models
  - `CLAUDE_SONNET_4_5` - claude-sonnet-4-5
  - `CLAUDE_OPUS_4` - claude-opus-4
- `anthropic_client` - AsyncAnthropic client instance

### Data Models (`src/model/model.py`)

| Model | Purpose |
|-------|---------|
| `UserPlan` | FREE or STANDARD plan |
| `CharacterRequest` | Input for character generation |
| `CharacterResponse` | Generated character output |
| `LLMRequest` | API request for /generate |
| `LLMResponse` | API response for /generate |
| `TextClassificationRequest` | API request for /classify |
| `ClassificationResult` | Classification output (structured) |
| `TextClassificationResponse` | API response for /classify |

### Plan-Based Model Restrictions

| Plan | Available Models |
|------|------------------|
| FREE | claude-sonnet-4-5 |
| STANDARD | claude-sonnet-4-5, claude-opus-4 |

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| anthropic | >=0.74.1 | Anthropic Claude API client |
| fastapi | >=0.119.0 | Web framework |
| pydantic | >=2.12.2 | Data validation |
| uvicorn | >=0.37.0 | ASGI server |
| python-dotenv | >=1.1.1 | Environment variables |

## Usage

### Setup

```bash
# Copy environment template
cp .env.example .envrc

# Set your API key in .envrc
# ANTHROPIC_API_KEY=sk-ant-xxxxx

# Install dependencies
uv sync
```

### Run

```bash
# Development server with hot reload
uv run uvicorn src.api.llm_server:app --host 0.0.0.0 --port 8000 --reload

# Or using Docker
make docker-build
make docker-up
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| POST | /generate | Character generation |
| POST | /classify | Text classification |

### Example Requests

**Character Generation:**
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5",
    "user_plan": "free",
    "character_request": {
      "gender": "female",
      "age": 25,
      "additional_instructions": "Adventurous personality"
    }
  }'
```

**Text Classification:**
```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5",
    "user_plan": "free",
    "text": "This product is excellent!",
    "categories": ["Positive", "Negative", "Neutral"]
  }'
```

## Development Commands

| Command | Description |
|---------|-------------|
| `make lint` | Run ruff linter |
| `make fmt` | Format code with ruff |
| `make fix` | Run lint and format |
| `make mypy` | Type checking |
| `make docker-build` | Build Docker image |
| `make docker-up` | Start containers |
| `make docker-down` | Stop containers |
| `make docker-logs` | View container logs |

## Implementation Notes

### Interface Segregation Principle

Each service interface has a single responsibility:
- `ITextGenerationService` - Only character generation
- `ITextClassificationService` - Only text classification

Clients depend only on the interfaces they need, not a monolithic service.

### Dependency Injection

The `ServiceContainer` centralizes service creation:
- Services are instantiated once at startup
- Anthropic client is shared across services
- Easy to mock for testing

### Structured Output

Uses Anthropic's beta structured output feature:
```python
result = await self.client.beta.messages.parse(
    model=model,
    max_tokens=1024,
    betas=["structured-outputs-2025-11-13"],
    messages=prompt,
    output_format=CharacterResponse,  # Pydantic model
)
```

### Request Flow

```
1. Client -> POST /generate
2. FastAPI validates request with Pydantic
3. ServiceContainer provides ITextGenerationService
4. Service validates user plan model access
5. Prompt generated via make_generation_prompt()
6. Anthropic API called with structured output
7. Response parsed into CharacterResponse
8. LLMResponse returned to client
```

### Error Handling

- Plan restriction errors: HTTP 400 with available models listed
- Validation errors: HTTP 400 with Pydantic error details
- LLM errors: HTTP 500 with error message

### Security

- API keys stored in environment variables
- Secret type masks keys in logs
- Pydantic validates all input
- Age constrained to 0-100 range
