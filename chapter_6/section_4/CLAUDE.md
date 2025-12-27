# Chapter 6 Section 4: Forgetting Unnecessary Past - State-Based Rollback Pattern

## Overview

This project demonstrates the **"Forgetting Unnecessary Past"** pattern for LLM applications through a state-based rollback mechanism. Users can roll back to any previous phase of a multi-step pipeline, effectively "forgetting" contaminated context and regenerating content with fresh state.

The implementation is a parallel world article generation pipeline that:
- Creates multiple content variants in parallel
- Uses LLM-as-a-Judge for automated evaluation
- Provides Human-in-the-Loop decision points with rollback capabilities

## Architecture

### Core Design Principles

1. **State as Memory**: The state object serves as the pipeline's memory. Presence or absence of state variables indicates phase completion.

2. **Forgetting by Deletion**: Rolling back removes state variables for later phases, causing regeneration from scratch.

3. **Idempotent Phases**: Each phase checks completion before executing, allowing resumption from any point.

4. **Human-in-the-Loop**: Critical decision points allow users to review progress and roll back.

### Pipeline Flow

```
+-------------+     +-------------+     +-------------+     +-------------+
|  Phase 1    |     |  Phase 2    |     |  Phase 3    |     |  Phase 4    |
|  Outline    |---->|  Outline    |---->|  First Half |---->|  Second Half|
|  Generation |     |  Selection  |     |  Generation |     |  Generation |
+-------------+     +-------------+     +------+------+     +-------------+
                                               |                   |
                                               v                   |
                                        +-----------+              |
                                        | Rollback  |              |
                                        | Point #1  |              |
                                        +-----------+              |
                                                                   v
+-------------+     +-------------+     +-------------+     +-------------+
|  Phase 9    |     |  Phase 7    |     |  Phase 6    |     |  Phase 5    |
|  Save       |<----|  Approval   |<----|  Article    |<----|  Review     |
|  Article    |     |  Decision   |     |  Selection  |     |  (LLM Judge)|
+-------------+     +------+------+     +-------------+     +-------------+
                           |
                           v
                    +-----------+
                    | Rollback  |
                    | Point #2  |
                    +-----------+
                           |
                           v (if rejected)
                    +-------------+
                    |  Phase 8    |
                    | Regenerate  |
                    | with        |
                    | Feedback    |
                    +-------------+
```

### Directory Structure

```
chapter_6/section_4/
+-- src/
|   +-- client/
|   |   +-- __init__.py
|   |   +-- llm_client.py        # Gemini client initialization
|   +-- model/
|   |   +-- __init__.py
|   |   +-- model.py             # State and data models (Pydantic)
|   +-- prompt/
|   |   +-- __init__.py
|   |   +-- prompt.py            # System prompts for all phases
|   +-- service/
|   |   +-- __init__.py
|   |   +-- generation_service.py # LLM generation logic
|   |   +-- runner_service.py     # Pipeline orchestration and rollback
|   |   +-- helper.py             # UI helpers and file I/O
|   +-- __init__.py
|   +-- config.py                 # Environment configuration
|   +-- logger.py                 # Logging setup
|   +-- main.py                   # CLI entry point
+-- outputs/                       # Generated articles (auto-created)
+-- .envrc.example                 # Environment variables template
+-- pyproject.toml                 # Project dependencies
+-- Makefile                       # Development commands
+-- README.md                      # User documentation
+-- CLAUDE.md                      # This file
```

## Key Components

### State Model (`src/model/model.py`)

The `ParallelWorldState` TypedDict uses `total=False` to make phase-specific fields optional:

```python
class ParallelWorldState(TypedDict, total=False):
    # Required: Pipeline configuration
    theme: str
    language: Literal["en", "ja"]
    llm_provider: str
    model: str
    num_outline_variants: int
    num_second_half_variants: int

    # Optional: Phase-specific state (presence indicates completion)
    outline_sessions: list[ParallelSession]           # Phase 1
    selected_outline_session_id: str | None           # Phase 2
    first_half_session: ParallelSession | None        # Phase 3
    second_half_sessions: list[ParallelSession]       # Phase 4
    reviewed_sessions: list[ParallelSession]          # Phase 5
    final_selected_session_id: str | None             # Phase 6
    human_approved: bool | None                       # Phase 7
```

### Pydantic Models

- `ArticleOutline`: Title, summary, structure (3-10 sections)
- `ArticleHalf`: Content with reasoning
- `ArticleReview`: Grade (1-5), strengths, weaknesses
- `BestArticleSelection`: Selection decision with reasoning
- `ParallelSession`: Session tracking with all variants
- `CompletedArticle`: Final article with all components

### Phase Detection (`src/service/runner_service.py`)

```python
def get_current_phase(state: ParallelWorldState) -> int:
    if state.get("human_approved") is not None:
        return 7
    elif state.get("final_selected_session_id") is not None:
        return 6
    elif state.get("reviewed_sessions"):
        return 5
    # ... continues checking earlier phases
    else:
        return 0
```

### Rollback Implementation (`src/service/runner_service.py`)

```python
def forget_phases_after(state: ParallelWorldState, target_phase: int) -> ParallelWorldState:
    if target_phase < 7:
        state.pop("human_approved", None)
        state.pop("rejected_session_ids", None)
        state.pop("review_loop_iteration", None)
    if target_phase < 6:
        state.pop("final_selected_session_id", None)
    # ... continues for all phases
    state.pop("error", None)
    return state
```

