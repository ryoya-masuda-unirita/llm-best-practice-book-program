# Chapter 2 Section 12: LLM Script Generation and Sandboxed Execution

## What This Section Demonstrates

LLMs are unreliable at exact computation and large-scale deterministic text processing — but excellent at *writing code* that does those things. This section implements the practice of having the LLM **generate a Python extraction script, validating and executing it in a sandbox, and using the script's deterministic output** instead of asking the model to produce the answer directly.

The pipeline processes documents (contracts, reports): sample the document → generate a structure-extraction script → execute with validation/sandboxing → judge the result quality — with two self-correction loops (execution errors and low judge scores both feed back into script regeneration). Apply this whenever the task is deterministic-at-heart (parsing, counting, calculating, restructuring) and correctness matters more than a single-call answer.

## Practice Rules

1. **Generate code, not answers**, for computation-shaped tasks. The LLM writes a script tailored to the document's observed structure; the runtime produces the result.
2. **Never execute generated code unvalidated.** Statically check the script against a forbidden-pattern list AND an import whitelist before it runs; reject on first violation with the reason.
3. **Sandbox the execution**: subprocess with emptied environment (`PATH`/`HOME`/`PYTHONPATH`), input passed via stdin, hard timeout (30s), temp file deleted afterwards.
4. **Feed failures back for self-correction.** On execution error, re-prompt the LLM with the script + error message + document context; retry up to 3 times.
5. **Judge the output, not just the exit code.** LLM-as-a-Judge scores extraction quality 1–5; score ≤ 3 triggers a `fix_proposal` and script re-correction (up to 3 validation rounds).
6. **State security requirements in the generation prompt too** (allowed modules, stdin input contract) — prompt-level constraints reduce rejected candidates; static validation remains the enforcement.
7. **Persist all three artifacts** — extracted structure JSON, the generated script, and processing metadata — so every result is reproducible and auditable.

## Architecture

```
CLI (src/main.py)  -m model -i document
  ▼
Document Processor (src/service/document_processor.py)
  Step 1: sample_document()               — LLM identifies doc type, key sections, samples
  Step 2: generate_extraction_script()    — LLM writes a Python script for this structure
  Step 3: execute_script_with_retry()
            validate_script()             — forbidden patterns + import whitelist
            execute_script()              — sandboxed subprocess (empty env, timeout)
            └─ on error → correct_script() → retry (≤3)
  Step 4: validate_extraction_result()    — LLM-as-a-Judge (1–5)
            └─ score ≤ 3 → correct_script_from_validation() → back to Step 3 (≤3)
  ▼
outputs/{filename}_{run_id}_structure.json / _script.py / _metadata.json
```

### Directory Structure

```
chapter_2/section_12/
├── src/
│   ├── main.py                  # CLI entry point (Click)
│   ├── config.py / logger.py
│   ├── client/llm_client.py     # AnthropicModel enum + client
│   ├── model/model.py           # pipeline data models
│   ├── prompt/prompt.py         # sampling / generation / correction / judge prompts
│   └── service/
│       ├── document_processor.py  # 4-step orchestration + artifact saving
│       ├── request_llm.py         # sample / generate / correct LLM calls
│       ├── script_executor.py     # validation + sandboxed execution
│       └── validator.py           # LLM-as-a-Judge quality evaluation
├── data/                        # contract_0.md / report_0.md / python_blog_0.md
├── outputs/
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Static validation before any execution (`src/service/script_executor.py`)

```python
FORBIDDEN_PATTERNS = [
    r"\bopen\s*\(", r"\bos\.", r"\bpathlib\b", r"\bsubprocess\b",
    r"\brequests\b", r"\burllib\b", r"\bsocket\b",
    r"\beval\s*\(", r"\bexec\s*\(", r"\bcompile\s*\(", r"\b__import__\s*\(",
    r"\bgetattr\s*\(", r"\bglobals\s*\(", r"\binput\s*\(", ...
]
ALLOWED_IMPORTS = {"sys", "json", "re"}

def validate_script(script: str) -> tuple[bool, str]:
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, script):
            return False, f"Forbidden pattern detected: {pattern}"
    # every import line must be in ALLOWED_IMPORTS
```

Deny dangerous constructs *and* allow only known-safe modules — two independent gates.

### 2. Sandboxed subprocess execution (`src/service/script_executor.py`)

```python
def execute_script(script: str, document_content: str, timeout: int = 30) -> ScriptExecutionResult:
    is_valid, error_message = validate_script(script)
    if not is_valid:
        return ScriptExecutionResult(success=False, error=error_message)
    # write script to a temp file; run:
    #   subprocess.run([sys.executable, script_path], input=document_content,
    #                  env={"PATH": "", "HOME": "", "PYTHONPATH": ""},
    #                  capture_output=True, timeout=timeout)
    # document goes in via stdin; JSON comes out via stdout; temp file removed in finally
