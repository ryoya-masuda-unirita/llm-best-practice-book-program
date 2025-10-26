# Chapter 4, Section 5: Forgetting Unnecessary Past - State-Based Rollback Pattern

## Overview

This project demonstrates the **"Forgetting Unnecessary Past"** pattern for LLM applications through a practical implementation of a state-based rollback mechanism. The system allows users to roll back to any previous phase of a multi-step pipeline, effectively "forgetting" contaminated context and regenerating content with fresh, clean state.

The implementation showcases a parallel world article generation pipeline that creates multiple content variants in parallel, uses LLM-as-a-Judge for evaluation, and provides human-in-the-loop decision points with rollback capabilities at critical junctures.

## Architecture

### Core Design Principles

1. **State as Memory**: The state object itself serves as the pipeline's memory. The presence or absence of state variables indicates which phases have been completed.

2. **Forgetting by Deletion**: Rolling back is implemented by simply deleting state variables that represent later phases, causing the pipeline to regenerate them from scratch.

3. **Idempotent Phases**: Each phase checks whether its work has already been completed before executing, allowing the pipeline to resume from any point.

4. **Human-in-the-Loop Integration**: Critical decision points allow users to intervene, review progress, and decide whether to continue or roll back to a previous state.

### State Management Model

The `ParallelWorldState` TypedDict (defined in `src/model/parallel_world_model.py:237-283`) uses `total=False` to make phase-specific fields optional:

```python
class ParallelWorldState(TypedDict, total=False):
    # Required: Pipeline configuration (always present)
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

## Pipeline Phases

### Phase 0: Initial State
- Only configuration fields are populated
- Pipeline ready to begin execution

### Phase 1: Outline Generation
- Generates multiple article outlines in parallel (parallel world branching #1)
- Populates `outline_sessions` list
- Implementation: `src/service/generation_service.py:239-283`

### Phase 2: Outline Selection
- Human selects preferred outline (human-in-the-loop #1)
- Populates `selected_outline_session_id`
- Implementation: `src/service/runner_service.py:203-229`

### Phase 3: First Half Generation
- Generates first half of article based on selected outline
- Populates `first_half_session`
- **Rollback Point #1** offered after completion
- Implementation: `src/service/runner_service.py:232-257`

### Phase 4: Second Half Variants
- Generates multiple second half variants in parallel (parallel world branching #2)
- Populates `second_half_sessions` list
- Implementation: `src/service/generation_service.py:345-397`

### Phase 5: Article Review
- Reviews all complete articles using LLM-as-a-Judge
- Populates `reviewed_sessions` with graded articles
- Implementation: `src/service/generation_service.py:400-455`

### Phase 6: Article Selection
- Human selects final article from reviewed variants (human-in-the-loop #2)
- Populates `final_selected_session_id`
- Implementation: `src/service/runner_service.py:311-348`

### Phase 7: Approval Decision
- Human approves or rejects selected article (human-in-the-loop #3)
- Populates `human_approved` (True/False)
- If rejected, loops back to Phase 4 with feedback
- **Rollback Point #2** offered after approval
- Implementation: `src/service/runner_service.py:351-378`

### Phase 8: Regeneration (Conditional)
- Only triggered if Phase 7 rejected the article
- Regenerates second halves with feedback from previous attempts
- Loops back to Phase 5 for re-review
- Implementation: `src/service/runner_service.py:381-432`

### Phase 9: Finalization
- Saves selected article and all variants to disk
- Implementation: `src/service/runner_service.py:492-549`

## Key Implementation Details

### Phase Detection

The system automatically detects the current phase by checking which state variables are populated (reverse order from Phase 7 to 0):

```python
def get_current_phase(state: ParallelWorldState) -> int:
    """src/service/runner_service.py:50-77"""
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

### Rollback Implementation

The `forget_phases_after()` function implements the "forgetting" mechanism by removing state variables:

```python
def forget_phases_after(state: ParallelWorldState, target_phase: int) -> ParallelWorldState:
    """src/service/runner_service.py:95-151"""
    # Remove state variables for phases after target_phase
    if target_phase < 7:
        state.pop("human_approved", None)
        state.pop("rejected_session_ids", None)
        state.pop("review_loop_iteration", None)

    if target_phase < 6:
        state.pop("final_selected_session_id", None)

    # ... continues for all phases

    state.pop("error", None)  # Clear error state
    return state
```

**Key Points:**
- Uses `state.pop(key, None)` for safe deletion
- Clears error state during rollback
- User-friendly logging of what was forgotten
- Causes pipeline to regenerate deleted phases

### Pipeline Control Loop

The main execution loop uses conditional phase execution:

