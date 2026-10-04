# Chapter 6 Section 4: Forget, Replay, Speculate — Three-Stage Context Management for Long-Running Agents

## What This Section Demonstrates

Long multi-phase LLM sessions accumulate **contaminated context**: a bad generation or misdirected instruction pollutes everything after it. This section implements three context-management operations, combined in an article-generation pipeline (outline → first half → second half → review → approval):

- **Forget** — checkpoint-based rollback (`PipelineMemory` phase snapshots, Memento pattern): discard the polluted suffix and restore a known-good state.
- **Replay** — after rollback, valid user prompts recorded in a `PromptLog` are automatically re-applied (`ReplayEngine` + `ReplayFilter`), so users don't lose the legitimate steering they gave; context-dependent prompts ask for confirmation, and a diff summary shows what changed.
- **Speculate** — at decision points, multiple candidate branches run as **parallel worlds** (`WorldManager`, N outline candidates → phases 2–5 concurrently); the user (or LLM-as-a-Judge auto-select, grade ≥ 4) picks the winning world and the rest are cancelled.

Built on the core/extensions agent framework (Chapter 4 Section 8). Apply these patterns to any long agent session where mistakes must be recoverable without restarting and alternatives are worth exploring before committing.

## Practice Rules

1. **Snapshot at phase boundaries** (`PipelinePhaseSnapshot`) — rollback granularity should match meaningful units of work, not raw messages.
2. **Log user prompts with validity metadata** (`PromptLog`) — replay must distinguish steering that's still valid after rollback from prompts contaminated by the discarded context (`ReplayFilter`; ambiguous ones require user confirmation).
3. **Rollback and replay are one motion**: forget without replay silently discards user intent; always re-apply the surviving prompt sequence and show the diff (`ReplayResult`/`ReplayDiff`).
4. **Bound speculation** (`max_parallel_worlds=3`) — parallel worlds multiply cost linearly; cap concurrency and cancel losers immediately (`cancel_unselected`).
5. **Score worlds with LLM-as-a-Judge** (weighted rubric: content 30%, structure 25%, writing 20%, completeness 15%, language 10%) so auto-select is principled and interactive selection is informed (`WorldSummary` with grades).
6. **Put humans at the decision points, not in the loop**: speculative selection, rollback choice, and final approval are explicit HITL gates; everything between them runs autonomously (`--auto-select` replaces gates for unattended runs).
7. **Keep worlds isolated**: each `World` owns its state copy; only the selected world's state merges back into the main pipeline.

## Architecture

```
Article pipeline (phases):  1 outline → 2 first half → 3 second half → 4 review → 5 approval

Forget:   PipelineMemory ── snapshot per phase ──▶ rollback(phase_n) restores state
Replay:   PromptLog(entries + validity) ─▶ ReplayEngine.get_replayable_entries(rollback_point)
              └─ ReplayFilter: valid → auto-replay / context-dependent → confirm
              └─ ReplayResult + diff summary displayed
Speculate: WorldManager.create_worlds(N outlines)
              └─ execute_worlds: phases 2–5 per world, concurrently (≤ max_parallel_worlds)
              └─ judge grades → display_world_summaries → select_world (human or auto ≥4)
              └─ cancel_unselected; selected world's state continues as main
```

### Directory Structure (delta over the Chapter 4 Section 8 framework)

```
chapter_6/section_4/
├── src/
│   ├── agent/
│   │   ├── core/                      # framework core (agent/memory/controller/…)
│   │   └── extensions/
│   │       ├── memory/pipeline.py     # PipelineMemory + PipelinePhaseSnapshot  [Forget]
│   │       ├── replay/                # prompt_log.py / filter.py / engine.py    [Replay]
│   │       ├── speculative/           # world.py / world_manager.py / branch_detector.py  [Speculate]
│   │       ├── mediators/article_pipeline.py   # the 5-phase pipeline mediator
│   │       ├── nodes/pipeline.py / tools/generation.py
│   │       └── strategies/ handlers/ agents/   # as in Chapter 4 Section 8
│   ├── service/runner_service.py      # run_forget_replay_speculate_article_generation
│   ├── service/helper.py              # HITL prompts (approval / rollback choice / requirements)
│   ├── client/llm_client.py / model/ prompt/ config.py / logger.py
│   └── main.py                        # CLI
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Phase snapshots for rollback (`src/agent/extensions/memory/pipeline.py`)

```python
@dataclass
class PipelinePhaseSnapshot:
    # phase number/name + serialized PipelineState

