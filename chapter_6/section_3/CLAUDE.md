# Best-of-N with LLM-as-a-Judge

## Overview

This project implements the "Best-of-N" pattern with LLM-as-a-Judge evaluation for quality control. It generates multiple candidate outputs in parallel, evaluates each using an LLM judge on three criteria (accuracy, comprehensiveness, clarity), and returns the best candidate that meets a quality threshold.

Key features:
- Parallel generation of N candidates (1-10)
- LLM-as-a-Judge evaluation with structured scoring
- Quality threshold filtering with automatic retry
- Multi-provider support (OpenAI, Gemini, Anthropic)
- Separate generation and judge model configuration

## Architecture

```
+-------------------------------------------------------------------------+
|                           CLI (main.py)                                 |
|   --num-candidates, --quality-threshold, --max-retries                  |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                    request_with_best_of_n()                             |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |              Parallel Candidate Generation (asyncio.gather)       |  |
|  |   +----------+  +----------+  +----------+      +----------+      |  |
|  |   |Candidate |  |Candidate |  |Candidate | ...  |Candidate |      |  |
|  |   |    1     |  |    2     |  |    3     |      |    N     |      |  |
|  |   +----+-----+  +----+-----+  +----+-----+      +----+-----+      |  |
|  +--------|-------------|-------------|----------------|-------------+  |
|           |             |             |                |                |
|           v             v             v                v                |
|  +-------------------------------------------------------------------+  |
|  |              LLM-as-a-Judge Evaluation (Parallel)                 |  |
|  |   +----------+  +----------+  +----------+      +----------+      |  |
|  |   | Score:   |  | Score:   |  | Score:   | ...  | Score:   |      |  |
|  |   |  4.2/5   |  |  3.1/5   |  |  4.8/5   |      |  2.5/5   |      |  |
|  |   +----------+  +----------+  +----------+      +----------+      |  |
|  +-------------------------------------------------------------------+  |
|                                     |                                   |
|                                     v                                   |
|  +-------------------------------------------------------------------+  |
|  |                    Threshold Check                                |  |
|  |   passing = [c for c in results if score >= threshold]           |  |
|  |   if passing: return max(passing)                                 |  |
|  |   else: retry or fallback                                         |  |
|  +-------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
                                     |
                                     v
                        +------------------------+
                        |   Best Candidate +     |
                        |   Judge Evaluation     |
                        |   (JSON output)        |
                        +------------------------+
```

### Directory Structure

```
section_3/
+-- .envrc.example           # Environment variables template
+-- pyproject.toml           # Project configuration
+-- README.md                # Documentation (Japanese)
+-- CLAUDE.md                # This file
+-- src/
    +-- __init__.py
    +-- main.py              # CLI entry point with Click
    +-- config.py            # Configuration with Pydantic
    +-- logger.py            # Logging setup
    +-- client/
    |   +-- __init__.py
    |   +-- llm_client.py    # LLM client initialization and model enums
    +-- model/
    |   +-- __init__.py
    |   +-- model.py         # CharacterRequest/Response models
    |   +-- llm_as_a_judge_model.py  # JudgeRequest/Response models
    +-- prompt/
    |   +-- __init__.py
    |   +-- prompt.py        # Character generation prompts
    |   +-- llm_as_a_judge_prompt.py  # Evaluation prompts
    +-- service/
        +-- __init__.py
        +-- request_llm.py   # Best-of-N generation logic
        +-- llm_as_a_judge.py  # Judge evaluation logic
```

## Key Components

### Core Functions (src/service/request_llm.py)

| Function | Description |
|----------|-------------|
| `request_with_best_of_n()` | Main orchestrator: generates N candidates in parallel, evaluates each, returns best passing candidate |
| `generate_and_evaluate_candidate()` | Generates single candidate and evaluates it |
| `generate_single_candidate()` | Routes to provider-specific generation |
| `evaluate_candidate()` | Evaluates candidate using LLM-as-a-Judge |

