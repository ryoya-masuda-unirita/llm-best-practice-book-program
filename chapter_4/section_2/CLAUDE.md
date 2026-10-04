# Chapter 4 Section 2: Interface Segregation and DI for LLM API Services

## What This Section Demonstrates

This section applies the **Interface Segregation Principle (ISP)** and **Dependency Injection (DI)** to an LLM API service. Two independent capabilities — text generation and text classification — are defined as separate abstract interfaces (`ITextGenerationService`, `ITextClassificationService`) with separate concrete implementations, wired together by a `ServiceContainer` and exposed through FastAPI endpoints.

It also demonstrates **plan-based model authorization**: the `AnthropicModel` enum knows which models each subscription plan may use, and services validate the requested model against the caller's plan before any LLM call.

Apply this when an LLM service grows beyond one capability: segregated interfaces keep each endpoint's dependency surface minimal, DI makes services mockable, and plan gating turns "who may use the expensive model" into typed, testable logic.

## Practice Rules

1. **One interface per capability, not one god-service.** `ITextGenerationService.generate_character()` and `ITextClassificationService.classify()` are separate ABCs; endpoints depend only on the interface they use.
2. **Wire implementations in a DI container** (`ServiceContainer`): services instantiated once at startup, the Anthropic client shared, endpoints pull via `get_*_service()` accessors.
3. **Put plan→model policy on the model enum** (`AnthropicModel.free_plan_models()` / `standard_plan_models()`), resolved through one helper (`get_available_models(user_plan)`) — policy lives in one place.
4. **Validate plan access before calling the LLM** and fail with an explanatory error listing the allowed models (HTTP 400).
5. **Use structured outputs at the service boundary** (`beta.messages.parse` + Pydantic `output_format`) so both services return typed results.
6. **Keep request/response contracts per endpoint** (`LLMRequest`/`LLMResponse`, `TextClassificationRequest`/`TextClassificationResponse`) — they carry `user_plan` explicitly.

## Architecture

```
FastAPI (src/api/llm_server.py)
  POST /generate ────────┐        POST /classify ────────┐       GET /health
        ▼                │              ▼                │
ServiceContainer (DI)    │      ServiceContainer (DI)    │
  get_text_generation_service()   get_text_classification_service()
        ▼                               ▼
ITextGenerationService          ITextClassificationService     ← interfaces (ISP)
        ▼                               ▼
TextGenerationService           TextClassificationService      ← implementations
        │   validate model ∈ get_available_models(user_plan)   ← plan gating
        └───────────────┬───────────────┘
                        ▼
              AsyncAnthropic (shared client)
              beta.messages.parse (structured outputs)
```

### Directory Structure

```
chapter_4/section_2/
├── src/
│   ├── api/llm_server.py                 # /generate, /classify, /health
│   ├── service/
│   │   ├── interfaces.py                 # ITextGenerationService / ITextClassificationService / get_available_models
│   │   ├── container.py                  # ServiceContainer (DI)
│   │   ├── text_generation_service.py    # generation implementation + plan validation
│   │   └── text_classification_service.py# classification implementation + plan validation
│   ├── client/llm_client.py              # AnthropicModel enum (+ plan model lists), client
│   ├── model/model.py                    # UserPlan + request/response models
│   ├── prompt/prompt.py
│   └── config.py / logger.py
├── docker-compose.yml / Dockerfile.web
├── Makefile / pyproject.toml / .env.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Segregated interfaces (`src/service/interfaces.py`)

```python
def get_available_models(user_plan: UserPlan) -> list[str]:
    if user_plan == UserPlan.FREE:
        return AnthropicModel.free_plan_models()
    return AnthropicModel.standard_plan_models()
