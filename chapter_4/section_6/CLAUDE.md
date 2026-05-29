# Chapter 3, Section 13: Dependency Injection for LLM Pipelines

## Project Overview

This project demonstrates the implementation of **Dependency Injection (DI)** pattern for building flexible, testable, and maintainable LLM-based workflows. In real-world LLM applications, the processing pipeline typically consists of three distinct responsibilities: prompt construction, model invocation, and response parsing. Without proper separation of concerns, these components become tightly coupled, making the system difficult to test, extend, and maintain.

The DI pattern addresses these challenges by inverting the dependency relationships - instead of components creating their own dependencies, they receive them from external sources. This project showcases a complete DI implementation including interfaces (Protocols), concrete implementations for multiple LLM providers (OpenAI, Gemini), and a lightweight DI container supporting three service lifetimes (Singleton, Transient, Scoped).

Built on top of a workflow orchestration engine, this implementation demonstrates how DI enhances the architecture of complex LLM systems, enabling seamless provider switching, isolated unit testing, and parallel team development.

## Core Architecture

### The Problem: Tight Coupling

Consider a typical LLM pipeline without DI:

```python
class AssessmentPipeline:
    def __init__(self):
        # Direct dependencies - tightly coupled
        self.client = openai.Client()
        self.model = "gpt-4o-mini"

    async def process(self, document: str):
        # Prompt construction embedded
        prompt = f"Assess this document: {document}"

        # Direct API call - cannot be mocked
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )

        # Response parsing embedded
        return response.choices[0].message.content
```

**Problems:**
- **Cannot test without API calls**: Every test hits the OpenAI API, making tests slow and expensive
- **Cannot switch providers**: Changing from OpenAI to Gemini requires rewriting the entire class
- **Cannot reuse components**: Prompt construction and response parsing are embedded and cannot be shared
- **Cannot develop in parallel**: Teams must wait for the entire implementation to be completed

### The Solution: Dependency Injection

With DI, we separate concerns and inject dependencies:

```python
class AssessmentPipeline:
    def __init__(
        self,
        prompt_builder: IPromptBuilder,
        llm_client: ILLMClient,
        response_parser: IResponseParser
    ):
        # Dependencies injected from outside
        self.prompt_builder = prompt_builder
        self.llm_client = llm_client
        self.response_parser = response_parser

    async def process(self, context: ExecutionContext):
        # Each component has a single responsibility
        prompt = self.prompt_builder.build_prompt(context)
        raw_response = await self.llm_client.generate(prompt, context)
        result = self.response_parser.parse_response(raw_response, context)
        return result
```

**Benefits:**
- **Testable**: Inject `MockLLMClient` for fast unit tests without API costs
- **Flexible**: Swap `OpenAILLMClient` with `GeminiLLMClient` without changing pipeline code
- **Reusable**: Share `TemplatePromptBuilder` across multiple workflows
- **Parallel development**: Teams can work on different components independently

## Design Pattern Implementation

### 1. Protocol-Based Interfaces

We use Python's `Protocol` for structural subtyping (duck typing with type checking):

```python
@runtime_checkable
class IPromptBuilder(Protocol):
    """Interface for prompt building components."""
    def build_prompt(self, context: ExecutionContext) -> str | list[dict[str, Any]]:
        ...

@runtime_checkable
class ILLMClient(Protocol):
    """Interface for LLM client components."""
    async def generate(
        self, prompt: str | list[dict[str, Any]],
        context: ExecutionContext,
        **kwargs: Any
    ) -> dict[str, Any]:
        ...

@runtime_checkable
class IResponseParser(Protocol):
    """Interface for response parsing components."""
    def parse_response(
        self, raw_response: dict[str, Any],
        context: ExecutionContext
    ) -> Any:
        ...
```

**Key Points:**
- `Protocol` enables structural subtyping - no inheritance required
- `@runtime_checkable` allows `isinstance()` checks at runtime
- Return types clearly defined for type safety
- Each interface has a single, well-defined responsibility (SOLID principles)

### 2. Concrete Implementations

#### Prompt Builders

```python
class TemplatePromptBuilder(BasePromptBuilder):
    """Simple template-based prompt builder."""
    def build_prompt(self, context: ExecutionContext) -> str:
        return self.template.format(**context.variables)

class MessageListPromptBuilder(BasePromptBuilder):
    """Builds chat message lists."""
    def build_prompt(self, context: ExecutionContext) -> list[dict[str, Any]]:
        messages = []
        if self.system_message:
            messages.append({"role": "system", "content": self.system_message})
        messages.append({"role": "user", "content": context.get_variable("prompt")})
        return messages

class DynamicPromptBuilder(BasePromptBuilder):
    """Advanced prompt builder with conversation history support."""
    def build_prompt(self, context: ExecutionContext) -> str | list[dict[str, Any]]:
        if self.include_history:
            history = context.get_variable("conversation_history", [])
            return history[-self.max_history:] + [current_message]
        return self._format(context)
```

