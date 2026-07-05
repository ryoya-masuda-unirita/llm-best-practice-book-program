# Chapter 2 Section 9: Prompt Unit Testing with LLM-as-a-Judge

## What This Section Demonstrates

Prompts are code, and this section shows how to **unit-test them like code**. It layers deterministic tests (prompt structure, parameter propagation, regression checks — no API calls) with quality tests that use the LLM-as-a-Judge pattern from Section 7 (mocked in CI, live in integration runs), all in ordinary pytest.

The result: prompt edits can't silently drop a required field, break JSON-format instructions, or degrade output quality below a threshold without a failing test. Apply this to every prompt that matters — it's the difference between "we tweak prompts and hope" and a reviewable, CI-gated prompt lifecycle.

## Practice Rules

1. **Test the rendered prompt deterministically first.** Assert that required field names, format directives ("JSON"), counts ("3" traits), and user parameters actually appear in the rendered prompt — these tests are fast, free, and catch most regressions.
2. **Test quality with a judge behind a threshold API.** Give the verdict model a `is_passing(threshold)` method and assert on it — tests express the quality bar explicitly.
3. **Mock the judge in unit tests; keep one live integration test (skipped by default).** Use fixtures with realistic high-quality AND low-quality verdicts; verify the threshold separates them.
4. **Cover representative inputs, not the input space**: 3–5 scenarios spanning primary use case, different demographics, and minimal/edge input.
5. **Encode regression checks as invariants** (all fields present, non-empty names, age/gender echo the request, JSON serializable) so known past failures stay fixed.
6. **Allow custom judge criteria per domain** (`make_custom_judge_prompt(criteria, scoring_guide)`) — creativity/fantasy-consistency for characters, faithfulness for RAG — instead of one generic rubric.
7. **Keep test fixtures as typed model instances** (`conftest.py` builds `CharacterRequest` / `CharacterResponse` / `JudgeResponse` objects) so schema changes break tests loudly.

## Architecture

```
tests/
├── conftest.py                    # typed fixtures: sample/low-quality responses, judge verdicts
├── test_prompt_unit_testing.py    # the 6 testing patterns (below)
└── test_llm_as_a_judge.py         # judge service behavior

Test layers:
  [deterministic]  TestCharacterPromptStructure   — rendered prompt content assertions
  [deterministic]  TestRepresentativeInputs       — 3–5 scenario renderings
  [deterministic]  TestRegressionDetection        — output invariants on fixtures
  [mocked LLM]     TestCharacterOutputQuality     — judge threshold pass/fail
  [mocked LLM]     TestCustomJudgeCriteria        — domain-specific rubrics
  [live, skipped]  TestEndToEndWithJudge          — real generation + judgment

src/ = generation + judge implementation (same shape as Chapter 2 Section 7)
```

### Directory Structure

```
chapter_2/section_9/
├── src/
│   ├── main.py                        # CLI: generate + judge (like Section 7)
│   ├── client/llm_client.py           # 3-provider clients + model enums
│   ├── model/model.py                 # CharacterRequest / CharacterResponse
│   ├── model/llm_as_a_judge_model.py  # JudgeRequest / JudgeResponse (+ is_passing)
│   ├── prompt/prompt.py               # generation prompt (unit under test)
│   ├── prompt/llm_as_a_judge_prompt.py# default + custom-criteria judge prompts
│   └── service/                       # request_llm.py / llm_as_a_judge.py
├── tests/                             # the practice lives here
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Deterministic prompt-structure tests (`tests/test_prompt_unit_testing.py`)

```python
def test_prompt_includes_required_fields(self, sample_character_request):
    prompt = make_prompt(sample_character_request)
    system_content = prompt[0]["content"]
    assert "first_name" in system_content
    assert "personalities" in system_content

def test_prompt_includes_request_parameters(self, sample_character_request):
    system_content = make_prompt(sample_character_request)[0]["content"]
    assert sample_character_request.gender.value in system_content
    assert str(sample_character_request.age) in system_content
