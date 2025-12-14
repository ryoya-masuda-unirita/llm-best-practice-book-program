# Prompt Performance Profiling

## Overview

This project implements a prompt performance profiling system for LLM applications. It provides data-driven measurement and analysis of prompt execution, enabling scientific optimization of quality, cost, and response time.

The system uses a 3-layer architecture (Collection, Analysis, Visualization) to transparently monitor LLM API calls, detect anomalies, and generate comprehensive reports. A character generation task serves as the demonstration use case, with LLM-as-a-Judge integration for automated quality evaluation.

## Architecture

```
+------------------------------------------------------------------+
|                      CLI Entry Point                              |
|                       (src/main.py)                               |
+------------------------------------------------------------------+
                              |
            +-----------------+------------------+
            v                                    v
+------------------------+          +------------------------+
|   Standard Request     |          |   Profiled Request     |
|   (request_llm.py)     |          | (profiled_request_     |
|                        |          |      llm.py)           |
+------------------------+          +------------------------+
            |                                    |
            |                       +------------+------------+
            |                       v                         v
            |           +-------------------+    +-------------------+
            |           | [Collection Layer]|    |  LLM-as-a-Judge   |
            |           |  PromptProfiler   |    |                   |
            |           +-------------------+    +-------------------+
            |                       |
            |                       v
            |           +-------------------+
            |           | [Analysis Layer]  |
            |           |  MetricsAnalyzer  |
            |           +-------------------+
            |                       |
            |                       v
            |           +-------------------+
            |           | [Visualization]   |
            |           |  ProfilerReporter |
            |           +-------------------+
            |                       |
            v                       v
+------------------------------------------------------------------+
|                         LLM Clients                               |
|  +-------------+   +-------------+   +------------------------+   |
|  |   OpenAI    |   |   Gemini    |   |       Anthropic        |   |
|  +-------------+   +-------------+   +------------------------+   |
+------------------------------------------------------------------+
```

### Directory Structure

```
chapter_3/section_8/
|-- CLAUDE.md                 # This file
|-- README.md                 # Project documentation (Japanese)
|-- pyproject.toml            # Dependencies
|-- .envrc.example            # Environment variables template
|-- Makefile                  # Development commands
|-- src/
|   |-- __init__.py
|   |-- main.py               # CLI entry point (Click)
|   |-- config.py             # Configuration management
|   |-- logger.py             # Logging setup
|   |-- client/
|   |   |-- __init__.py
|   |   +-- llm_client.py     # LLM client initialization
|   |-- model/
|   |   |-- __init__.py
|   |   |-- model.py          # Character request/response models
|   |   |-- llm_as_a_judge_model.py  # Judge evaluation models
|   |   +-- profiler_metrics.py      # Profiler metrics models
|   |-- prompt/
|   |   |-- __init__.py
|   |   |-- prompt.py         # Character generation prompts
|   |   +-- llm_as_a_judge_prompt.py  # Judge evaluation prompts
|   +-- service/
|       |-- __init__.py
|       |-- request_llm.py    # Standard LLM request functions
|       |-- llm_as_a_judge.py # Judge service functions
|       |-- prompt_profiler.py      # Collection layer
|       |-- metrics_analyzer.py     # Analysis layer
|       |-- profiler_reporter.py    # Visualization layer
|       +-- profiled_request_llm.py # Profiled request functions
+-- tests/
    |-- __init__.py
    |-- conftest.py
    |-- test_prompt_profiler.py
    |-- test_metrics_analyzer.py
    +-- test_profiler_reporter.py
```

## Key Components

### PromptProfiler (Collection Layer)

Wraps LLM API calls to transparently collect performance metrics using async context managers.

```python
async with profiler.profile(prompt_id="gen", model="gpt-4o", provider="openai") as ctx:
    result = await client.generate(...)
    ctx["input_tokens"] = result.usage.input_tokens
    ctx["output_tokens"] = result.usage.output_tokens
```

