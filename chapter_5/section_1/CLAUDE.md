# ReAct AI Agent - Dinner Menu Advisor

## Overview

A practical implementation of the ReAct (Reasoning and Acting) pattern using LangGraph and LangChain. The agent recommends dinner menus by iteratively reasoning through user requests and using tools to gather information about recipes, nutrition, seasonal ingredients, and cooking times.

## Architecture

```
+------------------------------------------+
|           CLI Layer (main.py)            |
|  - Argument parsing with Click           |
|  - Output directory management           |
+--------------------+---------------------+
                     |
                     v
+------------------------------------------+
|        ReAct Agent (service.py)          |
|  - StateGraph for state transitions      |
|  - Thought-Action-Observation loop       |
|  - Structured output via tool calls      |
+--------------------+---------------------+
                     |
          +----------+----------+
          |                     |
          v                     v
+-----------------+   +-----------------+
|   Tool Layer    |   |  Response Tool  |
| - search_recipes|   | DinnerRecom-    |
| - check_nutrition   | mendation       |
| - get_seasonal_ |   | (Pydantic)      |
|   ingredients   |   +-----------------+
| - estimate_     |
|   cooking_time  |
+-----------------+
```

### ReAct Loop Flow

```
     +-------+
     | Start |
     +---+---+
         |
         v
     +-------+
     | Agent |<--------------+
     +---+---+               |
         |                   |
         v                   |
   +------------+  tools  +------+
   | Tool Call? |-------->| Tool |
   +-----+------+         +------+
         | respond
         v
   +-----------+
   |  Respond  |
   +-----+-----+
         |
         v
     +-------+
     |  End  |
     +-------+
```

### Directory Structure

```
chapter_5/section_1/
|-- src/
|   |-- __init__.py
|   |-- config.py           # API key configuration with Pydantic
|   |-- logger.py           # Logging utilities
|   |-- main.py             # CLI entry point (Click)
|   |-- client/
|   |   |-- __init__.py
|   |   +-- llm_client.py   # OpenAI client and model enum
|   |-- model/
|   |   |-- __init__.py
|   |   +-- model.py        # AgentState, DinnerRecommendation, data constants
|   |-- prompt/
|   |   |-- __init__.py
|   |   +-- prompt.py       # System and user prompt templates
|   +-- service/
|       |-- __init__.py
|       +-- service.py      # ReAct agent graph and tool definitions
|-- outputs/                # Generated recommendation files
|-- .envrc.example          # Environment variable template
|-- pyproject.toml          # Project dependencies
|-- Makefile                # Development commands
+-- README.md               # User documentation
```

## Key Components

### Tools (src/service/service.py)

| Tool | Description |
|------|-------------|
| `search_recipes` | Search recipes by keyword and cuisine type |
| `check_nutrition` | Get nutritional info (calories, protein, etc.) |
| `get_seasonal_ingredients` | Get current season's ingredients |
| `estimate_cooking_time` | Estimate cooking time by skill level |

### Models (src/model/model.py)

- **AgentState**: TypedDict for LangGraph state management
- **DinnerRecommendation**: Pydantic model for structured output with `to_markdown()` method

### Graph Nodes (src/service/service.py)

- **call_model**: Invokes LLM with tool bindings (Thought + Action)
- **tool_node**: Executes tool calls (Observation)
- **should_continue**: Routes to tools or respond based on tool calls
- **respond**: Extracts DinnerRecommendation from final tool call

## Dependencies

| Package | Purpose |
|---------|---------|
| langchain-openai | OpenAI LLM integration |
| langgraph | Agent state graph management |
| click | CLI framework |
| pydantic | Data validation and settings |
| python-dotenv | Environment variable loading |

## Usage

### Setup

```bash
# Copy environment template
cp .envrc.example .envrc

# Set your OpenAI API key
# OPENAI_API_KEY=sk-...

# Install dependencies
uv sync
```

### Run

```bash
# Basic usage
uv run python -m src.main -r "I want something easy to cook tonight"

# With specific model
uv run python -m src.main -m gpt-5.4 -r "Healthy Japanese food"

# Custom output directory
uv run python -m src.main -r "Quick Italian" -od ./my_output
```

### CLI Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| --model | -m | gpt-5-mini | OpenAI model to use |
| --output-directory | -od | outputs | Directory for recommendation files |
| --request | -r | (required) | Natural language dinner request |
| --help | | | Show help message |

## Development Commands

```bash
make lint   # Run ruff linter with auto-fix
make fmt    # Format code with ruff
make fix    # Run both lint and fmt
make mypy   # Run type checking
```

## Implementation Notes

### Infinite Loop Prevention

`MAX_ITERATIONS = 10` limits tool execution cycles to prevent runaway agents.

### Structured Output

Uses `tool_choice="any"` with DinnerRecommendation as a response tool, forcing the model to always call a tool and produce structured output.

### Data Sources

Recipe, nutrition, and seasonal ingredient data are defined as constants in `model.py` for demonstration purposes. In production, these would connect to external APIs or databases.
