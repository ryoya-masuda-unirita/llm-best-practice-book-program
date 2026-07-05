# Chapter 5 Section 6: Learning AI Agent — External Memory and Feedback-Driven Adaptation

## What This Section Demonstrates

This section implements an agent that **improves per user over time without retraining**: a training-plan generator whose behavior adapts through an external memory loop. User feedback and history accumulate as JSON files; a **pattern-analyzer agent** periodically distills them into `LearnedPattern`s ("prefers short practical tasks", "struggles with theory-heavy days"); and the **plan-generator agent** injects those patterns into its prompt, producing increasingly personalized plans.

The learning loop: **generate → record feedback → extract patterns → inject into the next generation**. Apply this pattern to any recurring per-user LLM task (recommendations, coaching, report styles) where "learning" can be represented as *retrieved context*, not model weights.

## Practice Rules

1. **Persist memory outside the model** as versioned JSON files (`memory/{user_id}_{timestamp}.json`) containing profile, history, feedback, and learned patterns — inspectable, portable, deletable per user.
2. **Separate the learner from the doer.** The pattern analyzer (one agent/prompt) turns raw feedback into structured `LearnedPattern`s; the plan generator (another agent/prompt) consumes patterns. Neither parses the other's prose.
3. **Gate learning on evidence volume**: pattern analysis runs only with `MIN_FEEDBACK_FOR_LEARNING` feedback entries and reads only the most recent N (`get_recent_feedback(limit=10)`) — no patterns from one data point, no unbounded context.
4. **Inject learnings as a dedicated prompt block** (`LEARNED_CONTEXT_TEMPLATE`) — patterns enter generation as explicit context, so their influence is visible and debuggable.
5. **Record which feedback produced each pattern** (`feedback_ids` on `LearnedPattern`) — learned behavior stays auditable back to its evidence.
6. **Type feedback as enums** (`FeedbackRating`, `DifficultyRating`, `TaskCompletion`) so pattern analysis aggregates over closed vocabularies.
7. **Parse LLM enums defensively** (`_safe_enum_parse` with defaults) — memory spans many generations of prompts; old files must keep loading.

## Architecture

```
generate command                         feedback command
  ▼                                        ▼
run_training_plan_generation             add_feedback_to_memory
  ├─ load_memory(user_id) ◀───────────── memory/{user_id}_{ts}.json
  ├─ analyze_feedback_patterns           (profile / history / feedback /
  │    (if ≥ MIN_FEEDBACK)                learned patterns / progress)
  │    Pattern Analyzer Agent → LearnedPattern[]
  ├─ generate_training_plan
  │    Plan Generator Agent
  │    prompt = profile + request + LEARNED_CONTEXT(patterns)
  └─ save_memory (new snapshot file)
  ▼
outputs/training_plan_*.md
```

### Directory Structure

```
chapter_5/section_6/
├── src/
│   ├── service/
│   │   ├── service.py          # both agents + conversions + run entrypoints
│   │   └── memory_service.py   # save/load/list memory files, feedback append
│   ├── model/model.py          # profile/plan/feedback/pattern/memory models
│   ├── prompt/prompt.py        # generator + analyzer prompts, LEARNED_CONTEXT_TEMPLATE
│   ├── client/llm_client.py    # OpenAI model enum
│   ├── main.py                 # CLI group: generate / feedback / list / show
│   └── config.py / logger.py
├── memory/                     # per-user memory snapshots (runtime)
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Evidence-gated pattern extraction (`src/service/service.py`)

```python
def analyze_feedback_patterns(memory: UserMemory, model=...) -> list[LearnedPattern]:
    feedback_list = memory.get_recent_feedback(limit=10)
    if len(feedback_list) < MIN_FEEDBACK_FOR_LEARNING:
        return []                                    # don't learn from noise

    user_prompt = make_pattern_analyzer_user_prompt(
        feedback_history=format_feedback_for_analysis(feedback_list),
        total_weeks_completed=memory.progress.total_weeks_completed,
        average_completion_rate=memory.progress.average_completion_rate, ...)
    response = invoke_with_structured_output(llm, messages, PatternAnalysisResponse, "Pattern Analyzer")
    patterns = [_convert_response_to_learned_pattern(p, feedback_ids) for p in response.patterns]
    for pattern in patterns:
        memory.add_learned_pattern(pattern)
    return patterns
