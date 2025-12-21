# Event-Driven AI Agent for Contract Review

## Overview

This project implements an event-driven AI agent system that monitors a directory for new contract files and automatically triggers a contract risk compliance pipeline. When a new file is detected, the system publishes events through an event bus, which coordinates handlers to process the contract and generate a compliance report.

The architecture demonstrates the event-driven pattern for AI agents, enabling loose coupling between components, extensibility, and real-time responsiveness.

## Architecture

```
+-----------------------------------------------------------------------+
|                       Event-Driven AI Agent                           |
|                                                                       |
|  +----------------+     +----------------+     +--------------------+ |
|  |   Watchdog     |---->|   Event Bus    |---->|  Event Handlers    | |
|  | (File Monitor) |     | (Pub/Sub)      |     |                    | |
|  +----------------+     +----------------+     +--------------------+ |
|         |                      |                       |              |
|         v                      v                       v              |
|  FileCreatedEvent      Publish/Subscribe       Contract Pipeline     |
|                                                                       |
+-----------------------------------------------------------------------+

Event Flow:
    FileCreatedEvent
          |
          v
    +---------------------+
    | FileCreatedHandler  |  (Filter & transform)
    +----------+----------+
               |
               v
    ContractReviewRequestedEvent
               |
               v
    +-----------------------------+
    | ContractReviewHandler       |  (Execute pipeline)
    +----------+------------------+
               |
               v
    ContractReviewCompletedEvent / ContractReviewFailedEvent

Contract Review Pipeline (LangGraph):
    +-------------------+
    |   Input Stage     |  (Read contract file)
    +---------+---------+
              |
              v
    +-------------------+
    | Extraction Stage  |  (Parse chapters/sections)
    +---------+---------+
              |
              v
    +-------------------+
    | Risk Scoring      |  (Evaluate each section)
    |     Stage         |
    +---------+---------+
              |
              v
    +-------------------+
    |  Report Stage     |  (Generate compliance report)
    +---------+---------+
              |
              v
            [END]
```

### Directory Structure

```
chapter_5/section_7/
|-- CLAUDE.md                    # This file
|-- README.md                    # User documentation
|-- pyproject.toml               # Project configuration
|-- Makefile                     # Development commands
|-- .envrc.example               # Environment variable template
|-- contract/                    # Contract files (watched directory)
|   |-- contract_0.md
|   |-- contract_1.md
|   +-- ...
|-- outputs/                     # Generated reports
+-- src/
    |-- __init__.py
    |-- event_runner.py          # Event-driven runner (entry point)
    |-- config.py                # Configuration management
    |-- logger.py                # Logging setup
    |-- client/
    |   +-- llm_client.py        # LLM model definitions
    |-- model/
    |   |-- __init__.py
    |   |-- model.py             # Pipeline data models
    |   +-- event_model.py       # Event definitions
    |-- service/
    |   |-- __init__.py
    |   |-- service.py           # Pipeline orchestration
    |   +-- event_handler.py     # Event handlers and bus
    |-- layer/
    |   |-- base.py              # Base layer utilities
    |   +-- contract_pipeline/
    |       |-- extraction.py    # Extraction stage node
    |       |-- risk_scoring.py  # Risk scoring stage node
    |       +-- report.py        # Report generation stage node
    +-- prompt/
        +-- prompt.py            # Prompt templates
```

## Key Components

### Event Models (`src/model/event_model.py`)
- `EventType`: Enum of event types (FILE_CREATED, CONTRACT_REVIEW_REQUESTED, etc.)
- `BaseEvent`: Base class with event_id, correlation_id, timestamp
- `FileCreatedEvent`: Published when a new file is detected
- `ContractReviewRequestedEvent`: Triggers the review pipeline
- `ContractReviewCompletedEvent`: Published on successful review
- `ContractReviewFailedEvent`: Published on failure

### Event Handlers (`src/service/event_handler.py`)
- `EventHandler`: Abstract base class for all handlers
- `FileCreatedHandler`: Filters files and emits review requests
- `ContractReviewHandler`: Executes the contract pipeline
- `EventBus`: In-memory pub/sub system (replaceable with Kafka/RabbitMQ)

### Event Runner (`src/event_runner.py`)
- `ContractFileEventHandler`: Bridges watchdog events to the event bus
- `EventDrivenRunner`: Main runner coordinating file watching and event processing

### Pipeline Service (`src/service/service.py`)
- `create_contract_pipeline_graph()`: Creates LangGraph state machine
- `run_contract_compliance_pipeline()`: Executes the full pipeline

### Pipeline Stages (`src/layer/contract_pipeline/`)
- `extraction_stage_node`: Parses contract structure (chapters, sections)
- `risk_scoring_stage_node`: Evaluates risk for each section
- `report_stage_node`: Generates comprehensive compliance report

## Dependencies

| Package | Purpose |
|---------|---------|
| langgraph | Pipeline AI agent state machine |
| langchain-openai | OpenAI LLM integration |
| langchain-anthropic | Anthropic LLM integration |
| langchain-google-genai | Google Gemini LLM integration |
| watchdog | File system monitoring |
| click | CLI framework |
| pydantic | Data validation and models |
| python-dotenv | Environment variable loading |

## Usage

### Setup

```bash
# Copy environment template
cp .envrc.example .envrc

# Edit .envrc and set your API keys
# OPENAI_API_KEY=sk-...
# GEMINI_API_KEY=...
# ANTHROPIC_API_KEY=...

# Install dependencies
uv sync
```

### Run

Watch a directory and process new files automatically:

```bash
# Watch data/ directory (default)
uv run python -m src.event_runner

# Watch custom directory
uv run python -m src.event_runner -w contracts/

# With custom model
uv run python -m src.event_runner -m gpt-4o

# With custom output directory
uv run python -m src.event_runner -od reports/
```

### CLI Options

#### Event Runner (`src.event_runner`)

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| --watch-directory | -w | data | Directory to watch for new files |
| --model | -m | gpt-4o-mini | LLM model to use |
| --output-directory | -od | outputs | Directory for reports |

## Development Commands

```bash
# Lint code with ruff
make lint

# Format code with ruff
make fmt

# Run both lint and format
make fix

# Type check with mypy
make mypy
```

## Implementation Notes

### Event-Driven Design
- All inter-component communication happens via events
- Correlation IDs track event chains for observability
- Handlers are independent and can be added/removed without affecting others

### File Monitoring
- Uses watchdog library for cross-platform file system events
- Debounce logic (1 second) prevents duplicate processing
- Supports .md and .txt file extensions

### Error Handling
- Failed reviews emit `ContractReviewFailedEvent` with error details
- Handlers catch exceptions and log errors without crashing the system
- Pipeline failures are captured and reported

### Extensibility
- Add new handlers by implementing `EventHandler` interface
- Replace `EventBus` with Kafka/RabbitMQ for production
- Add new pipeline stages by creating nodes and updating the graph

### Observability
- All events are logged with correlation IDs
- Event callbacks can be registered for monitoring
- Completion events include status, risk score, and report path
