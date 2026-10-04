# Chapter 6 Section 3: Best-of-N Generation with LLM-as-a-Judge Selection

## What This Section Demonstrates

Single-shot generation quality is a lottery; this section trades compute for quality with the **Best-of-N pattern**: generate N candidates **in parallel**, score each with an LLM judge (accuracy / comprehensiveness / clarity, 1–5), and return the highest-scoring candidate that clears a quality threshold. If no candidate passes, regenerate the whole batch (bounded retries); if retries exhaust, return the best available with an explicit warning.

Generation and judging are independently configurable (provider/model each), reusing the judge from Chapter 2 Section 7. Apply this pattern to high-stakes, low-volume outputs — published copy, contracts, canonical dataset entries — where an extra N× generation cost is cheaper than a bad output escaping.

## Practice Rules

1. **Generate candidates concurrently** — `asyncio.gather` over `generate_and_evaluate_candidate` tasks; Best-of-N latency should approach 1× generation + 1× judging, not N×.
2. **Judge each candidate immediately in the same task** (generation and evaluation paired per candidate) so selection needs no second pass.
3. **Select by threshold-then-max**: filter to `is_passing(threshold)`, then take `max(score)` — a threshold alone wastes quality headroom; a max alone can return garbage when everything is bad.
4. **Retry the batch, not the champion**: if all N fail the threshold, regenerate all candidates (up to `max_retries`); diversity across batches is the point.
5. **Define the exhaustion policy explicitly**: return the best-available candidate *with a logged warning* rather than raising — and make that a conscious choice per use case.
6. **Keep N, threshold, and retries configurable** (config defaults + CLI overrides: `-n`, `-qt`, `-mr`) — the quality/cost dial must be tunable per call site.
7. **Judge with a different provider/model when possible** (`-jp/-jm`) to avoid self-preference bias in selection.

## Architecture

```
CLI (src/main.py)  -n N -qt threshold -mr retries  (-lp/-m generation, -jp/-jm judge)
  ▼
request_with_best_of_n (src/service/request_llm.py)
  for retry in range(max_retries):
      tasks = [generate_and_evaluate_candidate(i) for i in range(N)]   ← parallel
      results = await asyncio.gather(*tasks)
      passing = [r for r in results if r.judge_result.is_passing(threshold)]
      if passing: return max(passing, key=score)          ← threshold-then-max
  # exhausted: return best_overall with warning            ← explicit fallback
  ▼
outputs/<id>_<provider>_character.json + _judge.json
```

### Directory Structure

```
chapter_6/section_3/
├── src/
│   ├── service/
│   │   ├── request_llm.py           # candidate generation + best-of-n loop
│   │   └── llm_as_a_judge.py        # judge_with_openai/gemini/anthropic
│   ├── model/model.py               # CharacterRequest/Response + CandidateResult
│   ├── model/llm_as_a_judge_model.py# JudgeRequest / JudgeResponse (is_passing)
│   ├── prompt/                      # generation + judge prompts
│   ├── client/llm_client.py         # 3-provider clients + model enums
│   ├── main.py                      # CLI
│   └── config.py / logger.py        # defaults: num_candidates / quality_threshold / max_retries
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Parallel generate-and-judge per candidate (`src/service/request_llm.py`)

```python
tasks = [
    generate_and_evaluate_candidate(prompt=prompt, model=model, provider=provider,
                                    judge_model=judge_model, judge_provider=judge_provider, index=i)
    for i in range(num_candidates)
]
results: list[CandidateResult] = await asyncio.gather(*tasks)
```

### 2. Threshold-then-max selection

```python
passing_candidates = [r for r in results if r.judge_result.is_passing(threshold=quality_threshold)]
if passing_candidates:
    best_candidate = max(passing_candidates, key=lambda r: r.judge_result.overall_score)
    return best_candidate.candidate, best_candidate.judge_result
```

### 3. Batch retry + explicit exhaustion fallback

```python
for retry in range(max_retries):
    ...  # regenerate ALL candidates when none pass
logger.error(f"All {max_retries} retry attempts exhausted. Returning best available candidate.")
best_overall = max(results, key=lambda r: r.judge_result.overall_score)
return best_overall.candidate, best_overall.judge_result   # logged as below-threshold
```

### 4. Config defaults with per-call overrides

```python
if num_candidates is None:   num_candidates = config.num_candidates
if quality_threshold is None: quality_threshold = config.quality_threshold
if judge_model is None:       judge_model = model        # same-model judging as fallback
```

## Data Models

| Model | Purpose |
|-------|---------|
| `CandidateResult` | index + candidate + judge verdict, the unit of selection |
| `JudgeRequest` / `JudgeResponse` (+ `is_passing`) | 3-criteria judge I/O (from Chapter 2 Section 7) |
| `CharacterRequest` / `CharacterResponse` | Demo task I/O |

## Setup & Run

```bash
cp .envrc.example .envrc     # OPENAI_API_KEY / GEMINI_API_KEY / ANTHROPIC_API_KEY
uv sync

# Canonical example: 3 candidates, threshold 3.0
uv run python -m src.main -g FEMALE -a 25 -lp ANTHROPIC -m CLAUDE_HAIKU_4_5 -n 3 -qt 3.0

# Cross-provider judge
uv run python -m src.main -g FEMALE -a 25 -lp ANTHROPIC -m CLAUDE_HAIKU_4_5 \
  -n 5 -qt 4.0 -jp OPENAI -jm GPT_5_4
```

### CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--gender` / `--age` / `--additional-instructions` | `-g` / `-a` / `-ai` | Character request |
| `--llm-provider` / `--model` | `-lp` / `-m` | Generation provider/model |
| `--judge-provider` / `--judge-model` | `-jp` / `-jm` | Judge (defaults to generation) |
| `--num-candidates` | `-n` | N (1–10) |
| `--quality-threshold` | `-qt` | Minimum passing overall score (1.0–5.0) |
| `--max-retries` | `-mr` | Batch regeneration attempts |
| `--output-directory` | `-od` | Output directory |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
```

## Implementation Notes

- **Cost model**: one call becomes N generations + N judgments (× retry batches worst case). Best-of-3 with a cheap judge roughly quadruples cost — reserve for outputs whose failure costs more than that.
- **Choosing N and the threshold**: run N=1 with judging first to measure your baseline score distribution; set the threshold near the score you'd accept manually, and N so that P(at least one candidate passes) is high (score variance decides — high variance favors larger N).
- **Batch retry vs temperature bumping**: this implementation regenerates with the same settings, relying on sampling diversity; a common extension is escalating temperature or model tier per retry batch.
- **The fallback return is deliberate product behavior** — some flows prefer "best effort + warning" (this code), others must raise and queue for human review. Pick and document one; the returned judge verdict always carries the true score, so callers can re-check.
- **Best-of-N composes with the rest of this repo**: candidates can be generated through the fallback coordinator (3-2), logged via LLMOps logging (2-4), and judged with custom criteria (2-9).

## How to Apply This Practice to Your Own Project

1. Reuse your Chapter 2 Section 7 judge; add `CandidateResult` and the generate-and-evaluate-per-candidate task shape.
2. Fan out with `asyncio.gather`; keep generation+judging paired per candidate.
3. Implement threshold-then-max selection and a bounded batch retry.
4. Decide the exhaustion policy per product surface (best-effort vs raise); log it loudly either way.
5. Expose N/threshold/retries as config with call-site overrides.
6. Measure: track scores of selected vs rejected candidates over time — if rejected candidates rarely differ, lower N and save the money.