```

No API call; catches "someone reworded the prompt and dropped a field" instantly.

### 2. Threshold-based quality assertion with a mocked judge

```python
mock_parse = mocker.patch("src.service.llm_as_a_judge.openai_client.beta.chat.completions.parse")
mock_parse.return_value = mock_result   # returns sample_judge_response fixture

judge_response = await judge_with_openai(judge_request=judge_request, model=OpenAIModel.GPT_5_4_MINI)
assert judge_response.is_passing(threshold=3.0)
assert judge_response.overall_score >= 4.0
```

The low-quality twin test asserts `not is_passing(...)` — proving the threshold discriminates.

### 3. The threshold API on the verdict model (`src/model/llm_as_a_judge_model.py`)

```python
class JudgeResponse(BaseModel):
    evaluations: list[EvaluationCriterion]
    overall_score: float = Field(..., ge=1.0, le=5.0)

    def is_passing(self, threshold: float = 3.0) -> bool:
        return self.overall_score >= threshold
```

### 4. Domain-specific judge criteria (`src/prompt/llm_as_a_judge_prompt.py`)

```python
def make_custom_judge_prompt(request, criteria, scoring_guide) -> list:
    return make_custom_openai_judge_prompt(request, criteria, scoring_guide)
# e.g. criteria = {"creativity": "...", "fantasy_elements": "...", "consistency": "..."}
```

### 5. Typed fixtures incl. a deliberately bad sample (`tests/conftest.py`)

```python
@pytest.fixture
def sample_character_response() -> CharacterResponse:
    return CharacterResponse(first_name="Elena", last_name="Stormweaver", ...)
# plus low_quality_character_response / low_quality_judge_response fixtures
```

## Data Models

| Model | Purpose |
|-------|---------|
| `CharacterRequest` / `CharacterResponse` | Generation task input/output (the prompt under test) |
| `JudgeRequest` / `JudgeResponse` / `EvaluationCriterion` | Judge I/O; `JudgeResponse.is_passing(threshold)` is the test API |

## Setup & Run

```bash
cp .envrc.example .envrc     # OPENAI_API_KEY / GEMINI_API_KEY / ANTHROPIC_API_KEY
uv sync

# Run the app (generation + judgment)
uv run python -m src.main -g FEMALE -a 25 -lp GEMINI -m GEMINI_2_5_FLASH

# Run the prompt unit tests (no API key needed except the skipped E2E class)
uv run pytest tests/ -v
uv run pytest tests/test_prompt_unit_testing.py -v
```

### CLI Options

Same surface as Chapter 2 Section 7: `-g/-a/-ai` (character request), `-lp/-m` (generation), `-jp/-jm` (judge override), `-od` (output directory).

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
uv run pytest tests/ -v
```

## Implementation Notes

- **Layer economics**: structure tests run in milliseconds and gate every commit; mocked-judge tests validate the quality *machinery*; the live E2E test (skipped by default) validates the actual quality and runs on demand or nightly — don't put paid API calls in the default test path.
- **Mock at the SDK boundary** (`openai_client.beta.chat.completions.parse`), not at your service function — the test then exercises your real parsing/error handling.
- **Testing the threshold both ways matters**: a judge that passes everything is worse than no judge. The low-quality fixture is the guard.
- **Representative inputs beat parametrized sweeps** for prompts: each scenario documents an intended use case; a failing one tells you which user story broke.
- **This section builds on Section 7** (same judge implementation); the new material is the test suite structure in `tests/`.

## How to Apply This Practice to Your Own Project

1. For each production prompt, write structure tests first: required fields, format directives, parameter propagation — assert on the *rendered* prompt.
2. Add `is_passing(threshold)` to your judge verdict model; pick the threshold from measured good/bad samples.
3. Create fixtures for one high-quality and one low-quality output with matching judge verdicts; mock the judge SDK call and test both directions of the threshold.
4. Write 3–5 representative-input tests mirroring your real user scenarios.
5. Convert every prompt bug you fix into a regression invariant test.
6. Keep one live E2E test marked skip/nightly for true quality tracking; never let CI depend on LLM API availability.
