# LLM Script Generation and Execution

## Overview

This project demonstrates a practice where LLM generates Python scripts to handle tasks that LLMs struggle with (numerical calculations, complex data processing) and executes them in a sandboxed environment. Instead of asking the LLM to compute results directly, the system has the LLM generate extraction scripts, executes them safely, and uses the deterministic output.

The application takes documents (contracts, reports, etc.) as input, generates Python scripts to extract document structure, and outputs results in JSON format. If script execution fails, the system uses LLM-based self-correction to automatically fix and retry.

## Architecture

```
+-------------------------------------------------------------------------+
|                           CLI (main.py)                                  |
|                      Load document file                                  |
+----------------------------------+--------------------------------------+
                                   |
                                   v
+-------------------------------------------------------------------------+
|                  Document Processor (service layer)                      |
|  +----------------------------------------------------------------+     |
|  | Step 1: sample_document()                                       |     |
|  |   - Identify document type (contract, report, manual, etc.)     |     |
|  |   - Identify key sections                                       |     |
|  |   - Sample representative sentences                             |     |
|  +----------------------------------------------------------------+     |
|                                   |                                      |
|                                   v                                      |
|  +----------------------------------------------------------------+     |
|  | Step 2: generate_extraction_script()                            |     |
|  |   - Generate Python script suited for document structure        |     |
|  |   - Specify security requirements in prompt                     |     |
|  +----------------------------------------------------------------+     |
|                                   |                                      |
|                                   v                                      |
|  +----------------------------------------------------------------+     |
|  | Step 3: execute_script_with_retry()                             |     |
|  |   - Validate script (forbidden patterns/module check)           |     |
|  |   - Sandbox execution (empty PATH/PYTHONPATH, timeout)          |     |
|  |   - On error: correct_script() and retry (up to 3 times)        |     |
|  +----------------------------------------------------------------+     |
+----------------------------------+--------------------------------------+
                                   |
                                   v
+-------------------------------------------------------------------------+
|                          Output Files                                    |
|  - {filename}_{run_id}_structure.json  # Extracted document structure    |
|  - {filename}_{run_id}_script.py       # Generated Python script         |
|  - {filename}_{run_id}_metadata.json   # Processing metadata             |
+-------------------------------------------------------------------------+
```

### Directory Structure

```
section_16/
|-- src/
|   |-- __init__.py
|   |-- main.py              # CLI entry point
|   |-- config.py            # Configuration management
|   |-- logger.py            # Logging setup
|   |-- client/
|   |   |-- __init__.py
|   |   +-- llm_client.py    # Anthropic API client
|   |-- model/
|   |   |-- __init__.py
|   |   +-- model.py         # Pydantic data models
|   |-- prompt/
|   |   |-- __init__.py
|   |   +-- prompt.py        # LLM prompt definitions
|   +-- service/
|       |-- __init__.py
|       |-- document_processor.py  # Document processing orchestration
|       |-- request_llm.py         # LLM request handling
|       +-- script_executor.py     # Script execution and validation
|-- data/                     # Sample input documents
|   |-- contract_0.md
|   |-- report_0.md
|   +-- python_blog_0.md
|-- outputs/                  # Output files
|-- pyproject.toml
|-- .envrc.example
+-- README.md
```

## Key Components

### document_processor.py
- `extract_document_structure()`: Main orchestration function for the 3-step pipeline
- `_execute_script_with_retry()`: Handles retry loop with self-correction
- `save_extraction_results()`: Saves structure, script, and metadata files
- `ExtractionResult`: Dataclass containing extraction results

### script_executor.py
- `validate_script()`: Checks for forbidden patterns and imports
- `execute_script()`: Runs script in sandboxed subprocess
- `FORBIDDEN_PATTERNS`: Regex patterns for dangerous operations (open, os, subprocess, etc.)
- `ALLOWED_IMPORTS`: Whitelist of safe modules (sys, json, re)

### request_llm.py
- `sample_document()`: Extracts document type and key sections using LLM
- `generate_extraction_script()`: Generates Python extraction script
- `correct_script()`: Fixes failed scripts based on error messages

### model.py
- `SampledSentences`: Document sampling results
- `GeneratedScript`: Script and explanation from LLM
- `DocumentStructure`: Hierarchical document structure
- `DocumentSection`: Individual section with title, level, content, subsections
- `ScriptExecutionResult`: Execution status and output

## Dependencies

| Package | Purpose |
|---------|---------|
| anthropic>=0.74.1 | Anthropic API client for Claude models |
| click>=8.3.0 | CLI framework |
| pydantic>=2.12.2 | Data validation and models |
| python-dotenv>=1.1.1 | Environment variable management |

## Usage

### Setup

```bash
# Install dependencies
uv sync

# Configure environment
cp .envrc.example .envrc
# Edit .envrc and set ANTHROPIC_API_KEY
```

### Run

```bash
# Basic usage
python -m src.main -m claude-sonnet-4-5 -i data/contract_0.md

# With custom output directory
python -m src.main -m claude-sonnet-4-5 -i data/contract_0.md -od outputs

# Show help
python -m src.main --help
```

### CLI Options

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| --model | -m | Yes | - | Model to use (claude-sonnet-4-5 or claude-opus-4-1) |
| --input | -i | Yes | - | Path to input document file |
| --output-directory | -od | No | outputs | Directory to save output files |

## Development Commands

```bash
# Lint code
make lint

# Format code
make fmt

# Run both lint and format
make fix

# Type checking
make mypy
```

## Implementation Notes

### Security Mechanisms

The script executor implements multiple layers of security:

1. **Pattern-based validation**: Blocks dangerous patterns like `open()`, `os.*`, `subprocess`, `eval()`, `exec()`
2. **Import whitelist**: Only allows `sys`, `json`, `re` modules
3. **Environment isolation**: Runs with empty PATH, HOME, PYTHONPATH
4. **Timeout**: Default 30-second execution limit
5. **Temporary file cleanup**: Script files are deleted after execution

### Self-Correction Loop

When script execution fails:
1. Error message is captured
2. LLM receives original script + error message + document context
3. LLM generates corrected script
4. Process retries up to 3 times (configurable via DEFAULT_MAX_CORRECTION_ATTEMPTS)

### Structured Outputs

Uses Anthropic's beta Structured Outputs feature:
```python
result = await anthropic_client.beta.messages.parse(
    model=model,
    betas=["structured-outputs-2025-11-13"],
    messages=prompt,
    output_format=PydanticModel,  # Type-safe response
)
```