```

Each ABC declares only its own operation; no service knows about the other's methods.

### 2. Plan policy on the enum (`src/client/llm_client.py`)

```python
class AnthropicModel(StrEnum):
    CLAUDE_SONNET_4_6 = "global.anthropic.claude-sonnet-4-6"
    CLAUDE_SONNET_4_6 = "global.anthropic.claude-sonnet-4-6"
    CLAUDE_SONNET_4_6 = "global.anthropic.claude-sonnet-4-6"
    CLAUDE_SONNET_4_6 = "global.anthropic.claude-sonnet-4-6"
    CLAUDE_HAIKU_4_5 = "global.anthropic.claude-haiku-4-5-20251001-v1:0"

    @classmethod
    def free_plan_models(cls) -> list[str]:
        return [cls.CLAUDE_SONNET_4_6]

    @classmethod
    def standard_plan_models(cls) -> list[str]:
        return cls.all_models()
```

FREE gets `global.anthropic.claude-sonnet-4-6`; STANDARD gets every model in the enum — new models automatically join the standard plan.

### 3. Validate before you spend (`src/service/text_generation_service.py`)

```python
available_models = get_available_models(user_plan)
if model not in available_models:
    raise ValueError(
        f"Model '{model}' is not available for {user_plan.value} plan. "
        f"Available models: {', '.join(available_models)}"
    )   # surfaced as HTTP 400 with the allowed list
```

### 4. Structured output at the boundary

```python
result = await self.client.beta.messages.parse(
    model=model,
    max_tokens=1024,
    betas=["structured-outputs-2025-11-13"],
    messages=prompt,
    output_format=CharacterResponse,     # or ClassificationResult
)
```

## Data Models

| Model | Purpose |
|-------|---------|
| `UserPlan` | `FREE` / `STANDARD` subscription plans |
| `LLMRequest` / `LLMResponse` | /generate contract (model, user_plan, character_request) |
| `TextClassificationRequest` / `TextClassificationResponse` / `ClassificationResult` | /classify contract (text, categories) |
| `CharacterRequest` / `CharacterResponse` | Generation task schemas |

## Setup & Run

```bash
cp .env.example .envrc       # set ANTHROPIC_API_KEY

# Canonical (docker)
make docker-build && make docker-up
curl -s http://localhost:8000/health
make docker-down

# Or local dev server
uv run uvicorn src.api.llm_server:app --host 0.0.0.0 --port 8000 --reload
```

### API Examples

```bash
# Generation (free plan → global.anthropic.claude-sonnet-4-6 only)
curl -X POST http://localhost:8000/generate -H "Content-Type: application/json" \
  -d '{"model": "global.anthropic.claude-sonnet-4-6", "user_plan": "free",
       "character_request": {"gender": "female", "age": 25}}'

# Classification
curl -X POST http://localhost:8000/classify -H "Content-Type: application/json" \
  -d '{"model": "global.anthropic.claude-sonnet-4-6", "user_plan": "free",
       "text": "This product is excellent!", "categories": ["Positive", "Negative", "Neutral"]}'

# Plan violation → HTTP 400 listing available models
```

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
make docker-build / make docker-up / make docker-down / make docker-logs
```

## Implementation Notes

- **Why ISP for LLM services**: capabilities accrete fast (generation, classification, summarization, embedding…). Segregated interfaces stop the "one service class with 12 methods" drift and let each capability version, test, and scale independently.
- **DI payoff is in tests**: endpoints depend on interfaces, so tests inject fakes via the container — no Anthropic client, no network.
- **Plan gating as domain logic, not middleware**: putting model policy on the enum + one resolver keeps authorization decisions typed and unit-testable, and error messages self-documenting.
- **Request flow**: FastAPI validation → container resolves interface → plan check → prompt build → structured-output call → typed response. Errors: plan violations → 400, LLM failures → 500.
- **Secrets** use `Secret` types so keys are masked in logs; age is constrained 0–100 at the Pydantic layer.

## How to Apply This Practice to Your Own Project

1. List your service's capabilities; define one ABC per capability with exactly one or two methods.
2. Implement each ABC in its own module sharing one provider client; construct everything in a container at startup.
3. Make endpoints depend on interfaces via the container accessor — never instantiate services in route handlers.
4. If you have tiers/plans, encode model allowances as classmethods on your model enum and resolve through one function; validate before calling the provider.
5. Return the allowed alternatives in authorization errors — it turns a 400 into self-service documentation.
6. Add new capabilities as new interfaces + implementations + endpoints; existing code should not change (open-closed).
