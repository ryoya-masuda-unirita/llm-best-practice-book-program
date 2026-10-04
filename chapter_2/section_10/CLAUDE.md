# Chapter 2 Section 10: Prompt Performance Profiling

## What This Section Demonstrates

You can't optimize prompts you don't measure. This section implements a **prompt performance profiler**: an async context manager that transparently wraps LLM calls and records latency, token usage, estimated cost, status, and (optionally) an LLM-as-a-Judge quality score per request — then aggregates those metrics, detects anomalies against baselines, and renders reports (text/JSON/HTML).

The system is a 3-layer pipeline — **Collection → Analysis → Visualization** — deliberately mirroring how observability stacks are built, so each layer can be swapped (e.g. ship metrics to Grafana instead of local reports). Apply this practice when you need data to decide between prompts, models, or providers, or to catch latency/cost/quality regressions in production.

## Practice Rules

1. **Collect via a context manager, not scattered instrumentation.** `async with profiler.profile(...) as ctx:` brackets the call; callers only fill in `ctx["input_tokens"]` / `ctx["output_tokens"]` / `ctx["quality_score"]` — everything else (timing, status, errors, cost) is captured automatically in `finally`.
2. **One metrics record per request, typed** (`ProfilerMetrics`): prompt_id, request_id, prompt_name, latency_ms, tokens in/out/total, model, provider, status, cost, quality score, metadata.
3. **Store metrics asynchronously** (`asyncio.create_task(self._store_metrics(...))`) so profiling never blocks the response path.
4. **Estimate cost from a pricing table keyed by provider+model** (`TOKEN_PRICING` in `prompt_profiler.py`); return `None` for unknown models instead of guessing.
5. **Analyze with aggregations, not raw logs**: group by prompt/model/provider/time-bucket; compute mean/median/P95/P99/stddev.
6. **Alert on both absolute and relative thresholds** — "latency > 10s" AND "latency > 200% of this prompt's baseline". Baselines come from `calculate_baseline` over historical records.
7. **Keep quality measurement optional and pluggable** — the profiler accepts a quality score from any source; here it comes from LLM-as-a-Judge (Section 7).

## Architecture

```
CLI (src/main.py) ── standard path ──▶ request_llm.py (unprofiled)
        └── --enable-profiling ──▶ profiled_request_llm.py
                                        │
                       ┌────────────────┴─────────────────┐
                       ▼                                  ▼
        [Collection] PromptProfiler          LLM-as-a-Judge (optional quality)
          async with profile(...) as ctx
          → ProfilerMetrics → async store
                       ▼
        [Analysis] MetricsAnalyzer
          aggregate_by_prompt/model/provider/time_bucket
          calculate_baseline / detect_anomalies / generate_alerts
                       ▼
        [Visualization] ProfilerReporter
          text (terminal) / JSON (Grafana・Kibana) / HTML (dashboard)
```

### Directory Structure

```
chapter_2/section_10/
├── src/
│   ├── main.py                        # CLI (generation ± profiling ± judge)
│   ├── client/llm_client.py           # 3-provider clients + model enums
│   ├── model/
│   │   ├── model.py                   # character generation schemas
│   │   ├── llm_as_a_judge_model.py    # judge schemas
│   │   └── profiler_metrics.py        # ProfilerMetrics / MetricStatus / thresholds
│   ├── prompt/                        # generation + judge prompts
│   └── service/
│       ├── request_llm.py             # unprofiled request path
│       ├── profiled_request_llm.py    # profiled request path
│       ├── prompt_profiler.py         # [Collection] profiler + TOKEN_PRICING + estimate_cost
│       ├── metrics_analyzer.py        # [Analysis] aggregation/baseline/anomaly/alerts
│       ├── profiler_reporter.py       # [Visualization] text/JSON/HTML reports
│       └── llm_as_a_judge.py          # quality scoring
├── tests/                             # profiler / analyzer / reporter tests
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Transparent collection wrapper (`src/service/prompt_profiler.py`)

```python
async with profiler.profile(prompt_id="gen", model="openai.gpt-5.4", provider="openai") as ctx:
    result = await client.generate(...)
    ctx["input_tokens"] = result.usage.input_tokens
    ctx["output_tokens"] = result.usage.output_tokens
```

Inside, the `finally` block builds the record no matter what happened:

```python
finally:
    latency_ms = (time.perf_counter() - start_time) * 1000
    estimated_cost = estimate_cost(provider=provider, model=model,
                                   input_tokens=input_tokens, output_tokens=output_tokens)
    metrics = ProfilerMetrics(prompt_id=..., latency_ms=latency_ms, ...,
                              quality_score=context.get("quality_score"),
                              estimated_cost_usd=estimated_cost, metadata=metadata)
    asyncio.create_task(self._store_metrics(metrics))     # non-blocking persist