#### LLM Clients

```python
class OpenAILLMClient(BaseLLMClient):
    """OpenAI LLM client with structured output support."""

    async def generate(
        self, prompt: str | list[dict[str, Any]],
        context: ExecutionContext,
        **kwargs
    ) -> dict[str, Any]:
        messages = self._to_messages(prompt)

        if self.response_format:
            # Structured output using Pydantic models
            result = await openai_client.responses.parse(
                model=self.model,
                input=messages,
                text_format=self.response_format,
                **{**self.params, **kwargs}
            )
            return {
                "content": result.output_text,
                "parsed": result.output_parsed,
                "model": self.model,
                "usage": result.usage
            }
        else:
            # Standard text output
            result = await openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                **{**self.params, **kwargs}
            )
            return {
                "content": result.choices[0].message.content,
                "model": result.model,
                "usage": result.usage.model_dump()
            }

class GeminiLLMClient(BaseLLMClient):
    """Gemini LLM client with JSON schema support."""

    async def generate(
        self, prompt: str | list[dict[str, Any]],
        context: ExecutionContext,
        **kwargs
    ) -> dict[str, Any]:
        content = self._extract_content(prompt)
        config_params = {**self.params, **kwargs}

        if self.response_schema:
            # Structured output using Pydantic schema
            config_params["response_mime_type"] = "application/json"
            config_params["response_schema"] = self.response_schema

        result = await google_genai_client.aio.models.generate_content(
            model=self.model,
            contents=content,
            config=GenerateContentConfig(**config_params)
        )

        return {
            "content": result.text,
            "parsed": result.parsed if self.response_schema else None,
            "model": self.model,
            "usage": self._extract_usage(result)
        }

class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing without API costs."""

    def __init__(self, mock_response: str = "Mock response"):
        super().__init__("mock-model")
        self.mock_response = mock_response
        self.call_count = 0
        self.last_prompt = None

    async def generate(
        self, prompt: str | list[dict[str, Any]],
        context: ExecutionContext,
        **kwargs
    ) -> dict[str, Any]:
        self.call_count += 1
        self.last_prompt = prompt
        return {
            "content": self.mock_response,
            "model": "mock-model",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        }
```

#### Response Parsers

```python
class TextResponseParser:
    """Extracts plain text content from responses."""
    def parse_response(self, raw_response: dict[str, Any], context: ExecutionContext) -> str:
        return raw_response.get("content", "")

class StructuredResponseParser:
    """Extracts parsed Pydantic models from responses."""
    def parse_response(self, raw_response: dict[str, Any], context: ExecutionContext) -> Any:
        return raw_response.get("parsed", raw_response.get("content", ""))

class JSONResponseParser:
    """Parses JSON from text responses."""
    def parse_response(self, raw_response: dict[str, Any], context: ExecutionContext) -> dict:
        import json
        content = raw_response.get("content", "")
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return content if not self.strict else raise

class EnhancedResponseParser:
    """Parser with metadata and usage tracking."""
    def parse_response(self, raw_response: dict[str, Any], context: ExecutionContext) -> dict:
        # Track token usage
        if usage := raw_response.get("usage"):
            total = context.get_variable("total_tokens_used", 0)
            context.set_variable("total_tokens_used", total + usage.get("total_tokens", 0))

        return {
            "content": raw_response.get("content", ""),
            "model": raw_response.get("model", "unknown"),
            "usage": raw_response.get("usage", {}),
            "parsed_data": raw_response.get("parsed")
        }
```

### 3. DI Container

The DI container manages service registration and resolution with support for three service lifetimes:

