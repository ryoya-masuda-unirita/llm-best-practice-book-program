# LLM Pipeline Implementation with LangGraph

## Project Overview

This project demonstrates a **production-ready LLM pipeline** implementation using LangGraph, showcasing best practices for building complex multi-stage LLM applications. It implements a document analysis system that processes Japanese technical documents through multiple stages, evaluates output quality using the LLM-as-a-Judge pattern, and automatically retries with feedback to improve results.

### Key Concepts Demonstrated

1. **LLM Pipeline Pattern**: Breaking down complex tasks into discrete stages with clear responsibilities
2. **LLM-as-a-Judge**: Using a separate LLM call to evaluate the quality of generated outputs
3. **Feedback Loop**: Automatically retrying analysis with constructive feedback when quality is below threshold
4. **Multi-Provider Support**: Abstraction layer supporting both OpenAI and Google Gemini APIs
5. **Type-Safe Structured Outputs**: Using Pydantic models for reliable, validated data structures
6. **State Management**: LangGraph's StateGraph for managing complex pipeline state

## Architecture

### System Components

```
+-------------------------------------------------------------+
|                    CLI Layer (main.py)                      |
|  - Argument parsing (Click)                                 |
|  - Pipeline orchestration                                   |
|  - Output persistence (JSON/Markdown)                       |
+------------------------+------------------------------------+
                         |
                         v
+------------------------+------------------------------------+
|            LangGraph Pipeline Service                       |
|                                                             |
|  +--------------+    +--------------+    +--------------+   |
|  |     Read     |--->|   Analyze    |--->|    Judge     |   |
|  |   Document   |    |   Document   |    |   Quality    |   |
|  +--------------+    +--------------+    +------+-------+   |
|                              ^                  |           |
|                              |                  |           |
|                              |   Grade < 4?     |           |
|                              +------------------+           |
|                           (Retry with Feedback)             |
|                                                             |
|  Maximum 3 attempts (1 initial + 2 retries)                 |
+-------------------------------------------------------------+
```

### Pipeline Flow

1. **Document Reading** (`read_document_node`)
   - Load markdown document from file system
   - Validate file exists and is readable
   - Store content in pipeline state

2. **Document Analysis** (`analyze_document_[openai|gemini]_node`)
   - Extract theme (1-2 sentences)
   - Assess value (2-3 sentences)
   - Generate improvement requests (3-5 items)
   - On retry: incorporate feedback from judge

3. **Quality Evaluation** (`judge_analysis_[openai|gemini]_node`)
   - Evaluate analysis against 5 criteria
   - Assign grade from 1-5
   - Provide detailed reasoning
   - Generate specific improvements if grade < 4

4. **Routing Logic** (`route_after_judge`)
   - Grade >= 4: Accept and end pipeline
   - Grade < 4 and retries < 2: Retry with feedback
   - Max retries reached: Accept current result

### Data Models

#### DocumentAnalysis (src/model/llm_pipeline_model.py:35-79)
```python
class DocumentAnalysis(BaseModel):
    theme: str  # Main theme (1-2 sentences)
    value: str  # Document value (2-3 sentences)
    improvement_requests: list[str]  # 3-5 improvement suggestions
```

**Key Features**:
- Immutable (`frozen=True`)
- Assignment validation enabled
- Built-in JSON and Markdown serialization
- Min/max constraints on improvement requests

#### AnalysisEvaluation (src/model/llm_pipeline_model.py:7-33)
```python
class AnalysisEvaluation(BaseModel):
    grade: Literal[1, 2, 3, 4, 5]  # Quality grade
    reasoning: str  # 3-5 sentences explaining grade
    specific_improvements: list[str]  # Concrete suggestions for improvement
```

**Key Features**:
- Literal type for grade ensures valid values
- `is_acceptable()` helper method (grade >= 4)
- Structured feedback for retry loop

#### PipelineState (src/model/llm_pipeline_model.py:81-90)
```python
class PipelineState(TypedDict):
    document_path: str
    document_content: str
    analysis_result: DocumentAnalysis | None
    evaluation_result: AnalysisEvaluation | None
    retry_count: int
    error: str | None
```

**Purpose**: Type-safe state management for LangGraph

**Note**: Additional fields `llm_provider` and `model` are added at runtime in `run_document_analysis_pipeline()` (line 491-492) with type ignore comments:
```python
"llm_provider": llm_provider,  # type: ignore
"model": model,  # type: ignore
```
These fields are accessed throughout the pipeline but aren't in the TypedDict definition to maintain type safety for the core state fields.

## Implementation Details

### Prompt Engineering (src/prompt/llm_pipeline_prompt.py)

The project implements 4 prompt generation functions:

1. **`make_document_analysis_prompt()`** - For OpenAI analysis (returns messages list)
2. **`make_document_analysis_system_instruction()`** - For Gemini analysis (returns system_instruction + user_content tuple)
3. **`make_judge_prompt()`** - For OpenAI evaluation (returns messages list)
4. **`make_judge_system_instruction()`** - For Gemini evaluation (returns system_instruction + user_content tuple)