## Dependencies

Core dependencies:
- `click>=8.3.0`: CLI framework
- `google-genai>=1.45.0`: Google Gemini integration
- `openai>=2.4.0`: OpenAI API (reserved for future use)
- `pydantic>=2.12.2`: Data validation and structured outputs
- `python-dotenv>=1.1.1`: Environment configuration

Development dependencies:
- `pytest>=8.4.2`: Testing framework
- `pytest-asyncio>=1.2.0`: Async test support
- `pytest-mock>=3.15.1`: Mocking utilities

## Usage

### Setup

1. Create environment file:
```bash
cp .envrc.example .envrc
```

2. Configure API key:
```bash
# .envrc
export GEMINI_API_KEY="your-gemini-api-key-here"
```

3. Install dependencies:
```bash
uv sync
```

### Run

**Interactive mode** (with rollback options):
```bash
uv run python -m src.main \
  --theme "The Future of AI" \
  --language en \
  --model gemini-2.5-flash
```

**Auto-select mode** (no user prompts):
```bash
uv run python -m src.main \
  --theme "Quantum Computing" \
  --language ja \
  --model gemini-2.5-flash \
  --auto-select
```

**With custom variants**:
```bash
uv run python -m src.main \
  --theme "Space Exploration" \
  --language ja \
  --model gemini-2.5-pro \
  --num-outline-variants 5 \
  --num-second-half-variants 5
```

### CLI Options

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--theme` | `-t` | Yes | - | Article theme/topic |
| `--language` | `-l` | Yes | - | Language (`en` or `ja`) |
| `--model` | `-m` | Yes | - | Gemini model name |
| `--output-directory` | `-od` | No | `outputs` | Output directory |
| `--num-outline-variants` | `-no` | No | `3` | Number of outline variants |
| `--num-second-half-variants` | `-ns` | No | `3` | Number of second half variants |
| `--auto-select` | `-a` | No | `False` | Auto-select mode flag |

Available models:
- `gemini-2.5-pro`
- `gemini-2.5-flash`
- `gemini-2.5-flash-lite`

## Development Commands

```bash
# Lint and format code
make fix

# Lint only
make lint

# Format only
make fmt

# Type checking
make mypy
```

## Implementation Notes

### Parallel Generation

Uses `asyncio.gather()` for concurrent variant generation:

```python
tasks = [
    generate_outline(theme, language, model, provider)
    for _ in range(num_outline_variants)
]
outlines = await asyncio.gather(*tasks)
```

### LLM-as-a-Judge

Articles are graded on a 1-5 scale with detailed feedback:
- **5 (Excellent)**: Outstanding, exceeds expectations
- **4 (Good)**: High-quality with minor improvements possible
- **3 (Acceptable)**: Adequate but with noticeable gaps
- **2 (Poor)**: Significant issues
- **1 (Very Poor)**: Fails basic quality standards

Auto-select mode approves articles with grade >= 4.

### Human-in-the-Loop Decision Points

1. **Outline Selection** (Phase 2): Choose from generated outlines
2. **Rollback Option** (After Phase 3): Continue or roll back
3. **Article Selection** (Phase 6): Choose best reviewed article
4. **Approval Decision** (Phase 7): Approve or reject with regeneration
5. **Rollback Option** (After Phase 7): Continue or roll back

### Output Files

```
outputs/
+-- parallel_world_article_{session_id}/
    +-- parallel_world_article_{session_id}.json
    +-- parallel_world_article_{session_id}.md
    +-- all_variants/
        +-- variant_1_grade_5.md
        +-- variant_2_grade_4.md
        +-- variant_3_grade_3.md
```

### Error Handling

Errors are tracked in state and checked at each phase:
```python
if state.get("error"):
    return None
```

### Feedback Loop

When an article is rejected, the system:
1. Tracks the rejected session ID
2. Regenerates second halves with feedback from previous attempts
3. Re-reviews all new variants
4. Repeats up to 5 iterations maximum

## Key Takeaways

1. **State-based rollback** eliminates complex checkpoint management
2. **Forgetting by deletion** prevents context contamination
3. **Phase detection** enables resumption from any point
4. **Human-in-the-loop** at critical junctures improves quality
5. **Parallel world pattern** generates variants for better selection
6. **LLM-as-a-Judge** automates consistent quality evaluation
7. **Feedback loops** enable iterative improvement
8. **Type-safe structured outputs** ensure reliability

## Extending the System

### Adding New Phases

1. Add state variable in `ParallelWorldState`
2. Update `get_current_phase()` to check the new variable
3. Update `forget_phases_after()` to handle rollback
4. Implement phase logic in runner service
5. Add conditional execution in main loop

### Adding New LLM Providers

1. Add provider enum to `LLMProvider`
2. Add model enum (e.g., `ClaudeModel`)
3. Implement `_generate_with_provider()` helper in generation_service.py
4. Update CLI to accept new provider/model combinations

### Custom Review Criteria

Modify prompts in `src/prompt/prompt.py`:
- `make_article_review_system_instruction()` for review criteria
- Grading scale and evaluation weights
- Feedback format and detail level