```python
class ServiceLifetime(str, Enum):
    SINGLETON = "singleton"   # Single instance per application
    TRANSIENT = "transient"   # New instance per resolution
    SCOPED = "scoped"         # Single instance per scope (e.g., per request)

class DIContainer:
    """Lightweight dependency injection container."""

    def register_singleton(
        self, service_type: type[T],
        impl: Callable[..., T] | type[T]
    ) -> DIContainer:
        """Register a service as singleton."""
        self._services[service_type] = (impl, ServiceLifetime.SINGLETON, None)
        return self

    def register_transient(
        self, service_type: type[T],
        impl: Callable[..., T] | type[T]
    ) -> DIContainer:
        """Register a service as transient."""
        self._services[service_type] = (impl, ServiceLifetime.TRANSIENT, None)
        return self

    def register_scoped(
        self, service_type: type[T],
        impl: Callable[..., T] | type[T]
    ) -> DIContainer:
        """Register a service as scoped."""
        self._services[service_type] = (impl, ServiceLifetime.SCOPED, None)
        return self

    def register_instance(self, service_type: type[T], instance: T) -> DIContainer:
        """Register an existing instance as singleton."""
        self._services[service_type] = (lambda: instance, ServiceLifetime.SINGLETON, instance)
        return self

    def resolve(self, service_type: type[T], scope_id: str | None = None) -> T:
        """Resolve a service from the container."""
        impl, lifetime, instance = self._services[service_type]

        if lifetime == ServiceLifetime.SINGLETON:
            if instance is None:
                instance = impl() if callable(impl) else impl
                self._services[service_type] = (impl, lifetime, instance)
            return instance

        elif lifetime == ServiceLifetime.SCOPED:
            if scope_id not in self._scoped:
                self._scoped[scope_id] = {}
            if service_type not in self._scoped[scope_id]:
                self._scoped[scope_id][service_type] = impl()
            return self._scoped[scope_id][service_type]

        else:  # TRANSIENT
            return impl() if callable(impl) else impl
```

**Key Features:**
- **Fluent API**: Method chaining for readable registration
- **Service lifetimes**: Singleton for shared state, Transient for stateless, Scoped for request-level
- **Scope management**: `DIScope` context manager for automatic cleanup
- **Type safety**: Generic type parameters ensure type correctness

## Key Features

### 1. Seamless Provider Switching (A/B Testing)

Test multiple LLM providers with the same workflow definition:

```python
# Define workflow once
def build_workflow(llm_client: ILLMClient):
    return (
        WorkflowBuilder("analysis")
        .add_start_node(initial_data={"document": "..."})
        .add_prompt_node(
            "analyze",
            prompt_template="Analyze: {document}",
            injected_llm_client=llm_client,
            injected_response_parser=TextResponseParser()
        )
        .add_end_node()
        .add_edge("start", "analyze")
        .add_edge("analyze", "end")
        .build()
    )

# Test with different providers
providers = [
    ("OpenAI GPT-4o-mini", OpenAILLMClient(model="gpt-4o-mini")),
    ("Gemini 2.5 Flash", GeminiLLMClient(model="gemini-2.0-flash-exp")),
]

for name, client in providers:
    workflow = build_workflow(client)
    result = await engine.execute(workflow)
    print(f"{name}: {result['outputs']['analyze']}")
```

### 2. Isolated Unit Testing

Test workflows without API calls using `MockLLMClient`:

```python
async def test_workflow():
    # Create mock client with predictable response
    mock_client = MockLLMClient(mock_response="Analyzed: positive sentiment")

    workflow = build_workflow(mock_client)
    result = await WorkflowEngine(enable_checkpointing=False).execute(workflow)

    # Assertions
    assert result["status"] == "completed"
    assert mock_client.call_count == 1
    assert "positive sentiment" in result["outputs"]["analyze"]

    # Verify prompt was built correctly
    assert "Analyze:" in mock_client.last_prompt
```

**Benefits:**
- **No API costs**: Tests run instantly without network calls
- **Deterministic results**: Predictable outputs for reliable assertions
- **Fast CI/CD**: Test suites complete in seconds, not minutes
- **Offline development**: Work without internet connection

### 3. Multi-Stage Pipelines

Compose complex workflows with different components at each stage:

```python
async def example_multi_stage_pipeline():
    # Stage 1: Extract key points using Gemini
    extract_builder = TemplatePromptBuilder(template="Extract key points from: {document}")
    extract_client = GeminiLLMClient(model="gemini-2.0-flash-exp", temperature=0.3)
    extract_parser = TextResponseParser()

    # Stage 2: Summarize using OpenAI
    summarize_builder = TemplatePromptBuilder(template="Summarize professionally: {key_points}")
    summarize_client = OpenAILLMClient(model="gpt-4o-mini", temperature=0.5)
    summarize_parser = TextResponseParser()

    # Stage 3: Format output (custom Python logic)
    def format_output(context: ExecutionContext) -> dict:
        key_points = context.get_node_output("extract")
        summary = context.get_node_output("summarize")
        return {
            "key_points": key_points,
            "summary": summary,
            "formatted": f"## Key Points\n{key_points}\n\n## Summary\n{summary}"
        }

    workflow = (
        WorkflowBuilder("multi-stage", "Multi-Stage Pipeline")
        .add_start_node(initial_data={"document": "Long document text..."})
        .add_prompt_node(
            "extract",
            injected_prompt_builder=extract_builder,
            injected_llm_client=extract_client,
            injected_response_parser=extract_parser
        )
        .add_prompt_node(
            "summarize",
            injected_prompt_builder=summarize_builder,
            injected_llm_client=summarize_client,
            injected_response_parser=summarize_parser
        )
        .add_python_script_node("format", script_function=format_output)
        .add_end_node()
        .add_edge("start", "extract")
        .add_edge("extract", "summarize")
        .add_edge("summarize", "format")
        .add_edge("format", "end")
        .build()
    )

    return await WorkflowEngine().execute(workflow)
```

