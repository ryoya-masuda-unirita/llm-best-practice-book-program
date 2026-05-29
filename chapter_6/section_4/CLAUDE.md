# Chapter 6 Section 9: Forget, Replay, Speculate - Three-Stage Context Management

## Overview

This project demonstrates the **"Forget, Replay, Speculate"** three-stage pattern for LLM applications. Building upon the state-based rollback mechanism (section_4), it adds **automatic prompt replay** after rollback and **speculative parallel-world execution** at decision points.

The implementation is an article generation pipeline that:
- Generates content step by step (outline -> first half -> second half -> review -> approval)
- Implements checkpoint-based rollback (**Forget**) to discard contaminated context
- Automatically replays valid user prompts after rollback (**Replay**) to restore state without manual re-entry
- Speculatively executes multiple candidate branches in parallel (**Speculate**) so users can compare final outcomes before choosing
- Uses LLM-as-a-Judge for automated quality evaluation
- Provides Human-in-the-Loop decision points

## Architecture

### Three-Stage Design

```
Stage 1: FORGET          Stage 2: REPLAY           Stage 3: SPECULATE
(Checkpoint & Rollback)  (Auto Prompt Re-send)     (Parallel Worlds)

  [Checkpoint]             [Prompt Log]              [World Manager]
       |                        |                         |
  Save state at            Record user              At branch points,
  phase boundaries         prompts in WAL           fork N worlds and
       |                        |                   run them in parallel
  On error/request,        After rollback,               |
  restore to a             filter & re-send         Present final
  checkpoint               valid prompts            outcomes to user
       |                        |                         |
  Discard phases           Skip context-             User picks best
  after target             dependent prompts         world; discard rest
```

### Pipeline Flow

```
+-------------+     +-------------+     +-------------+     +-------------+
|  Phase 1    |     |  Phase 2    |     |  Phase 3    |     |  Phase 4    |
|  Outline    |---->|  First Half |---->|  Second Half|---->|   Review    |
|  Generation |     |  Generation |     |  Generation |     | (LLM Judge) |
+------+------+     +------+------+     +-------------+     +------+------+
       |                   |                                       |
       v                   v                                       v
  +---------+        +-----------+                          +-------------+
  | Specul. |        | Rollback  |                          |  Phase 5    |
  | Point   |        | + Replay  |                          |  Approval   |
  | (N out- |        | Point #1  |                          |  Decision   |
  | lines)  |        +-----------+                          +------+------+
  +---------+                                                      |
       |                                                    +-----------+
  Generate N                                                | Rollback  |
  parallel                                                  | + Replay  |
  worlds,                                                   | Point #2  |
  show final                                                +-----------+
  outcomes                                                         |
       |                                                           v (if rejected)
  User picks                                                +-------------+
  best world                                                | Regenerate  |
                                                            | with        |
                                                            | Feedback    |
                                                            +-------------+
```

### Agent Architecture

```
+-------------------------------+
|       PipelineMediator        |  Orchestrates all three stages
| (Forget + Replay + Speculate) |
+------+--------+--------+-----+
       |        |        |
       v        v        v
  +--------+ +-------+ +----------------+
  |Pipeline| |Replay | |  World         |
  |Memory  | |Engine | |  Manager       |
  |        | |       | | (Speculative)  |
  +--------+ +-------+ +----------------+
       |        |        |
    +--+--------+--------+--+
    |                       |
    v                       v
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

### Memento + WAL Pattern for State Management

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
          |
          v
   +-------------+
   | Prompt WAL  |  <-- Write-Ahead Log of user prompts
   +-------------+      for replay after rollback
   | Entry 1     |
   | Entry 2     |
   | ...         |
   +-------------+

+-------------------+
|  World Manager    |  Manages speculative parallel worlds
+-------------------+
| World A (outline1)|---> run phases 2-5 in background
| World B (outline2)|---> run phases 2-5 in background
| World C (outline3)|---> run phases 2-5 in background
+-------------------+
         |
    User picks one;
    others discarded
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
|   |       |   +-- article_pipeline.py  # ArticlePipelineMediator (all 3 stages)
|   |       |   +-- simple.py            # Simple mediator
|   |       |   +-- parallel.py          # Parallel mediator
|   |       +-- memory/
|   |       |   +-- pipeline.py          # PipelineMemory, PipelineMemoryCaretaker
|   |       |   +-- context.py           # Context memory
|   |       |   +-- conversational.py    # Conversational memory
|   |       |   +-- caretaker.py         # Caretaker implementation
|   |       +-- replay/
|   |       |   +-- __init__.py
|   |       |   +-- engine.py            # ReplayEngine: WAL-based prompt replay
|   |       |   +-- prompt_log.py        # PromptLog: records user prompts with metadata
|   |       |   +-- filter.py            # ReplayFilter: classify prompts as replayable/skip/confirm
|   |       +-- speculative/
|   |       |   +-- __init__.py
|   |       |   +-- world.py             # World: isolated pipeline execution context
|   |       |   +-- world_manager.py     # WorldManager: fork, run, compare, select worlds
|   |       |   +-- branch_detector.py   # BranchDetector: identify speculative branch points
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

### Stage 1: Forget (Checkpoint & Rollback)

#### State Model (`src/agent/extensions/nodes/pipeline.py`)

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

#### Phase Detection (`src/agent/extensions/memory/pipeline.py`)

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

#### Rollback (`src/agent/extensions/memory/pipeline.py`)

```python
def forget_phases_after(self, target_phase: int) -> None:
    """Discard all state after the target phase."""
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