Collected metrics:
- `latency_ms` - Request execution time
- `input_tokens` / `output_tokens` - Token usage
- `estimated_cost_usd` - Cost estimation
- `quality_score` - LLM-as-a-Judge score (1.0-5.0)

### MetricsAnalyzer (Analysis Layer)

Multi-dimensional analysis with anomaly detection and alert generation.

- Statistical aggregation (mean, median, P95, P99, std dev)
- Grouping by prompt/model/provider
- Time-series bucketing and trend detection
- Threshold-based alert generation

### ProfilerReporter (Visualization Layer)

Generates reports in multiple formats:
- Text format for terminal output
- JSON format for Grafana/Kibana integration
- HTML format for visual dashboards

### AlertThreshold

Configurable thresholds for monitoring:

| Metric | Warning | Critical |
|--------|---------|----------|
| Latency | 5000ms | 10000ms |
| Tokens | 8000 | 16000 |
| Quality | 3.0 | 2.0 |
| Cost | $0.10 | $0.50 |

## Dependencies

| Package | Purpose |
|---------|---------|
| openai | OpenAI API client |
| google-genai | Google Gemini API client |
| anthropic | Anthropic API client |
| pydantic | Data validation and models |
| click | CLI framework |
| python-dotenv | Environment variable management |

## Usage

### Setup

1. Copy environment template and set API keys:

```bash
cp .envrc.example .envrc
# Edit .envrc with your API keys:
# OPENAI_API_KEY=sk-...
# GEMINI_API_KEY=AIza...
# ANTHROPIC_API_KEY=sk-ant-...
```

2. Install dependencies:

```bash
uv sync
```

### Run

```bash
# Basic character generation
python -m src.main -g FEMALE -a 25 -lp GEMINI -m GEMINI_2_5_FLASH

# With profiling enabled
python -m src.main -g MALE -a 30 -lp OPENAI -m GPT_4O_MINI --enable-profiling

# With separate judge provider and HTML report
python -m src.main -g FEMALE -a 22 -lp GEMINI -m GEMINI_2_5_FLASH \
  -jp ANTHROPIC -jm CLAUDE_SONNET_4_5 -p -prf html
```

### CLI Options

| Option | Short | Description | Required |
|--------|-------|-------------|----------|
| --gender | -g | Character gender (FEMALE/MALE) | Yes |
| --age | -a | Character age (0-100) | Yes |
| --additional-instructions | -ai | Extra generation instructions | No |
| --llm-provider | -lp | LLM provider (OPENAI/GEMINI/ANTHROPIC) | Yes |
| --model | -m | Model to use | Yes |
| --output-directory | -od | Output directory | No |
| --judge-provider | -jp | Judge LLM provider | No |
| --judge-model | -jm | Judge model | No |
| --enable-profiling | -p | Enable profiling | No |
| --profiler-report-format | -prf | Report format (json/html/txt) | No |

## Development Commands

```bash
make lint    # Run ruff linter with auto-fix
make fmt     # Format code with ruff
make fix     # Run lint + fmt
make mypy    # Run type checking
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_prompt_profiler.py -v
python -m pytest tests/test_metrics_analyzer.py -v
python -m pytest tests/test_profiler_reporter.py -v
```

## Implementation Notes

### Profiling Design

- Async context manager minimizes impact on main processing flow
- Metrics stored asynchronously to avoid blocking
- Cost estimation uses per-provider pricing tables
- In-memory storage with optional file persistence

### Alert System

Two types of threshold checking:
1. Absolute thresholds (e.g., latency > 10000ms)
2. Relative thresholds (e.g., latency > 200% of baseline)

### Quality Evaluation

LLM-as-a-Judge evaluates generated content on:
- Accuracy (request compliance)
- Comprehensiveness (information completeness)
- Clarity (readability)

Overall score: 1.0-5.0 (passing threshold: 3.0)