### 4. Structured Output with Pydantic

Use Pydantic models for type-safe LLM responses:

```python
from pydantic import BaseModel, Field

class SentimentAnalysis(BaseModel):
    """Structured sentiment analysis result."""
    sentiment: str = Field(description="positive, negative, or neutral")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    key_phrases: list[str] = Field(description="Key phrases that influenced sentiment")

async def example_structured_output():
    # Configure client for structured output
    llm_client = OpenAILLMClient(
        model="gpt-4o-mini",
        response_format=SentimentAnalysis  # Pydantic model
    )

    prompt_builder = TemplatePromptBuilder(
        template="Analyze sentiment: {text}"
    )

    # Use StructuredResponseParser to extract parsed model
    parser = StructuredResponseParser()

    workflow = (
        WorkflowBuilder("sentiment-analysis")
        .add_start_node(initial_data={"text": "I love this product!"})
        .add_prompt_node(
            "analyze",
            injected_prompt_builder=prompt_builder,
            injected_llm_client=llm_client,
            injected_response_parser=parser
        )
        .add_end_node()
        .add_edge("start", "analyze")
        .add_edge("analyze", "end")
        .build()
    )

    result = await WorkflowEngine().execute(workflow)

    # Type-safe access to structured data
    analysis: SentimentAnalysis = result["outputs"]["analyze"]
    print(f"Sentiment: {analysis.sentiment}")
    print(f"Confidence: {analysis.confidence}")
    print(f"Key phrases: {', '.join(analysis.key_phrases)}")
```

### 5. DI Container for Complex Applications

Use the DI container to manage dependencies across large applications:

```python
# Configure container
container = DIContainer()

# Register services
container.register_singleton(
    ILLMClient,
    lambda: OpenAILLMClient(model="gpt-4o-mini")
)
container.register_singleton(
    IResponseParser,
    TextResponseParser
)
container.register_transient(
    IPromptBuilder,
    lambda: TemplatePromptBuilder(template="Process: {input}")
)

# Resolve services anywhere in the application
llm_client = container.resolve(ILLMClient)
parser = container.resolve(IResponseParser)
prompt_builder = container.resolve(IPromptBuilder)

# Services are automatically reused (singleton) or recreated (transient)
assert container.resolve(ILLMClient) is llm_client  # Same instance
assert container.resolve(IPromptBuilder) is not prompt_builder  # New instance
```

### 6. Scoped Services for Request-Level State

Use scoped services for managing request-specific state:

```python
container = DIContainer()

# Register scoped service (one instance per workflow execution)
container.register_scoped(
    ILLMClient,
    lambda: OpenAILLMClient(model="gpt-4o-mini")
)

# Create scope for workflow execution
with container.create_scope("workflow-123") as scope:
    client1 = scope.resolve(ILLMClient)
    client2 = scope.resolve(ILLMClient)
    assert client1 is client2  # Same instance within scope

# Scope automatically cleaned up after workflow completes
```

## Refactoring Summary

This project underwent significant refactoring to reduce code complexity while maintaining all functionality:

### Before Refactoring
- **Total lines**: 2,962 lines across 15 files
- **DI components**: Split across 3 files (di_interfaces.py, di_implementations.py, di_container.py)
- **Node implementations**: 434 lines with duplicated logic
- **Engine implementation**: 345 lines with verbose methods

### After Refactoring
- **Total lines**: 1,994 lines (33% reduction)
- **DI components**: Consolidated into single `di.py` module (391 lines)
- **Node implementations**: 239 lines (45% reduction)
- **Engine implementation**: 185 lines (46% reduction)

