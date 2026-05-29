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
- **State Management**: Memento pattern for phase-based state with rollback capability

## Architecture

The system follows a "Stable Core and Flexible Extensions" architecture pattern, separating reusable agent core abstractions from article-generation-specific extensions.

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
|                 Service Layer (runner_service.py)                            |
|   - Thin wrapper delegating to agent pipeline                                |
+----------------------------------+-------------------------------------------+
                                   |
                                   v
+----------------------------------+-------------------------------------------+
|             AI Agent Pipeline Layer (agent/extensions/)                      |
|   - ArticlePipelineMediator: Workflow orchestration                          |
|   - Pipeline Nodes: Outline, FirstHalf, SecondHalf, Review, Regeneration     |
|   - Generation Tools: LLM generation functions                               |
|   - PipelineMemory: Phase-based state with rollback (Memento pattern)        |
+----------------------------------+-------------------------------------------+
                                   |
                                   v
+----------------------------------+-------------------------------------------+
|                    Agent Core Layer (agent/core/)                            |
|   - Tool, Strategy, Action, ToolResult (base.py)                             |
|   - Memory, MemorySnapshot (memory.py)                                       |
|   - Node, Edge, GraphMediator (mediator.py)                                  |
|   - ExecutionHandler, ExecutionController (controller.py)                    |
+----------------------------------+-------------------------------------------+
                                   |
                                   v
+------------------------------------------------------------------------------+
|                         Infrastructure Layer                                 |
|   - LLM clients (llm_client.py) - Google Gemini                              |
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
|   |-- agent/                   # AI Agent Framework
|   |   |-- __init__.py          # Re-exports all public APIs
|   |   |-- core/                # Stable core abstractions
|   |   |   |-- base.py          # Tool, Strategy, Action, ToolResult
|   |   |   |-- states.py        # AgentState, AgentContext, AgentStatus
|   |   |   |-- memory.py        # Memory, MemorySnapshot (Memento pattern)
|   |   |   |-- toolbox.py       # ToolBox (Composite pattern)
|   |   |   |-- controller.py    # ExecutionHandler, ExecutionController
|   |   |   |-- mediator.py      # GraphMediator, Node, Edge
|   |   |   +-- agent.py         # BaseAgent
|   |   +-- extensions/          # Flexible implementations
|   |       |-- tools/
|   |       |   |-- generation.py  # LLM generation tools for article pipeline
|   |       |   |-- calculator.py  # Calculator tool
|   |       |   |-- web_search.py  # Web search tool
|   |       |   +-- text_generator.py  # Text generation tool
|   |       |-- nodes/
|   |       |   |-- pipeline.py    # Pipeline nodes for each generation phase
|   |       |   |-- agent_node.py  # Agent execution node
|   |       |   |-- decision_node.py  # Decision branching node
|   |       |   +-- aggregator_node.py  # Result aggregation node
|   |       |-- memory/
|   |       |   |-- pipeline.py    # PipelineMemory with phase-based rollback
|   |       |   |-- context.py     # Context-based memory
|   |       |   |-- conversational.py  # Conversation memory
|   |       |   +-- caretaker.py   # Memory snapshot caretaker
|   |       |-- mediators/
|   |       |   |-- article_pipeline.py  # ArticlePipelineMediator
|   |       |   |-- simple.py      # Simple sequential mediator
|   |       |   +-- parallel.py    # Parallel execution mediator
|   |       |-- strategies/
|   |       |   |-- base_strategy.py  # Base strategy implementation
|   |       |   |-- chain_of_thought.py  # CoT strategy
|   |       |   |-- react.py       # ReAct strategy
|   |       |   +-- tree_of_thought.py  # ToT strategy
|   |       |-- handlers/
|   |       |   |-- max_steps.py   # Max steps handler
|   |       |   |-- loop_detection.py  # Loop detection handler
|   |       |   |-- cost_limit.py  # Cost limit handler
|   |       |   |-- dangerous_action.py  # Dangerous action handler
|   |       |   +-- tool_rate_limit.py  # Tool rate limit handler
|   |       +-- agents/
|   |           |-- configurable.py  # Configurable agent
|   |           +-- multi_strategy.py  # Multi-strategy agent
|   |-- client/
|   |   |-- __init__.py
|   |   +-- llm_client.py        # LLM client initialization (Google Gemini)
|   |-- model/
|   |   |-- __init__.py
|   |   +-- model.py             # Pydantic data model definitions
|   |-- prompt/
|   |   |-- __init__.py
|   |   +-- prompt.py            # Prompt generation logic
|   +-- service/
|       |-- __init__.py
|       |-- helper.py            # UI display and file saving helpers
|       +-- runner_service.py    # Thin wrapper delegating to agent pipeline
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

### Core Abstractions (src/agent/core/)

| Component | Description |
|-----------|-------------|
| `Tool` | Abstract base class for tools with execute() method |
| `Strategy` | Abstract base class for thinking strategies (CoT, ReAct) |
| `Action` | Represents an action (TOOL_CALL, FINAL_ANSWER, THINK, OBSERVE) |
| `ToolResult` | Result from tool execution with success/error status |
| `Memory` | Abstract memory with snapshot/restore (Memento pattern) |
| `MemorySnapshot` | Point-in-time state capture for rollback |
| `Node` | Abstract base class for graph nodes |
| `GraphMediator` | Abstract mediator for node coordination |
| `Edge` | Connection between nodes (sequential, conditional, parallel) |

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

