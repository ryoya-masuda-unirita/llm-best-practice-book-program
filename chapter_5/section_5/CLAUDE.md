# Contract Risk Compliance Pipeline

## Overview

This project implements a Pipeline AI Agent pattern for contract risk compliance evaluation. It demonstrates how to decompose complex LLM processing into a series of sequential stages, where each stage has a specific responsibility and passes its output to the next stage.

The pipeline reads a contract document, extracts its structure (chapters and sections), evaluates risk for each section, and generates a comprehensive compliance report.

## Architecture

```
+------------------------------------------------------------------+
|                    Contract Pipeline                              |
+------------------------------------------------------------------+
|                                                                   |
|  +-------------------+                                            |
|  |   Input Stage     |  Read contract file from disk              |
|  |   (main.py)       |                                            |
|  +---------+---------+                                            |
|            |                                                      |
|            v                                                      |
|  +-------------------+                                            |
|  | Extraction Stage  |  Parse document structure                  |
|  | (extraction.py)   |  -> Extract chapters and sections          |
|  |                   |  -> Identify parties                       |
|  +---------+---------+                                            |
|            |                                                      |
|            v                                                      |
|  +-------------------+                                            |
|  | Risk Scoring      |  Evaluate each section                     |
|  | Stage             |  -> Assess risk level (low/med/high/crit)  |
|  | (risk_scoring.py) |  -> Categorize findings                    |
|  +---------+---------+                                            |
|            |                                                      |
|            v                                                      |
|  +-------------------+                                            |
|  | Report Stage      |  Generate final report                     |
|  | (report.py)       |  -> Executive summary                      |
|  |                   |  -> Recommendations                        |
|  +---------+---------+                                            |
|            |                                                      |
|            v                                                      |
|        [Output]         Markdown compliance report                |
|                                                                   |
+------------------------------------------------------------------+
```

### Directory Structure

```
src/
|-- __init__.py
|-- main.py                         # CLI entry point
|-- config.py                       # Environment configuration
|-- logger.py                       # Logging utilities
|-- client/
|   |-- __init__.py
|   +-- llm_client.py               # OpenAI model definitions
|-- model/
|   |-- __init__.py
|   +-- model.py                    # Pydantic data models
|-- prompt/
|   |-- __init__.py
|   +-- prompt.py                   # System/user prompt templates
|-- layer/
|   |-- __init__.py
|   |-- base.py                     # Abstract base agent class
|   +-- contract_pipeline/
|       |-- __init__.py
|       |-- extraction.py           # Extraction stage agent
|       |-- risk_scoring.py         # Risk scoring stage agent
|       +-- report.py               # Report generation stage agent
+-- service/
    |-- __init__.py
    +-- service.py                  # LangGraph pipeline orchestration
```

## Key Components

### Data Models (`src/model/model.py`)

- **ContractPipelineState**: TypedDict for LangGraph state management
- **RiskLevel**: Enum (low, medium, high, critical)
- **RiskCategory**: Enum (10 categories: intellectual_property, liability, etc.)
- **ComplianceStatus**: Enum (compliant, needs_review, non_compliant)
- **ContractSection/Chapter**: Document structure models
- **RiskFinding/SectionRiskAssessment**: Risk evaluation results
- **ComplianceReport**: Final output with `to_markdown()` method

### Pipeline Stages (`src/layer/contract_pipeline/`)

- **ExtractionAgent**: Parses raw contract text into structured chapters/sections
- **RiskScoringAgent**: Evaluates each section for risks with severity and category
- **ReportAgent**: Aggregates findings and generates executive summary

### Base Agent (`src/layer/base.py`)

Abstract base class providing:
- LLM invocation with structured output (`with_structured_output`)
- Retry logic (3 attempts with 2s delay)
- Error handling and logging

### Pipeline Service (`src/service/service.py`)

Uses LangGraph StateGraph to orchestrate the linear pipeline flow:
```
extraction -> risk_scoring -> report -> END
```

## Dependencies

| Package | Purpose |
|---------|---------|
| langchain-openai | OpenAI API client with LangChain integration |
| langgraph | Pipeline orchestration with StateGraph |
| pydantic | Data model validation and structured output |
| click | CLI framework |
| python-dotenv | Environment variable loading |
| openai | OpenAI Python SDK |
| anthropic | Anthropic Claude API (optional) |
| google-genai | Google Gemini API (optional) |

## Usage

### Setup

1. Copy environment template:
```bash
cp .envrc.example .envrc
```

2. Set your OpenAI API key in `.envrc`:
```
OPENAI_API_KEY=your_api_key_here
```

3. Install dependencies:
```bash
uv sync
```

### Run

```bash
# Basic usage
python -m src.main -c data/contract_0.md

# Specify model
python -m src.main -c data/contract_0.md -m gpt-5.4

# Custom output directory
python -m src.main -c data/contract_0.md -od reports
```

### CLI Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| --contract-file | -c | Path to contract file (required) | - |
| --model | -m | OpenAI model to use | gpt-5.4-mini |
| --output-directory | -od | Output directory for reports | outputs |
| --help | - | Show help message | - |

### Available Models

- gpt-5.4, gpt-5.4-mini, gpt-5.4-nano
- gpt-5.2
- gpt-5.1
- gpt-5, gpt-5-mini, gpt-5-nano

## Development Commands

```bash
# Lint code
make lint

# Format code
make fmt

# Run both lint and format
make fix

# Type check
make mypy
```

## Implementation Notes

### Pipeline State Flow

Each stage updates the shared `ContractPipelineState`:
1. **extraction**: Populates `extraction_output` and `pending_sections`
2. **risk_scoring**: Populates `risk_scoring_output` from all sections
3. **report**: Populates `compliance_report` with final analysis

### Risk Evaluation Categories

The system evaluates contracts across 10 risk categories:
- Intellectual Property
- Liability
- Confidentiality
- Termination
- Payment
- Compliance
- Warranty
- Indemnification
- Dispute Resolution
- Other

### Concurrency

- Risk scoring stage uses async processing with semaphore-based concurrency control
- Default concurrency limit: 20 parallel section assessments
- Other stages run synchronously

### Error Handling

- LLM calls include retry logic (3 attempts with 2s delay)
- Uses structured output mode for type-safe responses
- Failed section assessments log warnings but continue processing

### Output Format

Reports are generated as Markdown with:
- Executive summary with overall status and risk score
- Risk breakdown by category
- Section-by-section assessment details
- Prioritized recommendations
- Conclusion with action items
