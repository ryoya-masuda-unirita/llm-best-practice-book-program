# Chapter 3, Section 12: Workflow Orchestration for LLM Applications

## Overview

A **workflow orchestration engine** for managing complex LLM processing flows using DAG-based definitions with automatic checkpointing, retry logic, and state management.

**LLM Provider**: Google Gemini (2.5 Flash/Pro)

## Architecture

```
+-----------------------------------------------------------+
|                     WorkflowBuilder                        |
|         (Fluent interface for DAG construction)            |
+-----------------------------------------------------------+
                            |
                            v
+-----------------------------------------------------------+
|                        Workflow                            |
|              (DAG: Nodes + Edges + Validation)             |
|   +-----+    +--------+    +------+    +---+               |
|   |Start|--->|PromptLLM|--->|IfElse|--->|End|              |
|   +-----+    +--------+    +------+    +---+               |
+-----------------------------------------------------------+
                            |
                            v
+-----------------------------------------------------------+
|                    WorkflowEngine                          |
|  +------------------+  +-------------------+               |
|  |CheckpointManager |  |  Retry Logic      |               |
|  | (Persistence)    |  |  (Exp. Backoff)   |               |
|  +------------------+  +-------------------+               |
+-----------------------------------------------------------+
                            |
                            v
+-----------------------------------------------------------+
|                    Gemini Executor                         |
|           (LLM API calls via google-genai)                 |
+-----------------------------------------------------------+
```

## Directory Structure

```
src/
+-- __init__.py           # Package marker
+-- client.py             # Gemini client and executor factory
+-- config.py             # Configuration (API key)
+-- logger.py             # Logging setup
+-- main.py               # CLI entry point
+-- examples.py           # Workflow examples
+-- workflow/
    +-- __init__.py       # Public exports
    +-- models.py         # Core models (Node, Edge, Context, State)
    +-- nodes.py          # Node implementations
    +-- workflow.py       # Workflow DAG class
    +-- builder.py        # WorkflowBuilder
    +-- engine.py         # WorkflowEngine
    +-- checkpoint.py     # Checkpoint management
```

## Key Components

| Component | File | Purpose |
|-----------|------|---------|
| `ExecutionContext` | `models.py` | Carries data between nodes |
| `WorkflowState` | `models.py` | Tracks execution progress |
| `Node` | `models.py` | Abstract base for all nodes |
| `StartNode`, `EndNode` | `nodes.py` | Entry/exit points |
| `PromptNode` | `nodes.py` | LLM API calls |
| `IfElseNode` | `nodes.py` | Conditional branching |
| `LoopNode` | `nodes.py` | Iteration |
| `ScriptNode` | `nodes.py` | Custom Python functions |
| `WorkflowBuilder` | `builder.py` | Fluent workflow construction |
| `WorkflowEngine` | `engine.py` | Execution with retry/checkpoint |
| `CheckpointManager` | `checkpoint.py` | State persistence |
| `create_executor` | `client.py` | Gemini executor factory |

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `click` | >=8.3.0 | CLI framework |
| `google-genai` | >=1.45.0 | Gemini API client |
| `pydantic` | >=2.12.2 | Data validation and models |
| `python-dotenv` | >=1.1.1 | Environment variable loading |

## Usage

### Setup

```bash
cp .envrc.example .envrc
export GEMINI_API_KEY="your-key"
uv sync
```

### Run

```bash
python -m src.main --help
python -m src.main -w example_gemini_simple
python -m src.main -w example_conditional_workflow
python -m src.main -w all
```

### CLI Options

| Option | Values | Description |
|--------|--------|-------------|
| `-w, --workflow` | `example_gemini_simple`, `example_checkpoint_recovery`, `example_loop_workflow`, `example_conditional_workflow`, `example_complex_content_pipeline`, `example_complex_research_workflow`, `all` | Workflow to run |
| `--help` | - | Show help message |

## Development Commands

| Command | Description |
|---------|-------------|
| `make lint` | Lint code with ruff |
| `make fmt` | Format code with ruff |
| `make fix` | Lint and format |
| `make mypy` | Type check with mypy |

## Example

```python
from src.client import GeminiModel, create_executor
from src.workflow import WorkflowBuilder, WorkflowEngine

executor = create_executor(model=GeminiModel.GEMINI_2_5_FLASH)

workflow = (
    WorkflowBuilder("my_workflow", "My Workflow")
    .add_start_node("start", initial_data={"topic": "AI"})
    .add_prompt_node("generate", prompt_template="Explain {topic}.", llm_executor=executor)
    .add_end_node("end")
    .add_edge("start", "generate")
    .add_edge("generate", "end")
    .build()
)

result = await WorkflowEngine().execute(workflow)
```

## Implementation Notes

### Checkpointing
- Auto-saves state every N nodes (configurable via `checkpoint_interval`)
- Checkpoints stored as JSON in `checkpoints/` directory
- Resume from checkpoint: `engine.execute(workflow, resume_from_checkpoint="checkpoint_id")`

### Retry Logic
- Configurable max retries (default: 3)
- Exponential backoff: waits 2^attempt seconds between retries
- Failed nodes tracked in workflow state

### DAG Validation
- Cycle detection using DFS
- Validates start/end nodes exist
- Validates edge node references

### Gemini Models
```python
GeminiModel.GEMINI_2_5_PRO        # gemini-2.5-pro
GeminiModel.GEMINI_2_5_FLASH      # gemini-2.5-flash (default)
GeminiModel.GEMINI_2_5_FLASH_LITE # gemini-2.5-flash-lite
```
