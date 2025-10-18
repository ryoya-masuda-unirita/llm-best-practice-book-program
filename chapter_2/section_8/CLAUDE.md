# Chapter 2 Section 8: Prompt Unit Testing with LLM-as-a-Judge

## Overview

This project demonstrates **Prompt Unit Testing**, a design practice for verifying the behavior of prompts given to LLMs (Large Language Models) and continuously ensuring their quality and stability. In LLM-integrated applications, changes to prompts can have unexpected impacts on the entire system's output.

This practice applies the concept of unit testing from traditional software development to prompt engineering. By introducing a mechanism to automatically verify the impact of prompt changes, it aims to detect unintended quality degradation (regression) early and enhance the reliability of LLM systems.

The implementation showcases two key patterns:
1. **Prompt Unit Testing**: Systematic testing of prompts using representative inputs, structure validation, and regression detection
2. **LLM-as-a-Judge**: Using another LLM to evaluate the quality of generated outputs based on defined criteria

## Features

- **Comprehensive Prompt Testing Framework**: Multiple test patterns for validating prompt behavior
- **LLM-as-a-Judge Integration**: Automated quality evaluation using LLM-based judges
- **Multi-Provider Support**: Works with both OpenAI GPT-4o-mini and Google Gemini 2.5 Flash
- **Structured Output Validation**: Type-safe responses using Pydantic models
- **Flexible Evaluation Criteria**: Support for both default and custom evaluation criteria
- **Regression Detection**: Tests designed to catch quality degradation when prompts change
- **Mock-based Testing**: Fast unit tests using mocks alongside integration tests
- **Quality Thresholds**: Configurable pass/fail thresholds for automated quality gates
- **JSON Export**: Save both generation results and evaluation reports
- **Async Architecture**: Efficient async/await pattern for API calls

## Project Structure

### Directory Structure

```
chapter_2/section_8/
├── src/
│   ├── __init__.py              # Package initialization
│   ├── config.py                # Configuration management (API keys)
│   ├── logger.py                # Logging setup
│   ├── main.py                  # Main entry point with CLI
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # LLM client initialization (OpenAI, Gemini)
│   ├── model/
│   │   ├── __init__.py
│   │   ├── model.py             # Character models (Request/Response)
│   │   └── llm_as_a_judge_model.py  # Judge models (Request/Response)
│   ├── prompt/
│   │   ├── __init__.py
│   │   ├── prompt.py            # Character generation prompt
│   │   └── llm_as_a_judge_prompt.py # Judge evaluation prompt
│   └── service/
│       ├── __init__.py
│       ├── request_llm.py       # Character generation service
│       └── llm_as_a_judge.py    # Judge evaluation service
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── test_prompt_unit_testing.py  # Main prompt unit tests
│   └── test_llm_as_a_judge.py   # LLM-as-a-Judge functionality tests
├── outputs/                      # Generated results (auto-created)
├── .envrc.example               # Environment variables template
├── pyproject.toml               # Project dependencies
├── pytest.ini                   # Pytest configuration
├── Makefile                     # Development commands
├── README.md                    # Project documentation (Japanese)
└── CLAUDE.md                    # This file
```

### Architecture

The project follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────┐
│         CLI Layer (main.py)                     │
│     - Command-line argument parsing             │
│     - Output directory management               │
│     - Orchestration of generation + evaluation  │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│      Business Logic Layer                       │
│  - Prompt generation (prompt.py)                │
│  - LLM client management (llm_client.py)        │
│  - Data models (model.py)                       │
│  - Judge prompts (llm_as_a_judge_prompt.py)     │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│      Service Layer                              │
│  - Character generation (request_llm.py)        │
│  - Judge evaluation (llm_as_a_judge.py)         │
│  - Coordinated workflows (request_with_judge)   │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│      Infrastructure Layer                       │
│  - Configuration (config.py)                    │
│  - Logging (logger.py)                          │
│  - External APIs (OpenAI, Gemini)               │
└─────────────────────────────────────────────────┘
```

### Implementation Details

#### 1. Data Models

**Character Models** (`src/model/model.py`):

```python
class CharacterRequest(BaseModel):
    gender: Gender
    age: int  # 0-100
    additional_instructions: Optional[str]