#### Analysis Prompt Strategy
- Clear role definition ("excellent document analyst")
- Structured output requirements with JSON schema dynamically generated from Pydantic model
- Explicit constraints (sentence counts, item counts)
- Language specification (Japanese markdown with explicit instruction)
- Objective and constructive tone
- **IMPORTANT**: All responses must be in Japanese

#### Judge Prompt Strategy
- Expert evaluator persona
- 5 weighted evaluation criteria:
  - Theme Accuracy (20%)
  - Value Assessment (30%)
  - Improvement Quality (30%)
  - Completeness (10%)
  - Clarity (10%)
- Clear grading rubric (1-5 scale with descriptions):
  - 5 (Excellent): Outstanding analysis with highly valuable insights
  - 4 (Good): Solid analysis with minor improvements needed
  - 3 (Acceptable): Adequate but missing some aspects or depth
  - 2 (Poor): Significant issues with accuracy/completeness
  - 1 (Very Poor): Fails to capture document's essence
- Requirement to provide actionable feedback (3-5 specific improvements if grade < 4)
- **IMPORTANT**: All evaluations must be in Japanese

### LLM Provider Abstraction

#### OpenAI Implementation (src/service/llm_pipeline_service.py:55-112, 175-218)
```python
result = await openai_client.responses.parse(
    model=model,
    input=prompt,
    text_format=DocumentAnalysis,  # Structured output
)
analysis_result = result.output_parsed
```

#### Gemini Implementation (src/service/llm_pipeline_service.py:113-173, 220-268)
```python
result = await google_genai_client.aio.models.generate_content(
    model=model,
    contents=user_content,
    config=GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=DocumentAnalysis,
    ),
)
analysis_result = result.parsed
```

**Key Differences**:
- OpenAI uses `input` parameter with messages array; Gemini uses `system_instruction` + `contents`
- OpenAI uses `text_format` parameter; Gemini uses `response_schema` with `response_mime_type`
- OpenAI result is accessed via `result.output_parsed`; Gemini via `result.parsed`
- Both support structured output with Pydantic models
- Temperature configuration removed in current implementation (using defaults)

### Error Handling Strategy

1. **Node-Level Error Handling**
   - Each node wraps operations in try/except
   - Errors stored in state.error
   - Pipeline can gracefully terminate on errors

2. **Routing-Level Error Handling**
   - Route functions check for errors in state
   - Automatic routing to END on error conditions
   - No silent failures

3. **Retry Logic**
   - Maximum 2 retries (3 total attempts)
   - Retry only when grade < 4
   - Each retry includes previous feedback in Japanese:
     ```
     前回の分析は {grade}/5 の評価を受けました。
     評価フィードバック: {reasoning}
     改善が必要な具体的な点: {specific_improvements}
     このフィードバックに基づいて分析を改善してください。
     ```
   - Graceful acceptance after max retries

## Working with This Codebase

### When Making Changes

1. **Adding New Analysis Fields**
   - Update `DocumentAnalysis` model in `src/model/llm_pipeline_model.py`
   - Update prompts in `src/prompt/llm_pipeline_prompt.py`
   - Update tests to cover new fields
   - Consider impact on evaluation criteria

2. **Modifying Evaluation Logic**
   - Update `AnalysisEvaluation` model if changing grade scale
   - Modify `route_after_judge` if changing acceptance threshold
   - Update judge prompts to reflect new criteria
   - Update MAX_RETRIES constant if needed

3. **Adding New LLM Providers**
   - Add provider to `LLMProvider` enum in `src/client/llm_client.py`
   - Create model enum (e.g., `ClaudeModel`)
   - Implement analyze and judge nodes
   - Update routing functions
   - Add CLI option validation

4. **Modifying Pipeline Structure**
   - Edit `create_document_analysis_graph()` in `src/service/llm_pipeline_service.py`
   - Add new nodes with `graph.add_node()`
   - Define routing logic with `add_conditional_edges()` or `add_edge()`
   - Update `PipelineState` TypedDict if adding state fields
   - Update tests to cover new flow paths

### Testing Strategy

#### Unit Tests (tests/test_models.py)
- Pydantic model validation
- Serialization/deserialization
- Helper method behavior

#### Service Tests (tests/test_llm_pipeline_service.py)
- Individual node behavior with mocked LLM calls
- Routing function logic
- Error handling scenarios

**Running Tests**:
```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=html

# Verbose output
uv run pytest -v --tb=short
```

### Configuration

#### Environment Variables (.envrc)
```bash
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIzaSy...
```

**Note**: The project uses `python-dotenv` for loading environment variables. Create `.envrc` from `.envrc.example`.

