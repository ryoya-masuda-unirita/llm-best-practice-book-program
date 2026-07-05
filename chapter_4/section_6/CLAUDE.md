# Chapter 4 Section 6: Dependency Injection for LLM Pipelines

## What This Section Demonstrates

An LLM pipeline node has three separable responsibilities: **build the prompt → call the model → parse the response**. This section defines each as a `Protocol` interface (`IPromptBuilder`, `ILLMClient`, `IResponseParser`), provides interchangeable implementations (template/message-list builders; OpenAI/Gemini/Mock clients; text/JSON/structured parsers), and injects them into workflow nodes — either manually or via a lightweight **DI container** supporting Singleton / Transient / Scoped lifetimes.

Six runnable examples build up the practice: manual injection → container with singletons → provider swapping → multi-stage pipeline → structured output injection → the testing pattern with `MockLLMClient`. Apply DI when pipeline components need to vary independently (providers, prompt styles, output parsing) or when you want LLM workflows unit-testable without network calls — which is to say, almost always.

## Practice Rules

1. **Split every LLM step into builder / client / parser** and depend on `Protocol` interfaces, not classes. `@runtime_checkable` Protocols keep implementations duck-typed but verifiable.
2. **Inject dependencies into nodes from outside** (`add_prompt_node(..., injected_prompt_builder=..., injected_llm_client=..., injected_response_parser=...)`); nodes never construct their own.
3. **Use a DI container when wiring grows**: `register_singleton` for stateless shared services (LLM clients), `register_transient` for stateful per-use objects, `register_scoped` for per-workflow-run instances.
4. **Ship a `MockLLMClient` as a first-class implementation** — records `call_count` and `last_prompt`, returns canned responses; tests inject it through the same interface as real clients.
5. **Swap providers by swapping one registration** (`create_llm_client(provider)`), never by editing pipeline code.
6. **Keep interfaces minimal**: `build_prompt(context)`, `generate(prompt, context, **kwargs)`, `parse_response(raw_response, context)` — three methods total across the seam.
7. **Normalize the client boundary to `dict[str, Any]`** raw responses; parsing to domain types is the parser's job, keeping clients thin.

## Architecture

```
WorkflowBuilder / WorkflowEngine  (DAG engine from Chapter 4 Section 5,
                                   + mediator/memento/state modules)
        │  PromptNode executes:
        ▼
  IPromptBuilder.build_prompt(context)      ← TemplatePromptBuilder | MessageListPromptBuilder
        ▼
  ILLMClient.generate(prompt, context)      ← OpenAIClient | GeminiClient | MockLLMClient
        ▼
  IResponseParser.parse_response(raw, ctx)  ← TextResponseParser | JSON/Structured parsers
        │
        ▼ parsed output → ExecutionContext[node_id]

DIContainer
  register_singleton / register_transient / register_scoped / register_instance
  resolve(service_type, scope_id) → implementation per lifetime rules
```

### Directory Structure

```
chapter_4/section_6/
├── src/
│   ├── workflow/
│   │   ├── di.py           # Protocols + implementations + DIContainer (consolidated)
│   │   ├── engine.py       # WorkflowEngine
│   │   ├── builder.py      # WorkflowBuilder (accepts injected components)
│   │   ├── nodes.py        # PromptNode consuming the three interfaces
│   │   ├── base.py         # ExecutionContext etc.
│   │   ├── mediator.py / memento.py / state.py / workflow.py
│   ├── examples.py         # examples 1–6 (manual DI → testing pattern)
│   ├── client/llm_client.py
│   ├── main.py             # CLI: -w <example>
│   └── config.py / logger.py
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Protocol interfaces (`src/workflow/di.py`)

```python
@runtime_checkable
class IPromptBuilder(Protocol):
    def build_prompt(self, context: ExecutionContext) -> str | list[dict[str, Any]]: ...

@runtime_checkable
class ILLMClient(Protocol):
    async def generate(self, prompt, context: ExecutionContext, **kwargs) -> dict[str, Any]: ...

@runtime_checkable
class IResponseParser(Protocol):
    def parse_response(self, raw_response: dict[str, Any], context: ExecutionContext) -> Any: ...
```

### 2. Manual injection — the essence of DI (`src/examples.py`, example 1)

```python
prompt_builder = TemplatePromptBuilder(template="Translate '{text}' to {target_language}")
llm_client: ILLMClient = MockLLMClient(mock_response="Bonjour le monde")  # or create_llm_client(provider)
response_parser = TextResponseParser()

