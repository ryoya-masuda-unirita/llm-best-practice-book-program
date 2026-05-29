---
name: run-samples
description: Run sample code in section directories and record success/failure. Use when asked to run samples, test sections, verify code works, or check if sections execute correctly.
argument-hint: "[chapter_X] [chapter_X/section_Y] [--cli-only] [--docker-only]"
disable-model-invocation: true
allowed-tools: Bash
---

Run sample code from section directories sequentially, recording success/failure for each.

## Parsing arguments

Parse `$ARGUMENTS` to determine which sections to run:
- No arguments: run ALL sections
- `chapter_X`: run all sections in that chapter
- `chapter_X/section_Y`: run a specific section
- `--cli-only`: run only cli-type sections
- `--docker-only`: run only docker-type sections
- Multiple space-separated section paths are supported

## Section registry

For each section, look up the command from the registry in [registry.md](registry.md).

## Execution steps

For each selected section:

1. `cd` into the section directory (from the project root)
2. Run `uv sync --quiet` to install dependencies
3. Run the command from the registry with a 5-minute timeout (`timeout 300 ...`)
4. Record: PASS (exit 0), FAIL (non-zero), or SKIP (prerequisites missing)

### Docker sections (`type=docker`)

- First check if `docker` CLI is available; if not, record as SKIP
- Always run `make docker-down` in cleanup, even on failure
- If curl health check fails but docker-up succeeded, still consider it a pass

### Special sections (`type=special`)

- These involve background processes
- Always clean up background processes after the test

## Output

After all sections complete, output a summary table:

```
| Section | Result | Notes |
|---------|--------|-------|
| chapter_2/section_1 | PASS | |
| chapter_2/section_6 | SKIP | docker not available |
```

## Important rules

- Run sections **sequentially**, not in parallel
- Always `cd` into the section directory before running commands
- Capture stdout/stderr and show relevant error output on failure
- Do NOT stop on first failure -- continue with remaining sections
- For Docker sections, always clean up containers even on failure