class PipelineMemory(Memory):
    def __init__(self, initial_state: PipelineState): ...
    # snapshot() at each phase boundary; rollback(phase) restores and truncates
```

### 2. Selective replay after rollback (`src/agent/extensions/replay/engine.py`)

```python
class ReplayEngine:
    def get_replayable_entries(self, rollback_point, ...) -> list[PromptLogEntry]:
        # ReplayFilter classifies: valid / context-dependent (confirm) / invalidated (drop)
    def build_replay_result(self, ...) -> ReplayResult:   # diffs of re-applied prompts
    def display_replay_summary(self, result: ReplayResult) -> None: ...
```

### 3. Parallel-world speculation (`src/agent/extensions/speculative/world_manager.py`)

```python
class WorldManager:
    def __init__(self, max_parallel_worlds: int = 3): ...
    def create_worlds(self, ...) -> list[World]           # one per outline candidate
    async def execute_worlds(self, worlds, ...):          # run phases 2-5 concurrently
    def select_world(self, worlds, auto_select) -> World: # judge-graded auto (≥4) or interactive
    def cancel_unselected(self, worlds, selected_world) -> None: ...
```

### 4. HITL gates as helpers (`src/service/helper.py`)

```python
def get_human_approval(completed_article, auto_select: bool) -> bool: ...
def get_rollback_choice(available_phases, auto_select) -> int | None: ...
def get_user_requirements(phase, auto_select) -> str | None: ...
```

Every gate has an `auto_select` path so the pipeline can run unattended.

## Data Models

| Model | Purpose |
|-------|---------|
| `PipelineState` / `PipelinePhaseSnapshot` | Pipeline context + rollback checkpoints |
| `PromptLogEntry` / `ReplayDiff` / `ReplayResult` | Replay bookkeeping and reporting |
| `World` / `WorldSummary` | Speculative branch state + judge-graded summary |
| `CompletedArticle` | Final deliverable (article + metadata + grade) |

## Setup & Run

```bash
cp .envrc.example .envrc     # set GEMINI_API_KEY
uv sync

# Canonical example (auto-select: judge decides at every gate)
uv run python -m src.main --theme 'AI in healthcare' --language en -m global.anthropic.claude-haiku-4-5-20251001-v1:0 --auto-select

# Interactive with speculation (3 parallel outline worlds, human picks)
uv run python -m src.main --theme 'AIと医療' --num-outlines 3
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--theme` | Article theme |
| `--language` | Output language |
| `--model` / `-m` | Gemini model |
| `--num-outlines` | Number of speculative worlds (1 = no speculation) |
| `--auto-select` | Judge-driven decisions at all HITL gates (grade ≥ 4 approves) |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
```

## Implementation Notes

- **Why "forget" beats "correct"**: appending "ignore the previous draft, actually…" leaves the contaminated text in context, where it keeps influencing generation. Rollback removes it; replay then reconstructs only the valid instruction history. This is the core of context hygiene in long sessions.
- **Replay classification is the hard part**: a prompt like "make it more formal" survives any rollback; "expand the second section" depends on a specific draft. `ReplayFilter` automates the clear cases and defers ambiguous ones to the user — copy that split.
- **Speculation economics**: N worlds ≈ N× phases-2–5 cost. It pays when a phase-1 decision (outline) dominates final quality and human comparison of *finished* outcomes beats comparing outlines. Cancel-on-select caps the waste.
- **The weighted judge rubric** makes world grades comparable and auto-select trustworthy; weights are explicit in the prompt, so tuning quality priorities is a prompt edit.
- **All three mechanisms ride on the framework's seams** (Memory/Memento, mediator pipeline, handler-gated execution) — evidence that the Chapter 4 Section 7/8 abstractions carry advanced patterns without core changes.

## How to Apply This Practice to Your Own Project

1. Define your session's phase boundaries and snapshot state at each (Memento) — rollback targets must be nameable ("back to outline").
2. Log user steering prompts with enough metadata to classify replay validity; implement the valid/confirm/drop filter.
3. Wire rollback+replay as a single user action with a visible diff of what was re-applied.
4. Add speculation only at genuinely divergent decision points; bound parallel worlds and cancel losers eagerly.
5. Grade branches with a weighted judge rubric; let humans see grades + previews when selecting.
6. Provide an `--auto-select` path for every human gate so the same pipeline runs attended and unattended.