```python
async def run_parallel_world_article_generation(...) -> CompletedArticle | None:
    """src/service/runner_service.py:557-692"""

    # Initialize state with only required fields
    state: ParallelWorldState = {
        "theme": theme,
        "language": language,
        "llm_provider": llm_provider.value,
        "model": model,
        "num_outline_variants": num_outline_variants,
        "num_second_half_variants": num_second_half_variants,
    }

    while True:
        current_phase = get_current_phase(state)

        # Execute only incomplete phases
        if current_phase < 1:
            state = await generate_outlines(state)

        if current_phase < 2:
            state = await select_outline(state, auto_select)

        if current_phase < 3:
            state = await generate_first_half(state)

            # Offer rollback after Phase 3
            available_phases = get_available_rollback_phases(state)
            rollback_phase = get_rollback_choice(available_phases, auto_select)
            if rollback_phase is not None:
                state = forget_phases_after(state, rollback_phase)
                continue  # Restart loop to regenerate

        # ... continues for remaining phases

        if approved:
            break

    # Save final article
    save_article(state, final_completed_article, output_directory, iteration)
    return final_completed_article
```

**Features:**
- Completed phases are automatically skipped
- Rollback restarts the loop via `continue`
- State integrity maintained throughout
- No checkpoint objects needed

## LLM Integration

### Multi-Provider Support

The system supports multiple LLM providers through a unified interface:

- **OpenAI**: GPT-4o, GPT-4o-mini, GPT-4.1, GPT-5 series
- **Google Gemini**: Gemini 2.5 Pro, Flash, Flash-lite

Provider-specific implementations in `src/service/generation_service.py:34-64`:

```python
async def _generate_with_openai(prompt, response_format, model):
    """OpenAI structured output generation"""
    result = await openai_client.beta.chat.completions.parse(
        model=model,
        messages=prompt,
        response_format=response_format,
    )
    return result.choices[0].message.parsed

async def _generate_with_gemini(system_instruction, user_content, response_schema, model):
    """Gemini structured output generation"""
    result = await google_genai_client.aio.models.generate_content(
        model=model,
        contents=user_content,
        config=GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_schema,
        ),
    )
    return result.parsed
```

### Structured Output Models

All LLM responses use Pydantic models for type safety and validation:

- `ArticleOutline`: Article structure with title, summary, and sections
- `ArticleHalf`: Content with reasoning
- `ArticleReview`: LLM-as-a-Judge evaluation with grade (1-5), strengths, weaknesses
- `BestArticleSelection`: Selection decision with reasoning
- `ParallelSession`: Complete session tracking all variants
- `CompletedArticle`: Final article with all components

Defined in `src/model/parallel_world_model.py:11-235`

### Parallel Generation

The system uses `asyncio.gather()` for efficient parallel generation:

```python
# Generate multiple outlines in parallel
tasks = [
    generate_outline(theme, language, model, provider)
    for _ in range(num_outline_variants)
]
outlines = await asyncio.gather(*tasks)
```

Implementation locations:
- Outline generation: `src/service/generation_service.py:250-259`
- First half generation: `src/service/generation_service.py:303-312`
- Second half generation: `src/service/generation_service.py:360-370`
- Article review: `src/service/generation_service.py:409-425`

## User Interaction

### Interactive Mode

Prompts users at key decision points:

1. **Outline Selection** (Phase 2): Choose from generated outlines
2. **Rollback Option** (After Phase 3): Continue or roll back
3. **Article Selection** (Phase 6): Choose best reviewed article
4. **Approval Decision** (Phase 7): Approve or request regeneration
5. **Rollback Option** (After Phase 7): Continue or roll back

### Auto-Select Mode

For testing and automated workflows:
- Automatically selects first/best options
- Skips rollback prompts
- Auto-approves articles with grade >= 4
- Useful for CI/CD and batch processing

### User Interface Helpers

Located in `src/service/helper.py`:

- `display_outlines()`: Shows all outline variants
- `display_reviews()`: Shows reviewed articles with grades
- `get_rollback_choice()`: Prompts for rollback decision
- `get_outline_selection()`: Prompts for outline selection
- `get_final_article_selection()`: Prompts for article selection
- `get_human_approval()`: Prompts for approval/rejection
- `print_article_preview()`: Shows content preview
- `save_article_files()`: Saves all output files

## File Structure

```
chapter_4/section_5/
   src/
      client/
         llm_client.py           # LLM client initialization (OpenAI, Gemini)
      model/
         parallel_world_model.py # State and data models
      prompt/
         parallel_world_prompt.py # System prompts for all phases
      service/
         generation_service.py   # LLM generation logic
         runner_service.py       # Pipeline orchestration & rollback
         helper.py               # UI helpers and file I/O
      config.py                   # Configuration management
      logger.py                   # Logging setup
      main.py                     # CLI entry point
   outputs/                        # Generated articles (auto-created)
   .envrc.example                  # Environment variables template
   pyproject.toml                  # Project dependencies
   Makefile                        # Development commands
   README.md                       # User documentation
```

## Usage

### Setup

1. Create `.envrc` from template:
```bash
cp .envrc.example .envrc
```

2. Configure API keys in `.envrc`:
```bash
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="AIzaSy..."
```

3. Install dependencies:
```bash
uv sync
```

### Running the Pipeline

**Interactive mode** (with rollback options):
```bash
uv run python -m src.main \
  --theme "The Future of AI" \
  --language en \
  --llm-provider gemini \
  --model gemini-2.5-flash
```

