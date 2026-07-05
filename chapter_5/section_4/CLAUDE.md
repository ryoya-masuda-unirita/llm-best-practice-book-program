# Chapter 5 Section 4: Pipeline Agent — Contract Risk Compliance Evaluation

## What This Section Demonstrates

This section implements the **Pipeline Agent pattern**: a linear sequence of stages, each with one responsibility and a typed output contract, composed as a LangGraph state machine — `extraction → risk_scoring → report`.

Given a contract document, the pipeline extracts its structure (chapters/sections/parties), assesses risk **per section, concurrently** (semaphore-bounded fan-out inside the risk stage), then generates a compliance report with executive summary, severity distribution, and recommendations.

Compared with the hierarchical agent (Chapter 5 Section 3) and orchestrator-worker (Chapter 5 Section 2), the pipeline is the simplest multi-stage shape: no planner, no dynamic routing — just a fixed sequence with strict contracts. Apply it when the processing steps are known and stable, and what you need is reliability, per-stage testability, and internal parallelism.

## Practice Rules

1. **Fix the stage sequence in the graph** (`extraction → risk_scoring → report → END`); no conditional routing unless the domain demands it.
2. **Split each stage's I/O into Response vs Output models**: `*Response` (what the LLM returns, lenient) is converted by the agent into `*Output` (frozen, validated domain objects) — LLM output never flows downstream raw.
3. **Make domain objects immutable** (`FrozenModel` base) — pipeline state accumulates; stages must not mutate upstream artifacts.
4. **Parallelize inside stages, not across them**: risk scoring fans out per section with `asyncio.gather` + `Semaphore(CONCURRENCY_LIMIT)` while the pipeline stays sequential.
5. **Validate stage preconditions explicitly** (`if extraction is None: raise ValueError(...)`) — a pipeline stage must fail loudly if its upstream contract is unmet.
6. **Share agent plumbing in a `BaseAgent`** (model-from-config, message building, structured invoke, layer logging) so each stage class contains only its stage logic.
7. **Use closed enums for risk vocabulary** (`RiskLevel`: low/medium/high/critical, `RiskCategory`, `ComplianceStatus`) so scores aggregate deterministically.

## Architecture

```
CLI (src/main.py)  -c contract.md
  ▼
LangGraph: ContractPipelineState
  [1] extraction_stage_node   (ExtractionAgent)
        contract text → ExtractionResponse → ExtractionOutput
        (chapters, sections, parties)
  ▼
  [2] risk_scoring_stage_node (RiskScoringAgent)
        per section (concurrent, Semaphore(CONCURRENCY_LIMIT)):
          RiskScoringResponse → SectionRiskAssessment (findings, category, level)
  ▼
  [3] report_stage_node       (ReportAgent)
        assessments → ComplianceReport (executive summary, severity distribution,
                                        risk breakdown, recommendations)
  ▼
outputs/compliance_report_<id>.md
```

### Directory Structure

```
chapter_5/section_4/
├── src/
│   ├── layer/
│   │   ├── base.py                      # BaseAgent: config/model/messages/structured invoke
│   │   └── contract_pipeline/
│   │       ├── extraction.py            # ExtractionAgent + stage node
│   │       ├── risk_scoring.py          # RiskScoringAgent (parallel sections) + stage node
│   │       └── report.py                # ReportAgent + stage node
│   ├── service/service.py               # graph factory + runner + state init
│   ├── model/model.py                   # Response/Output model pairs + enums + state
│   ├── prompt/prompt.py                 # per-stage system/user prompts
│   ├── client/llm_client.py             # OpenAI model enum
│   ├── main.py                          # CLI (Click)
│   └── config.py / logger.py
├── data/contract_0.md ...               # sample contracts
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Fixed pipeline graph (`src/service/service.py`)

```python
graph = StateGraph(ContractPipelineState)
graph.add_node("extraction", extraction_stage_node)
graph.add_node("risk_scoring", risk_scoring_stage_node)
graph.add_node("report", report_stage_node)
graph.set_entry_point("extraction")
graph.add_edge("extraction", "risk_scoring")
graph.add_edge("risk_scoring", "report")
graph.add_edge("report", END)
```

### 2. Response→Output conversion at each stage boundary (`src/layer/contract_pipeline/extraction.py`)

```python
class ExtractionAgent(BaseAgent):
    def _convert_response_to_output(self, response: ExtractionResponse, contract_id: str) -> ExtractionOutput:
        # LLM-shaped ExtractionResponse → frozen domain ExtractionOutput
        # (ContractStructure with ContractChapter/ContractSection, parties)
