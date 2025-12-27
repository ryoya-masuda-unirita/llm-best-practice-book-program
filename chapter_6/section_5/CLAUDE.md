# Parallel World Pattern Article Generation System

## Overview

This project implements an AI agent article generation system utilizing the **Parallel World Pattern**. It combines multiple parallel LLM sessions with Human-in-the-Loop decision-making and LLM-as-a-Judge evaluation to generate high-quality article content.

The Parallel World Pattern is a workflow technique in AI agent systems where multiple different execution paths (parallel worlds) are generated simultaneously, and the optimal result is selected from among them. This approach ensures content diversity while maintaining quality and controllability through strategic human intervention at key decision points.

**Key Features**:
- **Parallel World Article Generation**: Generate multiple article variations simultaneously
- **Human-in-the-Loop**: User intervention at critical decision points
- **LLM-as-a-Judge**: Automated article quality evaluation and review
- **Feedback Loop**: Regeneration based on feedback from rejected articles
- **Bilingual Support**: Generate articles in English or Japanese

## Architecture

```
+------------------------------------------------------------------------------+
|                           CLI Layer (main.py)                                |
|   - Command-line argument parsing                                            |
|   - User input and interaction                                               |
|   - Output directory management                                              |
+----------------------------------+-------------------------------------------+
                                   |
                                   v
+----------------------------------+-------------------------------------------+
|                 Orchestration Layer (runner_service.py)                      |
|   - Workflow phase management                                                |
|   - Human-in-the-Loop control                                                |
|   - Review loop orchestration                                                |
|   - File saving and output management                                        |
+----------------------------------+-------------------------------------------+
                                   |
                                   v
+----------------------------------+-------------------------------------------+
|             AI Agent Pipeline Layer (generation_service.py)                  |
|   - LLM generation functions (outline, halves, review)                       |
|   - Pipeline nodes (parallel generation, review, regeneration)               |
|   - Parallel World branching and merging logic                               |
+----------------------------------+-------------------------------------------+
                                   |
                                   v
+------------------------------------------------------------------------------+
|                         Infrastructure Layer                                 |
|   - LLM clients (llm_client.py)                                              |
|   - Prompt generation (prompt.py)                                            |
|   - Data models (model.py)                                                   |
|   - Configuration (config.py)                                                |
|   - Logging (logger.py)                                                      |
+------------------------------------------------------------------------------+
```

### Workflow Phases

The system orchestrates a 9-phase pipeline:

```
START
  |
  v
Phase 1: Generate Multiple Outlines (Parallel World Branching #1)
  |
  v
Phase 2: User Selects Outline (Human-in-the-Loop #1)
  |
  v
Phase 3: Generate First Half of Article
  |
  v
Phase 4: Generate Multiple Second Halves (Parallel World Branching #2)
  |
  v
Phase 5: Review All Articles with LLM-as-a-Judge
  |
  v
Phase 6: User Selects Final Article (Human-in-the-Loop #2)
  |
  v
Phase 7: User Approves or Rejects (Human-in-the-Loop #3)
  |
  +--[Approved]--> Phase 9: Save Article --> END
  |
  +--[Rejected]--> Phase 8: Regenerate with Feedback --> Loop to Phase 5
```

### Directory Structure

```
chapter_6/section_5/
|-- src/
|   |-- __init__.py              # Package initialization
|   |-- config.py                # Configuration management (API keys)
|   |-- logger.py                # Logging configuration
|   |-- main.py                  # Main entry point (CLI commands)
|   |-- client/
|   |   |-- __init__.py
|   |   +-- llm_client.py        # LLM client initialization (OpenAI)
|   |-- model/
|   |   |-- __init__.py
|   |   +-- model.py             # Pydantic data model definitions
|   |-- prompt/
|   |   |-- __init__.py
|   |   +-- prompt.py            # Prompt generation logic
|   +-- service/
|       |-- __init__.py
|       |-- generation_service.py # LLM generation and pipeline nodes
|       |-- helper.py            # UI display and file saving helpers
|       +-- runner_service.py    # Workflow orchestration
|-- outputs/                     # Generated results (auto-created)
|   +-- parallel_world_article_<uuid>/
|       |-- parallel_world_article_<uuid>.json  # Selected article (JSON)
|       |-- parallel_world_article_<uuid>.md    # Selected article (Markdown)
|       +-- all_variants/        # All candidate variants
|           |-- variant_1_grade_5.md
|           |-- variant_2_grade_4.md
|           +-- variant_3_grade_3.md
|-- pyproject.toml               # Project dependencies
|-- Makefile                     # Development commands
|-- .envrc.example               # Environment variables sample
|-- README.md                    # Project documentation (Japanese)
+-- CLAUDE.md                    # This file
```

## Key Components

### Data Models (src/model/model.py)

| Model | Description |
|-------|-------------|
| `ArticleOutline` | Article outline with title, summary, and section structure |
| `ArticleHalf` | First or second half of article content |
| `BestArticleSelection` | Selection result when choosing best variant |
| `ArticleReview` | LLM-as-a-Judge review with grade and feedback |
| `CompletedArticle` | Complete article with all components |
| `ParallelSession` | Single parallel world session state |
| `ParallelWorldState` | TypedDict for entire pipeline state |

### Generation Service (src/service/generation_service.py)

**LLM Generation Functions**:
- `generate_outline()` - Generate article outline
- `generate_first_half()` - Generate first half of article
- `choose_best_first_half()` - Select best first half from candidates
- `generate_second_half()` - Generate second half of article
- `review_article()` - Review article with LLM-as-a-Judge
- `regenerate_second_half()` - Regenerate with feedback