### Key Improvements
- **Consolidated modules**: Merged 3 DI files into 1 without breaking changes
- **Removed duplication**: Unified execute logic in PromptNode for DI and legacy approaches
- **Simplified engine**: Streamlined workflow execution loop
- **Preserved interfaces**: All public APIs remain unchanged - zero breaking changes
- **Maintained tests**: All 6 example workflows pass without modification

See `REFACTORING_SUMMARY.md` for detailed line-by-line comparison.

## Example Workflows

### Example 1: Manual Dependency Injection

**Use case**: Simple workflow without container overhead

```bash
python -m src.main --workflow example_1_manual_di
```

**Code**:
```python
# Create dependencies manually
prompt_builder = TemplatePromptBuilder(
    template="Translate '{text}' to {target_language}"
)
llm_client = MockLLMClient(mock_response="Bonjour le monde")
response_parser = TextResponseParser()

# Inject into workflow
workflow = (
    WorkflowBuilder("translation-workflow", "Translation Example")
    .add_start_node(initial_data={"text": "Hello world", "target_language": "French"})
    .add_prompt_node(
        "translate",
        name="Translate Text",
        injected_prompt_builder=prompt_builder,
        injected_llm_client=llm_client,
        injected_response_parser=response_parser
    )
    .add_end_node()
    .add_edge("start", "translate")
    .add_edge("translate", "end")
    .build()
)

engine = WorkflowEngine(enable_checkpointing=False)
result = await engine.execute(workflow)
```

**Output**:
```
============================================================
Example 1: Manual Dependency Injection
============================================================
Translation result: Bonjour le monde
Mock client was called 1 time(s)
 Workflow completed successfully
  Status: completed
  Nodes executed: 3
```

### Example 2: DI Container with Singletons

**Use case**: Centralized dependency management for large applications

```bash
python -m src.main --workflow example_2_di_container_singleton
```

**Code**:
```python
# Create and configure container
container = DIContainer()

# Register services with appropriate lifetimes
container.register_singleton(
    ILLMClient,
    lambda: MockLLMClient(mock_response="Analyzed content here...")
)
container.register_singleton(IResponseParser, TextResponseParser)
container.register_transient(
    IPromptBuilder,
    lambda: TemplatePromptBuilder(template="Analyze the following content: {content}")
)

# Resolve services from container
llm_client = container.resolve(ILLMClient)
response_parser = container.resolve(IResponseParser)
prompt_builder = container.resolve(IPromptBuilder)

# Build workflow with resolved dependencies
workflow = build_analysis_workflow(llm_client, response_parser, prompt_builder)
result = await engine.execute(workflow)
```

**Benefits**:
- Centralized configuration
- Automatic instance reuse (singleton)
- Easy to swap implementations by changing registration

### Example 3: Swapping Providers (A/B Testing)

**Use case**: Compare performance/quality across different LLM providers

```bash
python -m src.main --workflow example_3_swapping_providers
```

**Code**:
```python
# Define workflow factory
def build_workflow(llm_client: ILLMClient):
    return (
        WorkflowBuilder("summary")
        .add_start_node(initial_data={"article": "Long article text..."})
        .add_prompt_node(
            "summarize",
            prompt_template="Summarize this article: {article}",
            injected_llm_client=llm_client,
            injected_response_parser=TextResponseParser()
        )
        .add_end_node()
        .add_edge("start", "summarize")
        .add_edge("summarize", "end")
        .build()
    )

# Test with multiple providers
providers = [
    ("Provider A (Mock 1)", MockLLMClient("Summary from provider A")),
    ("Provider B (Mock 2)", MockLLMClient("Summary from provider B")),
]

for name, client in providers:
    print(f"\n{'='*60}\nTesting with {name}\n{'='*60}")
    workflow = build_workflow(client)
    result = await engine.execute(workflow)
    print(f"Result: {result['outputs']['summarize']}")
```

**Output**:
```
============================================================
Testing with Provider A (Mock 1)
============================================================
Result: Summary from provider A

============================================================
Testing with Provider B (Mock 2)
============================================================
Result: Summary from provider B
```

### Example 4: Multi-Stage Pipeline

**Use case**: Complex workflows with different components per stage

```bash
python -m src.main --workflow example_4_multi_stage_pipeline
```

**Code**: See "Multi-Stage Pipelines" section above

**Output**:
```
============================================================
Example 4: Multi-Stage Pipeline with DI
============================================================

Final formatted output:
## Key Points
Key points: A, B, C

## Summary
Professional summary of key points

 Workflow completed successfully
  Status: completed
  Nodes executed: 5
```

### Example 5: Structured Output

**Use case**: Type-safe LLM responses using Pydantic models