class CharacterResponse(BaseModel):
    first_name: str
    last_name: str
    gender: Gender
    age: int  # 0-100
    personalities: list[CharacterPersonality]  # Exactly 3 traits
```

**Judge Models** (`src/model/llm_as_a_judge_model.py`):

```python
class EvaluationScore(IntEnum):
    COMPLETELY_INAPPROPRIATE = 1
    POOR = 2
    ACCEPTABLE = 3
    GOOD = 4
    PERFECT = 5

class JudgeRequest(BaseModel):
    question: str
    response: str
    context: str | None

class JudgeResponse(BaseModel):
    evaluations: list[EvaluationCriterion]
    overall_score: float  # 1.0-5.0
    summary: str
```

#### 2. Prompt Unit Testing Patterns

The test suite (`tests/test_prompt_unit_testing.py`) demonstrates six key testing patterns:

**a) Structure Validation** (`TestCharacterPromptStructure`):
- Verifies prompt includes all required fields
- Checks format enforcement (JSON)
- Validates parameter propagation

**b) Quality Testing** (`TestCharacterOutputQuality`):
- Uses LLM-as-a-Judge to validate output quality
- Tests both high-quality and low-quality detection
- Ensures quality thresholds work correctly

**c) Representative Inputs** (`TestRepresentativeInputs`):
- Tests 3-5 key scenarios covering main use cases
- Young female fantasy character (primary use case)
- Elderly male realistic character (different demographics)
- Minimal input (edge case)

**d) Custom Criteria** (`TestCustomJudgeCriteria`):
- Demonstrates domain-specific evaluation criteria
- Example: creativity, fantasy_elements, consistency for fantasy characters

**e) Regression Detection** (`TestRegressionDetection`):
- Verifies all required fields are present
- Checks personality traits have descriptions
- Validates JSON serialization
- Ensures names are non-empty
- Confirms age/gender match requests

**f) End-to-End Integration** (`TestEndToEndWithJudge`):
- Full workflow test (skipped by default)
- Requires actual API calls
- Validates complete generation + evaluation pipeline

#### 3. LLM-as-a-Judge Implementation

**Judge Service** (`src/service/llm_as_a_judge.py`):

```python
async def judge_with_openai(
    judge_request: JudgeRequest,
    model: OpenAIModel,
) -> JudgeResponse:
    """Evaluate response using OpenAI as judge."""
    prompt = make_judge_prompt(judge_request)
    result = await openai_client.beta.chat.completions.parse(
        model=model,
        messages=prompt,
        response_format=JudgeResponse,
    )
    return result.choices[0].message.parsed
```

**Default Evaluation Criteria**:
1. **Accuracy**: Does the response correctly answer the question?
2. **Comprehensiveness**: Is all necessary information included?
3. **Clarity**: Is the response clear and easy to understand?

**Custom Criteria Support**:
```python
custom_criteria = [
    {"name": "creativity", "description": "Is the character unique..."},
    {"name": "fantasy_elements", "description": "Does it contain magic..."},
]
prompt = make_custom_judge_prompt(request, criteria=custom_criteria)
```

#### 4. Integrated Workflow

The `request_with_judge` function (`src/service/request_llm.py`) coordinates:

1. **Character Generation**: Generate character using OpenAI or Gemini
2. **Automatic Evaluation**: Evaluate result using LLM-as-a-Judge
3. **Return Both**: Return both character and evaluation results

```python
character_result, judge_result = await request_with_judge(
    prompt=prompt,
    model=model,
    provider=provider,
    judge_model=judge_model,
    judge_provider=judge_provider,
)
```

## Usage

### Environment Setup

- **Python**: 3.13.2 or higher
- **Dependencies**:
  - click>=8.3.0
  - google-genai>=1.45.0
  - openai>=2.4.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1
  - pytest>=8.4.2 (dev)
  - pytest-asyncio>=1.2.0 (dev)
  - pytest-mock>=3.15.1 (dev)

### Setup

1. **Create environment variables file**

```bash
# Copy example and edit
cp .envrc.example .envrc