```

### 2. Patterns injected as an explicit prompt block (`src/prompt/prompt.py`)

```python
LEARNED_CONTEXT_TEMPLATE = """..."""    # renders learned patterns into the generator prompt
# generation prompt = profile + request + LEARNED_CONTEXT(patterns)
```

The generator's personalization is entirely visible in its rendered prompt — nothing hidden in fine-tuning.

### 3. Append-only memory snapshots (`src/service/memory_service.py`)

```python
def save_memory(memory: UserMemory) -> Path:
    # writes memory/{user_id}_{timestamp}.json — new snapshot per run
def load_memory(user_id: str) -> UserMemory | None:
    # loads the latest snapshot for the user
def add_feedback_to_memory(...):
    # appends TrainingFeedback and saves a new snapshot
```

### 4. Defensive enum parsing across memory generations

```python
def _safe_enum_parse(enum_class, value: str, default):
    # unknown/legacy values → default instead of crash; old memories stay loadable
```

## Data Models

| Model | Purpose |
|-------|---------|
| `UserProfile` | Goal, skill level, available time |
| `TrainingPlan` / `DailyPlan` / `DailyTask` / `WeeklyAssessment` | Generated deliverable |
| `TrainingFeedback` / `TaskCompletion` / `FeedbackRating` / `DifficultyRating` | Recorded user feedback |
| `LearnedPattern` | Distilled preference/insight + source `feedback_ids` |
| `UserMemory` / `TrainingRecord` | The persistent external memory container |

## Setup & Run

```bash
cp .envrc.example .envrc     # set OPENAI_API_KEY
uv sync

# 1. Generate a plan (creates memory for the user)
uv run python -m src.main generate -g 'Learn Python programming' -h 10 -s beginner

# 2. Record feedback (accumulates learning evidence)
uv run python -m src.main feedback ...    # rating / difficulty / completed tasks

# 3. Generate again — once feedback ≥ threshold, learned patterns shape the plan
uv run python -m src.main generate -g 'Learn Python programming' -h 10 -s beginner

# Inspect memory
uv run python -m src.main list
```

### CLI (click group)

| Command | Purpose |
|---------|---------|
| `generate` | Create a 1-week training plan (`-g` goal, `-h` hours, `-s` skill level, …) |
| `feedback` | Record ratings/completions against a plan |
| `list` | List stored user memories |
| (see `--help` for the full command set) | |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
```

## Implementation Notes

- **"Learning" here is context engineering, not weight updates** — the same practice behind memory in production assistants. Its strengths: per-user, immediately effective, fully auditable, erasable (delete the JSON). Its limit: patterns must fit the prompt budget — hence the recent-N window and distillation into compact `LearnedPattern`s rather than raw feedback replay.
- **Distill-then-inject beats raw-history injection**: 10 feedback entries → a few patterns is both cheaper and more instructive to the generator than pasting the history verbatim.
- **Snapshot-per-run persistence** gives free history/rollback at the cost of file accumulation; production variants keep the same `UserMemory` schema in a database with versioning.
- **The two-agent split matters for quality control**: you can evaluate the analyzer (are extracted patterns supported by the feedback?) separately from the generator (does the plan follow the patterns?).
- **Cold start is explicit**: with no memory, generation runs pattern-free; the system degrades to a good generic generator rather than hallucinating preferences.

## How to Apply This Practice to Your Own Project

1. Define your `UserMemory` schema: profile, interaction history, feedback (typed enums), learned patterns with evidence links.
2. Build the feedback capture path first — no feedback, no learning loop.
3. Write the analyzer agent with a structured `PatternAnalysisResponse`; gate it on minimum evidence and a recent-N window.
4. Inject patterns via a dedicated template block in the doer agent's prompt; log the rendered block per run.
5. Store memory externally (files → DB) with per-user deletion support; never bury user-specific learning in prompt code.
6. Evaluate the loop end-to-end: does plan quality (or acceptance rate) actually improve after feedback? If not, fix the analyzer prompt before adding more memory.