```bash
python -m src.main --workflow example_5_structured_output
```

**Code**: See "Structured Output with Pydantic" section above

**Output**:
```
============================================================
Example 5: Structured Output with Pydantic
============================================================
Parsed sentiment analysis:
  Sentiment: positive
  Confidence: 0.95
  Key phrases: ['love', 'amazing', 'highly recommend']

 Workflow completed successfully
```

### Example 6: Testing Pattern

**Use case**: Fast, deterministic unit tests without API costs

```bash
python -m src.main --workflow example_6_testing_pattern
```

**Code**:
```python
# Create mock client with known response
mock_client = MockLLMClient(mock_response="Test response content")

# Build workflow with mock
workflow = (
    WorkflowBuilder("test-workflow")
    .add_start_node(initial_data={"input": "test input"})
    .add_prompt_node(
        "process",
        prompt_template="Process: {input}",
        injected_llm_client=mock_client,
        injected_response_parser=TextResponseParser()
    )
    .add_end_node()
    .add_edge("start", "process")
    .add_edge("process", "end")
    .build()
)

# Execute and verify
result = await engine.execute(workflow)

# Assertions
assert result["status"] == "completed"
assert mock_client.call_count == 1
assert result["outputs"]["process"] == "Test response content"
print(f" All assertions passed")
print(f"  Mock client called: {mock_client.call_count} time(s)")
print(f"  Last prompt: {mock_client.last_prompt}")
```

**Output**:
```
============================================================
Example 6: Testing Pattern with Mock Client
============================================================
 All assertions passed
  Mock client called: 1 time(s)
  Last prompt: Process: test input

 Workflow completed successfully
```

## Project Structure

```
chapter_3/section_13/
   src/
      __init__.py
      config.py                    # Configuration management
      logger.py                    # Logging setup
      main.py                      # CLI entry point
      examples.py                  # 6 DI example workflows
      client/
         __init__.py
         llm_client.py            # LLM client initialization
      workflow/
          __init__.py              # Export all workflow components
          base.py                  # Base classes (Node, ExecutionContext)
          workflow.py              # Workflow class (DAG management)
          builder.py               # WorkflowBuilder pattern
          engine.py                # WorkflowEngine (execution engine)
          nodes.py                 # Node implementations (Start, End, Prompt, etc.)
          di.py                    # DI components (consolidated)
                                   #   - Interfaces: IPromptBuilder, ILLMClient, IResponseParser
                                   #   - Base classes: BasePromptBuilder, BaseLLMClient
                                   #   - Implementations: OpenAI, Gemini, Mock clients
                                   #   - Prompt builders: Template, MessageList, Dynamic
                                   #   - Response parsers: Text, Structured, JSON, Enhanced
                                   #   - DIContainer: Service registration & resolution
          state.py                 # Workflow state management
          mediator.py              # Mediator pattern (node communication)
          memento.py               # Memento pattern (checkpointing)
          llm_executors.py         # Legacy LLM executor functions
   checkpoints/                     # Checkpoint storage (auto-created)
   .envrc.example                   # Environment variable template
   pyproject.toml                   # Project dependencies
   README.md                        # Japanese documentation
   CLAUDE.md                        # This file (English documentation)
   REFACTORING_SUMMARY.md           # Detailed refactoring report
   MIGRATION_SUMMARY.md             # Migration guide from legacy to DI
```

## Dependencies

```toml
[project]
dependencies = [
    "google-genai>=1.45.0",      # Gemini API client
    "openai>=2.4.0",             # OpenAI API client
    "pydantic>=2.12.2",          # Data validation and structured outputs
    "click>=8.3.0",              # CLI framework
    "python-dotenv>=1.1.1",      # Environment variable loading
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",             # Testing framework
    "pytest-asyncio>=0.21.0",    # Async test support
    "black>=24.0.0",             # Code formatting
    "ruff>=0.1.0",               # Linting
]
```

## Setup and Usage

### Prerequisites

- **Python**: 3.10 or higher
- **API Keys**: OpenAI and/or Gemini API keys (optional for mock examples)

### Installation

```bash
# Clone repository
cd chapter_3/section_13

# Create environment file
cp .envrc.example .envrc

# Edit .envrc and add your API keys
# export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
# export GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX

# Install dependencies using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### Running Examples

```bash
# Run all examples
python -m src.main --workflow all

# Run specific example
python -m src.main --workflow example_1_manual_di
python -m src.main --workflow example_2_di_container_singleton
python -m src.main --workflow example_3_swapping_providers
python -m src.main --workflow example_4_multi_stage_pipeline
python -m src.main --workflow example_5_structured_output
python -m src.main --workflow example_6_testing_pattern

