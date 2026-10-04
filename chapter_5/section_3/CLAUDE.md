# Chapter 5 Section 3: Hierarchical AI Agent — Strategy / Tactics / Execution / Reflection

## What This Section Demonstrates

This section implements a **Hierarchical (Multi-Layer) Agent** for a personalized-learning-plan generator. Like an organization, responsibilities are split by abstraction level, each layer consuming the layer above's output as its specification:

- **Strategy Layer (戦略・プランニング層)** — interprets the ambiguous goal, sets skill levels, produces a module roadmap (the blueprint). Never touches implementation details.
- **Tactics Layer (戦術・マネジメント層)** — decomposes the roadmap into weekly themes and daily tasks (the ToDo list for execution).
- **Execution Layer (実行層)** — specialists (`ContentAgent`, `QuizAgent`) faithfully produce learning content and quizzes per task. No strategic decisions.
- **Reflection Layer (自己評価・省察層)** — an independent auditor that scores quality, checks goal alignment, and recommends corrections — preventing confident execution in the wrong direction.

The layers are orchestrated as a LangGraph state machine (`strategy → tactics → execution loop → reflection → END`). Apply this when a goal is too abstract for one prompt and needs progressive refinement with an independent quality check. See `REFERENCE.md` for the underlying architectural principles.

## Practice Rules

1. **Each layer has one abstraction level** and communicates only through structured JSON models (`StrategyOutput` → `TacticsOutput` → `LearningSession`s → `ProgressReport`) — never free text between layers.
2. **Upper layers produce blueprints, not implementations**: the Strategy layer outputs modules/milestones; how a day's content looks is not its business.
3. **Execution agents are specialists**: `ContentAgent` and `QuizAgent` each do one thing per task, iterating the Tactics layer's task list.
4. **Reflection is a separate, independent layer** — it evaluates execution outputs against the original goal and can request corrections; it does not generate content itself.
5. **Bound the execution loop** (the demo generates sessions for the first week, capped) — hierarchical agents multiply LLM calls fast; cap fan-out per run.
6. **Harden JSON handling in the base agent** (`BaseAgent`): multiple extraction strategies (raw / markdown fence / brace matching), truncated-JSON repair, `MAX_RETRIES=3`.
7. **Derive plan size from explicit inputs** (`--duration-weeks`, `--hours-per-week`), not from prose in the goal — runtime and cost scale with the plan, so the knobs must be first-class.

## Architecture

```
CLI (src/main.py)  goal / hours / duration / profile JSON
  ▼
LangGraph state machine (src/service/llm_pipeline_service.py)
  1. STRATEGY   (layer/strategy.py)   goal → skill levels → LearningRoadmap (blueprint)
  2. TACTICS    (layer/tactics.py)    roadmap → WeeklyPlan + DailyTask list
  3. EXECUTION  (layer/execution.py)  per task: ContentAgent → LearningContent
        ▲                             QuizAgent → Quiz            (loop over tasks)
        └── more tasks? ──┘
  4. REFLECTION (layer/reflection.py) outputs vs goal → ProgressReport + recommendations
  ▼
outputs/learning_plan_<id>.md
```

### Directory Structure

