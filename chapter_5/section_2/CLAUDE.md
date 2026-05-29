# Chapter 5 Section 2: Deep Think Novel Writer Agent

## Overview

This project implements a **Deep Think Novel Writer Agent** using LangGraph and Google Gemini's extended thinking capabilities. The agent follows the ReAct (Reasoning + Acting) pattern with deep thinking to generate high-quality short novels based on user requests.

The agent leverages Gemini's thinking mode (`thinking_budget=10000`) to perform careful reasoning at each step, using specialized tools for theme analysis, character generation, plot structuring, and prose refinement.

## Architecture

### ReAct Agent Flow

```
+-------------------------------------------------------------+
|                      User Request                           |
|       "Write a story about a lonely lighthouse keeper"      |
+-----------------------------+-------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                 Agent Node (Deep Think)                     |
|    - Gemini 2.5 with thinking_budget=10000                  |
|    - Extended reasoning before action                       |
|    - Decides: use tool OR output final novel                |
+-----------------------------+-------------------------------+
                              |
              +---------------+---------------+
              |                               |
              v                               v
+---------------------+           +---------------------+
|     Tools Node      |           |   Finalize Node     |
|  - analyze_theme    |           |  - Extract novel    |
|  - generate_chars   |           |  - Return result    |
|  - create_plot      |           +---------------------+
|  - refine_prose     |
+---------+-----------+
          |
          +-----------> Back to Agent Node
```

### Directory Structure

```
chapter_5/section_2/
|-- src/
|   |-- __init__.py
|   |-- main.py              # CLI entry point
|   |-- config.py            # Configuration (API keys)
|   |-- logger.py            # Logging setup
|   |-- client/
|   |   |-- __init__.py
|   |   +-- llm_client.py    # LLM client and model enums
|   |-- model/
|   |   |-- __init__.py
|   |   +-- model.py         # Pydantic models and tool data
|   |-- prompt/
|   |   |-- __init__.py
|   |   +-- prompt.py        # Prompt templates
|   +-- service/
|       |-- __init__.py
|       +-- service.py       # LangGraph agent implementation
|-- outputs/                 # Generated novels (auto-created)
|-- .envrc.example           # Environment variable template
|-- pyproject.toml           # Project dependencies
|-- Makefile                 # Development commands
+-- CLAUDE.md                # This file
```

## Key Components

### 1. Agent Service (`src/service/service.py`)

The core ReAct agent implementation using LangGraph:

- **`call_model`**: Invokes Gemini with deep thinking enabled
- **`tool_node`**: Executes tools and returns observations
- **`should_continue`**: Conditional routing (tools vs. end)
- **`extract_final_novel`**: Extracts the completed novel
- **`create_novel_writer_graph`**: Builds the LangGraph state machine
- **`run_novel_writer`**: Main entry point for novel generation

### 2. Tools (`src/service/service.py`)

Four specialized tools for creative writing:

| Tool | Purpose |
|------|---------|
| `analyze_theme` | Extract literary elements, symbolism, and emotional undertones |
| `generate_characters` | Create character profiles with roles and development arcs |
| `create_plot_structure` | Build story structure with tone-specific guidance |
| `refine_prose` | Analyze and suggest improvements for prose style |

### 3. Data Models (`src/model/model.py`)

- **`AgentState`**: TypedDict for LangGraph state management
- **`NovelOutline`**: Pydantic model for story outlines
- **`NovelResult`**: Pydantic model for final novel output
- **Tool Data**: Predefined templates for themes, characters, tones, and styles

### 4. Prompts (`src/prompt/prompt.py`)

System prompts and writing tips that guide the agent's creative process.

## Dependencies

- **LangGraph** (>=1.0.0): Agent orchestration framework
- **LangChain Google GenAI** (>=3.2.0): Gemini integration with thinking support
- **Google GenAI** (>=1.45.0): Direct Gemini API access
- **Pydantic** (>=2.12.2): Data validation and models
- **Click** (>=8.3.0): CLI framework

## Usage

### Setup

```bash
# Copy environment template and set your Gemini API key
cp .envrc.example .envrc
# Edit .envrc: GEMINI_API_KEY=your-api-key

# Install dependencies
uv sync
```

### Run

```bash
# Basic usage
uv run python -m src.main -r "Write a story about finding hope in darkness"

# With specific model
uv run python -m src.main -m gemini-2.5-pro -r "A tale of friendship between unlikely companions"

# Custom output directory
uv run python -m src.main -od ./my_novels -r "A mystery in a small coastal town"
```

### CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--model` | `-m` | Gemini model (gemini-2.5-flash, gemini-2.5-pro, gemini-2.5-flash-lite, gemini-3.5-flash, gemini-3.1-flash-lite) |
| `--output-directory` | `-od` | Directory for output files (default: `outputs`) |
| `--request` | `-r` | Novel request in natural language (required) |

## Development Commands

```bash
make lint    # Run ruff linter with auto-fix
make fmt     # Format code with ruff
make fix     # Run both lint and format
make mypy    # Run type checking
```

## Implementation Notes

### Deep Thinking Configuration

The agent uses Gemini's extended thinking mode:
- `thinking_budget=10000`: Allows up to 10,000 tokens for reasoning
- `temperature=1.0`: Required for thinking mode
- `include_thoughts=True`: Includes thinking process in response

### Safety Mechanisms

- **MAX_ITERATIONS=15**: Prevents infinite tool-calling loops
- Tool results are validated before being passed back to the agent
- Structured error handling throughout the pipeline

### Output Format

Generated novels are saved as Markdown files with UUID-based names:
```
outputs/novel_{uuid}.md
```
