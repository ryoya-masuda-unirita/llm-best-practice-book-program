# Chapter 4 Section 7: AI Agent Abstraction Design — Brain / ToolBox / Memory / Controller

## What This Section Demonstrates

This section defines a **reference decomposition for autonomous LLM agents**, separating what most agent frameworks fuse together:

- **Brain (`Strategy`)** — pluggable thinking algorithms: Chain-of-Thought, ReAct, Tree-of-Thought, all behind one `Strategy.think()` interface.
- **ToolBox (`Tool` + Composite)** — tools and nested tool collections share the `Tool` interface, so a toolbox is itself a tool.
- **Memory (`Memory` + Memento)** — context accumulation with snapshot/restore (`MemorySnapshot`, `MemoryCaretaker`).
- **Controller (Chain of Responsibility)** — safety handlers (max steps, cost limit, tool rate limit, dangerous actions, loop detection) that every proposed action passes through.
- **State machine + Mediator** — explicit agent lifecycle states (Idle/Thinking/Acting/…​) and graph-based multi-agent coordination (`SimpleGraphMediator`, `ParallelGraphMediator`).

Eight GoF patterns cooperate here (Strategy, Composite, Memento, State, Chain of Responsibility, Builder, Factory, Mediator). Apply this when building agents beyond a demo: the decomposition is what lets you change the reasoning style, restrict tools, cap costs, or coordinate multiple agents without rewriting the loop.

## Practice Rules

1. **Type the agent's vocabulary first**: `Action` (TOOL_CALL / FINAL_ANSWER / THINK / OBSERVE), `ToolResult` (success/data/error), `ContextData` — everything the loop passes around is a dataclass, never loose dicts.
2. **The think step is a strategy**: `Strategy.think(goal, context, tools) -> Action`. CoT/ReAct/ToT differ only inside; the agent loop doesn't change.
3. **Tools compose**: `ToolBox(Tool)` contains tools (or other toolboxes) — agents receive one `Tool` root and discover capabilities uniformly.
4. **Gate every action through a handler chain** before execution: `MaxStepsHandler → CostLimitHandler → ToolRateLimitHandler → DangerousActionHandler → LoopDetectionHandler`. Each can block with a reason; adding a policy = adding a handler.
5. **Make agent status explicit** (`AgentStatus` + `AgentState` classes with legal transitions) — "the agent is stuck" becomes an inspectable state, and pause/resume becomes possible.
6. **Snapshot memory at milestones** (Memento) so long runs can roll back to a known-good context instead of dying.
7. **Coordinate multiple agents through a mediator graph** (Agent/Decision/Aggregator nodes + edges), not through agents calling each other directly.

## Architecture

```
BaseAgent.execute(goal)
  State: Idle → Thinking
  loop:
    context = Memory.get_context()
    action  = Strategy.think(goal, context, tools)        ← Brain (CoT/ReAct/ToT)
    Controller.check_execution(action)                    ← handler chain gate
    ├─ TOOL_CALL     → State: Acting → ToolBox.execute → Memory.add_observation → Thinking
    ├─ FINAL_ANSWER  → State: Completed
    └─ blocked       → State: Error/Paused (reason recorded)

Multi-agent: GraphMediator
  AgentNode ─▶ DecisionNode ─▶ AgentNode(s) ─▶ AggregatorNode
  (SimpleGraphMediator = sequential, ParallelGraphMediator = concurrent branches)
```

### Directory Structure

```
chapter_4/section_7/
├── src/
│   ├── agent/
│   │   ├── base.py          # Action/ActionType/ToolResult/ContextData/Tool/Strategy/Memory ABCs
│   │   ├── agent.py         # BaseAgent / ConfigurableAgent / MultiStrategyAgent
│   │   ├── strategies.py    # ChainOfThought / ReAct / TreeOfThought strategies
│   │   ├── toolbox.py       # ToolBox (Composite) + concrete tools (calculator, search, writing...)
│   │   ├── memory.py        # ContextMemory / ConversationalMemory / MemorySnapshot / Caretaker
│   │   ├── controller.py    # ExecutionController + 5 safety handlers (Chain of Responsibility)
│   │   ├── states.py        # AgentStatus + state classes (State pattern)
│   │   ├── factory.py       # AgentBuilder (Builder/Factory)
│   │   └── mediator.py      # graph nodes/edges + Simple/Parallel mediators
│   ├── examples.py          # examples 1–8 (basic → ReAct → multi-strategy → graph → control)
│   ├── client/llm_client.py
│   ├── main.py              # CLI: -a <example>
│   └── config.py / logger.py
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Typed agent vocabulary (`src/agent/base.py`)

```python
class ActionType(Enum):
    TOOL_CALL = "tool_call"
    FINAL_ANSWER = "final_answer"
    THINK = "think"
    OBSERVE = "observe"

