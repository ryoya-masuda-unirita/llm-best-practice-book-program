# AI Agent Framework with GoF Design Patterns

## Overview

An extensible AI agent framework built with GoF design patterns, implementing a "stable core with flexible extensions" architecture. The framework provides multiple reasoning strategies (Chain-of-Thought, ReAct, Tree-of-Thought), tool management, memory management, execution control, and multi-agent coordination.

## Architecture

```
+-------------------------------------------------------------------------+
|                          Agent Framework                                 |
+-------------------------------------------------------------------------+
|                                                                          |
|  +-------------------------------------------------------------------+  |
|  |                       Extensions Layer                             |  |
|  |  +---------------+ +---------------+ +---------------+             |  |
|  |  |  Strategies   | |   Handlers    | |   Mediators   |             |  |
|  |  |  - CoT        | |  - MaxSteps   | |  - Simple     |             |  |
|  |  |  - ReAct      | |  - CostLimit  | |  - Parallel   |             |  |
|  |  |  - ToT        | |  - RateLimit  | |               |             |  |
|  |  +---------------+ +---------------+ +---------------+             |  |
|  |  +---------------+ +---------------+ +---------------+             |  |
|  |  |    Memory     | |     Tools     | |    Agents     |             |  |
|  |  | - Conversa.   | | - Calculator  | | - Configurable|             |  |
|  |  | - Context     | | - WebSearch   | | - MultiStrat. |             |  |
|  |  | - Caretaker   | | - TextGen     | |               |             |  |
|  |  +---------------+ +---------------+ +---------------+             |  |
|  +-------------------------------------------------------------------+  |
|                                  |                                       |
|                                  v                                       |
|  +-------------------------------------------------------------------+  |
|  |                          Core Layer                                |  |
|  |  +---------------+ +---------------+ +---------------+             |  |
|  |  |   Strategy    | |    Memory     | |  Controller   |             |  |
|  |  |   (Abstract)  | |   (Abstract)  | |   + Handler   |             |  |
|  |  +---------------+ +---------------+ +---------------+             |  |
|  |  +---------------+ +---------------+ +---------------+             |  |
|  |  |   ToolBox     | |   BaseAgent   | | GraphMediator |             |  |
|  |  |  (Composite)  | |               | |   (Abstract)  |             |  |
|  |  +---------------+ +---------------+ +---------------+             |  |
|  |  +---------------+                                                 |  |
|  |  | AgentContext  | <- State Pattern                                |  |
|  |  |   (States)    |                                                 |  |
|  |  +---------------+                                                 |  |
|  +-------------------------------------------------------------------+  |
|                                                                          |
+-------------------------------------------------------------------------+
```

### Directory Structure

```
src/
|-- main.py                    # CLI entry point with Click
|-- examples.py                # 8 example implementations
|-- config.py                  # Environment configuration (Pydantic)
|-- logger.py                  # Logging setup
|-- client/
|   +-- llm_client.py          # Google Gemini API client
+-- agent/
    |-- core/                  # Core layer (stable abstractions)
    |   |-- base.py            # Base interfaces (Tool, Strategy, Action)
    |   |-- agent.py           # BaseAgent implementation
    |   |-- controller.py      # ExecutionController (Chain of Responsibility)
    |   |-- mediator.py        # GraphMediator (Mediator Pattern)
    |   |-- memory.py          # Memory abstract class (Memento Pattern)
    |   |-- states.py          # State management (State Pattern)
    |   +-- toolbox.py         # ToolBox (Composite Pattern)
    +-- extensions/            # Extensions layer (concrete implementations)
        |-- factory.py         # AgentBuilder, create_agent_from_config
        |-- agents/            # ConfigurableAgent, MultiStrategyAgent
        |-- strategies/        # ChainOfThought, ReAct, TreeOfThought
        |-- handlers/          # MaxSteps, CostLimit, ToolRateLimit, etc.
        |-- mediators/         # SimpleGraphMediator, ParallelGraphMediator
        |-- memory/            # ConversationalMemory, ContextMemory, MemoryCaretaker
        |-- nodes/             # AgentNode, DecisionNode, AggregatorNode
        +-- tools/             # Calculator, WebSearch, TextGenerator
```