```

### 3. Bounded concurrency inside the risk stage (`src/layer/contract_pipeline/risk_scoring.py`)

```python
async def execute_async(self, state, config) -> dict:
    extraction = state["extraction_output"]
    if extraction is None:
        raise ValueError("Risk scoring requires extraction output")   # precondition

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    tasks = [self._assess_section_async(section, parties, config, semaphore)
             for section in state["pending_sections"]]
    assessments = await asyncio.gather(*tasks)      # sections assessed concurrently
```

### 4. Immutable domain models (`src/model/model.py`)

```python
class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, ...)

class RiskLevel(StrEnum): ...               # low / medium / high / critical
class SectionRiskAssessment(FrozenModel): ...   # section + findings + overall_risk_level
class ComplianceReport(FrozenModel): ...        # summary + distribution + recommendations
```

## Data Models

| Pair | Purpose |
|------|---------|
| `ExtractionResponse` → `ExtractionOutput` (`ContractStructure`) | Stage 1: document structure + parties |
| `RiskScoringResponse` → `SectionRiskAssessment` (`RiskFinding`) | Stage 2: per-section risk with findings |
| `ReportResponse` → `ComplianceReport` (`ExecutiveSummary`, `RiskBreakdown`, `SeverityDistribution`) | Stage 3: deliverable |
| `RiskLevel` / `RiskCategory` / `ComplianceStatus` | Closed risk vocabulary |
| `ContractPipelineState` | TypedDict graph state |

## Setup & Run

```bash
cp .envrc.example .envrc     # set OPENAI_API_KEY
uv sync

# Canonical example
uv run python -m src.main -c data/contract_0.md
```

### CLI Options

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--contract-file` | `-c` | Yes | Contract document to evaluate |
| `--model` | `-m` | No | OpenAI model |
| `--output-directory` | `-od` | No | Report output directory |

Output: `outputs/compliance_report_<id>.md` with overall status (e.g. `non_compliant`) and a 0–100 risk score.

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
```

## Implementation Notes

- **Pipeline vs hierarchy vs orchestrator-worker**: choose the pipeline when the steps are fixed and knowable; hierarchy (5-3) when the goal needs progressive interpretation; orchestrator-worker (5-2) when a planner should decide task decomposition at runtime. All three share the "typed contracts between agents" discipline.
- **The Response/Output split is the pipeline's immune system**: LLM responses are validated at the boundary and converted to frozen domain objects; any schema drift is caught at one stage instead of corrupting the report two stages later.
- **Section-level fan-out** is where the wall-clock win lives — a 20-section contract assesses in ~(20 / CONCURRENCY_LIMIT) × per-call latency. The semaphore protects your rate limit (same pattern as Chapter 3 Section 3).
- **Preconditions over defensive defaults**: a stage that silently continues without its input produces a plausible but hollow report — `raise ValueError` is the correct behavior.
- **Per-stage testing**: each agent's `_convert_response_to_output` and stage node can be tested with fixture Responses; graph tests stub the three nodes.

## How to Apply This Practice to Your Own Project

1. Write the stage list and the frozen domain model each stage must produce; define Response twins for the LLM boundary.
2. Implement one agent class per stage over a shared `BaseAgent`; keep stage nodes as thin wrappers.
3. Wire the fixed sequence in a graph; add explicit precondition checks at every stage entry.
4. Fan out per-item LLM calls inside stages with `gather` + semaphore; keep the stage sequence serial.
5. Use closed enums for anything you'll aggregate (levels, categories, statuses).
6. Version the final report model — downstream consumers (dashboards, approvals) will depend on its shape.