### Agent Extensions (src/agent/extensions/)

**Generation Tools** (`tools/generation.py`):
- `OutlineGeneratorTool` - Generate article outline
- `FirstHalfGeneratorTool` - Generate first half of article
- `BestFirstHalfSelectorTool` - Select best first half from candidates
- `SecondHalfGeneratorTool` - Generate second half of article
- `ArticleReviewerTool` - Review article with LLM-as-a-Judge
- `SecondHalfRegeneratorTool` - Regenerate with feedback
- `GenerationToolBox` - Container for all generation tools

**Pipeline Nodes** (`nodes/pipeline.py`):
- `OutlineGenerationNode` - Parallel outline generation
- `FirstHalfGenerationNode` - First half generation with selection
- `SecondHalfGenerationNode` - Parallel second half generation
- `ArticleReviewNode` - Parallel article review
- `SecondHalfRegenerationNode` - Feedback-based regeneration
- `HumanDecisionNode` - Human-in-the-loop decision points

**Pipeline Memory** (`memory/pipeline.py`):
- `PipelineState` - Dataclass for pipeline state
- `PipelineMemory` - Memory with phase-based rollback (Memento pattern)
- `PipelineMemoryCaretaker` - Manages memory snapshots

**Article Pipeline Mediator** (`mediators/article_pipeline.py`):
- `ArticlePipelineMediator` - Orchestrates the entire pipeline
- `run_article_pipeline()` - Main entry point for pipeline execution

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
| google-genai | >=1.45.0 | Google Gemini API client |
| openai | >=2.4.0 | OpenAI API client (optional) |
| pydantic | >=2.12.2 | Data validation and models |
| python-dotenv | >=1.1.1 | Environment variable loading |

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
export GEMINI_API_KEY="your-gemini-api-key-here"
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
  --model gemini-2.5-flash

# Japanese article
uv run python -m src.main \
  --theme "AI no Mirai" \
  --language ja \
  --model gemini-2.5-flash
```

#### Advanced Configuration

```bash
uv run python -m src.main \
  -t "Quantum Computing Breakthrough" \
  -l en \
  -m gemini-2.5-pro \
  -od ./my_articles \
  -no 5 \
  -ns 4
```

#### Auto Mode (No Human Interaction)

```bash
uv run python -m src.main \
  -t "Climate Change Solutions" \
  -l en \
  -m gemini-2.5-flash \
  -a
```

### CLI Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--theme` | `-t` | TEXT | Required | Article theme/topic |
| `--language` | `-l` | en/ja | Required | Article language |
| `--model` | `-m` | Choice | Required | Gemini model to use |
| `--output-directory` | `-od` | PATH | outputs | Output directory |
| `--num-outline-variants` | `-no` | INT | 3 | Number of outline variants |
| `--num-second-half-variants` | `-ns` | INT | 3 | Number of second half variants |
| `--auto-select` | `-a` | FLAG | False | Auto-select without human input |

**Available Models**: gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite, gemini-3.5-flash, gemini-3.1-flash-lite

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

### State Management (Memento Pattern)

The pipeline uses the Memento pattern for state management with rollback capability:
- `PipelineState` dataclass holds all pipeline state
- `PipelineMemory` manages state with phase-based rollback
- `PipelineMemoryCaretaker` stores snapshots at each phase completion
- Users can roll back to any previous phase and regenerate
- Error states tracked in `state.error`
- Maximum 5 iterations for review loop to prevent infinite loops

### Phase Detection

The `PipelineMemory` determines current phase based on populated state fields:
- Phase 0: Initial state (only theme, language, metadata)
- Phase 1: outline_sessions populated
- Phase 2: selected_outline_session_id populated
- Phase 3: first_half_session populated
- Phase 4: second_half_sessions populated
- Phase 5: reviewed_sessions populated
- Phase 6: final_selected_session_id populated
- Phase 7: human_approved populated

### Async Parallel Processing

Uses `asyncio.gather()` for efficient parallel LLM calls:

```python
tasks = [
    self.toolbox.outline_generator.execute_async(
        state.theme,
        state.language,
        state.model,
        state.llm_provider,
    )
    for _ in range(state.num_outline_variants)
]
outlines = await asyncio.gather(*tasks)
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `LOG_LEVEL` | No | Logging level (default: DEBUG) |

### Output Files

Each generation creates a unique directory:
- `parallel_world_article_<uuid>.json` - Complete article data
- `parallel_world_article_<uuid>.md` - Article in Markdown format
- `all_variants/` - All generated variants for comparison

### Agent Framework Design Patterns

The agent framework implements several design patterns:

| Pattern | Component | Purpose |
|---------|-----------|---------|
| **Memento** | Memory, MemorySnapshot, Caretaker | State snapshots and rollback |
| **Strategy** | Strategy, CoT, ReAct, ToT | Interchangeable thinking strategies |
| **Composite** | ToolBox | Hierarchical tool organization |
| **Mediator** | GraphMediator, Node | Graph-based agent coordination |
| **Chain of Responsibility** | ExecutionHandler | Handler chain for execution control |
| **Template Method** | BaseAgent | Standard agent execution flow |