**Auto-select mode** (no user prompts):
```bash
uv run python -m src.main \
  --theme "Quantum Computing" \
  --language en \
  --llm-provider openai \
  --model gpt-4o \
  --auto-select
```

**With custom variants**:
```bash
uv run python -m src.main \
  --theme "Space Exploration" \
  --language ja \
  --llm-provider gemini \
  --model gemini-2.5-flash \
  --num-outline-variants 5 \
  --num-second-half-variants 5
```

### CLI Options

- `--theme, -t`: Article topic (required)
- `--language, -l`: Target language (`en` or `ja`) (required)
- `--llm-provider, -lp`: LLM provider (`openai` or `gemini`) (required)
- `--model, -m`: Model name (required, must match provider)
- `--output-directory, -od`: Output directory (default: `outputs`)
- `--num-outline-variants, -no`: Number of outline variants (default: 3)
- `--num-second-half-variants, -ns`: Number of second half variants (default: 3)
- `--auto-select, -a`: Enable auto-select mode (flag)

### Output Files

Generated files are organized in a session-specific directory:

```
outputs/
   parallel_world_article_{session_id}/
       parallel_world_article_{session_id}.json  # Selected article (JSON)
       parallel_world_article_{session_id}.md    # Selected article (Markdown)
       all_variants/
           variant_1_grade_5.md
           variant_2_grade_4.md
           variant_3_grade_3.md
```

**JSON format** includes:
- Session ID and timestamps
- Complete outline with structure
- First and second half content
- Review with grade, strengths, weaknesses
- Language and metadata

**Markdown format** includes:
- Complete article text
- Review section with grade and feedback

## Development

### Code Quality

```bash
# Lint and format code
make fix

# Type checking
make mypy
```

### Dependencies

Core dependencies (defined in `pyproject.toml:7-13`):
- `click>=8.3.0`: CLI framework
- `google-genai>=1.45.0`: Google Gemini integration
- `openai>=2.4.0`: OpenAI integration
- `pydantic>=2.12.2`: Data validation
- `python-dotenv>=1.1.1`: Environment configuration

Development dependencies:
- `pytest>=8.4.2`: Testing framework
- `pytest-asyncio>=1.2.0`: Async test support
- `pytest-mock>=3.15.1`: Mocking utilities

## Best Practices Demonstrated

### 1. State as Memory
Instead of maintaining separate checkpoint objects, the state itself indicates completion status through field presence. This is self-documenting and memory-efficient.

### 2. Forgetting by Deletion
Rolling back is as simple as deleting state variables. The pipeline logic handles the rest automatically.

### 3. Conditional Execution
Each phase checks completion status before executing:
```python
if current_phase < N:
    state = await execute_phase_N(state)
```

### 4. Error Handling
Errors are tracked in state and checked at each phase:
```python
if state.get("error"):
    return None
```

### 5. Parallel Efficiency
Multiple variants are generated concurrently using async/await and `asyncio.gather()`.

### 6. Type Safety
Pydantic models ensure LLM outputs conform to expected schemas, catching errors early.

### 7. Provider Abstraction
Unified interface for multiple LLM providers allows easy switching without code changes.

### 8. Human-in-the-Loop
Strategic decision points allow human expertise to guide the pipeline while maintaining automation.

### 9. Review Loop
Automatic regeneration with feedback improves quality over iterations.

### 10. Comprehensive Logging
Detailed logs at each phase aid debugging and monitoring.

## Key Takeaways

1. **State-based rollback** eliminates the need for complex checkpoint management systems
2. **Forgetting unnecessary past** prevents context contamination from propagating
3. **Phase detection** enables resumption from any point without manual intervention
4. **Human-in-the-loop integration** at critical junctures improves output quality
5. **Parallel world pattern** generates multiple variants for better selection
6. **LLM-as-a-Judge** automates quality evaluation consistently
7. **Feedback loops** enable iterative improvement without starting over
8. **Type-safe structured outputs** ensure reliability in production systems

## Extending the System

### Adding New Phases

1. Define new state variable in `ParallelWorldState`
2. Update `get_current_phase()` to check the new variable
3. Update `forget_phases_after()` to handle rollback
4. Implement phase logic in runner service
5. Add conditional execution in main loop

### Supporting Additional LLM Providers

1. Add provider enum to `LLMProvider`
2. Add model enum (e.g., `ClaudeModel`)
3. Implement `_generate_with_provider()` helper
4. Update generation functions to support new provider
5. Update CLI validation

### Custom Review Criteria

Modify prompts in `src/prompt/parallel_world_prompt.py` to customize:
- Review rubrics
- Grading scales
- Evaluation criteria
- Feedback format

### Alternative Output Formats

Extend `CompletedArticle` model with new save methods:
- `save_as_html()`
- `save_as_pdf()`
- `save_as_docx()`

## References

- Project README: `README.md`
- State model definition: `src/model/parallel_world_model.py:237-283`
- Pipeline orchestration: `src/service/runner_service.py:557-692`
- Rollback implementation: `src/service/runner_service.py:95-151`
- Phase detection: `src/service/runner_service.py:50-77`
- Generation logic: `src/service/generation_service.py`
- CLI interface: `src/main.py`