```
chapter_5/section_3/
├── src/
│   ├── layer/
│   │   ├── base.py          # BaseAgent: LLM call + robust JSON parsing + retries
│   │   ├── strategy.py      # Strategy layer (戦略・プランニング層)
│   │   ├── tactics.py       # Tactics layer (戦術・マネジメント層)
│   │   ├── execution.py     # Execution layer: ContentAgent / QuizAgent
│   │   └── reflection.py    # Reflection layer (自己評価・省察層)
│   ├── service/llm_pipeline_service.py   # LangGraph orchestration
│   ├── model/llm_pipeline_model.py       # per-layer Pydantic models + state
│   ├── prompt/llm_pipeline_prompt.py     # per-layer prompts
│   ├── client/llm_client.py              # OpenAI client + model enum
│   ├── main.py                           # CLI (Click)
│   └── config.py / logger.py
├── example/learner_profile.json
├── outputs/
├── REFERENCE.md              # architectural principles for hierarchical agents
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Layer contracts as Pydantic models (`src/model/llm_pipeline_model.py`)

```
StrategyOutput   = LearningRoadmap (modules, milestones) + levels
TacticsOutput    = WeeklyPlan[] + DailyTask[]           # execution's ToDo list
LearningSession  = LearningContent + Quiz (QuizQuestion[])
ProgressReport   = ProgressMetrics + recommendations     # reflection's verdict
HierarchicalAgentState = LangGraph state carrying all of the above
```

Every layer boundary is a schema — swapping a layer's implementation cannot corrupt its neighbors.

### 2. State machine flow (`src/service/llm_pipeline_service.py`)

```
strategy -> tactics -> execution (loop while tasks remain) -> reflection -> END
```

### 3. Robust JSON handling in the shared base agent (`src/layer/base.py`)

- Extraction strategies in order: raw JSON → markdown code block → brace matching
- Truncated-JSON repair (close unclosed brackets/braces)
- Retry with `MAX_RETRIES=3` on parse failure

### 4. Reflection as independent audit (`src/layer/reflection.py`)

The reflection agent receives the goal, the plan, and execution outputs — and returns quality scores, goal-alignment checks, and improvement recommendations that are attached to the final report.

## Data Models

| Model | Layer | Purpose |
|-------|-------|---------|
| `LearnerProfile` | input | goal, current knowledge, hours/week, duration |
| `LearningModule` / `LearningRoadmap` / `StrategyOutput` | Strategy | blueprint |
| `DailyTask` / `WeeklyPlan` / `TacticsOutput` | Tactics | task decomposition |
| `LearningContent` / `Quiz` / `QuizQuestion` / `LearningSession` | Execution | deliverables |
| `ProgressMetrics` / `ProgressReport` | Reflection | audit result |
| `PersonalizedLearningPlan` / `HierarchicalAgentState` | — | final artifact / graph state |

## Setup & Run

> **Runtime scales with plan size**: every day × task in the plan costs multiple LLM calls (content + quiz). A 1-week plan (`-d 1`) takes ~5 minutes; a 12-week plan takes much longer. Start small.

```bash
cp .envrc.example .envrc     # set OPENAI_API_KEY
uv sync

# Canonical (small, fast) example
uv run python -m src.main -g '1週間でPythonの基礎を学びたい' -h 3 -d 1

# Larger plan / profile file / knowledge priors
uv run python -m src.main -g "3ヶ月でPythonプログラミングを習得したい" -h 10 -d 12
uv run python -m src.main -p example/learner_profile.json
uv run python -m src.main -g "データ分析を学びたい" -k "Excel基礎,統計基礎"
```

### CLI Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--goal` | `-g` | — | Learning goal (natural language) |
| `--hours-per-week` | `-h` | 10 | Available study hours per week |
| `--duration-weeks` | `-d` | 12 | Target duration — the main runtime/cost knob |
| `--current-knowledge` | `-k` | "" | Comma-separated existing skills |
| `--profile-file` | `-p` | — | Learner profile JSON (alternative to flags) |
| `--model` | `-m` | `openai.gpt-5.4` | OpenAI model |
| `--output-directory` | `-od` | `outputs` | Output directory |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
```

## Implementation Notes

- **Why layers instead of one planner prompt**: a single "make me a full learning plan" prompt produces shallow, inconsistent plans. Splitting interpretation (strategy) from decomposition (tactics) from production (execution) lets each prompt be small, focused, and independently improvable — and reflection catches drift between them.
- **Trade-offs (from REFERENCE.md)**: latency multiplies with layers; layer interfaces add design work; upper-layer errors propagate downward (a bad roadmap yields a bad everything); rigid hierarchies can suppress useful bottom-up signals. Reflection mitigates but doesn't eliminate these.
- **Build bottom-up**: implement and test execution agents first with hand-written tasks, then add tactics, then strategy — each layer's tests use fixture inputs shaped like the layer above's output.
- **Skill levels and content types are closed enums** (beginner…advanced; video/article/interactive/exercise/project) so plans stay renderable and comparable.
- **Cost control lives at the tactics/execution boundary**: cap sessions per run, or generate content lazily (only the first week) as this demo does.

## How to Apply This Practice to Your Own Project

1. Identify the abstraction levels in your task (interpret → decompose → produce → audit) and define one Pydantic contract per boundary.
2. Implement a shared `BaseAgent` with hardened JSON parsing and retries; every layer agent extends it.
3. Orchestrate layers as a state machine (LangGraph or Chapter 4 Section 4's pattern) with an explicit execution loop and cap.
4. Make the reflection layer independent — different prompt, evaluating against the *original* goal, empowered to recommend corrections.
5. Expose plan-size knobs (duration, budget) as first-class parameters; never infer scale from prose.
6. Test each layer with fixtures of its upstream contract before wiring the full hierarchy.