```

### 2. Pricing table + safe cost estimation (`src/service/prompt_profiler.py`)

```python
TOKEN_PRICING = {
    "openai":    {"openai.gpt-5.4": {...}, ...},
    "gemini":    {"global.anthropic.claude-haiku-4-5-20251001-v1:0": {...}, ...},
    "anthropic": {
        "global.anthropic.claude-sonnet-4-6": {"input": 0.003, "output": 0.015},
        "global.anthropic.claude-sonnet-4-6":   {"input": 0.015, "output": 0.075},
        "global.anthropic.claude-sonnet-4-6":   {"input": 0.003, "output": 0.015},
        "global.anthropic.claude-sonnet-4-6":   {"input": 0.015, "output": 0.075},
    },
}

def estimate_cost(provider, model, input_tokens, output_tokens) -> Optional[float]:
    model_pricing = TOKEN_PRICING.get(provider.lower(), {}).get(model.lower())
    if not model_pricing:
        return None            # unknown model → no estimate, never a guess
```

(Prices are per-1K-token illustrative values; update the table to current list prices for real accounting.)

### 3. Baseline-relative anomaly detection (`src/service/metrics_analyzer.py`)

`MetricsAnalyzer` provides `aggregate_metrics`, `aggregate_by_prompt/model/provider/time_bucket`, `calculate_baseline`, `detect_anomalies`, `generate_alerts`, `compare_prompts`. Alerts fire on absolute thresholds and on deviation from the per-prompt baseline (e.g. latency > 200% of baseline).

Default thresholds:

| Metric | Warning | Critical |
|--------|---------|----------|
| Latency | 5000ms | 10000ms |
| Tokens | 8000 | 16000 |
| Quality | 3.0 | 2.0 |
| Cost | $0.10 | $0.50 |

### 4. Multi-format reporting (`src/service/profiler_reporter.py`)

Text for terminals, JSON for Grafana/Kibana ingestion, HTML for a self-contained dashboard — same analyzed data, three renderers.

## Data Models

| Model | Purpose |
|-------|---------|
| `ProfilerMetrics` | One record per profiled request (latency, tokens, cost, status, quality) |
| `MetricStatus` | success / error status enum |
| `AlertThreshold` | Configurable warning/critical bounds per metric |
| `CharacterRequest/Response`, `JudgeRequest/Response` | Demo task + quality-evaluation schemas |

## Setup & Run

```bash
cp .envrc.example .envrc     # OPENAI_API_KEY / GEMINI_API_KEY / ANTHROPIC_API_KEY
uv sync

# Canonical example: generation with profiling enabled
uv run python -m src.main -g FEMALE -a 25 -lp ANTHROPIC -m CLAUDE_HAIKU_4_5 -p

# With separate judge provider and HTML report
uv run python -m src.main -g FEMALE -a 22 -lp ANTHROPIC -m CLAUDE_HAIKU_4_5 \
  -jp ANTHROPIC -jm CLAUDE_SONNET_4_6 -p -prf html
```

### CLI Options

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--gender` / `--age` / `--additional-instructions` | `-g` / `-a` / `-ai` | g,a: Yes | Character request |
| `--llm-provider` / `--model` | `-lp` / `-m` | Yes | Generation provider/model |
| `--judge-provider` / `--judge-model` | `-jp` / `-jm` | No | Quality judge (optional) |
| `--enable-profiling` | `-p` | No | Turn profiling on |
| `--profiler-report-format` | `-prf` | No | `txt` / `json` / `html` |
| `--output-directory` | `-od` | No | Output directory |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
uv run pytest tests/ -v     # test_prompt_profiler / test_metrics_analyzer / test_profiler_reporter
```

## Implementation Notes

- **Profiled vs unprofiled paths coexist** (`request_llm.py` vs `profiled_request_llm.py`) so you can measure the overhead and adopt profiling incrementally. The wrapper itself adds microseconds; the optional judge call is the expensive part.
- **`perf_counter`, not `time.time`**, for latency — monotonic and immune to clock adjustments.
- **Fire-and-forget persistence** trades durability for latency: a crash can lose the last records. Production variants should flush to a real sink (OTLP, StatsD, BigQuery) with buffering.
- **Baselines make alerts meaningful**: absolute thresholds catch catastrophes; relative-to-baseline detection catches slow drifts (a prompt that got 40% slower is invisible to a 10s absolute limit).
- **Quality is just another metric here** — piping the Section 7 judge score into `ctx["quality_score"]` means cost, latency, and quality can be compared on the same aggregation axes (`compare_prompts`).

## How to Apply This Practice to Your Own Project

1. Copy the profiler shape: an async context manager that captures timing/status in `finally` and lets callers contribute token counts and quality via the yielded `ctx` dict.
2. Define your `ProfilerMetrics` equivalent with exactly the dimensions you'll aggregate on (prompt_id, model, provider are the minimum).
3. Maintain a pricing table per provider+model; return `None` for unknowns and alert on missing entries.
4. Start with the four default thresholds above, then compute per-prompt baselines from a week of data and add relative alerts.
5. Ship JSON metrics into your existing observability stack rather than building dashboards — the reporter layer is intentionally replaceable.
6. Sample quality scoring (e.g. judge 5% of traffic) to bound cost while keeping trend visibility.
