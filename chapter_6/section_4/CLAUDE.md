# Chapter 6 Section 4: Forgetting Unnecessary Past - State-Based Rollback Pattern

## Overview

This project demonstrates the **"Forgetting Unnecessary Past"** pattern for LLM applications through a state-based rollback mechanism. Users can roll back to any previous phase of a multi-step pipeline, effectively "forgetting" contaminated context and regenerating content with fresh state.

The implementation is an article generation pipeline that:
- Generates content step by step (outline -> first half -> second half)
- Uses LLM-as-a-Judge for automated quality evaluation
- Provides Human-in-the-Loop decision points with rollback capabilities
- Implements the Memento pattern for state snapshot management

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
|  Outline    |---->|  First Half |---->|  Second Half|---->|   Review    |
|  Generation |     |  Generation |     |  Generation |     | (LLM Judge) |
+-------------+     +------+------+     +-------------+     +------+------+
                           |                                       |
                           v                                       v
                    +-----------+                           +-------------+
                    | Rollback  |                           |  Phase 5    |
                    | Point #1  |                           |  Approval   |
                    +-----------+                           |  Decision   |
                                                            +------+------+
                                                                   |
                                                            +-----------+
                                                            | Rollback  |
                                                            | Point #2  |
                                                            +-----------+
                                                                   |
                                                                   v (if rejected)
                                                            +-------------+
                                                            | Regenerate  |
                                                            | with        |
                                                            | Feedback    |
                                                            +-------------+
```

### Agent Architecture

```
+----------------------+
|      Mediator        |  Pipeline orchestration
| (ArticlePipeline     |
|      Mediator)       |
+----------+-----------+
           |
    +------+------+------+------+------+
    |      |      |      |      |      |
    v      v      v      v      v      v
+------+ +------+ +------+ +------+ +------+
| Node | | Node | | Node | | Node | | Node |
|Outln | |First | |Second| |Review| |Regen |
| Gen  | |Half  | |Half  | |      | |      |
+--+---+ +--+---+ +--+---+ +--+---+ +--+---+
   |        |        |        |        |
   v        v        v        v        v
+--------------------------------------------------+
|              GenerationToolBox                   |
+--------------------------------------------------+
| OutlineGenerator    | FirstHalfGenerator         |
| SecondHalfGenerator | ArticleReviewer            |
| SecondHalfRegenerator                            |
+--------------------------------------------------+
                      |
                      v
              +---------------+
              |  Gemini API   |
              +---------------+
```

### Memento Pattern for State Management

```
+-------------------+        +--------------------+
|    Originator     |        |     Caretaker      |
| (PipelineMemory)  |<------>| (MemoryCaretaker)  |
+---------+---------+        +--------------------+
          |                            |
          v                            v
     +---------+                 +-----------+
     |  State  |                 | Snapshots |
     +---------+                 +-----------+
          |                      | Phase 0   |
          |                      | Phase 1   |
     Phase variable              | Phase 2   |
     presence indicates          | ...       |
     completion                  +-----------+
