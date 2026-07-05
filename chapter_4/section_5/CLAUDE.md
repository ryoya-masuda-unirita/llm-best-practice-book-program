# Chapter 4 Section 5: Building a Workflow Orchestration Engine for LLM Applications

## What This Section Demonstrates

Where Chapter 4 Section 4 used LangGraph, this section **builds the workflow engine itself** — a small DAG-based orchestrator for LLM flows — to expose the mechanics every orchestration tool provides:

- **Node types** as the vocabulary of LLM workflows: `StartNode`, `PromptNode` (LLM call with template), `IfElseNode` (conditional branch), `LoopNode` (bounded iteration), `ScriptNode` (arbitrary Python), `EndNode`.
- **A fluent `WorkflowBuilder`** that constructs and validates the DAG.
- **A `WorkflowEngine`** that walks the graph with per-node retry (exponential backoff) and **checkpointing** — state persisted after each node, so failed runs resume from the last checkpoint instead of restarting.

Apply this practice to understand what you're buying when you adopt LangGraph/Temporal/Step Functions — or when your flow is simple enough that a few hundred lines of your own engine beats a framework dependency.

## Practice Rules

1. **Model workflows as data (nodes + edges), not code paths.** A validated DAG can be visualized, diffed, and persisted; imperative control flow can't.
2. **Give every node one interface**: `async execute(context: ExecutionContext) -> Any`. Outputs go into the context keyed by node ID (`ctx.get_node_output("generate")`); downstream nodes read them.
3. **Templates + context variables for prompts**: `PromptNode(prompt_template="Explain {topic} ...")` renders from context variables, keeping prompts data-driven.
4. **Branching/looping are nodes, not engine special cases** — `IfElseNode` holds a condition callable + branch targets; `LoopNode` holds a body node, exit node, and max iterations.
5. **Checkpoint after every node** (`CheckpointManager.save_checkpoint`) with enough state (`WorkflowState` + `ExecutionContext`) to resume: long LLM workflows must survive process death without re-paying every call.
6. **Retry at the node level** (`_execute_with_retry`, exponential backoff) — the engine retries individual failing nodes; the workflow definition stays clean.
7. **Validate the DAG at build time** (`builder.build()`): unknown edge targets, unset branches, and orphan nodes should fail before execution, not during.

## Architecture

```
WorkflowBuilder (fluent API)
  .add_start_node / add_prompt_node / add_if_else_node / add_loop_node / add_script_node / add_end_node
  .add_edge / set_if_else_branches / set_loop_nodes
  .build() ──▶ Workflow (validated DAG)
                  │
                  ▼
WorkflowEngine.execute(workflow)
  _run: current = start
    while current != end:
      output = _execute_with_retry(node, context, state)     ← exp. backoff per node
      _save_checkpoint(...)                                   ← resume point per node
      current = _get_next_node(workflow, node, output, ctx)   ← edges / branch targets
                  │
                  ▼
Gemini executor (src/client.py)  ← PromptNode LLM calls
CheckpointManager ⇄ checkpoints/<workflow_id>/<checkpoint_id>.json
```

### Directory Structure

```
chapter_4/section_5/
├── src/
│   ├── workflow/
│   │   ├── workflow.py     # Workflow (DAG container + validation)
│   │   ├── nodes.py        # Start/End/Prompt/IfElse/Loop/Script nodes
│   │   ├── builder.py      # WorkflowBuilder fluent API
│   │   ├── engine.py       # WorkflowEngine: run loop, retry, checkpoints
│   │   ├── checkpoint.py   # Checkpoint + CheckpointManager (JSON persistence)
│   │   └── models.py       # Node ABC / Edge / ExecutionContext / WorkflowState
│   ├── client.py           # Gemini client + create_executor factory
│   ├── examples.py         # 6 runnable workflows (simple/conditional/loop/recovery/pipelines)
│   ├── main.py             # CLI: -w <example name>
│   └── config.py / logger.py
├── checkpoints/            # runtime checkpoint files
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Fluent DAG construction (`src/examples.py`)

```python
workflow = (
    WorkflowBuilder("gemini_simple", "Simple Completion")
    .add_start_node("start", initial_data={"topic": "artificial intelligence"})
    .add_prompt_node("generate", "Generate",
                     prompt_template="Explain {topic} in 2-3 sentences.", llm_executor=executor)
    .add_script_node("display", "Display", func=lambda ctx: ctx.get_node_output("generate"))
    .add_end_node("end")
    .add_edge("start", "generate")
    .add_edge("generate", "display")
    .add_edge("display", "end")
    .build()
)
result = await WorkflowEngine(enable_checkpointing=False).execute(workflow)
```

### 2. Conditions as plain callables (`example_conditional_workflow`)

```python
def check_age(ctx: ExecutionContext) -> bool:
    return ctx.get_variable("character_age", 0) >= 18