## Key Components

### Design Patterns Used

| Pattern | Location | Purpose |
|---------|----------|---------|
| Strategy | `Strategy`, `ChainOfThoughtStrategy`, `ReActStrategy`, `TreeOfThoughtStrategy` | Reasoning algorithm switching |
| Composite | `ToolBox`, `CategorizableToolBox` | Hierarchical tool management |
| Memento | `Memory`, `MemorySnapshot`, `MemoryCaretaker` | State save/restore |
| Chain of Responsibility | `ExecutionHandler`, `ExecutionController` | Execution control chain |
| State | `AgentState`, `AgentContext`, `IdleState`, `ThinkingState`, etc. | Agent lifecycle management |
| Mediator | `GraphMediator`, `SimpleGraphMediator`, `ParallelGraphMediator` | Multi-agent coordination |
| Builder | `AgentBuilder` | Declarative agent construction |
| Factory Method | `create_agent_from_config` | Agent creation from config |

### Core Layer Components

- **BaseAgent**: Main agent orchestration class
- **Strategy**: Abstract interface for reasoning strategies
- **Tool**: Abstract interface for agent tools
- **ToolBox**: Composite container for tools
- **ExecutionController**: Manages execution handler chain
- **GraphMediator**: Coordinates multi-agent graphs
- **Memory**: Abstract interface for memory management
- **AgentContext/AgentState**: State machine for agent lifecycle

### Extension Layer Components

- **Strategies**: ChainOfThoughtStrategy, ReActStrategy, TreeOfThoughtStrategy
- **Handlers**: MaxStepsHandler, CostLimitHandler, ToolRateLimitHandler, DangerousActionHandler, LoopDetectionHandler
- **Memory**: ConversationalMemory, ContextMemory, MemoryCaretaker
- **Agents**: ConfigurableAgent, MultiStrategyAgent
- **Nodes**: AgentNode, DecisionNode, AggregatorNode
- **Tools**: CalculatorTool, WebSearchTool, TextGeneratorTool, CategorizableToolBox

## Dependencies

- `google-genai`: Google Gemini API client
- `click`: CLI framework
- `pydantic`: Configuration management
- `python-dotenv`: Environment variable loading

## Usage

### Setup

1. Copy environment template:

```bash
cp .envrc.example .envrc
```

2. Edit `.envrc` with your API key:

```bash
export GEMINI_API_KEY="your-gemini-api-key-here"
```

3. Install dependencies:

```bash
uv sync
```

### Run

Run a specific example:

```bash
uv run python -m src.main --agent example_1_basic_agent
```

Run all examples:

```bash
uv run python -m src.main --agent all
```

### CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--agent` | `-a` | Agent example to run (required) |

Available agent examples:

| Example | Description |
|---------|-------------|
| `example_1_basic_agent` | Chain-of-Thought strategy basic agent |
| `example_2_react_agent` | ReAct strategy agent |
| `example_3_multi_strategy_agent` | Multi-strategy switching agent |
| `example_4_config_based_agent` | Config dictionary-based agent creation |
| `example_5_graph_mediator` | Mediator pattern multi-agent coordination |
| `example_6_parallel_execution` | Parallel multi-agent execution |
| `example_7_memory_snapshots` | Memento pattern memory snapshots |
| `example_8_execution_control` | Chain of Responsibility execution control |

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

- **Core/Extensions Separation**: Core layer provides stable interfaces; extensions layer contains concrete implementations that can evolve independently
- **Agent Construction**: Use `AgentBuilder` for fluent API or `create_agent_from_config` for dictionary-based configuration
- **Execution Control**: Handlers are chained via Chain of Responsibility pattern, allowing flexible addition/removal of control logic
- **Multi-Agent Coordination**: `SimpleGraphMediator` for sequential execution, `ParallelGraphMediator` for concurrent execution
- **Memory Snapshots**: Use `MemoryCaretaker` to save and restore agent memory state at checkpoints