```

### Directory Structure

```
chapter_6/section_4/
+-- src/
|   +-- agent/
|   |   +-- core/                    # Core abstractions (stable interfaces)
|   |   |   +-- __init__.py
|   |   |   +-- base.py              # Tool, Strategy, Action, ToolResult
|   |   |   +-- memory.py            # Memory abstract class, MemorySnapshot
|   |   |   +-- mediator.py          # Node base class, NodeResult, NodeType
|   |   |   +-- controller.py        # Agent controller
|   |   |   +-- agent.py             # Agent implementation
|   |   |   +-- states.py            # State management
|   |   |   +-- toolbox.py           # Toolbox base
|   |   +-- extensions/              # Concrete implementations
|   |       +-- mediators/
|   |       |   +-- article_pipeline.py  # ArticlePipelineMediator
|   |       |   +-- simple.py            # Simple mediator
|   |       |   +-- parallel.py          # Parallel mediator
|   |       +-- memory/
|   |       |   +-- pipeline.py          # PipelineMemory, PipelineMemoryCaretaker
|   |       |   +-- context.py           # Context memory
|   |       |   +-- conversational.py    # Conversational memory
|   |       |   +-- caretaker.py         # Caretaker implementation
|   |       +-- nodes/
|   |       |   +-- pipeline.py          # PipelineState, generation nodes
|   |       |   +-- agent_node.py        # Agent node
|   |       |   +-- decision_node.py     # Decision node
|   |       |   +-- aggregator_node.py   # Aggregator node
|   |       +-- tools/
|   |       |   +-- generation.py        # LLM generation tools
|   |       |   +-- calculator.py        # Calculator tool
|   |       |   +-- text_generator.py    # Text generator tool
|   |       |   +-- web_search.py        # Web search tool
|   |       +-- strategies/              # Agent strategies
|   |       +-- handlers/                # Safety handlers
|   |       +-- agents/                  # Agent implementations
|   |       +-- factory.py               # Factory utilities
|   +-- client/
|   |   +-- llm_client.py            # Gemini client, LLMProvider, GeminiModel
|   +-- model/
|   |   +-- model.py                 # Pydantic models (ArticleOutline, etc.)
|   +-- prompt/
|   |   +-- prompt.py                # System prompts for all phases
|   +-- service/
|   |   +-- runner_service.py        # Pipeline entry point
|   |   +-- helper.py                # UI helpers, file I/O, user interaction
|   +-- config.py                    # Environment configuration
|   +-- logger.py                    # Logging setup
|   +-- main.py                      # CLI entry point
+-- outputs/                         # Generated articles (auto-created)
+-- .envrc.example                   # Environment variables template
+-- pyproject.toml                   # Project dependencies
+-- Makefile                         # Development commands
+-- README.md                        # User documentation (Japanese)
+-- CLAUDE.md                        # This file
```

## Key Components

### State Model (`src/agent/extensions/nodes/pipeline.py`)

The `PipelineState` dataclass tracks phase completion through optional fields:

```python
@dataclass
class PipelineState:
    theme: str
    language: Literal["en", "ja"]
    llm_provider: LLMProvider
    model: str

    # Phase 1: Outline generation
    outline: ArticleOutline | None = None

    # Phase 2: First half generation
    first_half: str | None = None

    # Phase 3: Second half generation
    second_half: str | None = None

    # Phase 4: Review
    review: ArticleReview | None = None

    # Phase 5: Human approval
    human_approved: bool | None = None

    # Regeneration tracking
    review_loop_iteration: int = 0
    previous_feedback: list[tuple[str, ArticleReview]] | None = None

    # Error tracking
    error: str | None = None
```

### Pydantic Models (`src/model/model.py`)

- `ArticleOutline`: Title, summary, structure (3-10 sections)
- `ArticleHalf`: Content with reasoning
- `ArticleReview`: Grade (1-5), strengths, weaknesses
- `CompletedArticle`: Final article with all components

### Phase Detection (`src/agent/extensions/memory/pipeline.py`)

```python
def get_current_phase(self) -> int:
    if self._state.human_approved is not None:
        return 5
    elif self._state.review is not None:
        return 4
    elif self._state.second_half is not None:
        return 3
    elif self._state.first_half is not None:
        return 2
    elif self._state.outline is not None:
        return 1
    else:
        return 0
```

### Rollback Implementation (`src/agent/extensions/memory/pipeline.py`)

```python
def forget_phases_after(self, target_phase: int) -> None:
    if target_phase < 5:
        self._state.human_approved = None
        self._state.review_loop_iteration = 0
        self._state.previous_feedback = None
    if target_phase < 4:
        self._state.review = None
    if target_phase < 3:
        self._state.second_half = None
    if target_phase < 2:
        self._state.first_half = None
    if target_phase < 1:
        self._state.outline = None
    self._state.error = None