#### Model Selection
- OpenAI models: gpt-5.4, gpt-5.4-mini, gpt-5, etc.
- Gemini models: gemini-2.5-flash, gemini-2.5-pro, etc.
- Models are validated against provider in main.py:67-70

### Common Operations

#### Running Analysis
```bash
# Using Gemini (default)
uv run python -m src.main \
  -lp gemini \
  -m gemini-2.5-flash \
  -dp dataset/document_0.md

# Using OpenAI
uv run python -m src.main \
  -lp openai \
  -m gpt-5.4 \
  -dp dataset/document_1.md

# Custom output directory
uv run python -m src.main \
  -lp gemini \
  -m gemini-2.5-flash \
  -dp dataset/document_0.md \
  -od custom_outputs
```

#### Makefile Shortcuts
```bash
make run-gemini    # Run with Gemini
make run-openai    # Run with OpenAI
make test          # Run all tests
make format        # Format code
```

### Expected Behavior

1. **First Analysis Attempt**
   - Document is analyzed based on prompt
   - Analysis sent to judge
   - If grade >= 4: Pipeline ends successfully
   - If grade < 4: Proceed to retry

2. **Retry with Feedback**
   - Previous evaluation feedback added to prompt
   - Analysis regenerated with improvements
   - New analysis sent to judge
   - Process repeats up to MAX_RETRIES (2)

3. **Output Files**
   - JSON: `{provider}_analysis_{uuid}.json`
   - Markdown: `{provider}_analysis_{uuid}.md`
   - Both contain the same DocumentAnalysis data

### Debugging Tips

1. **Enable Detailed Logging**
   - Logs are configured in `src/logger.py`
   - Default level: INFO
   - Look for "attempt X" in logs to track retries

2. **Check State at Each Node**
   - Each node logs its actions
   - Look for "Successfully analyzed" or "Evaluation complete"
   - Error messages include node name and error details

3. **Verify Structured Output**
   - Check JSON files are valid and match schema
   - Use `jq` to inspect: `cat output.json | jq .`
   - Validate with model: `DocumentAnalysis(**json.load(f))`

4. **Test Retry Mechanism**
   - Watch logs for "grade X/5 is below threshold"
   - Confirm feedback is added to retry prompts
   - Verify max retries are respected

## Design Patterns and Best Practices

### 1. Single Responsibility Principle
- Each node has one clear purpose
- Routing logic separated from business logic
- Prompt generation isolated in dedicated module

### 2. Type Safety
- Pydantic models enforce schema at runtime
- TypedDict for state provides editor support
- Literal types for enums (e.g., grade values)

### 3. Error Handling
- Never silently fail
- Errors stored in state for inspection
- Graceful degradation (accept after max retries)

### 4. Testability
- Async functions can be mocked
- State-based testing (pure functions)
- Integration tests cover full pipeline

### 5. Extensibility
- Easy to add new providers
- Pipeline structure defined declaratively
- Prompts externalized from logic

## Potential Improvements

When extending this project, consider:

1. **Parallel Processing**
   - Use LangGraph's parallel edges for independent tasks
   - Example: Analyze multiple documents concurrently

2. **Caching**
   - Cache analysis results by document hash
   - Reduce redundant API calls during testing

3. **Metrics and Monitoring**
   - Track average retry count
   - Monitor grade distribution
   - Measure latency per stage

4. **Human-in-the-Loop**
   - Add approval step before accepting low-grade results
   - Allow manual feedback injection

5. **Advanced Routing**
   - Dynamic model selection based on document complexity
   - Escalate to stronger model after failed retries

6. **Streaming Output**
   - Stream analysis results as they're generated
   - Provide real-time progress feedback

## File Modification Guidelines

### High-Change Areas
- `src/prompt/llm_pipeline_prompt.py` - Frequently tuned for quality
- `tests/` - Updated when adding features
- `dataset/` - Sample documents for testing

### Medium-Change Areas
- `src/model/llm_pipeline_model.py` - When adding fields
- `src/service/llm_pipeline_service.py` - When modifying pipeline structure

### Low-Change Areas
- `src/client/llm_client.py` - Stable provider abstraction (defines enums and initializes clients)
- `src/config.py` - Simple configuration loader
- `src/logger.py` - Logging configuration
- `src/main.py` - CLI interface

**Note**: The `llm_client.py` module initializes both API clients at import time:
```python
google_genai_client = genai.Client(api_key=config.gemini_api_key)
openai_client = AsyncOpenAI(api_key=config.openai_api_key)
```

### Protected Areas
- Do not modify generated outputs in `outputs/` directory
- Do not commit `.envrc` (API keys)
- Do not change `pyproject.toml` without testing dependencies

## Conclusion

This project exemplifies production-grade LLM application development with:
- Clear separation of concerns
- Type-safe implementations
- Comprehensive error handling
- Testable architecture
- Multi-provider flexibility

When working with this codebase, prioritize maintaining these qualities while extending functionality.
