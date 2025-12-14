# Chapter 3, Section 15: AI Agent Abstraction Design

## Overview

This project implements the **AI Agent Abstraction Design** pattern for building autonomous LLM-based systems. The pattern separates agent responsibilities into three independent components:

- **Brain (Strategy)**: Pluggable thinking algorithms (CoT, ReAct, ToT)
- **ToolBox**: Hierarchical tool management via Composite pattern
- **Memory**: Context management with snapshot/restore capabilities

Built on 8 design patterns: Strategy, Composite, Memento, State, Chain of Responsibility, Builder, Factory, and Mediator.

## Architecture

```
+---------------------------------------------------------------+
|                         BaseAgent                              |
|  +----------+  +----------+  +----------+  +---------------+  |
|  | Brain    |  | ToolBox  |  | Memory   |  | Controller    |  |
|  |(Strategy)|  |(Composite|  |(Memento) |  |(Chain of Resp)|  |
|  +----------+  +----------+  +----------+  +---------------+  |
+---------------------------------------------------------------+
        |                                           |
   +----v--------+                         +--------v-------+
   | AgentState  |                         |    Mediator    |
   | (State      |                         | (Multi-Agent   |
   |  Pattern)   |                         |  Coordination) |
   +-------------+                         +----------------+
```

**Execution Flow:**

```
1. User -> Agent.execute(goal)
              |
              v
2. State: Idle -> Thinking
              |
              v
3. Loop until complete:
   +-- Memory.get_context()
   +-- Strategy.think(goal, context, tools)
   +-- Controller.check_execution(action)
   +-- Execute Action:
   |   +-- TOOL_CALL: State -> Acting -> Execute -> Thinking
   |   +-- FINAL_ANSWER: State -> Completed
   |   +-- THINK: Continue reasoning
   +-- Memory.add_action(action)
   +-- Memory.add_observation(result)
              |
              v
4. Return result -> State: Idle
```

### Directory Structure

```
src/
  __init__.py
  config.py           # Configuration (API key loading via pydantic)
  logger.py           # Logging setup
  main.py             # CLI entry point (click-based)
  examples.py         # 8 comprehensive examples
  agent/
    __init__.py       # Package exports (all public classes)
    base.py           # Core abstractions (Tool, Strategy, Memory, Action)
    memory.py         # Memory implementations (ContextMemory, ConversationalMemory)
    toolbox.py        # Tool management (ToolBox, CategorizableToolBox)
    strategies.py     # Thinking strategies (CoT, ReAct, ToT)
    states.py         # State management (AgentState, AgentContext)
    controller.py     # Execution control (safety handlers chain)
    agent.py          # Agent implementations (Base, Configurable, MultiStrategy)
    factory.py        # Builder & Factory patterns
    mediator.py       # Multi-agent coordination (graph-based)
  client/
    __init__.py
    llm_client.py     # LLM client initialization (Gemini)
```

## Key Components

### Design Patterns

| Pattern | Component | Purpose |
|---------|-----------|---------|
| Strategy | `strategies.py` | Swappable thinking algorithms (CoT, ReAct, ToT) |
| Composite | `toolbox.py` | Hierarchical tool organization |
| Memento | `memory.py` | State snapshots and rollback |
| State | `states.py` | Agent execution state management |
| Chain of Responsibility | `controller.py` | Composable safety handlers |
| Builder | `factory.py` | Fluent agent construction |
| Factory | `factory.py` | Configuration-based creation |
| Mediator | `mediator.py` | Multi-agent graph coordination |

### Thinking Strategies

- **ChainOfThoughtStrategy**: Sequential step-by-step reasoning for math/logic
- **ReActStrategy**: Interleaved thought-action-observation for research tasks
- **TreeOfThoughtStrategy**: Explores multiple paths with scoring for creative problems

### Safety Handlers

- `MaxStepsHandler`: Limit total execution steps
- `CostLimitHandler`: Track and limit API costs
- `ToolRateLimitHandler`: Prevent excessive tool calls
- `DangerousActionHandler`: Block unsafe operations
- `LoopDetectionHandler`: Detect infinite loops via action signature tracking

### Agent Types