# Add your API keys
# .envrc
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
```

2. **Install dependencies**

```bash
# Using uv (recommended)
uv sync

# Using pip
pip install -e .
```

### Running Character Generation

#### Basic Usage

```bash
# Generate with Gemini (default)
uv run python -m src.main \
  -g female \
  -a 25 \
  -ai "Generate a wizard from a fantasy world." \
  -lp gemini \
  -m gemini-2.5-flash

# Generate with OpenAI
uv run python -m src.main \
  -g male \
  -a 30 \
  -ai "Generate a detective from the modern world." \
  -lp openai \
  -m gpt-4o-mini
```

#### Advanced Options

```bash
# Custom output directory
uv run python -m src.main -g female -a 25 -lp gemini -m gemini-2.5-flash -od ./custom_output

# Use different models for generation and judgment
uv run python -m src.main \
  -g female -a 25 \
  -lp gemini -m gemini-2.5-flash \
  -jp openai -jm gpt-4o-mini
```

#### CLI Options

```
Options:
  -g, --gender [female|male]       Character gender (required)
  -a, --age INTEGER RANGE          Character age 0-100 (required)
  -ai, --additional-instructions   Additional generation instructions
  -lp, --llm-provider              Provider for generation (openai|gemini)
  -m, --model                      Model for generation
  -jp, --judge-provider            Provider for judgment (optional)
  -jm, --judge-model              Model for judgment (optional)
  -od, --output-directory PATH     Output directory (default: outputs)
  --help                           Show help message
```

### Output Example

Running the generation creates two JSON files:

**Character File**: `outputs/{uuid}_gemini_character.json`
```json
{
    "first_name": "Aria",
    "last_name": "Stormweaver",
    "gender": "female",
    "age": 25,
    "personalities": [
        {
            "short_personality": "Curious scholar",
            "description": "Driven by an insatiable thirst for knowledge, constantly studying ancient texts and experimenting with new spell combinations."
        },
        {
            "short_personality": "Compassionate healer",
            "description": "Uses magic primarily to help others, often prioritizing healing and protection spells over offensive magic."
        },
        {
            "short_personality": "Impulsive risk-taker",
            "description": "Sometimes acts without fully thinking through consequences, especially when pursuing a fascinating magical discovery."
        }
    ]
}
```

**Judge File**: `outputs/{uuid}_gemini_judge.json`
```json
{
    "evaluations": [
        {
            "criterion_name": "accuracy",
            "score": 5,
            "reasoning": "The response perfectly matches the request for a 25-year-old female wizard character from a fantasy world."
        },
        {
            "criterion_name": "comprehensiveness",
            "score": 4,
            "reasoning": "Includes all required fields with detailed personality descriptions, though could expand on magical abilities."
        },
        {
            "criterion_name": "clarity",
            "score": 5,
            "reasoning": "Clear, well-structured output with easy-to-understand personality descriptions."
        }
    ],
    "overall_score": 4.67,
    "summary": "Excellent character generation that meets all requirements with creative and consistent personality traits."
}
```

**Console Output**:
```
[2025-10-18 10:30:45] [INFO] [__main__] Character Generation Request:
Gender: female
Age: 25
Additional Instructions: Generate a wizard from a fantasy world.

Generation LLM: gemini / gemini-2.5-flash
Judge LLM: gemini / gemini-2.5-flash
Output directory: outputs