**Pipeline Nodes**:
- `generate_multiple_outlines_node()` - Parallel outline generation
- `generate_first_half_node()` - First half generation with selection
- `generate_multiple_second_halves_node()` - Parallel second half generation
- `review_all_articles_node()` - Parallel article review
- `regenerate_second_halves_after_rejection_node()` - Feedback-based regeneration

### Runner Service (src/service/runner_service.py)

Orchestrates workflow phases:
- `generate_outlines()` - Phase 1
- `select_outline()` - Phase 2
- `generate_first_half()` - Phase 3
- `generate_second_halves()` - Phase 4
- `review_articles()` - Phase 5
- `review_loop()` - Phases 6-8 (selection, approval, regeneration loop)
- `save_article()` - Phase 9

### Helper Functions (src/service/helper.py)

- `display_outlines()` - Display outline variants to user
- `display_reviews()` - Display reviewed articles with grades
- `get_outline_selection()` - Get user outline selection
- `get_final_article_selection()` - Get user final article selection
- `get_human_approval()` - Get user approval/rejection
- `save_article_files()` - Save article to JSON and Markdown

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| click | >=8.3.0 | CLI framework |
| openai | >=2.4.0 | OpenAI API client |
| pydantic | >=2.12.2 | Data validation and models |
| python-dotenv | >=1.1.1 | Environment variable loading |
| google-genai | >=1.45.0 | Google Gemini API (optional) |

**Dev Dependencies**:
| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=8.4.2 | Testing framework |
| pytest-asyncio | >=1.2.0 | Async test support |
| pytest-mock | >=3.15.1 | Mocking utilities |

## Usage

### Setup

1. **Create environment variables file**

```bash
cat > .envrc << EOF
export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
EOF

# If using direnv
direnv allow

# Or manually export
source .envrc
```

2. **Install dependencies**

```bash
# Using uv (recommended)
uv sync

# Using pip
pip install -e .
```

### Run

#### Basic Usage

```bash
# English article
uv run python -m src.main \
  --theme "The Future of Artificial Intelligence" \
  --language en \
  --model gpt-4o

# Japanese article
uv run python -m src.main \
  --theme "AI no Mirai" \
  --language ja \
  --model gpt-4o
```

#### Advanced Configuration

```bash
uv run python -m src.main \
  -t "Quantum Computing Breakthrough" \
  -l en \
  -m gpt-4o \
  -od ./my_articles \
  -no 5 \
  -ns 4
```

#### Auto Mode (No Human Interaction)

```bash
uv run python -m src.main \
  -t "Climate Change Solutions" \
  -l en \
  -m gpt-4o \
  -a
```

### CLI Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--theme` | `-t` | TEXT | Required | Article theme/topic |
| `--language` | `-l` | en/ja | Required | Article language |
| `--model` | `-m` | Choice | Required | OpenAI model to use |
| `--output-directory` | `-od` | PATH | outputs | Output directory |
| `--num-outline-variants` | `-no` | INT | 3 | Number of outline variants |
| `--num-second-half-variants` | `-ns` | INT | 3 | Number of second half variants |
| `--auto-select` | `-a` | FLAG | False | Auto-select without human input |

**Available Models**: gpt-5, gpt-5-mini, gpt-5-nano, gpt-4.1, gpt-4.1-mini, gpt-4.1-nano, gpt-4o, gpt-4o-mini

## Development Commands

```bash
# Run the CLI
uv run python -m src.main --help

# Run tests
uv run pytest

# Sync dependencies
uv sync

# Install dev dependencies
uv sync --group dev

# Lint code
make lint

# Format code
make fmt

# Lint and format
make fix

# Type check
make mypy
```

## Implementation Notes

### Parallel World Pattern

**Branching Points**:
- Phase 1: Generate N outline variants in parallel using `asyncio.gather()`
- Phase 4: Generate N second half variants in parallel

**Selection Points**:
- Phase 2: User selects preferred outline
- Phase 6: User selects final article from reviewed candidates

**Feedback Loop**:
- Phase 7-8: If rejected, collect feedback from reviews and regenerate

### LLM-as-a-Judge Evaluation Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Content Quality | 30% | Accuracy, informativeness, value |
| Structure & Flow | 25% | Adherence to outline, logical flow |
| Writing Quality | 20% | Clarity, engagement, craftsmanship |
| Completeness | 15% | Coverage of theme and sections |
| Language Quality | 10% | Appropriateness, consistency |

**Grading Scale**:
- 5 (Excellent): Outstanding, exceeds expectations
- 4 (Good): High quality with minor improvements needed
- 3 (Acceptable): Adequate but with noticeable gaps
- 2 (Poor): Significant issues
- 1 (Very Poor): Fails basic standards

### Auto-Select Mode Behavior

When `--auto-select` is enabled:
- Phase 2: Auto-selects first outline variant
- Phase 6: Auto-selects highest graded article
- Phase 7: Auto-approves if grade >= 4, auto-rejects otherwise

### State Management

The pipeline uses explicit state management with `ParallelWorldState` TypedDict:
- Each phase receives state and returns updated state
- Immutable updates: `{**state, "key": value}`
- Error states tracked in `state["error"]`
- Maximum 5 iterations for review loop to prevent infinite loops

### Async Parallel Processing

Uses `asyncio.gather()` for efficient parallel LLM calls:

```python
tasks = [generate_outline(...) for _ in range(num_variants)]
outlines = await asyncio.gather(*tasks)
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `GEMINI_API_KEY` | No | Google Gemini API key (optional) |
| `LOG_LEVEL` | No | Logging level (default: DEBUG) |

### Output Files

Each generation creates a unique directory:
- `parallel_world_article_<uuid>.json` - Complete article data
- `parallel_world_article_<uuid>.md` - Article in Markdown format
- `all_variants/` - All generated variants for comparison
