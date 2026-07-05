# Chapter 4 Section 4: LLM Pipelines as State Machines with LangGraph

## What This Section Demonstrates

This section implements a multi-stage document-analysis pipeline as a **LangGraph state machine**: read document → analyze (OpenAI or Gemini) → judge the analysis (LLM-as-a-Judge, grade 1–5) → retry with feedback if the grade is too low (bounded retries) → save results.

The practice: when an LLM workflow has branching (provider routing), loops (quality-gated retry), and shared state, model it as an **explicit graph with typed state and pure routing functions** rather than nested if/else and while loops. The graph is inspectable, each node is unit-testable, and control flow is declared in one place. Apply this to any workflow beyond a linear chain — quality-retry loops, provider fallbacks, human-approval gates.

## Practice Rules

1. **Define the state as a `TypedDict` first** (`PipelineState`: document path/content, analysis result, evaluation result, retry_count, error). Every node reads and returns this state.
2. **Nodes do work; routers decide.** Node functions (`read_document_node`, `analyze_*_node`, `judge_*_node`) are async state transformers; routing functions (`route_to_llm_provider`, `route_to_judge`, `route_after_judge`) are pure, synchronous, and return `Literal` labels.
3. **Type router returns as `Literal[...]`** so the mapping in `add_conditional_edges` is checkable against reality.
4. **Carry errors in state, not exceptions.** Nodes set `state["error"]`; every router short-circuits to `"end"` when it's set — one error-handling convention across the whole graph.
5. **Bound every loop with a counter in state** (`retry_count` vs `MAX_RETRIES`) and define the exhaustion behavior explicitly (accept the best-effort analysis, warn).
6. **Gate quality with LLM-as-a-Judge in the graph** — `AnalysisEvaluation.is_acceptable()` decides retry vs end; the judge's `specific_improvements` feed the retry prompt.
7. **Compile the graph in a factory function** (`create_document_analysis_graph()`), keeping construction separate from execution (`run_document_analysis_pipeline`).

## Architecture

```
START
  ▼
read_document ── route_to_llm_provider ──┬─▶ analyze_openai ─┐
  (error → END)                          └─▶ analyze_gemini ─┤
                                                             ▼
                                              route_to_judge ├─▶ judge_openai ─┐
                                              (error → END)  └─▶ judge_gemini ─┤
                                                                               ▼
                                                              route_after_judge
                                              grade acceptable ──────────▶ END
                                              grade low & retries left ─▶ analyze_* (loop, retry_count++)
                                              retries exhausted ────────▶ END (accept best effort)
```

### Directory Structure

```
chapter_4/section_4/
├── src/
│   ├── service/llm_pipeline_service.py   # nodes + routers + graph factory + runner
│   ├── model/llm_pipeline_model.py       # PipelineState / DocumentAnalysis / AnalysisEvaluation
│   ├── prompt/llm_pipeline_prompt.py     # analysis + judge + retry-with-feedback prompts
│   ├── client/llm_client.py              # OpenAI/Gemini clients + model enums
│   ├── main.py                           # CLI: -lp provider -m model -dp document
│   └── config.py / logger.py
├── dataset/                              # sample documents (document_0.md ...)
├── tests/                                # node/router/model tests
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Typed state (`src/model/llm_pipeline_model.py`)

```python
class PipelineState(TypedDict):
    document_path: str
    document_content: str
    analysis_result: DocumentAnalysis | None
    evaluation_result: AnalysisEvaluation | None
    retry_count: int
    error: str | None
```

### 2. Pure routers with Literal returns (`src/service/llm_pipeline_service.py`)

```python
def route_after_judge(state: PipelineState) -> Literal["analyze_openai", "analyze_gemini", "end"]:
    if state.get("error"):
        return "end"
    evaluation_result = state.get("evaluation_result")
    if evaluation_result.is_acceptable():
        return "end"
    if state.get("retry_count", 0) >= MAX_RETRIES:
        logger.warning("Max retries reached. Accepting analysis with grade ...")
        return "end"
    state["retry_count"] = state.get("retry_count", 0) + 1
    return "analyze_openai" if provider == LLMProvider.OPENAI else "analyze_gemini"