workflow = (
    WorkflowBuilder("translation-workflow", "Translation Example")
    .add_start_node(initial_data={"text": "Hello world", "target_language": "French"})
    .add_prompt_node("translate",
        injected_prompt_builder=prompt_builder,
        injected_llm_client=llm_client,
        injected_response_parser=response_parser)
    .add_end_node()
    .add_edge("start", "translate").add_edge("translate", "end")
    .build()
)
```

### 3. The lightweight container (`src/workflow/di.py`)

```python
class DIContainer:
    def register(self, service_type: type[T], impl=None,
                 lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT) -> DIContainer:
        self._services[service_type] = (impl or service_type, lifetime, None)
        return self                                        # chainable

    def register_singleton(self, service_type, impl=None) -> DIContainer: ...
    def register_transient(self, service_type, impl=None) -> DIContainer: ...
    def register_scoped(self, service_type, impl=None) -> DIContainer: ...   # per scope_id
    def register_instance(self, service_type, instance) -> DIContainer: ...

    def resolve(self, service_type: type[T], scope_id: str | None = None) -> T: ...
```

### 4. Mock client for tests (example 6)

```python
class MockLLMClient(BaseLLMClient):
    def __init__(self, mock_response: str = "Mock response"):
        super().__init__("mock-model")
        self.call_count = 0
        self.last_prompt = None

    async def generate(self, prompt, context, **kwargs) -> dict[str, Any]:
        self.call_count += 1
        self.last_prompt = prompt
        return {"content": self.mock_response, ...}
```

Tests assert on `call_count` / `last_prompt` — the prompt that would have been sent is fully inspectable, no network involved.

## Data Models

| Component | Purpose |
|-----------|---------|
| `IPromptBuilder` / `ILLMClient` / `IResponseParser` | The three seams (Protocols) |
| `TemplatePromptBuilder` / `MessageListPromptBuilder` | Prompt construction strategies |
| OpenAI/Gemini clients, `MockLLMClient` | `ILLMClient` implementations |
| `DIContainer` / `ServiceLifetime` | Registration + resolution (SINGLETON / TRANSIENT / SCOPED) |
| `ExecutionContext` | Workflow-run state shared by all components |

## Setup & Run

```bash
cp .envrc.example .envrc     # OPENAI_API_KEY / GEMINI_API_KEY (examples default to MockLLMClient without a provider)
uv sync

# Canonical example
uv run python -m src.main -w example_1_manual_di

# The progression
uv run python -m src.main -w example_2_di_container_singleton
uv run python -m src.main -w example_3_swapping_providers
uv run python -m src.main -w example_4_multi_stage_pipeline
uv run python -m src.main -w example_5_structured_output
uv run python -m src.main -w example_6_testing_pattern
```

### CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--workflow` | `-w` | Example name (1–6, see above) |
| `--llm-provider` | `-lp` | Optional real provider; omitted → MockLLMClient |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
```

## Implementation Notes

- **Why Protocols over ABCs at the seam**: implementations don't need to inherit anything (structural typing), which lets you wrap third-party objects as-is; `@runtime_checkable` still enables `isinstance` checks where wiring needs validation.
- **Lifetime guidance**: LLM SDK clients → singleton (connection reuse); prompt builders → transient if they accumulate state, singleton if pure; anything caching per-run data → scoped with the run ID as `scope_id`.
- **DI vs the Adapter pattern (Chapter 3 Section 1)**: adapters unify *provider APIs*; DI governs *how components find each other*. This section uses both — provider clients behind `ILLMClient`, delivered by injection.
- **The mock is the point**: example 6 is the practice's proof — a full workflow executes and is asserted on without any API key. If your pipeline can't do that, the coupling is still there.
- **Manual DI first, container second**: examples 1→2 show that the container is a convenience for wiring at scale, not the pattern itself. Don't introduce a container for two dependencies.

## How to Apply This Practice to Your Own Project

1. Cut every LLM call site into builder/client/parser and define the three Protocols (copy them verbatim — they're domain-free).
2. Make nodes/services accept the three interfaces as constructor/call parameters; delete internal construction.
3. Write `MockLLMClient` immediately and convert one test to use it — this validates the seam.
4. Add the `DIContainer` when wiring appears in more than two places; register clients as singletons.
5. Route provider selection through one factory (`create_llm_client(provider)`) registered in the container.
6. For per-request state (user context, run-scoped caches), use scoped lifetime keyed by request/run ID.