[2025-10-18 10:30:46] [INFO] [src.service.request_llm] Step 1: Generating character...
[2025-10-18 10:30:48] [INFO] [src.service.request_llm] Character generation completed.
[2025-10-18 10:30:48] [INFO] [src.service.request_llm] Step 2: Evaluating character with LLM-as-a-Judge...
[2025-10-18 10:30:50] [INFO] [src.service.llm_as_a_judge] Judgment completed. Overall score: 4.67/5.0
[2025-10-18 10:30:50] [INFO] [__main__] Character file saved to outputs/abc123_gemini_character.json
[2025-10-18 10:30:50] [INFO] [__main__] Judge evaluation saved to outputs/abc123_gemini_judge.json
[2025-10-18 10:30:50] [INFO] [__main__] Overall evaluation score: 4.67/5.0
```

### Running Tests

#### Run All Tests

```bash
# Run all tests (mocked, no API calls)
uv run pytest

# Verbose output
uv run pytest -v

# Show print statements
uv run pytest -s
```

#### Run Specific Test Classes

```bash
# Test prompt structure validation
uv run pytest tests/test_prompt_unit_testing.py::TestCharacterPromptStructure -v

# Test quality evaluation
uv run pytest tests/test_prompt_unit_testing.py::TestCharacterOutputQuality -v

# Test regression detection
uv run pytest tests/test_prompt_unit_testing.py::TestRegressionDetection -v

# Test LLM-as-a-Judge functionality
uv run pytest tests/test_llm_as_a_judge.py -v
```

#### Run Integration Tests

```bash
# Run integration test (requires API keys and makes real API calls)
uv run pytest -k "test_full_generation" -v

# Skip integration tests (default behavior)
uv run pytest -v -k "not test_full_generation"
```

#### Test Organization

Tests are organized with pytest markers:

- `@pytest.mark.asyncio`: Async tests
- `@pytest.mark.skip`: Skipped tests (e.g., integration tests)
- `@pytest.mark.integration`: Integration tests requiring API calls
- `@pytest.mark.unit`: Fast unit tests with mocks

### Development Commands

```bash
# Lint code
make lint

# Format code
make fmt

# Lint + format
make fix

# Type checking
make mypy
```

## Key Design Patterns

### 1. Representative Input Testing

Instead of testing all possible inputs, focus on 3-5 representative cases:

```python
class TestRepresentativeInputs:
    async def test_young_female_fantasy_character(self):
        """Test Case 1: Primary use case"""

    async def test_elderly_male_realistic_character(self):
        """Test Case 2: Different demographics"""

    async def test_young_adult_no_additional_instructions(self):
        """Test Case 3: Minimal input edge case"""
```

### 2. Flexible Validation

Tests verify "conditions that must be met" rather than exact output matching:

```python
# ✓ Good: Flexible validation
assert len(response.personalities) == 3
assert response.age == request.age
assert all(len(p.description) > len(p.short_personality) for p in response.personalities)

# ✗ Bad: Exact matching
assert response.first_name == "Aria"  # Too strict, fails on valid variations
```

### 3. Regression Detection

Tests serve as canaries for prompt changes:

```python
async def test_personality_traits_have_descriptions(self):
    """If this fails after prompt change, descriptions may be missing."""
    for personality in response.personalities:
        assert len(personality.description) > 0
        assert len(personality.description) > len(personality.short_personality)
```

### 4. Quality Threshold Gates

Use LLM-as-a-Judge with configurable thresholds:

```python
assert judge_response.is_passing(threshold=3.0), \
    "Generated character should meet minimum quality threshold"
