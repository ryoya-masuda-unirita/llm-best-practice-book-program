# Chapter 6 Section 5: Function Calling at Scale — ID Reference Pattern and Composite Tools

## What This Section Demonstrates

Function calling breaks down when tool results are large: raw data dumped into the LLM context burns tokens, dilutes attention, and hits limits. This section is a school-data analysis agent (Gemini function calling over school records) built around two context-economy practices:

- **ID reference pattern** — tools return `{summary, result_id}`; the full `detailed_data` goes into a `SessionResultCache`, *not* the LLM context. If the model actually needs details, it pulls them explicitly via a `get_result_details(result_id)` tool.
- **Composite functions** — tools like `analyze_student_performance` or `compare_students` do multi-step work (load → join → aggregate) in one call, instead of forcing the model to chain 5 primitive calls and carry intermediate data through context.

Apply these when tools return datasets rather than scalars — analytics assistants, DB copilots, log analysis — anywhere "the model needs the conclusion, not the rows."

## Practice Rules

1. **Return summaries to the model, cache the payload**: every data-producing tool result passes through `extract_context_safe_result`, which strips `detailed_data` into the session cache and marks `detailed_data_available: true`.
2. **Make detail retrieval an explicit pull**: `get_result_details(result_id)` is the only tool whose full output enters context — the model opts into token spend deliberately.
3. **Design composite tools around questions, not tables**: "analyze this student" is one tool call, not `get_students` + `get_test_scores` × 4 + math in prose.
4. **Cap the tool loop** (up to 50 iterations here) and log every function call with args and the context-safe result — the loop trace is your debugging record.
5. **Return errors as structured results** (`{"error": ..., "status": "error"}`) so the model can react; never raise through the tool boundary.
6. **Scope the cache to the session** (`SessionResultCache` keyed by `result_id`, cleared per session) — cached data is conversation state, not a database.

## Architecture

```
CLI (src/main.py)  --query "全生徒の成績を分析してください"
  ▼
process_with_function_calling (src/service/request_llm.py)
  loop (≤ 50 iterations):
    Gemini generate_content(tools=[function declarations])
    ├─ function_call? → execute_function_call()
    │      ├─ TOOL_FUNCTIONS[name](**args)             ← composite tools (data_tools.py)
    │      ├─ detailed_data → SessionResultCache        ← ID reference pattern
    │      └─ summary (+result_id) → back to the model
    │    special case: get_result_details(result_id) → full cached data to the model (pull)
    └─ text answer → done
  ▼
analysis answer + per-quarter report result_ids
```

### Directory Structure

```
chapter_6/section_5/
├── src/
│   ├── service/
│   │   ├── request_llm.py        # function-calling loop + SessionResultCache + context-safe extraction
│   │   └── tools/
│   │       ├── data_tools.py     # composite tools + get_result_details
│   │       └── functions/        # loaders / analyzers / formatters / validators
│   ├── prompt/prompt.py          # system prompt + tool (function) declarations
│   ├── model/model.py / client/llm_client.py
│   ├── main.py                   # CLI (Click), session management + result export
│   └── config.py / logger.py
├── data/                         # school records (students, scores, curriculum…)
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Context-safe result extraction (`src/service/request_llm.py`)

```python
def extract_context_safe_result(result: dict, session_cache: SessionResultCache) -> dict:
    result_id = result.get("result_id", "")
    if "detailed_data" in result and result_id:
        session_cache.store(result_id, result["detailed_data"])       # payload → cache
        context_result = {k: v for k, v in result.items() if k != "detailed_data"}
        context_result["detailed_data_available"] = True               # model knows it can pull
        return context_result
    return result
```

### 2. Pull-based detail access

```python
def execute_function_call(function_call, session_cache) -> dict:
    result = TOOL_FUNCTIONS[func_name](**func_args)
    if func_name == "get_result_details":
        return result                          # the ONE tool that returns full data
    return extract_context_safe_result(result, session_cache)
```

### 3. Composite tools answer questions (`src/service/tools/data_tools.py`)

```python
def analyze_student_performance(student_id: str) -> dict:
    scores, reports, curriculum = _collect_student_data(student_id)   # multi-source join
    # aggregate trends, strengths/weaknesses → {summary stats, result_id, detailed_data}

def compare_students(student_id_1: str, student_id_2: str) -> dict: ...
def filter_scores(...) -> dict: ...
```

Tool inventory: `list_available_data`, `get_students`, `get_test_scores`, `get_grade_report`, `get_curriculum`, `analyze_student_performance`, `analyze_class_performance`, `compare_students`, `filter_scores`, `filter_grades`, `filter_curriculum`, `get_result_details`.

### 4. Structured tool errors

```python
except Exception as e:
    return {"error": str(e), "status": "error"}    # model-visible, recoverable
```

## Data Models

| Item | Purpose |
|------|---------|
| `SessionResultCache` | result_id → detailed_data, session-scoped |
| Tool result convention | `{summary fields..., result_id, detailed_data?}` |
| `TOOL_FUNCTIONS` | name → callable registry backing the declarations |

## Setup & Run

```bash
cp .envrc.example .envrc     # set GEMINI_API_KEY
uv sync

# Canonical example
uv run python -m src.main --query '全生徒の成績を分析してください'
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--query` | Analysis request in natural language |
| `--model` / `-m` | Gemini model |
| `--output-directory` | Session output directory |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
```

## Implementation Notes

- **The ID reference pattern is the RAG inverse**: instead of pushing data into context ahead of need, tools *withhold* data until the model asks. Token usage tracks what the model actually reasons about, not what tools happened to touch.
- **Composite vs primitive tools**: primitives maximize flexibility but explode iteration counts and context (every intermediate result lands in the conversation). Composites encode domain workflows; keep a few primitives (`get_students`, `filter_scores`) for questions your composites didn't anticipate.
- **The 50-iteration cap** is generous because composite tools make most analyses finish in a handful of calls; the cap is a runaway guard, not a target.
- **`detailed_data_available: true` is a teaching flag for the model** — the system prompt explains the pull mechanism, and the flag reminds the model per-result that more data exists.
- **Session cache lifetime = conversation lifetime**: `result_id`s are meaningless across sessions; export what you need (`main.py` writes results out) before the session ends.

## How to Apply This Practice to Your Own Project

1. Establish the tool-result convention first: `summary + result_id (+ cached detailed_data)`; wrap all tool dispatch through one `execute_function_call` that enforces it.
2. Add `get_result_details` and describe the pull mechanism in the system prompt.
3. Interview your users' actual questions and build composite tools for the top ones; keep primitives as fallback.
4. Cap the loop, log every call/args/summary, and return structured errors.
5. Watch token usage per session before/after adopting the pattern — the delta is your justification.
6. For multi-user services, key the cache by session/user and add TTL eviction.