### Data Models (src/model/)

| Model | Description |
|-------|-------------|
| `CharacterRequest` | Input: gender, age, additional_instructions |
| `CharacterResponse` | Output: first_name, last_name, gender, age, personalities |
| `JudgeRequest` | Evaluation input: question, response, context, request_parameters |
| `JudgeResponse` | Evaluation output: evaluations list, overall_score, summary |
| `CandidateResult` | Internal: candidate + judge_result + index |

### Evaluation Criteria

The LLM-as-a-Judge evaluates on three axes (1-5 scale):
- **accuracy**: Response is correct and faithful to requirements
- **comprehensiveness**: All required information is included
- **clarity**: Response is clear and well-written

## Dependencies

- `click` - CLI framework
- `pydantic` - Data validation and models
- `openai` - OpenAI API client (AsyncOpenAI)
- `google-genai` - Google Gemini API client
- `anthropic` - Anthropic API client (AsyncAnthropic)
- `python-dotenv` - Environment variable loading

## Usage

### Setup

```bash
# Copy environment template
cp .envrc.example .envrc

# Set API keys in .envrc
OPENAI_API_KEY=<your_key>
GEMINI_API_KEY=<your_key>
ANTHROPIC_API_KEY=<your_key>

# Install dependencies
uv sync
```

### Run

```bash
# Basic usage
uv run python -m src.main -lp gemini -m gemini-2.5-flash

# With Best-of-N parameters
uv run python -m src.main \
  -lp gemini -m gemini-2.5-flash \
  -n 5 -qt 4.0 -mr 3

# Different models for generation and evaluation
uv run python -m src.main \
  -lp gemini -m gemini-2.5-flash \
  -jp openai -jm gpt-5.4
```

### CLI Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--gender` | `-g` | Character gender (female/male) | female |
| `--age` | `-a` | Character age (0-100) | 25 |
| `--additional-instructions` | `-ai` | Extra generation instructions | "" |
| `--llm-provider` | `-lp` | Generation provider | gemini |
| `--model` | `-m` | Generation model | (required) |
| `--output-directory` | `-od` | Output directory | outputs |
| `--judge-provider` | `-jp` | Judge provider | (same as generation) |
| `--judge-model` | `-jm` | Judge model | (same as generation) |
| `--num-candidates` | `-n` | Number of candidates | 3 |
| `--quality-threshold` | `-qt` | Quality threshold (1.0-5.0) | 3.0 |
| `--max-retries` | `-mr` | Max retry attempts | 3 |

### Supported Models

| Provider | Models |
|----------|--------|
| OpenAI | gpt-5.5, gpt-5.4, gpt-5.4-mini, gpt-5.4-nano, gpt-5.2, gpt-5.1, gpt-5, gpt-5-mini, gpt-5-nano |
| Gemini | gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite, gemini-3.5-flash, gemini-3.1-flash-lite |
| Anthropic | claude-sonnet-4-6, claude-opus-4-7 |

## Implementation Notes

### Parallel Processing

All candidates are generated and evaluated in parallel using `asyncio.gather()`:

```python
tasks = [generate_and_evaluate_candidate(...) for i in range(num_candidates)]
results = await asyncio.gather(*tasks)
```

### Threshold and Fallback

1. Filter candidates by threshold: `passing = [r for r in results if r.judge_result.is_passing(threshold)]`
2. If passing candidates exist: return best score
3. If all below threshold: retry up to max_retries
4. If retries exhausted: return best available (with warning)

### Provider-Specific Configuration

- **Gemini**: Uses `temperature=2.0` for diversity, structured output with `response_schema`
- **OpenAI**: Uses `responses.parse()` with `text_format` for structured output
- **Anthropic**: Uses `beta.messages.parse()` with `output_format` for structured output

### Output Files

Two JSON files are generated per run:
- `{uuid}_{provider}_character.json` - Generated character data
- `{uuid}_{provider}_judge.json` - Evaluation results with scores and reasoning