```

### Generation Tools (`src/agent/extensions/tools/generation.py`)

- `OutlineGeneratorTool`: Generate article outline
- `FirstHalfGeneratorTool`: Generate first half of article
- `SecondHalfGeneratorTool`: Generate second half of article
- `ArticleReviewerTool`: LLM-as-a-Judge evaluation
- `SecondHalfRegeneratorTool`: Regenerate with feedback
- `GenerationToolBox`: Container for all generation tools

### Pipeline Nodes (`src/agent/extensions/nodes/pipeline.py`)

- `OutlineGenerationNode`: Generate single outline
- `FirstHalfGenerationNode`: Generate single first half
- `SecondHalfGenerationNode`: Generate single second half
- `ArticleReviewNode`: LLM-as-a-Judge review
- `SecondHalfRegenerationNode`: Feedback-based regeneration
- `HumanDecisionNode`: User interaction handler

### Pipeline Mediator (`src/agent/extensions/mediators/article_pipeline.py`)

The `ArticlePipelineMediator` orchestrates:
- Phase execution and tracking
- Rollback option handling
- Review loop management (max 5 iterations)
- Final article saving

## Dependencies

Core dependencies:
- `click>=8.3.0`: CLI framework
- `google-genai>=1.45.0`: Google Gemini integration
- `anthropic>=0.74.1`: Anthropic API (future use)
- `openai>=2.4.0`: OpenAI API (future use)
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

### CLI Options

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--theme` | `-t` | Yes | - | Article theme/topic |
| `--language` | `-l` | Yes | - | Language (`en` or `ja`) |
| `--model` | `-m` | Yes | - | Gemini model name |
| `--output-directory` | `-od` | No | `outputs` | Output directory |
| `--auto-select` | `-a` | No | `False` | Auto-select mode flag |

Available models:
- `gemini-2.5-pro`
- `gemini-2.5-flash`
- `gemini-2.5-flash-lite`

## Development Commands

```bash
# Lint and format code
make fix

# Lint only (ruff check with isort)
make lint

# Format only (ruff format)
make fmt

# Type checking
make mypy
```

## Implementation Notes

### LLM-as-a-Judge

Articles are graded on a 1-5 scale with detailed feedback:

| Grade | Level | Description |
|-------|-------|-------------|
| 5 | Excellent | Outstanding, exceeds expectations |
| 4 | Good | High-quality with minor improvements possible |
| 3 | Acceptable | Adequate but with noticeable gaps |
| 2 | Poor | Significant issues |
| 1 | Very Poor | Fails basic quality standards |

Evaluation criteria with weights:
- Content Quality (30%): Accuracy, informativeness, value
- Structure & Flow (25%): Outline adherence, logical flow
- Writing Quality (20%): Clarity, engagement
- Completeness (15%): Theme and section coverage
- Language Quality (10%): Appropriateness, consistency

Auto-select mode approves articles with grade >= 4.

### Human-in-the-Loop Decision Points

1. **Rollback Option** (After Phase 2): Continue or roll back to regenerate
2. **Approval Decision** (Phase 5): Approve or reject with regeneration
3. **Rollback Option** (After Phase 5): Continue or roll back to any previous phase

### Output Files

```
outputs/
+-- article_{session_id}/
    +-- article_{session_id}.json
    +-- article_{session_id}.md
```

### Error Handling

Errors are tracked in state and checked at each phase:
```python
if state.error:
    return self._error_result()
```

### Feedback Loop

When an article is rejected, the system:
1. Stores the rejected second half and its review in `previous_feedback`
2. Regenerates the second half with feedback from previous attempts
3. Re-reviews the new content
4. Repeats up to 5 iterations maximum (`max_iterations`)

## Key Takeaways

1. **State-based rollback** eliminates complex checkpoint management
2. **Forgetting by deletion** prevents context contamination
3. **Phase detection** enables resumption from any point
4. **Human-in-the-loop** at critical junctures improves quality
5. **LLM-as-a-Judge** automates consistent quality evaluation
6. **Feedback loops** enable iterative improvement
7. **Type-safe structured outputs** ensure reliability
8. **Memento pattern** provides robust snapshot management
9. **Modular agent architecture** enables extensibility

## Extending the System

### Adding New Phases

1. Add state variable in `PipelineState`
2. Update `get_current_phase()` to check the new variable
3. Update `forget_phases_after()` to handle rollback
4. Create a new Node class in `src/agent/extensions/nodes/`
5. Add execution logic in `ArticlePipelineMediator`
6. Add conditional execution in main loop

### Adding New LLM Providers

1. Add provider enum to `LLMProvider` in `src/client/llm_client.py`
2. Add model enum (e.g., `ClaudeModel`)
3. Implement `_generate_with_provider()` helper in `generation.py`
4. Update CLI to accept new provider/model combinations

### Adding New Tools

1. Create tool class extending `Tool` in `src/agent/extensions/tools/`
2. Implement `execute()` and/or `execute_async()` methods
3. Add to appropriate toolbox or create new toolbox

### Custom Review Criteria

Modify prompts in `src/prompt/prompt.py`:
- `make_article_review_system_instruction()` for review criteria
- Grading scale and evaluation weights
- Feedback format and detail level