@dataclass
class Action:
    type: ActionType
    tool_name: str | None = None
    params: ToolParams = field(default_factory=dict)
    answer: str | None = None
    thought: str | None = None

@dataclass
class ToolResult:
    success: bool
    data: ToolData
    error: str | None = None
```

### 2. Strategy as the brain (`src/agent/strategies.py`)

```python
class Strategy(ABC):
    @abstractmethod
    def think(self, goal, context: ContextData, tools) -> Action: ...

class ChainOfThoughtStrategy(BaseStrategy): ...   # linear reasoning then answer
class ReActStrategy(BaseStrategy): ...            # thought → tool call → observation loop
class TreeOfThoughtStrategy(BaseStrategy): ...    # ThoughtNode/ThoughtTreeLevel exploration
```

### 3. Safety as a handler chain (`src/agent/controller.py`)

```python
class ExecutionHandler(ABC): ...                      # handle(request) -> ExecutionResponse | pass on
class MaxStepsHandler(ExecutionHandler): ...          # step budget
class CostLimitHandler(ExecutionHandler): ...         # spend budget
class ToolRateLimitHandler(ExecutionHandler): ...     # per-tool call caps
class DangerousActionHandler(ExecutionHandler): ...   # deny-listed operations
class LoopDetectionHandler(ExecutionHandler): ...     # repeated-action detection

class ExecutionController:                            # chains them; first block wins
```

### 4. Memory snapshots (Memento) (`src/agent/memory.py`)

```python
class MemoryCaretaker:
    # save(snapshot) / restore(index) — roll back agent context to a prior point
```

### 5. Multi-agent graph (Mediator) (`src/agent/mediator.py`)

```python
AgentNode / DecisionNode / AggregatorNode + Edge(EdgeType)
SimpleGraphMediator      # sequential graph execution with logs
ParallelGraphMediator    # concurrent independent branches
```

## Data Models

| Model | Purpose |
|-------|---------|
| `Action` / `ActionType` / `ToolResult` / `ContextData` | Loop vocabulary |
| `StepInfo` | Per-step record (thought/action/result) |
| `AgentStatus` / `AgentState` subclasses | Lifecycle state machine |
| `MemorySnapshot` | Point-in-time context capture |
| `ExecutionRequest` / `ExecutionResponse` | Controller chain I/O |
| `Message` / `NodeResult` / `GraphExecutionResult` | Mediator graph I/O |

## Setup & Run

```bash
cp .envrc.example .envrc     # set GEMINI_API_KEY
uv sync

# Canonical example
uv run python -m src.main -a example_1_basic_agent

# The progression
uv run python -m src.main -a example_2_react_agent
uv run python -m src.main -a example_3_multi_strategy_agent
uv run python -m src.main -a example_4_config_based_agent
uv run python -m src.main -a example_5_graph_mediator
uv run python -m src.main -a example_6_parallel_execution
uv run python -m src.main -a example_7_memory_snapshots
uv run python -m src.main -a example_8_execution_control
```

### CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--agent-example` | `-a` | Example name (1–8, see above) |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
```

## Implementation Notes

- **Why decompose the agent**: monolithic agent loops entangle reasoning style, tool wiring, safety policy, and memory. Each concern here changes independently — swap ReAct for ToT (one constructor argument), tighten cost limits (one handler config), add a tool (one `Tool` subclass) — without touching the loop.
- **The controller chain is the production-readiness layer.** Every real incident class maps to a handler: runaway loops (LoopDetection/MaxSteps), budget burn (CostLimit), abusive tool usage (ToolRateLimit), destructive calls (DangerousAction). Handlers run *before* execution, not after.
- **State pattern earns its keep at pause/resume**: `PausedState`/`WaitingState` make human-in-the-loop insertion a state transition rather than a redesign.
- **`AgentBuilder`** assembles agents from config (example 4) — strategies/tools/limits declared as data, enabling per-tenant agent configurations.
- **Mediator over direct calls** in multi-agent setups keeps message routing, logging (`ExecutionLogEntry`), and aggregation observable in one place; `ParallelGraphMediator` adds concurrency without changing node code.

## How to Apply This Practice to Your Own Project

1. Adopt the vocabulary types (`Action`, `ToolResult`, `ContextData`) verbatim — they are domain-neutral and force clean seams.
2. Implement your reasoning style as a `Strategy`; start with ReAct, keep CoT as the cheap fallback.
3. Wrap existing functions/APIs as `Tool` subclasses and group them in a `ToolBox`; agents get the root toolbox only.
4. Stand up the `ExecutionController` with MaxSteps + CostLimit on day one; add DangerousAction patterns before giving agents write-capable tools.
5. Add memory snapshots around risky phases (before a destructive tool sequence) so recovery is a restore, not a rerun.
6. For multi-agent flows, define the graph (agents, decisions, aggregation) in mediator terms first — if you can't draw it, don't build it.
