# Chapter 6 Section 6: Tool Chain Pattern — Plan Once, Execute Without Round Trips

## What This Section Demonstrates

Standard function calling is a round trip per tool: call → result into context → model thinks → next call. For multi-step data work, most of those round trips (and their token costs) are waste. This section implements the **Tool Chain pattern**: the LLM **plans the whole chain upfront** as a structured object (steps, input mappings, objective), the system **validates and dry-runs** the plan, then executes all steps locally — passing outputs between tools directly ("bucket relay") — and returns only the final result to the model for report generation.

Same school-data domain as Chapter 6 Section 5; the difference is *when* the model is involved: 6-5 keeps the model in the loop per call, 6-6 moves it to plan-time and report-time only. Apply this when tool sequences are predictable from the request and intermediate results don't require model judgment — ETL-ish analysis, report assembly, fixed data workflows.

## Practice Rules

1. **Force plan-first**: the system prompt requires the model to define a tool chain (name, objective, steps) via structured output before any data operation.
2. **Validate the plan before running it** (`validate_chain`): every tool exists, input mappings reference available keys, categories are compatible. Reject with a specific error message the model can fix.
3. **Dry-run to check data flow** (`dry_run`) — simulate key propagation through the chain without executing tools; catches wiring bugs for free.
4. **Execute with explicit data plumbing**: each `ChainStepConfig` declares `input_mapping` (which previous output keys feed which parameters); `_resolve_input` wires step N's output into step N+1 without model involvement.
5. **Stop on first failure with a typed result** — `ToolChainResult` records per-step `ChainStepResult`s; a failed step ends the chain with the error preserved.
6. **Describe tools with machine-readable metadata** (`ToolMetadata`: category, input/output keys) — the model plans from metadata, so metadata quality determines plan quality.
7. **Keep the ID-reference cache for the final result** (`SessionResultCache`, as in 6-5) — even the final output returns summary + result_id.

## Architecture

```
User query
  ▼
Gemini (structured output: ToolChainResponseSchema)
  "plan_tool_chain": name / objective / steps[tool_name, input_mapping]
  ▼
execute_planned_tool_chain (src/service/request_llm.py)
  ├─ validate_chain()   ← tool existence, key compatibility → error message back to model on failure
  ├─ dry_run()          ← simulate key flow, no execution
  └─ execute()          ← bucket relay:
        Tool A ──output_keys──▶ input_mapping ──▶ Tool B ──▶ ... ──▶ final output
  ▼
final result (summary + result_id) → Gemini → user-facing report
```

### Directory Structure

```
chapter_6/section_6/
├── src/
│   ├── service/
│   │   ├── request_llm.py            # plan → validate → execute loop + SessionResultCache
│   │   └── tools/
│   │       ├── tool_chain.py         # ToolChainExecutor: validate / dry_run / execute
│   │       ├── tool_metadata.py      # ToolMetadata registry (planning surface)
│   │       ├── data_tools.py         # school-data tools
│   │       └── functions/            # loaders / analyzers / formatters / validators
│   ├── model/
│   │   ├── tool_chain_models.py      # ChainStepConfig / ToolChainConfig / results + response schema
│   │   └── model.py / schemas.py
│   ├── prompt/prompt.py              # plan-first system prompt + chain feedback messages
│   ├── client/llm_client.py / main.py / config.py / logger.py
├── data/                             # school records
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. The chain is a validated Pydantic plan (`src/model/tool_chain_models.py`)

```python
class ChainStepConfig(BaseModel):
    tool_name: str
    input_mapping: ...       # previous-output key → parameter name
class ToolChainConfig(BaseModel):
    name: str
    steps: list[ChainStepConfig]
    initial_input: ...
class ToolChainResult(BaseModel):
    step_results: list[ChainStepResult]
    final_output: ...
```

The model emits `ToolChainResponseSchema` via structured output — the plan itself is typed data.

### 2. Validate → dry-run → execute (`src/service/tools/tool_chain.py`)

```python
class ToolChainExecutor:
    def validate_chain(self, chain_config) -> ...:   # tools exist? keys compatible?
    def dry_run(self, chain_config) -> ...:          # simulate key propagation
    def execute(self, chain_config) -> ToolChainResult:
        previous_output = None
        for i, step in enumerate(chain_config.steps):
            resolved_input = self._resolve_input(step, previous_output, chain_config.initial_input)
            step_result = self._execute_step(step, i, resolved_input)
            if not step_result.success:
                return ToolChainResult(...)          # stop on first failure, error preserved
            previous_output = step_result.output
```

### 3. Validation errors go back to the planner

```python
# request_llm.py: on validation failure, get_chain_validation_error_message(...)
# is returned to Gemini so it can re-plan with the specific problem named.
```

### 4. Metadata as the planning surface (`src/service/tools/tool_metadata.py`)

```python
@dataclass
class ToolMetadata:
    # name, category (ToolCategory), description, input keys, output keys
```

The model never sees implementations — only this metadata; chains are only as good as these declarations.

## Data Models

| Model | Purpose |
|-------|---------|
| `ToolChainConfig` / `ChainStepConfig` | The LLM-authored plan |
| `ToolChainResult` / `ChainStepResult` | Execution record, per step |
| `ToolMetadata` / `ToolCategory` | Planning surface for the model |
| `ToolChainResponseSchema` (+ `KeyValuePair`) | Structured-output schema for plan emission |
| `SessionResultCache` | result_id → detailed data (ID reference pattern) |

## Setup & Run

```bash
cp .envrc.example .envrc     # set GEMINI_API_KEY
uv sync

# Canonical example
uv run python -m src.main --query '数学の成績を分析してください'
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--query` | Analysis request in natural language |
| `--model` / `-m` | Gemini model |
| `--output-directory` | Output directory |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
```

## Implementation Notes

- **Tool chain vs per-call function calling (6-5)**: chains cut LLM round trips from N to 2 (plan + report) — lower latency and tokens — but give up mid-course correction: the model can't react to surprising intermediate data. Choose per workflow; hybrid systems let the model pick between `plan_tool_chain` and direct calls.
- **Validation + dry-run are what make LLM-authored plans safe to execute** — the model routinely names wrong keys or misorders steps; catching that *before* running tools converts silent garbage into a re-planning loop.
- **Watch for empty-result reports**: if the chain executes but yields `[]`, the report generator will still write a report "based on empty results". Guard the report step with an emptiness check and route back to re-planning — this failure mode is visible in this demo when the plan filters incorrectly.
- **The bucket-relay `input_mapping`** is deliberately explicit (no magic auto-wiring): the plan documents exactly which output feeds which parameter, making chains auditable.
- **Structured output quirk**: Gemini's schema limitations are why `KeyValuePair` lists (not free dicts) carry mappings in `ToolChainResponseSchema` (converted by `key_value_list_to_dict`).

## How to Apply This Practice to Your Own Project

1. Write `ToolMetadata` for every tool (category, input/output keys) — this, not the code, is what the model plans against.
2. Define the plan schema (`ToolChainConfig` + response schema) and require plan-first in the system prompt.
3. Implement the executor triad: `validate_chain` → `dry_run` → `execute` with stop-on-failure and typed step results.
4. Feed validation errors back to the model as re-planning prompts (bounded retries).
5. Guard the final report against empty/degenerate chain outputs.
6. Offer both modes (chain + per-call) and log which the model chooses — that data tells you where chains actually pay off.
