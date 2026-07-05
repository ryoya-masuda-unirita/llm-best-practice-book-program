# Chapter 5 Section 2: Multi-Agent System — Orchestrator-Worker Contract Review

## What This Section Demonstrates

This section implements a **multi-agent system with the Orchestrator-Worker pattern** on LangGraph: an orchestrator agent plans the review strategy, then dispatches specialized worker agents — document parser → (clause classifier ∥ risk assessor ∥ diff checker, **in parallel**) → collector → amendment proposer → synthesizer — to review a contract against a standard template and produce a Markdown report.

Each worker is a focused LLM call with its own system prompt and structured-output schema; workers share a typed `AgentState` and are dispatched via LangGraph's `Send` API for fan-out. Apply this pattern when a task decomposes into specialist subtasks with different prompts/criteria, and some of them are independent enough to run concurrently — document review, due diligence, multi-aspect analysis.

## Practice Rules

1. **One agent = one responsibility + one system prompt + one output schema.** The clause classifier knows nothing about risk scoring; the diff checker only compares against the template.
2. **Let the orchestrator plan, not micro-manage**: it produces an `OrchestratorPlan` (strategy, focus areas, task list) via structured output; the graph topology executes the plan.
3. **Fan out independent workers with `Send`** (`dispatch_to_parallel_analyzers` returns three `Send` targets) and **join with a collector node** before dependent stages.
4. **Give the orchestrator a failure default** — if planning fails, fall back to a default sequential plan instead of aborting the run.
5. **Type every inter-agent artifact** (`ContractClause`, `RiskAssessment`, `ClauseDiff`, `AmendmentProposal`…): workers communicate through validated state fields, never prose.
6. **Pass runtime config through `RunnableConfig`** (`config["configurable"]["model"]`) so all agents honor the CLI-selected model without global state.
7. **Synthesize at the end**: a dedicated report generator merges all worker outputs into the human deliverable — workers never write the final report.

## Architecture

```
START ─▶ orchestrator (plan: strategy/focus/tasks — structured output)
            │ Send
            ▼
       document_parser_worker (contract text → ContractClause[])
            │ Send ×3 (parallel fan-out)
   ┌────────┼──────────────┐
   ▼        ▼              ▼
clause_   risk_        diff_checker_worker
classifier assessment  (vs standard template)
   └────────┼──────────────┘
            ▼
        collector (join)
            ▼
 amendment_proposer_worker (fixes for high-risk/deviant clauses)
            ▼
        synthesizer (ContractReviewReport → Markdown)
            ▼
           END
```

### Directory Structure

```
chapter_5/section_2/
├── src/
│   ├── service/multi_agent_service.py   # all agent nodes + dispatchers + graph factories
│   ├── model/multi_agent_model.py       # per-agent response schemas + plan + report + AgentState
│   ├── prompt/multi_agent_prompt.py     # per-agent system prompts
│   ├── client/llm_client.py             # Gemini via langchain-google-genai
│   ├── main.py                          # CLI: contract + template files
│   └── config.py / logger.py
├── example/sample_nda.md / standard_nda_template.md
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Orchestrator plans with structured output + failure default (`src/service/multi_agent_service.py`)

```python
def orchestrator_node(state: AgentState, config: RunnableConfig) -> dict:
    model = ChatGoogleGenerativeAI(model=model_name, temperature=0, ...)\
        .with_structured_output(OrchestratorResponse)
    try:
        response: OrchestratorResponse = model.invoke(messages)
        return {"orchestrator_plan": response.plan, "current_phase": "planning_complete"}
    except Exception:
        default_plan = OrchestratorPlan(tasks=[], strategy="Default sequential review",
                                        focus_areas=["All clauses"])
        return {"orchestrator_plan": default_plan, "current_phase": "planning_failed"}
```

### 2. Parallel fan-out with `Send` and a collector join

```python
graph.add_conditional_edges(
    "document_parser_worker",
    dispatch_to_parallel_analyzers,      # returns [Send("clause_classifier_worker", ...), Send(...), Send(...)]
    ["clause_classifier_worker", "risk_assessment_worker", "diff_checker_worker"],
)
graph.add_edge("clause_classifier_worker", "collector")
graph.add_edge("risk_assessment_worker", "collector")
graph.add_edge("diff_checker_worker", "collector")     # join point
graph.add_edge("collector", "amendment_proposer_worker")
```

The three analyzers run concurrently — wall-clock time is max(worker latencies), not the sum.

### 3. Specialist workers with typed outputs

Each `*_node` binds its own schema: `DocumentParserResponse` (clauses), `ClauseClassifierResponse` (categories), `RiskAssessmentResponse` (risk level + reasoning per clause), `DiffCheckerResponse` (deviations from the template), `AmendmentProposerResponse` (proposed fixes), `ReportGeneratorResponse` (final report structure).

### 4. Model selection flows through config

```python
model_name = config.get("configurable", {}).get("model", GeminiModel.GEMINI_2_5_PRO)
```

One CLI flag configures every agent — no globals, no per-node hardcoding.

## Data Models

| Model | Purpose |
|-------|---------|
| `OrchestratorPlan` / `TaskAssignment` / `OrchestratorResponse` | Planning output |
| `ContractClause` / `ClauseCategory` / `RiskAssessment` / `ClauseDiff` / `AmendmentProposal` | Inter-agent artifacts |
| `*Response` per worker | Structured output schema per agent |
| `ContractReviewReport` | Final synthesized report |
| `AgentState` | Shared graph state carrying all of the above |

## Setup & Run

```bash
cp .envrc.example .envrc     # set GEMINI_API_KEY
uv sync

# Canonical example (sample NDA vs standard template)
uv run python -m src.main -c example/sample_nda.md -t example/standard_nda_template.md
```

### CLI Options

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--contract-file` | `-c` | Yes | Contract document (Markdown) |
| `--template-file` | `-t` | Yes | Standard template to compare against |
| `--model` | `-m` | No | Gemini model (default `GEMINI_2_5_PRO`) |
| `--output-directory` | `-od` | No | Report output directory |

Output: `outputs/contract_review_<id>.md`.

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
```

## Implementation Notes

- **Why multiple agents instead of one big prompt**: specialist prompts with narrow schemas measurably beat a single "review everything" prompt on consistency — each worker's context contains only what its task needs, and each output is independently validated.
- **Parallelism is a topology decision**: classification, risk scoring, and diff checking all depend only on parsed clauses, so they fan out; amendment proposals need all three, so a collector joins before it. Draw the dependency graph first; parallelize the independent branches.
- **The run takes on the order of minutes with 7 LLM calls** — multi-agent quality costs latency and tokens. Reserve the pattern for high-stakes documents where thoroughness pays.
- **Failure containment**: the orchestrator's default plan and per-worker try/except keep one agent's failure from destroying the run; the report notes what's missing.
- **Subgraph factories** (`create_*_subgraph`) exist alongside the orchestrator-worker graph — each worker is also packaged as a standalone compiled graph, usable and testable in isolation.

## How to Apply This Practice to Your Own Project

1. Decompose your review/analysis task into specialists; write one system prompt + one output schema per specialist.
2. Draw the dependency DAG between specialists; use `Send` fan-out + collector joins for the independent branches.
3. Give the orchestrator a planning schema (strategy, focus, tasks) and a safe default plan on failure.
4. Keep all inter-agent communication in typed state fields; ban free-text handoffs.
5. Thread model/config through `RunnableConfig` so deployments can tune per-environment.
6. Budget the run: (number of agents) × (per-call latency/cost) — cut agents that don't earn their slot, or merge sequential ones with compatible prompts.