```

### 5. Custom Evaluation Criteria

Define domain-specific criteria for specialized use cases:

```python
custom_criteria = [
    {"name": "creativity", "description": "Uniqueness and originality"},
    {"name": "fantasy_elements", "description": "Appropriate magical elements"},
    {"name": "consistency", "description": "Internal logical consistency"},
]
```

## Best Practices Demonstrated

### From CLAUDE.md Documentation

This implementation follows the best practices outlined in the project documentation:

1. **Structured Prompt Management**: Prompts are managed as code in separate modules (`prompt.py`, `llm_as_a_judge_prompt.py`)

2. **Start with 3-5 Key Cases**: The `TestRepresentativeInputs` class demonstrates starting with the most important scenarios

3. **Flexible Validation Utilities**: Tests use a combination of:
   - Structure validation (field presence, type checking)
   - Keyword/content verification
   - LLM-as-a-Judge for quality assessment

4. **CI/CD Integration Ready**:
   - Pytest configuration in `pytest.ini`
   - Fast mocked tests for CI
   - Optional integration tests for comprehensive validation

5. **Cost-Aware Testing Strategy**:
   - Most tests use mocks (no API costs)
   - Integration tests are skipped by default
   - Can run full suite in nightly builds

6. **Clear Test Organization**:
   - Separate test classes for different concerns
   - Descriptive test names explaining what they validate
   - Comments explaining why tests matter for regression detection

## Trade-offs and Considerations

### Test Brittleness

**Challenge**: Model updates may change output style, breaking tests

**Mitigation**:
- Use flexible assertions (presence checks, not exact matches)
- Focus on structural requirements, not stylistic details
- Configurable quality thresholds to adjust sensitivity

### Execution Time and Cost

**Challenge**: API calls add time and cost to test runs

**Mitigation**:
- Mock responses for unit tests (instant, free)
- Skip integration tests by default (`@pytest.mark.skip`)
- Run full suite only in nightly builds or before releases

### Quality Threshold Calibration

**Challenge**: Setting thresholds too loose misses issues, too strict causes false failures

**Strategy**:
- Default threshold: 3.0/5.0 (acceptable quality)
- Adjust based on use case criticality
- Monitor threshold effectiveness over time

## Extension Points

### Adding New Evaluation Criteria

```python
# Define custom criteria
custom_criteria = [
    {"name": "tone", "description": "Appropriate tone for target audience"},
    {"name": "technical_accuracy", "description": "Factual correctness"},
]

# Use in tests
prompt = make_custom_judge_prompt(request, criteria=custom_criteria)
```

### Testing Different Prompt Versions

```python
# Version A (current)
def make_prompt_v1(request: CharacterRequest) -> list:
    return [...]

# Version B (experimental)
def make_prompt_v2(request: CharacterRequest) -> list:
    return [...]

# A/B test in unit tests
async def test_prompt_version_comparison():
    v1_result = await generate_with_prompt(make_prompt_v1(request))
    v2_result = await generate_with_prompt(make_prompt_v2(request))

    v1_score = await judge(v1_result)
    v2_score = await judge(v2_result)

    # Ensure v2 doesn't degrade quality
    assert v2_score >= v1_score - 0.5
```

### Snapshot Testing

For outputs that should remain stable:

```python
# First run creates snapshot
def test_output_snapshot(snapshot):
    result = generate_character(...)
    snapshot.assert_match(result.model_dump_json(), "character_output.json")

# Subsequent runs compare against snapshot
# Update snapshot with: pytest --snapshot-update
```

## Summary

This project demonstrates a comprehensive approach to prompt unit testing for LLM applications:

- **Systematic Testing**: Multiple test patterns covering structure, quality, and regression
- **Automated Evaluation**: LLM-as-a-Judge pattern for quality assessment
- **Practical Balance**: Trade-offs between test coverage and execution cost
- **CI/CD Ready**: Designed for integration into continuous integration pipelines
- **Extensible**: Easy to add new criteria, prompts, and test cases

By applying traditional software testing best practices to prompt engineering, this approach enables safe, continuous improvement of LLM systems while maintaining quality and reliability.

## References

- **Pydantic**: Type-safe data validation - https://docs.pydantic.dev/
- **Pytest**: Testing framework - https://docs.pytest.org/
- **OpenAI Structured Outputs**: https://platform.openai.com/docs/guides/structured-outputs
- **Google Gemini API**: https://ai.google.dev/gemini-api/docs
- **LLM-as-a-Judge Pattern**: Using LLMs to evaluate LLM outputs