```

### 3. Error-driven self-correction (`src/service/document_processor.py`, `src/service/request_llm.py`)

```python
# execute_script_with_retry: on failure, ask the LLM to fix its own script
corrected = await correct_script(model=model, script=script,
                                 error_message=result.error, document_sample=sample)
# retry up to DEFAULT_MAX_CORRECTION_ATTEMPTS (3)
```

### 4. Judge-driven re-correction (`src/service/validator.py`)

```python
validation = await validate_extraction_result(model, document, extraction_json)
# ValidationResult: score (1-5), reasoning, fix_proposal
if validation.score <= VALIDATION_THRESHOLD:   # 3
    script = await correct_script_from_validation(model, script, validation.fix_proposal)
    # re-execute, up to DEFAULT_MAX_VALIDATION_ATTEMPTS (3)
```

Exit-code success is not quality — the judge closes that gap.

### 5. Structured outputs for every LLM step

```python
result = await anthropic_client.beta.messages.parse(
    model=model,
    betas=["structured-outputs-2025-11-13"],
    messages=prompt,
    output_format=GeneratedScript,   # or SampledSentences / ValidationResult
)
```

## Data Models

| Model | Purpose |
|-------|---------|
| `SampledSentences` | Step-1 output: document type, key sections, representative samples |
| `GeneratedScript` | Step-2 output: script text + explanation |
| `ScriptExecutionResult` | Execution status, stdout, error |
| `DocumentStructure` / `DocumentSection` | Extracted hierarchical structure (title, level, content, subsections) |
| `ValidationResult` | Judge verdict: score (1–5), reasoning, fix_proposal |

## Setup & Run

```bash
cp .envrc.example .envrc     # set ANTHROPIC_API_KEY
uv sync

# Canonical example
uv run python -m src.main -m claude-sonnet-4-6 -i data/contract_0.md

# Custom output directory
uv run python -m src.main -m claude-sonnet-4-6 -i data/contract_0.md -od outputs
```

### CLI Options

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--model` | `-m` | Yes | — | `claude-opus-4-7` / `claude-sonnet-4-6` / `claude-haiku-4-5` / `claude-sonnet-5` / `claude-opus-4-8` |
| `--input` | `-i` | Yes | — | Input document path |
| `--output-directory` | `-od` | No | `outputs` | Output directory |

Outputs per run: `{filename}_{run_id}_structure.json`, `{filename}_{run_id}_script.py`, `{filename}_{run_id}_metadata.json`.

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
```

## Implementation Notes

- **Defense in depth**: prompt-level constraints (tell the model the rules) → static validation (enforce them) → environment isolation (empty PATH/HOME/PYTHONPATH) → timeout → temp-file cleanup. No single layer is trusted alone. For hostile inputs, add OS-level isolation (containers, seccomp) on top — regex validation is not a complete sandbox.
- **stdin/stdout as the only I/O channel** is what makes the whitelist workable: scripts never need `open()` because the document arrives on stdin and results leave as JSON on stdout.
- **Two distinct correction loops** matter: execution errors are cheap to detect and fix; semantic quality failures need the judge. Keeping their retry budgets separate (3 + 3) prevents one pathological document from looping forever.
- **Sampling before generation** (Step 1) keeps the generation prompt small — the model sees the document's *shape* (type, sections, examples), not the full text, and writes a script generic to that shape.
- **Why not code-execution-as-a-service**: this pattern runs entirely locally with your own guardrails; provider-hosted code execution tools are an alternative when you want the sandbox managed for you.

## How to Apply This Practice to Your Own Project

1. Identify tasks where the LLM currently computes answers directly (aggregation, parsing, math) and reframe them as "write a script that computes it".
2. Fix the I/O contract first: input on stdin, JSON on stdout — then your whitelist can stay tiny (`sys`, `json`, `re`, plus what your domain truly needs).
3. Copy `validate_script` + `execute_script` and tune `FORBIDDEN_PATTERNS`/`ALLOWED_IMPORTS`; add container isolation if inputs are untrusted.
4. Wire both correction loops with capped retries, always passing the concrete error/fix_proposal back to the model.
5. Judge results against the source document with a threshold before accepting them.
6. Persist script + result + metadata together; the script is your audit trail and your regression test seed.
