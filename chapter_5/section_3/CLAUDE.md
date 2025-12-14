# Multi-Agent Contract Review System

## Overview

A multi-agent AI system for contract document review using LangGraph and Anthropic Claude. The system employs 6 specialized agents that collaborate to analyze contracts, assess risks, compare against standard templates, and generate comprehensive review reports.

This project demonstrates the Multi-AI Agent architecture pattern, where complex tasks are decomposed and delegated to specialized expert agents, then results are integrated into a cohesive output.

## Architecture

```
+-------------------------------------------------------------------------+
|                     Contract Review Pipeline                             |
+-------------------------------------------------------------------------+
|                                                                          |
|  +------------+    +------------+    +------------+                      |
|  |  Contract  |--->|  Document  |--->|   Clause   |                      |
|  |   Input    |    |   Parser   |    | Classifier |                      |
|  +------------+    |   Agent    |    |   Agent    |                      |
|                    +------------+    +-----+------+                      |
|                                            |                             |
|                                            v                             |
|  +------------+    +------------+    +------------+                      |
|  |  Standard  |--->|    Diff    |<---|    Risk    |                      |
|  |  Template  |    |  Checker   |    | Assessment |                      |
|  +------------+    |   Agent    |    |   Agent    |                      |
|                    +-----+------+    +------------+                      |
|                          |                                               |
|                          v                                               |
|                    +------------+    +------------+                      |
|                    | Amendment  |--->|   Report   |                      |
|                    |  Proposer  |    | Generator  |                      |
|                    |   Agent    |    |   Agent    |                      |
|                    +------------+    +-----+------+                      |
|                                            |                             |
|                                            v                             |
|                                      +------------+                      |
|                                      |   Review   |                      |
|                                      |   Report   |                      |
|                                      +------------+                      |
+-------------------------------------------------------------------------+
```

### Directory Structure

```
chapter_4/section_3/
|-- src/
|   |-- __init__.py
|   |-- main.py                      # CLI entry point
|   |-- config.py                    # Environment configuration
|   |-- logger.py                    # Logging setup
|   |-- client/
|   |   |-- __init__.py
|   |   +-- llm_client.py            # Anthropic LLM client setup
|   |-- model/
|   |   |-- __init__.py
|   |   +-- multi_agent_model.py     # Pydantic data models and AgentState
|   |-- prompt/
|   |   |-- __init__.py
|   |   +-- multi_agent_prompt.py    # System prompts for each agent
|   +-- service/
|       |-- __init__.py
|       +-- multi_agent_service.py   # LangGraph pipeline implementation
|-- example/                          # Sample contracts and templates
|   |-- standard_nda_template.md
|   |-- sample_nda.md
|   |-- sample_nda_02.md
|   |-- sample_nda_03.md
|   |-- standard_purchase_order_template.md
|   |-- sample_purchase_order_01.md
|   |-- sample_purchase_order_02.md
|   |-- standard_consulting_template.md
|   |-- sample_consulting_01.md
|   +-- sample_consulting_02.md
|-- outputs/                          # Generated review reports
|-- pyproject.toml
|-- Makefile
|-- .envrc.example
+-- README.md
```

## Key Components

### Agents (src/service/multi_agent_service.py)

| Agent | Function | Output |
|-------|----------|--------|
| Document Parser | Extracts clauses from contract text | `parsed_clauses` |
| Clause Classifier | Categorizes clauses (confidentiality, liability, IP, etc.) | `clause_categories` |
| Risk Assessment | Evaluates risk level (1-10) for each clause | `risk_assessments` |
| Diff Checker | Compares contract with standard template | `diffs` |
| Amendment Proposer | Suggests modifications for high-risk clauses | `amendments` |
| Report Generator | Creates final markdown report | `final_report` |

### Data Models (src/model/multi_agent_model.py)

- `ContractClause` - Parsed clause structure
- `ClauseCategory` - Category classification result
- `RiskAssessment` - Risk evaluation with score and factors
- `ClauseDiff` - Difference between contract and template
- `AmendmentProposal` - Suggested modification with rationale
- `ContractReviewReport` - Final report with `to_markdown()` method
- `AgentState` - LangGraph state management TypedDict

### Prompts (src/prompt/multi_agent_prompt.py)

Each agent has:
- System prompt defining role and evaluation criteria
- Prompt generator function for dynamic user prompts

## Dependencies

| Package | Purpose |
|---------|---------|
| `langchain-anthropic` | LangChain integration for Claude |
| `langgraph` | Multi-agent graph orchestration |
| `anthropic` | Anthropic API client |
| `pydantic` | Data validation and models |
| `click` | CLI framework |
| `python-dotenv` | Environment variable management |

## Usage

### Setup

```bash
# Copy environment template
cp .envrc.example .envrc

# Edit .envrc and set API key
ANTHROPIC_API_KEY=<your_key>

# Install dependencies
uv sync
```

### Run

```bash
# Basic usage
python -m src.main -c <contract_file> -t <template_file>

# Example: Review NDA
python -m src.main \
  -c example/sample_nda.md \
  -t example/standard_nda_template.md

# With model selection and custom output
python -m src.main \
  -m claude-opus-4-1 \
  -c example/sample_consulting_02.md \
  -t example/standard_consulting_template.md \
  -od reports
```

### CLI Options

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--contract-file` | `-c` | Yes | - | Path to contract file (markdown) |
| `--template-file` | `-t` | Yes | - | Path to standard template (markdown) |
| `--model` | `-m` | No | claude-sonnet-4-5 | Model: claude-sonnet-4-5 or claude-opus-4-1 |
| `--output-directory` | `-od` | No | outputs | Directory for output files |

## Development Commands

```bash
# Lint code with ruff
make lint

# Format code with ruff
make fmt

# Run both lint and format
make fix

# Type checking with mypy
make mypy
```

## Implementation Notes

### Agent Communication Pattern

- Agents communicate through shared `AgentState` TypedDict
- Each agent receives full state and returns partial update
- LangGraph manages state merging automatically

### JSON Extraction

LLM responses may contain JSON in various formats. The `extract_json_from_response()` function handles:
1. Markdown code blocks: ```json ... ```
2. Direct JSON objects: { ... }
3. Raw response text as fallback

### Risk Evaluation Criteria

Risks are evaluated from the recipient's (Party B) perspective:
- Unilateral disadvantages
- Excessive obligations
- Ambiguous expressions
- Practical difficulties
- Legal risks
- Financial risks (damages, penalties)

### Sample Contracts

The `example/` directory contains intentionally problematic contracts for testing:
- Unlimited liability clauses
- One-sided IP ownership
- Unrestricted audit rights
- Minimal damage caps

These demonstrate the system's ability to identify and flag high-risk provisions.