### Stage 2: Replay (Automatic Prompt Re-send)

#### Prompt Log (`src/agent/extensions/replay/prompt_log.py`)

Records every user prompt with metadata in a Write-Ahead Log (WAL):

```python
@dataclass
class PromptLogEntry:
    index: int                          # Sequential index
    timestamp: datetime                 # When the prompt was received
    phase: int                          # Pipeline phase at time of prompt
    prompt_text: str                    # The user's actual input
    prompt_type: PromptType             # REQUIREMENT, FEEDBACK, CONFIRMATION, CONTEXT_DEPENDENT
    depends_on_prior_response: bool     # Whether it references LLM's prior output
    metadata: dict[str, Any] | None = None

class PromptType(Enum):
    REQUIREMENT = "requirement"         # Explicit user requirement (replayable)
    FEEDBACK = "feedback"               # Simple yes/no feedback (skip)
    CONFIRMATION = "confirmation"       # Confirm/deny (skip)
    CONTEXT_DEPENDENT = "context_dependent"  # References prior output (needs review)

class PromptLog:
    def append(self, entry: PromptLogEntry) -> None: ...
    def get_entries_after(self, phase: int) -> list[PromptLogEntry]: ...
    def get_all_entries(self) -> list[PromptLogEntry]: ...
```

#### Replay Filter (`src/agent/extensions/replay/filter.py`)

Classifies which prompts should be replayed after rollback:

```python
class ReplayDecision(Enum):
    REPLAY = "replay"       # Re-send this prompt
    SKIP = "skip"           # Do not re-send
    CONFIRM = "confirm"     # Ask user before re-sending

class ReplayFilter:
    def classify(self, entry: PromptLogEntry, rollback_phase: int) -> ReplayDecision:
        """
        Rules:
        - REQUIREMENT prompts -> REPLAY
        - FEEDBACK / CONFIRMATION prompts -> SKIP
        - CONTEXT_DEPENDENT prompts -> CONFIRM (ask user)
        - Prompts that caused the rollback -> SKIP
        """
```

#### Replay Engine (`src/agent/extensions/replay/engine.py`)

Orchestrates the replay process after rollback:

```python
class ReplayEngine:
    def __init__(self, prompt_log: PromptLog, replay_filter: ReplayFilter): ...

    async def replay_after_rollback(
        self,
        rollback_phase: int,
        mediator: ArticlePipelineMediator,
    ) -> ReplayResult:
        """
        1. Get all prompts after rollback_phase from the WAL
        2. Filter each prompt through ReplayFilter
        3. For REPLAY prompts: re-send in order
        4. For CONFIRM prompts: ask user
        5. For SKIP prompts: discard
        6. Return diff of before/after responses
        """

@dataclass
class ReplayResult:
    replayed_count: int
    skipped_count: int
    confirmed_count: int
    diffs: list[ReplayDiff]         # Before/after comparison

@dataclass
class ReplayDiff:
    prompt_index: int
    prompt_text: str
    original_response: str | None
    replayed_response: str | None
```

### Stage 3: Speculate (Parallel World Execution)

#### World (`src/agent/extensions/speculative/world.py`)

An isolated execution context representing one speculative branch:

```python
@dataclass
class World:
    world_id: str                       # Unique ID
    branch_point_phase: int             # Phase where this world branched
    candidate: Any                      # The candidate that started this world (e.g., ArticleOutline)
    state: PipelineState                # Independent copy of pipeline state
    status: WorldStatus                 # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    result: PipelineResult | None       # Final result if completed
    created_at: datetime
    completed_at: datetime | None = None

class WorldStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

#### World Manager (`src/agent/extensions/speculative/world_manager.py`)

Manages speculative parallel-world execution:

```python
class WorldManager:
    def __init__(self, max_parallel_worlds: int = 3): ...

    async def speculate(
        self,
        candidates: list[Any],
        branch_phase: int,
        base_state: PipelineState,
        execute_fn: Callable[[PipelineState], Awaitable[PipelineResult]],
    ) -> list[World]:
        """
        1. For each candidate, deep-copy base_state and set the candidate
        2. Launch execute_fn for each world concurrently (up to max_parallel)
        3. Return list of worlds with results
        """

    async def cancel_worlds(self, world_ids: list[str]) -> None:
        """Cancel running worlds that were not selected."""

    def get_world_summaries(self) -> list[WorldSummary]:
        """Return brief summaries for user comparison."""