- `BaseAgent`: Core agent with strategy, toolbox, memory, controller
- `ConfigurableAgent`: Adds logging and iteration tracking
- `MultiStrategyAgent`: Dynamic strategy switching at runtime

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| google-genai | >=1.45.0 | Gemini API client |
| openai | >=2.4.0 | OpenAI API client (optional) |
| pydantic | >=2.12.2 | Configuration and data validation |
| click | >=8.3.0 | CLI interface |
| python-dotenv | >=1.1.1 | Environment variable loading |

## Usage

### Setup

```bash
cd chapter_3/section_15

# Environment setup
cp .envrc.example .envrc
# Edit .envrc: export GEMINI_API_KEY=your_key

# Install dependencies
uv sync  # or: pip install -e .
```

### Run

```bash
# Run all examples
python -m src.main -a all

# Run specific example
python -m src.main -a example_1_basic_agent
python -m src.main -a example_2_react_agent
python -m src.main -a example_3_multi_strategy_agent
python -m src.main -a example_4_config_based_agent
python -m src.main -a example_5_graph_mediator
python -m src.main -a example_6_parallel_execution
python -m src.main -a example_7_memory_snapshots
python -m src.main -a example_8_execution_control

# Show help
python -m src.main --help
```

### CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--agent` | `-a` | The agent workflow to run (required) |
| `--help` | | Show help message |

**Available agents:**
- `example_1_basic_agent` - Chain-of-Thought strategy
- `example_2_react_agent` - ReAct strategy
- `example_3_multi_strategy_agent` - Dynamic strategy switching
- `example_4_config_based_agent` - Factory pattern creation
- `example_5_graph_mediator` - Multi-agent coordination
- `example_6_parallel_execution` - Parallel agent execution
- `example_7_memory_snapshots` - Memento pattern demo
- `example_8_execution_control` - Safety handler chain
- `all` - Run all examples

## Development Commands

```bash
# Lint code (ruff)
make lint

# Format code (ruff)
make fmt

# Lint and format
make fix

# Type check (mypy)
make mypy
```

## Quick Start

### Builder Pattern

```python
from src.agent import (
    AgentBuilder, ChainOfThoughtStrategy,
    CalculatorTool, CategorizableToolBox
)

# Build agent
toolbox = CategorizableToolBox()
toolbox.add_to_category("math", CalculatorTool())

agent = (
    AgentBuilder()
    .with_strategy(ChainOfThoughtStrategy(max_steps=5))
    .with_toolbox(toolbox)
    .with_agent_type("configurable")
    .build()
)

result = agent.execute("Calculate 15 plus 27")
```

### Factory Pattern (Configuration-Based)

```python
from src.agent import create_agent_from_config

config = {
    "type": "configurable",
    "strategy": {"type": "react", "max_iterations": 10},
    "toolbox": {"tools": [{"type": "calculator", "category": "math"}]},
    "controller": {"handlers": {"max_steps": 50, "enable_loop_detection": True}}
}

agent = create_agent_from_config(config)
```

### Multi-Strategy Agent

```python
agent.switch_strategy("cot")   # Use CoT for math
agent.switch_strategy("react") # Use ReAct for research
```

### Memory Snapshots

```python
from src.agent.memory import MemoryCaretaker

caretaker = MemoryCaretaker()
snapshot_id = caretaker.save(memory)
# ... execute tasks ...
caretaker.restore(memory, snapshot_id)  # Rollback
```

## Implementation Notes

### Structured Output Support

The `_call_llm` method in `BaseStrategy` supports structured output via Pydantic models:

```python
from pydantic import BaseModel

class MathResult(BaseModel):
    answer: int
    explanation: str

result = self._call_llm("What is 2+2?", response_schema=MathResult)
# Returns validated MathResult instance
```

### Safety Constraints

Default controller configuration:
- Max steps: 50
- Max cost: $10.0
- Max calls per tool: 10
- Dangerous tools blocked: `delete`, `destroy`, `remove_all`
- Loop detection: 3 repeats in 5-action window

### State Transitions

```
Valid transitions:
  Idle -> Thinking
  Thinking -> Acting, Completed, Error
  Acting -> Thinking, Completed, Error
  Completed -> Idle
  Error -> Idle
```

## Code Statistics

- **Total**: ~2,400 lines across 12 modules
- **Design Patterns**: 8 fully implemented
- **Examples**: 8 comprehensive demos
