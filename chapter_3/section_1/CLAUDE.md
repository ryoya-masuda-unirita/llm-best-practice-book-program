# Chapter 3 Section 1: LLM Adapter and Factory Patterns — A Unified Provider Interface

## What This Section Demonstrates

Every LLM provider has a different SDK surface (method names, message formats, structured-output bindings). This section applies two GoF patterns to contain that variance:

- **Adapter Pattern** — an abstract `LLMClient` interface (`chat`, `get_provider_name`, `get_model_name`, `aclose`) with one concrete adapter per provider that translates the unified call into SDK-specific code.
- **Factory Pattern** — `LLMClientFactory.create_client(provider, model)` centralizes construction, validates provider/model combinations, and returns the interface type.

The payoff: business logic (`request_llm`) is written once against `LLMClient`, provider swaps are a parameter change, tests mock a single interface, and vendor lock-in is confined to `src/client/adapters.py`. Apply this as soon as a codebase calls more than one provider — or might.

## Practice Rules

1. **Define the abstract interface around your app's needs, not any SDK's shape.** Here: `async chat(messages, response_format, **kwargs) -> BaseModel` — message list in, validated Pydantic instance out.
2. **One adapter class per provider**, owning its SDK client, model ID, and all provider-specific translation (e.g. Gemini needs system/user split and `response_schema`; OpenAI uses `responses.parse`; Anthropic uses `beta.messages.parse`).
3. **Adapters normalize the return type** — every `chat` returns the parsed Pydantic model, never a provider response object.
4. **Construct only through the factory.** The factory owns the provider→models table (`PROVIDER_MODELS`), rejects invalid combinations with actionable errors, and is the single place to register a new provider.
5. **Expose capability queries on the factory** (`get_supported_providers`, `get_supported_models`, `is_valid_combination`) so UIs/CLIs can enumerate options without touching adapters.
6. **Include lifecycle in the interface** (`aclose`) — some SDKs hold connections; callers clean up via the interface, not via provider-specific knowledge.
7. **Test adapters and factory separately**: factory tests cover validation/dispatch (no network); adapter tests mock the SDK boundary.

## Architecture

```
CLI (src/main.py)
  │  provider + model (enum-validated)
  ▼
LLMClientFactory.create_client(provider, model)      [Factory]
  │  validates combination → returns LLMClient
  ▼
request_llm(client: LLMClient)                        [Business logic — provider-agnostic]
  │  client.chat(messages, response_format=CharacterResponse)
  ▼
OpenAIAdapter | GeminiAdapter | AnthropicAdapter      [Adapters]
  │  SDK-specific translation
  ▼
Provider SDKs → CharacterResponse (validated)
```

### Directory Structure

```
chapter_3/section_1/
├── src/
│   ├── client/
│   │   ├── base.py       # LLMClient ABC (the unified interface)
│   │   ├── adapters.py   # OpenAIAdapter / GeminiAdapter / AnthropicAdapter
│   │   ├── factory.py    # LLMClientFactory (+ PROVIDER_MODELS table)
│   │   └── model.py      # LLMProvider / OpenAIModel / GeminiModel / AnthropicModel enums
│   ├── service/request_llm.py   # provider-agnostic business logic
│   ├── model/model.py           # CharacterResponse (structured output schema)
│   ├── prompt/prompt.py
│   ├── config.py / logger.py / main.py
├── tests/
│   ├── test_factory.py   # validation & dispatch tests (offline)
│   └── test_adapters.py  # adapter tests (SDK mocked)
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. The unified interface (`src/client/base.py`)

```python
class LLMClient(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict[str, str]], response_format: type, **kwargs: Any) -> BaseModel: ...

    @abstractmethod
    def get_provider_name(self) -> str: ...

    @abstractmethod
    def get_model_name(self) -> str: ...

    async def aclose(self) -> None:     # default no-op; adapters override when needed
        pass
```

### 2. An adapter contains ALL provider specifics (`src/client/adapters.py`)

```python
class OpenAIAdapter(LLMClient):
    def __init__(self, model: str):
        self._client = AsyncOpenAI(api_key=config.openai_api_key)
        self._model = model

    async def chat(self, messages, response_format, **kwargs) -> BaseModel:
        result = await self._client.responses.parse(
            model=self._model, input=messages, text_format=response_format, **kwargs,
        )
        return result.output_parsed        # normalized return type

    async def aclose(self) -> None:
        await self._client.close()