builder.add_if_else_node("age_check", "Check Age", condition=check_age)
builder.set_if_else_branches("age_check", true_branch="adult", false_branch="minor")
```

### 3. Checkpoint & resume (`src/workflow/checkpoint.py`)

```python
class CheckpointManager:
    def save_checkpoint(self, checkpoint: Checkpoint) -> Path: ...          # per-node persist
    def load_latest_checkpoint(self, workflow_id: str) -> Checkpoint | None: ...
    def restore_from_checkpoint(self, checkpoint) -> tuple[WorkflowState, ExecutionContext]: ...
```

`example_checkpoint_recovery` shows the full cycle: run → crash → `load_latest_checkpoint` → resume from the next node.

### 4. Engine run loop with per-node retry (`src/workflow/engine.py`)

```python
async def _run(self, workflow, context, state):
    # walk nodes from start; for each:
    output = await self._execute_with_retry(node, context, state)   # exp. backoff
    self._save_checkpoint(workflow, state, context)
    next_id = self._get_next_node(workflow, node, output, context)  # edge or branch target
```

## Data Models

| Model | Purpose |
|-------|---------|
| `Node` (ABC) / `Edge` | DAG building blocks (`src/workflow/models.py`) |
| `ExecutionContext` | Variables + per-node outputs shared across the run |
| `WorkflowState` / `ExecutionState` | Run status (running/completed/failed), current node, history |
| `Checkpoint` | Serialized state+context snapshot (JSON), keyed by workflow/checkpoint ID |

## Setup & Run

```bash
cp .envrc.example .envrc     # set GEMINI_API_KEY
uv sync

# Canonical example
uv run python -m src.main -w example_gemini_simple

# Other examples
uv run python -m src.main -w example_conditional_workflow
uv run python -m src.main -w example_loop_workflow
uv run python -m src.main -w example_checkpoint_recovery
uv run python -m src.main -w example_complex_content_pipeline
uv run python -m src.main -w example_complex_research_workflow
```

### CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--workflow` | `-w` | Example workflow name (see list above) |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
```

## Implementation Notes

- **Checkpointing is the killer feature for LLM workflows** — steps are expensive and slow, so resuming from node 7 of 10 instead of re-running everything saves real money. Persist after each node; the checkpoint must contain everything `restore_from_checkpoint` needs.
- **Node granularity = retry/checkpoint granularity.** Make nodes as small as the largest unit you're willing to re-execute on failure.
- **`ScriptNode` is the escape hatch** for glue logic (formatting, aggregation, side effects) — keeping it a node preserves checkpointing/retry semantics for non-LLM steps too.
- **Loops carry an iteration cap** (`LoopNode` max iterations) — same principle as every bounded-retry pattern in this repo: no unbounded LLM loops, ever.
- **Build vs adopt**: this engine is a few hundred lines and dependency-free beyond the LLM SDK. Reach for LangGraph/Temporal when you need concurrency, distributed workers, or event-driven triggers; the concepts (typed state, nodes, routers/edges, checkpoints) transfer 1:1.

## How to Apply This Practice to Your Own Project

1. Inventory your flow's steps and classify each as prompt / branch / loop / script — that's your node list.
2. Express the flow with the builder (or your framework's equivalent), with validation at build time.
3. Store node outputs in a shared context keyed by node ID; render prompts from context variables.
4. Turn on per-node checkpointing for any workflow whose total LLM cost exceeds what you're happy to re-pay on a crash.
5. Set retry (with backoff) and loop caps per node; treat exhaustion as a workflow-level failure with the checkpoint preserved.
6. Start with this minimal engine mentally even if you adopt a framework — if you can't map your flow onto nodes/edges/state, the framework won't save you.