@dataclass
class WorldSummary:
    world_id: str
    candidate_label: str                # e.g., outline title
    status: WorldStatus
    preview: str | None                 # Short preview of final output
    review_grade: int | None            # LLM-as-Judge grade if available
```

#### Branch Detector (`src/agent/extensions/speculative/branch_detector.py`)

Identifies when speculative execution should be triggered:

```python
class BranchDetector:
    def should_speculate(self, phase: int, candidates: list[Any]) -> bool:
        """
        Returns True when:
        - Multiple candidates exist (len > 1)
        - Phase is a known branch point (e.g., after outline generation)
        - Cost budget allows parallel execution
        """
```

### Pipeline Mediator (`src/agent/extensions/mediators/article_pipeline.py`)

The `ArticlePipelineMediator` integrates all three stages:

```python
class ArticlePipelineMediator:
    def __init__(self, ...):
        self.memory = PipelineMemory(initial_state)
        self.caretaker = PipelineMemoryCaretaker()
        self.toolbox = GenerationToolBox()
        self.prompt_log = PromptLog()
        self.replay_filter = ReplayFilter()
        self.replay_engine = ReplayEngine(self.prompt_log, self.replay_filter)
        self.world_manager = WorldManager(max_parallel_worlds=3)
        self.branch_detector = BranchDetector()
        self._init_nodes()

    async def execute(self) -> PipelineResult:
        """
        Main loop:
        Phase 1: Generate N outline candidates
                 -> If speculate: fork N worlds, run phases 2-5 for each
                 -> Present world summaries to user
                 -> User picks best world
        Phase 2: Generate first half (rollback + replay point)
        Phase 3: Generate second half
        Phase 4: Review with LLM-as-a-Judge
        Phase 5: Human approval (rollback + replay point)
        """

    async def _handle_rollback_with_replay(self, target_phase: int) -> None:
        """
        1. Save current state as checkpoint
        2. Rollback to target_phase (forget)
        3. Replay valid prompts from WAL (replay)
        4. Show diff of before/after to user
        """

    async def _handle_speculative_outlines(
        self, outlines: list[ArticleOutline]
    ) -> ArticleOutline:
        """
        1. Detect branch point
        2. Fork worlds for each outline
        3. Run pipeline in each world concurrently
        4. Present world summaries (with final article previews)
        5. User selects best world
        6. Cancel other worlds
        7. Return selected outline
        """
```

### Pydantic Models (`src/model/model.py`)

- `ArticleOutline`: Title, summary, structure (3-10 sections)
- `ArticleHalf`: Content with reasoning
- `ArticleReview`: Grade (1-5), strengths, weaknesses; `is_acceptable()` returns `True` if grade >= 4
- `CompletedArticle`: Final article with all components

### Generation Tools (`src/agent/extensions/tools/generation.py`)

- `OutlineGeneratorTool`: Generate article outline (extended to produce N candidates)
- `FirstHalfGeneratorTool`: Generate first half of article
- `SecondHalfGeneratorTool`: Generate second half of article
- `ArticleReviewerTool`: LLM-as-a-Judge evaluation
- `SecondHalfRegeneratorTool`: Regenerate with feedback
- `GenerationToolBox`: Container for all generation tools

## Dependencies

Core dependencies:
- `click>=8.3.0`: CLI framework
- `google-genai>=1.45.0`: Google Gemini integration
- `anthropic>=0.74.1`: Anthropic API (future use)
- `openai>=2.4.0`: OpenAI API (future use)
- `pydantic>=2.12.2`: Data validation and structured outputs
- `python-dotenv>=1.1.1`: Environment configuration

Development dependencies:
- `ruff>=0.12.4`: Linting and formatting
- `mypy>=1.17.0`: Type checking
- `isort>=6.0.1`: Import sorting

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

**Interactive mode** (with rollback, replay, and speculative execution):
```bash
uv run python -m src.main \
  --theme "The Future of AI" \
  --language en \
  --model gemini-2.5-flash
```

**Auto-select mode** (no user prompts, speculative execution disabled):
```bash
uv run python -m src.main \
  --theme "Quantum Computing" \
  --language ja \
  --model gemini-2.5-flash \
  --auto-select
```

**With speculative execution (N outlines)**:
```bash
uv run python -m src.main \
  --theme "Climate Change Solutions" \
  --language en \
  --model gemini-2.5-flash \
  --num-outlines 3
