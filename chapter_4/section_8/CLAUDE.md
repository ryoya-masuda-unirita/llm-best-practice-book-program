# Chapter 4 Section 8: Agent Framework Packaging — Stable Core, Flexible Extensions

## What This Section Demonstrates

This section takes the agent abstractions from Chapter 4 Section 7 and **restructures them as a framework**: a `core/` package containing only stable abstractions (ABCs, dataclasses, the agent loop) and an `extensions/` package containing everything replaceable (concrete strategies, tools, handlers, memories, mediators, agents). The dependency rule is one-way — extensions import core; core never imports extensions.

The practice is **framework packaging for growth**: when agents evolve, new reasoning styles/tools/policies land as new files under `extensions/` while `core/` stays untouched. Apply this layering when your agent code is shared across teams or products, or when Section 7's single-module layout starts accumulating merge conflicts.

## Practice Rules

1. **Core contains only contracts and the loop**: `base.py` (Action/ToolResult/Tool/Strategy ABCs), `agent.py` (BaseAgent), `controller.py` (ExecutionController + handler ABC), `memory.py` (Memory ABC + snapshot), `states.py`, `toolbox.py` (Composite), `mediator.py` (graph ABCs). No LLM calls, no concrete behavior.
2. **Everything concrete is an extension** in its own module: one strategy per file (`strategies/react.py`), one handler per file (`handlers/cost_limit.py`), one tool per file (`tools/calculator.py`). Adding capability = adding a file.
3. **Dependencies point inward only** — `extensions/* → core/*`, never the reverse. If core needs to know about a concrete class, the abstraction is wrong.
4. **Factories live at the extension boundary** (`extensions/factory.py`, `extensions/handlers/factory.py`) — assembly knowledge is an extension concern; core stays constructor-only.
5. **Group extensions by kind, not by feature** (`strategies/`, `handlers/`, `tools/`, `memory/`, `mediators/`, `nodes/`, `agents/`) so contributors know exactly where new code goes.
6. **Re-export a curated public API** via each package's `__init__.py`; consumers import from `src.agent`, not from deep paths.

## Architecture

```
src/agent/
├── core/                      ← stable: ABCs + loop + typed vocabulary
│   ├── base.py        Action / ActionType / ToolResult / ContextData / Tool / Strategy / StepInfo
│   ├── agent.py       BaseAgent (the execute loop)
│   ├── controller.py  ExecutionHandler ABC + ExecutionController (chain)
│   ├── memory.py      Memory ABC + MemorySnapshot
│   ├── states.py      AgentStatus / AgentState machine
│   ├── toolbox.py     ToolBox (Composite root)
│   └── mediator.py    Node/Edge/GraphMediator ABCs
└── extensions/                ← replaceable: concrete everything
    ├── strategies/    chain_of_thought.py / react.py / tree_of_thought.py
    ├── handlers/      max_steps / cost_limit / tool_rate_limit / dangerous_action / loop_detection (+factory)
    ├── tools/         calculator / web_search / text_generator / categorizable_toolbox
    ├── memory/        context.py / conversational.py / caretaker.py
    ├── mediators/     simple.py / parallel.py
    ├── nodes/         agent_node.py / decision_node.py / aggregator_node.py
    ├── agents/        configurable.py / multi_strategy.py
    └── factory.py     AgentBuilder (assembly from config)

Dependency rule:  extensions ──▶ core   (never core ──▶ extensions)
```

### Directory Structure (section root)

```
chapter_4/section_8/
├── src/
│   ├── agent/            # core/ + extensions/ as above
│   ├── examples.py       # runnable demos incl. example_1_basic_agent
│   ├── client/llm_client.py   # Gemini client
│   ├── main.py           # CLI: -a <example>
│   └── config.py / logger.py
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Core declares, extensions implement

```python
# core/base.py — contract only
class Strategy(ABC):
    @abstractmethod
    def think(self, goal, context: ContextData, tools) -> Action: ...

# extensions/strategies/react.py — one concrete style, one file
class ReActStrategy(BaseStrategy):
    def think(self, goal, context, tools) -> Action:
        ...  # thought → tool call → observation loop
```

### 2. Handlers as drop-in policy files (`extensions/handlers/`)

```python
# core/controller.py
class ExecutionHandler(ABC): ...          # handle(request) or pass to next
class ExecutionController: ...            # runs the chain

# extensions/handlers/cost_limit.py — a new policy is a new file
class CostLimitHandler(ExecutionHandler): ...
# extensions/handlers/factory.py assembles the default chain
```

### 3. Composite toolbox in core, tools in extensions

```python
# core/toolbox.py
class ToolBox(Tool):                      # a toolbox IS a tool (Composite)
    ...

# extensions/tools/calculator.py
class CalculatorTool(Tool): ...
```

### 4. Assembly via builder at the boundary (`extensions/factory.py`)

```python
class AgentBuilder:
    # .with_strategy(...).with_tools(...).with_handlers(...).build()
    # config-driven agent assembly; core classes never construct extensions
```

## Data Models

Same typed vocabulary as Chapter 4 Section 7 (`Action`, `ToolResult`, `ContextData`, `StepInfo`, `AgentStatus`, `MemorySnapshot`, mediator `Message`/`NodeResult`/`GraphExecutionResult`) — now all defined in `core/` and imported by extensions.

## Setup & Run

```bash
cp .envrc.example .envrc     # set GEMINI_API_KEY
uv sync

# Canonical example
uv run python -m src.main -a example_1_basic_agent
```

### CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--agent-example` | `-a` | Example to run (see `src/examples.py`) |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
```

## Implementation Notes

- **Section 7 vs Section 8**: identical patterns (Strategy, Composite, Memento, State, Chain of Responsibility, Builder, Factory, Mediator); different *packaging*. Section 7 optimizes for reading the whole design in a few files; this section optimizes for many contributors evolving it safely. Use 7's layout for exploration, 8's for a shared codebase.
- **The one-way dependency rule is the whole discipline.** Enforce it in review (or with import-linter); the first `core → extensions` import quietly turns the framework back into a monolith.
- **One-concept-per-file granularity** makes ownership and diffs clean: a new tool PR touches exactly one new file plus an `__init__.py` export.
- **Factories at the boundary** keep core free of construction knowledge, which is what allows alternative assemblies (test agents with mock tools, per-tenant agent configs) without core changes.
- **Public API via `__init__.py` re-exports** insulates consumers from internal file moves — refactor extensions freely as long as exports hold.

## How to Apply This Practice to Your Own Project

1. Split your agent code into `core/` (ABCs, typed vocabulary, loop) and `extensions/` (all concrete classes), enforcing the one-way import rule.
2. Give every extension kind its own subpackage; one class per file.
3. Move all object assembly into boundary factories/builders; core classes accept dependencies, never create them.
4. Curate `__init__.py` exports as your public API; treat deep imports as private.
5. Add an import-direction lint (e.g. import-linter contract) to CI so the layering survives contributors.
6. When a new requirement arrives, ask "which extension kind is this?" — if the answer is "core", stop and re-examine: core changes should be rare and deliberate.