# Show help
python -m src.main --help
```

## Testing

### Unit Testing with Mock Client

```python
import asyncio
from src.workflow import (
    WorkflowBuilder, WorkflowEngine,
    MockLLMClient, TemplatePromptBuilder, TextResponseParser
)

async def test_translation_workflow():
    """Test workflow with mock client - no API calls."""

    # Arrange
    mock_client = MockLLMClient(mock_response="Bonjour")
    prompt_builder = TemplatePromptBuilder(template="Translate: {text}")
    parser = TextResponseParser()

    workflow = (
        WorkflowBuilder("test")
        .add_start_node(initial_data={"text": "Hello"})
        .add_prompt_node(
            "translate",
            injected_prompt_builder=prompt_builder,
            injected_llm_client=mock_client,
            injected_response_parser=parser
        )
        .add_end_node()
        .add_edge("start", "translate")
        .add_edge("translate", "end")
        .build()
    )

    # Act
    engine = WorkflowEngine(enable_checkpointing=False)
    result = await engine.execute(workflow)

    # Assert
    assert result["status"] == "completed"
    assert result["nodes_executed"] == 3
    assert mock_client.call_count == 1
    assert result["outputs"]["translate"] == "Bonjour"
    assert "Translate: Hello" in str(mock_client.last_prompt)

    print(" All tests passed")

# Run test
asyncio.run(test_translation_workflow())
```

### Integration Testing with Real APIs

```python
async def test_openai_integration():
    """Integration test with real OpenAI API."""

    # Requires OPENAI_API_KEY in environment
    client = OpenAILLMClient(model="gpt-4o-mini", temperature=0.0)
    prompt_builder = TemplatePromptBuilder(template="Say 'test passed' in 2 words")
    parser = TextResponseParser()

    workflow = build_simple_workflow(client, prompt_builder, parser)
    result = await WorkflowEngine().execute(workflow)

    assert result["status"] == "completed"
    assert "test" in result["outputs"]["generate"].lower()

    print(" OpenAI integration test passed")

# Run with: python -m pytest tests/test_integration.py
```

### DI Container Testing

```python
def test_singleton_lifetime():
    """Test that singleton services return same instance."""
    container = DIContainer()
    container.register_singleton(ILLMClient, lambda: MockLLMClient("test"))

    instance1 = container.resolve(ILLMClient)
    instance2 = container.resolve(ILLMClient)

    assert instance1 is instance2
    print(" Singleton test passed")

def test_transient_lifetime():
    """Test that transient services return new instances."""
    container = DIContainer()
    container.register_transient(IPromptBuilder, TemplatePromptBuilder)

    instance1 = container.resolve(IPromptBuilder)
    instance2 = container.resolve(IPromptBuilder)

    assert instance1 is not instance2
    print(" Transient test passed")

def test_scoped_lifetime():
    """Test that scoped services are shared within scope."""
    container = DIContainer()
    container.register_scoped(ILLMClient, lambda: MockLLMClient("test"))

    with container.create_scope("scope1") as scope:
        instance1 = scope.resolve(ILLMClient)
        instance2 = scope.resolve(ILLMClient)
        assert instance1 is instance2

    with container.create_scope("scope2") as scope:
        instance3 = scope.resolve(ILLMClient)
        assert instance3 is not instance1  # Different scope = different instance

    print(" Scoped test passed")
```

## Key Learnings

### 1. SOLID Principles in Practice

- **Single Responsibility**: Each component has one clear purpose (build prompt, call LLM, parse response)
- **Open/Closed**: Add new providers without modifying existing code
- **Liskov Substitution**: All implementations can be used interchangeably through interfaces
- **Interface Segregation**: Small, focused interfaces instead of large monolithic ones
- **Dependency Inversion**: Depend on abstractions (ILLMClient) not concretions (OpenAILLMClient)

### 2. When to Use DI

**Good candidates for DI:**
- Multi-provider LLM applications
- Complex workflows with multiple stages
- Applications requiring extensive testing
- Team projects with parallel development
- Long-lived production systems

**When to skip DI:**
- Simple prototypes or PoCs
- Single-use scripts
- Tight deadlines with small scope
- Solo developer, short-term project

### 3. Design Patterns Integration

This project demonstrates how multiple patterns work together:

- **Builder**: Fluent workflow construction
- **Strategy**: Swappable LLM executors
- **Mediator**: Node communication
- **Memento**: State persistence
- **State**: Execution tracking
- **Dependency Injection**: Component composition

### 4. Testing Strategy

**Test Pyramid for LLM Applications:**

```
                         
          E2E Tests        Few, expensive, use real APIs
          (Real LLMs)    
                         $
         Integration       Some, moderate cost, use cheap models
         Tests             or cached responses
                         $
         Unit Tests        Many, fast, use MockLLMClient
         (Mocks)           Zero API cost
                         
