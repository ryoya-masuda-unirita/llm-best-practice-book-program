# Multi-Agent Contract Review System

## Overview

A multi-agent AI system for contract document review using LangGraph and Google Gemini. The system employs 7 specialized agents (including orchestrator) that collaborate to analyze contracts, assess risks, compare against standard templates, and generate comprehensive review reports.

This project demonstrates the Orchestrator-Worker pattern for Multi-AI Agent architecture, where an orchestrator plans the workflow and dispatches tasks to specialized worker agents, with some workers executing in parallel for efficiency.

## Architecture

```
+-------------------------------------------------------------------------+
|                   Orchestrator-Worker Pipeline                           |
+-------------------------------------------------------------------------+
|                                                                          |
|  +----------------+    +-------------------+                             |
|  | Contract Input |--->|   Orchestrator    |                             |
|  | (Contract/     |    |      Agent        |                             |
|  |  Template)     |    +--------+----------+                             |
|  +----------------+             |                                        |
|                                 v                                        |
|                    +-------------------+                                 |
|                    | Document Parser   |                                 |
|                    |     Worker        |                                 |
|                    +--------+----------+                                 |
|                             |                                            |
|          +------------------+------------------+                         |
|          |                  |                  |                         |
|          v                  v                  v                         |
|  +---------------+  +---------------+  +---------------+                 |
|  |    Clause     |  |     Risk      |  |     Diff      |  (Parallel)    |
|  |  Classifier   |  |  Assessment   |  |    Checker    |                 |
|  |    Worker     |  |    Worker     |  |    Worker     |                 |
|  +-------+-------+  +-------+-------+  +-------+-------+                 |
|          |                  |                  |                         |
|          +------------------+------------------+                         |
|                             |                                            |
|                             v                                            |
|                    +-------------------+                                 |
|                    |     Collector     |                                 |
|                    +--------+----------+                                 |
|                             |                                            |
|                             v                                            |
|                    +-------------------+                                 |
|                    |    Amendment      |                                 |
|                    |    Proposer       |                                 |
|                    +--------+----------+                                 |
|                             |                                            |
|                             v                                            |
|                    +-------------------+                                 |
|                    |   Synthesizer     |                                 |
|                    | (Report Generator)|                                 |
|                    +--------+----------+                                 |
|                             |                                            |
|                             v                                            |
|                    +-------------------+                                 |
|                    |  Review Report    |                                 |
|                    |   (Markdown)      |                                 |
|                    +-------------------+                                 |
+-------------------------------------------------------------------------+
```

### Directory Structure

```
chapter_5/section_3/
|-- src/
|   |-- __init__.py
|   |-- main.py                      # CLI entry point
|   |-- config.py                    # Environment configuration (Gemini API key)
|   |-- logger.py                    # Logging setup
|   |-- client/
|   |   |-- __init__.py
|   |   +-- llm_client.py            # Gemini model definitions
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
| Orchestrator | Plans workflow and dispatches tasks | `orchestrator_plan` |
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
- `OrchestratorPlan` - Task assignments and review strategy
- `ContractReviewReport` - Final report with `to_markdown()` method
- `AgentState` - LangGraph state management TypedDict
- `WorkerState` - State for individual worker agents

### Prompts (src/prompt/multi_agent_prompt.py)

Each agent has:
- System prompt defining role and evaluation criteria (in Japanese)
- Prompt generator function for dynamic user prompts

## Dependencies

| Package | Purpose |
|---------|---------|
| `langchain-google-genai` | LangChain integration for Gemini |
| `langgraph` | Multi-agent graph orchestration |
| `google-genai` | Google Gemini API client |
| `pydantic` | Data validation and models |
| `click` | CLI framework |
| `python-dotenv` | Environment variable management |

## Usage

### Setup

```bash
# Copy environment template
cp .envrc.example .envrc

# Edit .envrc and set API key
GEMINI_API_KEY=<your_key>

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
  -m gemini-2.5-flash \
  -c example/sample_consulting_02.md \
  -t example/standard_consulting_template.md \
  -od reports
```

### CLI Options

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--contract-file` | `-c` | Yes | - | Path to contract file (markdown) |
| `--template-file` | `-t` | Yes | - | Path to standard template (markdown) |
| `--model` | `-m` | No | gemini-2.5-pro | Model: gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite |
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

### Orchestrator-Worker Pattern

- Uses LangGraph `Send` API to dispatch tasks to worker agents
- Parallel execution of Clause Classifier, Risk Assessment, and Diff Checker
- Collector node aggregates results from parallel workers
- Synthesizer generates final report from all worker outputs

### Agent Communication Pattern

- Agents communicate through shared `AgentState` TypedDict
- Each agent receives full state and returns partial update
- `reduce_list` custom reducer handles concurrent list updates from parallel workers
- LangGraph manages state merging automatically

### Structured Output

- All agents use `with_structured_output()` for type-safe responses
- Pydantic models define expected response schemas
- Automatic JSON parsing and validation

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
