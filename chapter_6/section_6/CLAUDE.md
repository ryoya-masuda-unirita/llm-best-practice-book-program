# Tool Chain Function Calling Pattern

## Overview

This project demonstrates the **Tool Chain** pattern for LLM function calling. Instead of returning intermediate results to the LLM after each function call, the system executes a chain of tools defined by the LLM upfront, only returning the final result. This reduces token consumption and improves latency.

The implementation uses a school data analysis system as a use case, with tools for analyzing student records, test scores, grade reports, and curriculum data.

## Architecture

```
+------------------------------------------------------------------+
|                        User Request                               |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                        Gemini LLM                                 |
|  +------------------------------------------------------------+  |
|  | 1. Parse tool metadata                                     |  |
|  | 2. Output Tool Chain definition (JSON structured output)   |  |
|  | 3. Generate final report after chain execution             |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                   Tool Chain Executor                             |
|  +------------------------------------------------------------+  |
|  | validate_chain() -> dry_run() -> execute()                 |  |
|  +------------------------------------------------------------+  |
|                                                                   |
|  +------------------------------------------------------------+  |
|  |            Data Flow (Bucket Relay Pattern)                |  |
|  |                                                            |  |
|  |  +--------+  output_keys   +--------+   output_keys        |  |
|  |  | Tool A | ------------> | Tool B | -----------> ...      |  |
|  |  +--------+  input_mapping +--------+                      |  |
|  |                                                            |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                     Session Cache                                 |
|  +------------------------------------------------------------+  |
|  | result_id -> detailed_data mapping                         |  |
|  | (LLM context receives only result_id and summary)          |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

### Directory Structure

```
chapter_6/section_6/
|-- src/
|   |-- main.py                  # CLI entry point (Click)
|   |-- config.py                # Configuration (API keys via env)
|   |-- logger.py                # Logging setup
|   |-- client/
|   |   |-- __init__.py
|   |   `-- llm_client.py        # Gemini API client setup
|   |-- model/
|   |   |-- __init__.py          # Model exports
|   |   |-- model.py             # Result models (ToolResult, etc.)
|   |   |-- schemas.py           # Pydantic I/O schemas for tools
|   |   `-- tool_chain_models.py # Chain config/result models
|   |-- prompt/
|   |   |-- __init__.py
|   |   `-- prompt.py            # System prompt and tool docs
|   `-- service/
|       |-- __init__.py
|       |-- request_llm.py       # LLM request handler, chain executor
|       `-- tools/
|           |-- __init__.py      # Tool registry (TOOL_FUNCTIONS)
|           |-- data_tools.py    # Data analysis tool functions
|           |-- tool_chain.py    # ToolChainExecutor class
|           |-- tool_metadata.py # TOOL_METADATA registry
|           `-- functions/       # Small composable functions
|               |-- __init__.py
|               |-- analyzers.py
|               |-- formatters.py
|               |-- loaders.py
|               `-- validators.py
|-- data/                        # Sample school data (JSON files)
|   |-- students.json
|   |-- 1st_quarter_test_score.json
|   |-- 1st_quarter_grade_report.json
|   |-- 1st_quarter_curriculum.json
|   `-- ... (Q2, Q3, Q4 data)
|-- tests/                       # Test files
|-- pyproject.toml               # Project dependencies
|-- .envrc.example               # Environment variable template
|-- Makefile                     # Development commands
`-- README.md
```

## Key Components

### Tool Chain Executor (`tool_chain.py`)

The `ToolChainExecutor` class handles chain execution:

- `validate_chain()` - Validates chain structure (tool existence, connectable_to rules)
- `dry_run()` - Executes chain with test data to verify I/O compatibility
- `execute()` - Runs chain with actual data, passing outputs between steps

### Tool Metadata (`tool_metadata.py`)

Each tool has metadata defining:

- `input_model` / `output_model` - Pydantic schemas for type safety
- `output_keys` - Keys available for passing to connected tools
- `connectable_to` - List of tools that can follow this one
- `is_chain_terminal` - Whether tool typically ends a chain
- `test_input` - Mini test data for dry run validation

### Available Tools

| Tool | Category | Description |
|------|----------|-------------|
| `list_available_data` | loader | List all data files |
| `get_students` | loader | Get student list |
| `get_test_scores` | loader | Get scores by quarter |
| `get_grade_report` | loader | Get grades by quarter |
| `get_curriculum` | loader | Get curriculum by quarter |
| `filter_scores` | filter | Filter scores by criteria |
| `filter_grades` | filter | Filter grades by criteria |
| `filter_curriculum` | filter | Filter curriculum data |
| `analyze_student_performance` | analyzer | Analyze single student |
| `analyze_class_performance` | analyzer | Analyze class/subject |
| `compare_students` | analyzer | Compare two students |
| `get_result_details` | retriever | Get cached detailed data |

### Request Processing (`request_llm.py`)

The `process_with_tool_chain()` function:

1. Sends user request to Gemini with tool metadata as context
2. Receives structured JSON output defining the tool chain
3. Validates and executes the chain (with dry run first)
4. Caches detailed results, returns summary to LLM
5. Supports multiple iterations for complex queries
6. LLM generates final report based on collected data

## Dependencies

| Package | Purpose |
|---------|---------|
| `google-genai` | Gemini API client |
| `pydantic` | Data validation and schemas |
| `polars` | Data processing |
| `click` | CLI framework |
| `python-dotenv` | Environment variable loading |

## Usage

### Setup

```bash
# Copy environment template
cp .envrc.example .envrc

# Set your Gemini API key
# GEMINI_API_KEY=your_key_here

# Install dependencies
uv sync
```

### Run

```bash
# Basic query
uv run python src/main.py -q "Analyze math class performance"

# Specify model
uv run python src/main.py -m GEMINI_2_5_PRO -q "Compare top students"

# Save output to directory
uv run python src/main.py -q "Quarterly analysis" -od ./output
```

### CLI Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--model` | `-m` | Gemini model to use | `GEMINI_2_5_FLASH` |
| `--query` | `-q` | Analysis query (required) | - |
| `--output-directory` | `-od` | Save session log and result | - |

Available models: `GEMINI_2_5_PRO`, `GEMINI_2_5_FLASH`, `GEMINI_2_5_FLASH_LITE`

## Development Commands

```bash
# Lint code
make lint

# Format code
make fmt

# Lint and format
make fix

# Type check
make mypy
```

## Implementation Notes

### Tool Chain JSON Schema

The LLM outputs chain definitions as structured JSON:

```json
{
  "chain_name": "math_analysis",
  "objective": "Analyze math class performance",
  "steps": [
    {"tool_name": "analyze_class_performance", "args": [{"key": "class_name", "value": "math"}]}
  ],
  "is_final_iteration": true
}
```

### Data Flow Between Tools

- Output keys from tool A are mapped to input fields of tool B
- Auto-mapping occurs when output key names match input field names
- Manual `input_mapping` can override auto-mapping

### Context Token Optimization

- Detailed data stored in `SessionResultCache` with `result_id`
- LLM context only receives summaries and result IDs
- `get_result_details` tool retrieves cached data when needed

### Validation Flow

1. **Structure validation** - Check tool names, connectable_to rules
2. **Dry run** - Execute with test_input to verify I/O compatibility
3. **Execution** - Run with actual data if dry run passes

### Multi-Iteration Support

For complex queries requiring multiple data collection steps:

- LLM can set `is_final_iteration: false` to request another chain
- Previous results are included in system prompt context
- Maximum iterations configurable (default: 10)