```

**Benefits of DI for Testing:**
- Write unit tests for 90% of logic using mocks
- Reserve API calls for critical integration tests
- Achieve >90% code coverage without API costs
- Run full test suite in seconds on CI/CD

### 5. Production Best Practices

**Container Configuration:**
```python
# Production container setup
def create_production_container() -> DIContainer:
    container = DIContainer()

    # Singleton for expensive/stateful services
    container.register_singleton(
        ILLMClient,
        lambda: OpenAILLMClient(
            model="gpt-4o-mini",
            max_retries=3,
            timeout=30
        )
    )

    # Transient for stateless services
    container.register_transient(IPromptBuilder, DynamicPromptBuilder)
    container.register_transient(IResponseParser, EnhancedResponseParser)

    return container
```

**Error Handling:**
```python
class RobustLLMClient(BaseLLMClient):
    """Production-ready client with retry and fallback."""

    async def generate(self, prompt, context, **kwargs):
        try:
            return await self.primary_client.generate(prompt, context, **kwargs)
        except Exception as e:
            logger.warning(f"Primary client failed: {e}, trying fallback")
            return await self.fallback_client.generate(prompt, context, **kwargs)
```

## Migration from Legacy Code

See `MIGRATION_SUMMARY.md` for detailed migration guide.

**Quick migration steps:**

1. **Identify components**: Find prompt building, LLM calling, response parsing logic
2. **Extract interfaces**: Define `IPromptBuilder`, `ILLMClient`, `IResponseParser` for your use case
3. **Create implementations**: Implement interfaces for current behavior
4. **Inject dependencies**: Pass implementations via constructor instead of creating internally
5. **Add tests**: Write unit tests with mocks
6. **Gradual rollout**: Migrate one workflow at a time

## Troubleshooting

### Common Issues

**Issue**: `Service not registered` error
```python
# Problem: Trying to resolve unregistered service
client = container.resolve(ILLMClient)  # Error!

# Solution: Register before resolving
container.register_singleton(ILLMClient, OpenAILLMClient)
client = container.resolve(ILLMClient)  # Works!
```

**Issue**: Mock client not being called
```python
# Problem: Workflow still using legacy executor
workflow.add_prompt_node("test", llm_executor=old_function)

# Solution: Use injected_llm_client instead
workflow.add_prompt_node(
    "test",
    injected_llm_client=MockLLMClient("response"),
    injected_response_parser=TextResponseParser()
)
```

**Issue**: Type checking errors with Protocol
```python
# Problem: mypy complains about structural subtyping
def process(client: ILLMClient):  # Type error!
    ...

# Solution: Use @runtime_checkable and isinstance
from typing import runtime_checkable

@runtime_checkable
class ILLMClient(Protocol):
    ...

# Now isinstance checks work
assert isinstance(OpenAILLMClient(), ILLMClient)  # True
```

## Further Reading

- **SOLID Principles**: https://en.wikipedia.org/wiki/SOLID
- **Dependency Injection in Python**: https://python-dependency-injector.ets-labs.org/
- **Protocol vs ABC**: https://peps.python.org/pep-0544/
- **Testing with Mocks**: https://docs.python.org/3/library/unittest.mock.html

## Conclusion

Dependency Injection is a foundational pattern for building maintainable LLM applications. By separating concerns and inverting dependencies, we achieve:

- **Flexibility**: Swap providers without code changes
- **Testability**: Fast unit tests without API costs
- **Maintainability**: Clear separation of responsibilities
- **Scalability**: Easy to extend with new components

This implementation demonstrates that DI is not just theoretical - it provides concrete, measurable benefits for real-world LLM systems. The initial investment in proper architecture pays dividends throughout the application lifecycle, from development and testing to production maintenance and future enhancements.

**Key Takeaway**: When building LLM applications that will evolve beyond prototypes, invest in DI early. The cost of retrofitting DI into tightly coupled code far exceeds the cost of designing with DI from the start.

---

**Project Status**:  Implementation complete, tested, and documented

**Code Statistics**: 2,304 lines across 17 Python files

**Test Coverage**: 6 comprehensive examples demonstrating all DI patterns

**Documentation**: README.md (Japanese), CLAUDE.md (English)