```

### 3. Declarative wiring (`create_document_analysis_graph`)

```python
graph = StateGraph(PipelineState)
graph.add_node("read_document", read_document_node)
graph.add_node("analyze_openai", analyze_document_openai_node)
...
graph.add_edge(START, "read_document")
graph.add_conditional_edges("read_document", route_to_llm_provider,
    {"analyze_openai": "analyze_openai", "analyze_gemini": "analyze_gemini", "end": END})
graph.add_conditional_edges("judge_openai", route_after_judge,
    {"analyze_openai": "analyze_openai", "analyze_gemini": "analyze_gemini", "end": END})
return graph.compile()
```

All control flow is visible in ~40 lines; nodes contain none of it.

### 4. Judge schema drives the loop

```python
class AnalysisEvaluation(BaseModel):
    grade: Literal[1, 2, 3, 4, 5]
    reasoning: str
    specific_improvements: list[str]     # fed into the retry prompt
```

The retry analysis prompt includes prior `specific_improvements`, so each iteration addresses concrete feedback instead of re-rolling.

## Data Models

| Model | Purpose |
|-------|---------|
| `PipelineState` | Shared graph state (TypedDict) |
| `DocumentAnalysis` | Analysis output: theme, value, improvement_requests (+ save as JSON/Markdown) |
| `AnalysisEvaluation` | Judge verdict: grade 1–5, reasoning, specific_improvements, `is_acceptable()` |

## Setup & Run

```bash
cp .envrc.example .envrc     # OPENAI_API_KEY / GEMINI_API_KEY
uv sync

# Canonical example
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -dp dataset/document_0.md
```

### CLI Options

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--llm-provider` | `-lp` | Yes | `OPENAI` / `GEMINI` (selects both analyzer and judge branch) |
| `--model` | `-m` | Yes | Model enum name |
| `--document-path` | `-dp` | Yes | Document to analyze |
| `--output-directory` | `-od` | No | Output directory |

Outputs: analysis as JSON + Markdown in `outputs/`.

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
uv run pytest tests/ -v      # node / router / model tests (LLM mocked)
```

## Implementation Notes

- **Why a graph beats imperative code here**: the analyze→judge→retry loop with provider branching is 5 nodes × 3 routers declared once; the equivalent nested while/if code buries the control flow and can't be visualized or partially tested.
- **Routers must stay pure and cheap** — they run between every node; put LLM calls only in nodes.
- **Error-in-state convention**: exceptions inside nodes are caught and recorded (`state["error"]`), which keeps graph execution deterministic and gives END-state consumers a single place to check failure.
- **Retry-with-feedback is materially better than blind retry**: passing the judge's `specific_improvements` into the next analysis prompt converges in 1–2 iterations in practice; blind retries often repeat the same weaknesses.
- **Provider symmetry** (parallel openai/gemini node pairs) keeps each node simple at the cost of some duplication; an adapter-based single node (Chapter 3 Section 1) is the alternative when providers multiply.

## How to Apply This Practice to Your Own Project

1. Write the `TypedDict` state for your workflow: inputs, intermediate artifacts, decision fields (`retry_count`, `error`).
2. Implement each stage as an async node `state -> state`; catch exceptions into `state["error"]`.
3. Extract every decision into a pure router returning `Literal` labels; wire with `add_conditional_edges`.
4. Bound all loops with counters in state and define exhaustion behavior (accept / fail / escalate to human).
5. Put a judge node behind any stage whose quality matters; feed its structured feedback into the retry path.
6. Keep a `create_*_graph()` factory + `run_*` entry point; unit-test routers with hand-built states and nodes with mocked LLM calls.