```

`GeminiAdapter.chat` reshapes messages into `system_instruction` + contents and binds `response_schema`; `AnthropicAdapter.chat` calls `beta.messages.parse(..., output_format=response_format)`. Call sites can't tell the difference.

### 3. Factory with combination validation (`src/client/factory.py`)

```python
class LLMClientFactory:
    PROVIDER_MODELS = {
        LLMProvider.OPENAI: OpenAIModel.list_str(),
        LLMProvider.GEMINI: GeminiModel.list_str(),
        LLMProvider.ANTHROPIC: AnthropicModel.list_str(),
    }

    @staticmethod
    def create_client(provider, model) -> LLMClient:
        if provider.lower() not in LLMClientFactory.PROVIDER_MODELS:
            raise ValueError(f"Unknown provider: {provider}. Supported: ...")
        if model not in LLMClientFactory.PROVIDER_MODELS[provider.lower()]:
            raise ValueError(f"Invalid model '{model}' for '{provider}'. Supported: ...")
        if provider_lower == LLMProvider.OPENAI:
            return OpenAIAdapter(model=model)
        ...
```

### 4. Business logic sees only the interface (`src/service/request_llm.py`)

```python
async def request_llm(client: LLMClient, model) -> CharacterResponse:
    prompt = make_prompt(client.get_provider_name())
    return await client.chat(messages=prompt, response_format=CharacterResponse)
```

No `if provider == ...` branches anywhere above the adapter layer.

## Data Models

| Model | Purpose |
|-------|---------|
| `LLMClient` | Abstract adapter interface |
| `LLMProvider` | `openai` / `gemini` / `anthropic` |
| `OpenAIModel` / `GeminiModel` / `AnthropicModel` | Valid model IDs per provider (Anthropic includes global.anthropic.claude-sonnet-4-6, global.anthropic.claude-haiku-4-5-20251001-v1:0, global.anthropic.claude-sonnet-4-6) |
| `CharacterResponse` | Demo task structured-output schema |

## Setup & Run

```bash
cp .envrc.example .envrc     # OPENAI_API_KEY / GEMINI_API_KEY / ANTHROPIC_API_KEY
uv sync

# Canonical example
uv run python -m src.main -lp ANTHROPIC -m CLAUDE_HAIKU_4_5

# Same code path, different providers
uv run python -m src.main -lp OPENAI -m GPT_5_4
uv run python -m src.main -lp ANTHROPIC -m CLAUDE_SONNET_4_6
```

### CLI Options

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--llm-provider` | `-lp` | Yes | `OPENAI` / `GEMINI` / `ANTHROPIC` |
| `--model` | `-m` | Yes | Model enum name (validated against the provider by the factory) |
| `--output-directory` | `-od` | No | Output directory (default `outputs`) |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
uv run pytest tests/ -v      # factory + adapter tests, no API keys needed
```

## Implementation Notes

- **Where prompt differences live**: minor provider-specific prompt formatting is handled by `make_prompt(provider)` in the prompt layer — an acceptable seam because prompt content is data, not control flow. If prompt logic grows provider branches, push it down into the adapters.
- **The factory's `PROVIDER_MODELS` table is the registration point**: adding a provider = new adapter class + one enum + one table entry + one dispatch branch. Nothing else changes.
- **`aclose` matters in async apps** — the Gemini SDK in particular needs explicit closing; putting lifecycle in the interface avoids leaking that detail to callers.
- **Testing benefit is the quiet headline**: `request_llm` is tested with a stub `LLMClient` in-memory; adapter tests mock one SDK each. Compare with testing code that talks to three SDKs inline.
- **Trade-off**: the unified interface is a lowest-common-denominator. Provider-exclusive features (e.g. provider-specific tool types) either surface through `**kwargs` or force an interface extension — decide deliberately per feature.

## How to Apply This Practice to Your Own Project

1. Write the `LLMClient` ABC with exactly the operations your app performs today (usually `chat`; add `stream` or `embed` only when used).
2. Implement one adapter per provider you use; normalize inputs (message list) and outputs (parsed Pydantic model) at the adapter boundary.
3. Add the factory with a provider→models table and combination validation; make it the only construction path.
4. Refactor business logic to accept `LLMClient` via parameter (dependency injection) — delete inline SDK imports outside `client/`.
5. Port the two-file test layout (`test_factory.py` offline, `test_adapters.py` SDK-mocked).
6. When adding provider-specific capabilities, extend consciously: `**kwargs` passthrough for options, interface methods for genuinely shared concepts.
