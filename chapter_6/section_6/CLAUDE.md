# School Data Analysis Agent with Function Calling

## Overview

A CLI-based data analysis assistant that uses Google Gemini with function calling to analyze school data. The application demonstrates best practices for LLM tool usage, including the **ID reference pattern** for managing tool results and **composite functions** for efficient multi-step operations.

## Architecture

```
+------------------------------------------------------------------+
|                     CLI Layer (main.py)                          |
|  - Click-based CLI with query input and output options           |
|  - Session management (UUID, logging, result export)             |
+----------------------------+-------------------------------------+
                             |
                             v
+------------------------------------------------------------------+
|                   Service Layer                                  |
|  +------------------------------------------------------------+  |
|  |  request_llm.py                                            |  |
|  |  - Gemini API integration with function calling            |  |
|  |  - SessionResultCache for ID reference pattern             |  |
|  |  - Iterative tool execution loop (up to 50 iterations)     |  |
|  +------------------------------------------------------------+  |
|  +------------------------------------------------------------+  |
|  |  tools/data_tools.py                                       |  |
|  |  - 12 composite tool functions                             |  |
|  |  - ResultStorage for caching detailed data                 |  |
|  +------------------------------------------------------------+  |
|  +------------------------------------------------------------+  |
|  |  tools/functions/                                          |  |
|  |  - loaders.py: JSON data file loading                      |  |
|  |  - analyzers.py: Polars-based statistical analysis         |  |
|  |  - validators.py: Input validation                         |  |
|  |  - formatters.py: Output formatting                        |  |
|  +------------------------------------------------------------+  |
+----------------------------+-------------------------------------+
                             |
                             v
+------------------------------------------------------------------+
|                   Data Layer                                     |
|  data/                                                           |
|  - students.json (5 students with UUIDs)                         |
|  - {1st,2nd,3rd,4th}_quarter_test_score.json                     |
|  - {1st,2nd,3rd,4th}_quarter_grade_report.json                   |
|  - {1st,2nd,3rd,4th}_quarter_curriculum.json                     |
+------------------------------------------------------------------+
```

### Directory Structure

```
chapter_6/section_6/
|-- src/
|   |-- __init__.py
|   |-- main.py              # CLI entry point with Click
|   |-- config.py            # API key configuration (Pydantic)
|   |-- logger.py            # Logging setup
|   |-- client/
|   |   |-- __init__.py
|   |   |-- llm_client.py    # Gemini client and model definitions
|   |-- model/
|   |   |-- __init__.py
|   |   |-- model.py         # Pydantic models for tool results
|   |-- prompt/
|   |   |-- __init__.py
|   |   |-- prompt.py        # System prompt and tool declarations
|   |-- service/
|       |-- __init__.py
|       |-- request_llm.py   # LLM request handling with function calling
|       |-- tools/
|           |-- __init__.py  # Tool function registry
|           |-- data_tools.py # Composite tool implementations
|           |-- functions/
|               |-- __init__.py
|               |-- loaders.py    # Data file loaders
|               |-- analyzers.py  # Statistical analysis (Polars)
|               |-- validators.py # Input validation
|               |-- formatters.py # Output formatting
|-- data/                    # School data files (JSON)
|-- outputs/                 # Session logs and results
|-- pyproject.toml
|-- Makefile
|-- README.md
```

## Key Components

### Tool Functions (12 tools)

| Tool | Description |
|------|-------------|
| `list_available_data` | List all data files by category |
| `get_students` | Get all student IDs |
| `get_test_scores` | Get test scores for a quarter |
| `get_grade_report` | Get grade reports for a quarter |
| `get_curriculum` | Get curriculum info for a quarter |
| `analyze_student_performance` | Comprehensive student analysis across all quarters |
| `analyze_class_performance` | Class-wide performance analysis |
| `compare_students` | Compare two students side-by-side |
| `filter_scores` | Filter scores by class/student/quarter |
| `filter_grades` | Filter grades by class/student/quarter |
| `filter_curriculum` | Filter curriculum by class/quarter |
| `get_result_details` | Retrieve full data by result_id (pull pattern) |

### ID Reference Pattern

The application implements the ID reference pattern to manage LLM context size:

1. **Tool Execution**: Tools return a summary + `result_id` to the LLM
2. **Data Caching**: Full detailed data is stored in `SessionResultCache`
3. **On-Demand Retrieval**: LLM can call `get_result_details(result_id)` to pull full data when needed

This prevents context overflow when analyzing large datasets.

### Data Model

- **5 subjects**: Japanese, Math, Physics, History, PE
- **4 quarters**: Full academic year
- **5 students**: Each with UUID
- **Grades**: A, B, C, D, F with teacher advice
- **Curriculum**: Plan, actual progress, completion rate

## Dependencies

| Package | Purpose |
|---------|---------|
| `polars` | High-performance data analysis |
| `google-genai` | Gemini API client (via root pyproject.toml) |
| `click` | CLI framework (via root pyproject.toml) |
| `pydantic` | Data validation and settings (via root pyproject.toml) |
| `python-dotenv` | Environment variable loading (via root pyproject.toml) |

## Usage

### Setup

1. Copy `.envrc.example` to `.envrc` and set your Gemini API key:
   ```bash
   cp .envrc.example .envrc
   # Edit .envrc and set GEMINI_API_KEY=your-key
   ```

2. Load environment (using direnv or manually source):
   ```bash
   direnv allow  # or source .envrc
   ```

### Run

```bash
# Basic query
uv run python -m src.main --query "Analyze the performance of all students"

# With specific model
uv run python -m src.main -m gemini-2.5-pro -q "Compare math and physics scores"

# Save output to files
uv run python -m src.main -q "Show class performance trends" -od ./outputs
```

### CLI Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--model` | `-m` | Gemini model to use | `gemini-2.5-flash` |
| `--query` | `-q` | Analysis query (required) | - |
| `--output-directory` | `-od` | Save session log and result | None |

### Available Models

- `gemini-2.5-pro`
- `gemini-2.5-flash` (default)
- `gemini-2.5-flash-lite`

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

### Function Calling Flow

1. User query is sent to Gemini with system prompt and tool declarations
2. Gemini may respond with function calls (multiple per iteration allowed)
3. Functions are executed, results cached, summaries returned to LLM
4. Loop continues until Gemini produces a final text response (max 50 iterations)
5. Final response is a comprehensive report in the user's language

### Report Generation

The system prompt instructs the LLM to:
- Respond in the same language as the user's query
- Always produce a structured report with specific sections
- Include specific numbers, percentages, and statistics
- Cite data sources by result_id

### Session Output

When `--output-directory` is specified:
- `{session_id}_session_log.json`: Full conversation history with tool calls
- `{session_id}_result.md`: Final analysis report in Markdown
