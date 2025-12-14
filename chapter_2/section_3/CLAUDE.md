# Chapter 2 Section 14: Unstructured Data Structuring

## Overview

This project is a CLI tool that uses LLM (Large Language Model) multimodal recognition to extract structured data from unstructured image data such as invoices and presentation slides.

The tool leverages Gemini API's multimodal input and structured output capabilities to convert images into machine-processable JSON format, replacing traditional multi-step processes (OCR, text analysis, rule-based extraction) with a single LLM call.

## Architecture

```
+-----------------------------------------------------------------------+
|                          CLI (main.py)                                |
|  - Image file path input                                              |
|  - Model selection                                                    |
|  - Output directory specification                                     |
+-----------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
|                    Service Layer (request_llm.py)                     |
|  +---------------------------------------------------------------+   |
|  | Step 1: request_identify_diagram_type()                        |   |
|  | - Identify document type (invoice / slide)                     |   |
|  +---------------------------------------------------------------+   |
|                              |                                        |
|                              v                                        |
|  +---------------------------------------------------------------+   |
|  | Step 2: extract_from_image()                                   |   |
|  | - Extract structured data based on identified type             |   |
|  +---------------------------------------------------------------+   |
+-----------------------------------------------------------------------+
                                    |
                    +---------------+---------------+
                    v                               v
        +-------------------+           +-------------------+
        |  Invoice Model    |           |   Slide Model     |
        |  - issue_date     |           |  - title          |
        |  - issuer_name    |           |  - main_message   |
        |  - recipient      |           |  - diagrams[]     |
        |  - totals         |           |    - bar_chart    |
        |  - line_items[]   |           |    - line_chart   |
        |  - bank_details   |           |    - pie_chart    |
        +-------------------+           +-------------------+
                                    |
                                    v
                        +-------------------+
                        |   JSON Output     |
                        |   (outputs/*.json)|
                        +-------------------+
```

### Directory Structure

```
chapter_2/section_14/
|-- CLAUDE.md              # This file - project documentation
|-- README.md              # User-facing documentation (Japanese)
|-- Makefile               # Development commands
|-- pyproject.toml         # Project configuration and dependencies
|-- .envrc.example         # Environment variable template
|-- data/                  # Sample image data
|   |-- 001_*.png          # Invoice sample images
|   |-- 002_*.png
|   +-- 003_*.png
|-- outputs/               # Output directory for extracted JSON
+-- src/
    |-- __init__.py
    |-- main.py            # CLI entry point
    |-- config.py          # Configuration management
    |-- logger.py          # Logging setup
    |-- client/
    |   |-- __init__.py
    |   +-- llm_client.py  # Gemini API client initialization
    |-- model/
    |   |-- __init__.py
    |   +-- model.py       # Pydantic data model definitions
    |-- prompt/
    |   |-- __init__.py
    |   +-- prompt.py      # Prompt generation functions
    +-- service/
        |-- __init__.py
        +-- request_llm.py # LLM request handling
```

## Key Components

### Data Models (`src/model/model.py`)

- **DiagramType**: Enum for document types (invoice, slide)
- **Invoice**: Complete invoice data structure with line items, totals, bank details
- **Slide**: Presentation slide with diagrams and chart data
- **SlideDiagram**: Individual diagram with type-specific data points
- **ChartDataPoint**: Data point for charts with label, value, unit, series

### Service Layer (`src/service/request_llm.py`)

- **request_identify_diagram_type()**: Identifies document type from image
- **extract_from_image()**: Extracts structured data based on document type
- **request_gemini()**: Main orchestration function (2-step process)

### Prompt Generation (`src/prompt/prompt.py`)

- **make_diagram_identification_prompt()**: Prompt for document type classification
- **make_invoice_prompt()**: Prompt for invoice data extraction
- **make_slide_prompt()**: Prompt for slide data extraction with combination graph handling

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| click | >=8.3.0 | CLI framework |
| google-genai | >=1.45.0 | Gemini API client |
| pydantic | >=2.12.2 | Data validation and models |
| python-dotenv | >=1.1.1 | Environment variable management |

## Usage

### Setup

1. Create environment file:
```bash
cp .envrc.example .envrc
# Edit .envrc and set GEMINI_API_KEY
```

2. Install dependencies:
```bash
uv sync
# or
pip install -e .
```

### Run

```bash
# Basic usage
python -m src.main -m GEMINI_2_5_FLASH -i data/001_*.png

# With custom output directory
python -m src.main -m GEMINI_2_5_FLASH -i data/001_*.png -od outputs/
```

### CLI Options

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| --model | -m | Yes | Gemini model (GEMINI_2_5_PRO, GEMINI_2_5_FLASH, GEMINI_2_5_FLASH_LITE) |
| --image-path | -i | Yes | Path to input image file |
| --output-directory | -od | No | Output directory (default: outputs) |

## Development Commands

| Command | Description |
|---------|-------------|
| make lint | Run ruff linter with auto-fix |
| make fmt | Format code with ruff |
| make fix | Run both lint and format |
| make mypy | Run type checking with mypy |

## Implementation Notes

### Two-Step Processing

The tool uses a 2-step LLM call approach:
1. First call: Identify document type (invoice vs slide)
2. Second call: Extract data using type-specific schema

This separation improves accuracy by keeping prompts focused.

### Gemini API Constraints

- **No `additionalProperties`**: Gemini API does not support `dict` types in response schemas. Use explicitly typed Pydantic models instead.
- **SecretStr for API keys**: Use `SecretStr` type for secure API key handling with `get_secret_value()` method.

### Combination Graph Handling

For slides with combination graphs (e.g., bar chart + line chart):
- Each sub-graph is extracted as a separate `SlideDiagram` object
- Data points are separated by chart type
- This allows accurate data extraction without mixing different metrics

### Supported Diagram Types

| Type | Description |
|------|-------------|
| bar_chart | Bar/column charts |
| line_chart | Line graphs |
| pie_chart | Pie/donut charts |
| flow_chart | Process flow diagrams |
| system_diagram | Architecture/network diagrams |
| image_diagram | Photos, illustrations, other images |
