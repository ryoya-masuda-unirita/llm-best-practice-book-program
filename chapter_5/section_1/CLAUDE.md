# Chapter 5 Section 1: ReAct Agent — Reasoning + Acting with Tools and Structured Output

## What This Section Demonstrates

This section implements the **ReAct (Reasoning and Acting) pattern** with LangGraph: an agent that iterates *Thought → Action (tool call) → Observation* until it has enough information, then delivers a **typed final answer**. The demo is a dinner-menu advisor with four domain tools (recipe search, nutrition check, seasonal ingredients, cooking-time estimation) backed by an in-code database, running on Anthropic Claude.

Two production techniques stand out beyond textbook ReAct:
- **Structured output via a "response tool"** — the final answer is itself a tool (`DinnerRecommendation` Pydantic schema bound as a tool); the agent "calls" it to finish, giving a typed result with no text parsing.
- **A hard iteration cap** — `should_continue` counts tool messages and forces a response at `MAX_ITERATIONS`, so the loop can't run away.

Apply this pattern whenever the model must gather information dynamically (which tools, in which order, how many times — unknown upfront) but the deliverable must be machine-readable.

## Practice Rules

1. **Define tools with `@tool` + docstrings + typed parameters** — the docstring is the model's manual; log every invocation for traceability.
2. **Model the final answer as a tool** (`RESPONSE_TOOL_NAME` = the `DinnerRecommendation` schema). The agent ends the loop by calling it; `respond()` validates the args into the Pydantic model.
3. **Route with a pure decision function**: `should_continue(state) -> Literal["tools", "respond"]` — response tool called → respond; other tool calls → tools; nothing → respond.
4. **Cap the loop**: count `ToolMessage`s in state and force `respond` at `MAX_ITERATIONS`, logging the forced exit.
5. **Keep the graph minimal**: `agent → (tools ⇄ agent) → respond → END` — three nodes, one conditional edge.
6. **Tools return JSON strings** (compact, `ensure_ascii=False`) with graceful fallbacks (recipe search returns defaults rather than empty) — an empty observation stalls reasoning.
7. **Accumulate everything in `AgentState.messages`** — the message list is the agent's working memory and its audit log.

## Architecture

```
CLI (src/main.py)  -r "request" -m model
  ▼
create_dinner_advisor_graph (LangGraph StateGraph)

        ┌────────────► respond ──► END
        │ (response tool called,     extracts DinnerRecommendation
        │  or MAX_ITERATIONS)        from the tool_call args
  agent ┤
   ▲    │ (domain tool calls)
   │    ▼
   └── tools     search_recipes / check_nutrition /
                 get_seasonal_ingredients / estimate_cooking_time
                 (Observation → back to agent)
```

### Directory Structure

```
chapter_5/section_1/
├── src/
│   ├── service/service.py    # tools + graph nodes + ReAct loop + runner
│   ├── model/model.py        # DinnerRecommendation (response schema) + AgentState
│   ├── prompt/prompt.py      # system prompt (role, tool usage guidance)
│   ├── client/llm_client.py  # AnthropicModel enum + LangChain chat model
│   ├── main.py               # CLI (Click)
│   └── config.py / logger.py
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Tools with docstring contracts (`src/service/service.py`)

```python
@tool
def search_recipes(query: str, cuisine_type: str | None = None) -> str:
    """Search for recipes based on keywords and optional cuisine type."""
    ...
    if not results:      # graceful fallback — never return an empty observation
        results = [{**r, "cuisine": "Quick"} for r in RECIPES_DATABASE["Quick"]]
    return json.dumps(results[:5], ensure_ascii=False)
```

### 2. The loop decision with iteration cap

```python
def should_continue(state: AgentState) -> Literal["tools", "respond"]:
    tool_message_count = sum(1 for m in state["messages"] if isinstance(m, ToolMessage))
    if tool_message_count >= MAX_ITERATIONS:
        logger.warning("Max iterations reached, forcing response")
        return "respond"
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call["name"] == RESPONSE_TOOL_NAME:
                return "respond"          # the agent chose to finish
        return "tools"                    # keep acting
    return "respond"
```

### 3. Typed final answer via the response tool

```python
def respond(state: AgentState) -> dict:
    for message in reversed(state["messages"]):
        if isinstance(message, AIMessage) and message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call["name"] == RESPONSE_TOOL_NAME:
                    recommendation = DinnerRecommendation(**tool_call["args"])   # Pydantic validation
                    return {"final_response": recommendation}
```

### 4. Three-node graph

```python
graph = StateGraph(AgentState)
graph.add_node("agent", call_model)     # Thought + Action
graph.add_node("tools", tool_node)      # Observation
graph.add_node("respond", respond)      # typed extraction
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "respond": "respond"})
graph.add_edge("tools", "agent")
graph.add_edge("respond", END)
```

## Data Models

| Model | Purpose |
|-------|---------|
| `DinnerRecommendation` | Final answer schema (menu, cooking time, difficulty, reasons…) — bound as the response tool |
| `AgentState` | Graph state: `messages` history + `final_response` |
| `AnthropicModel` | Model choices: `CLAUDE_SONNET_4_6`, `CLAUDE_SONNET_4_6`, `CLAUDE_SONNET_4_6`, `CLAUDE_SONNET_4_6`, `CLAUDE_HAIKU_4_5` |

## Setup & Run

```bash
cp .envrc.example .envrc     # set ANTHROPIC_API_KEY
uv sync

# Canonical example (default model CLAUDE_HAIKU_4_5)
uv run python -m src.main -r '今日は疲れているので簡単な料理がいい'

# Other models
uv run python -m src.main -m CLAUDE_SONNET_4_6 -r "簡単な夕食"
```

### CLI Options

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--request` | `-r` | Yes | — | Dinner request in natural language |
| `--model` | `-m` | No | `CLAUDE_HAIKU_4_5` | Anthropic model enum name |
| `--output-directory` | `-od` | No | `outputs` | Output directory |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
```

## Implementation Notes

- **Why the response-tool trick**: tool use and free-text generation compete; by making the answer a tool call, the finish condition ("agent called `DinnerRecommendation`") is unambiguous, and the payload arrives pre-structured — no "extract JSON from the last message" fragility.
- **The iteration cap is a correctness feature, not a safety nicety** — LLMs occasionally re-query the same tool indefinitely; counting `ToolMessage`s in state is the cheapest reliable guard.
- **Tools here are deterministic in-code databases**, which keeps the section focused on the loop mechanics; swap the bodies for real APIs (the MCP pattern from Chapter 2 Section 11 fits) without touching the graph.
- **Fallback observations matter**: `search_recipes` returning "no results" repeatedly is the classic ReAct stall; returning sensible defaults keeps the reasoning moving.
- **The message list is your debugging tool** — the full Thought/Action/Observation trace is in `state["messages"]`; log it on failures.

## How to Apply This Practice to Your Own Project

1. List the information-gathering actions your task needs and wrap each as a `@tool` with a precise docstring and typed args.
2. Define the final-answer Pydantic schema and bind it as an additional tool; treat "model called it" as the exit condition.
3. Copy the three-node graph and `should_continue` shape; set `MAX_ITERATIONS` to the largest tool budget you'll pay for.
4. Make every tool return a non-empty, JSON-formatted observation with fallbacks.
5. Log tool invocations and keep the message trace for failed runs.
6. Start with a fast/cheap model (Haiku-class) — ReAct loops multiply per-call latency and cost; upgrade the model only if reasoning quality demands it.