```

### CLI Options

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--theme` | `-t` | Yes | - | Article theme/topic |
| `--language` | `-l` | Yes | - | Language (`en` or `ja`) |
| `--model` | `-m` | Yes | - | Gemini model name |
| `--output-directory` | `-od` | No | `outputs` | Output directory |
| `--auto-select` | `-a` | No | `False` | Auto-select mode (skips user prompts) |
| `--num-outlines` | `-n` | No | `1` | Number of outline candidates for speculative execution |

Available models:
- `gemini-2.5-pro`
- `gemini-2.5-flash`
- `gemini-2.5-flash-lite`
- `gemini-3.5-flash`
- `gemini-3.1-flash-lite`

## Development Commands

```bash
make fix    # Lint (ruff + isort) and format
make lint   # Lint only
make fmt    # Format only
make mypy   # Type checking
```

## Implementation Notes

### LLM-as-a-Judge

Articles are graded on a 1-5 scale. Auto-select mode approves articles with grade >= 4.

Evaluation criteria with weights:
- Content Quality (30%): Accuracy, informativeness, value
- Structure & Flow (25%): Outline adherence, logical flow
- Writing Quality (20%): Clarity, engagement
- Completeness (15%): Theme and section coverage
- Language Quality (10%): Appropriateness, consistency

### Human-in-the-Loop Decision Points

1. **Speculative Selection** (After Phase 1, if `--num-outlines > 1`): Compare parallel-world outcomes and pick the best
2. **Rollback + Replay** (After Phase 2): Continue or roll back; valid prompts auto-replayed
3. **Approval Decision** (Phase 5): Approve or reject with regeneration
4. **Rollback + Replay** (After Phase 5): Roll back to any phase; valid prompts auto-replayed

### Replay Behavior

When a rollback triggers replay:
1. System shows message: "Rolling back to Phase N. Replaying M valid prompts..."
2. Each replayed prompt is shown with its new response
3. Context-dependent prompts prompt user confirmation before replay
4. A diff summary is shown at the end

### Speculative Execution Behavior

When multiple outlines are generated:
1. System shows message: "Generating 3 outline candidates and exploring each..."
2. Each world runs phases 2-5 in parallel (background)
3. As worlds complete, summaries appear with review grades and article previews
4. User selects the best world; others are cancelled
5. Pipeline continues from the selected world's state

### Cost Control for Speculative Execution

- `max_parallel_worlds` limits concurrent executions (default: 3)
- Only the next 1-2 phases are speculatively executed (configurable)
- Cancellation mechanism stops unneeded worlds immediately
- Auto-select mode disables speculation to avoid unnecessary cost

### Feedback Loop

When an article is rejected, the system:
1. Stores the rejected second half and its review in `previous_feedback`
2. Regenerates the second half with feedback from previous attempts
3. Re-reviews the new content
4. Repeats up to 5 iterations maximum (`max_iterations`)

### Output Files

```
outputs/
+-- article_{session_id}/
    +-- article_{session_id}.json
    +-- article_{session_id}.md
```

### Error Handling

Errors are tracked in state and checked at each phase. The replay engine skips prompts that caused errors during the original execution.

## Key Takeaways

1. **Forget**: State-based rollback eliminates complex checkpoint management; forgetting by deletion prevents context contamination
2. **Replay**: WAL-based prompt logging enables automatic re-send after rollback, preserving valid user inputs without manual re-entry
3. **Speculate**: Parallel-world execution lets users compare final outcomes (not just candidates), enabling informed decisions at branch points
4. **Three stages are independently deployable**: Start with Forget only, add Replay when rollbacks become frequent, add Speculate at high-value decision points
5. **Cost awareness**: Speculation multiplies API costs by N; use judiciously with budget controls and cancellation

## Extending the System

### Adding New Phases

1. Add state variable in `PipelineState`
2. Update `get_current_phase()` to check the new variable
3. Update `forget_phases_after()` to handle rollback
4. Create a new Node class in `src/agent/extensions/nodes/`
5. Add execution logic in `ArticlePipelineMediator`
6. Update `PromptLog` phase tracking

### Adding New Branch Points for Speculation

1. Identify the phase that produces multiple candidates
2. Register it in `BranchDetector`
3. Implement the candidate generation in the corresponding tool
4. The `WorldManager` handles the rest automatically

### Adding New Replay Filters

1. Define new `PromptType` enum values
2. Add classification rules in `ReplayFilter.classify()`
3. Update `PromptLog` to detect the new type

### Adding New LLM Providers

1. Add provider enum to `LLMProvider` in `src/client/llm_client.py`
2. Add model enum (e.g., `ClaudeModel`)
3. Implement `_generate_with_provider()` helper in `generation.py`
4. Update CLI to accept new provider/model combinations
