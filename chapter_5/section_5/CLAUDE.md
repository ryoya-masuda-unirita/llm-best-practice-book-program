# Chapter 5 Section 5: Event-Driven AI Agent — Triggering Pipelines from Events

## What This Section Demonstrates

This section makes an AI agent **event-driven**: instead of being invoked by a CLI/user, the contract-review pipeline (from Chapter 5 Section 4) is triggered automatically when a new contract file appears in a watched directory. A watchdog file monitor publishes `FileCreatedEvent`s to an in-memory **event bus**; handlers transform events (`FileCreated → ContractReviewRequested → ContractReviewCompleted | Failed`), each stage loosely coupled through typed event objects with correlation IDs.

Apply this pattern to connect agents to the world's triggers — file drops, webhooks, queue messages, schedules — so agent work starts within seconds of the triggering fact, without a human in the invocation path. The in-memory bus stands in for Kafka/RabbitMQ/EventBridge; the design translates directly.

## Practice Rules

1. **Define events as typed objects with an enum type and correlation ID** (`BaseEvent`: event_type, timestamp, correlation_id, `to_dict()`) — the correlation ID ties a file drop to its final report across every hop.
2. **Handlers declare what they consume and return follow-up events**: `can_handle(event) -> bool` + `handle(event) -> BaseEvent | None`. Returning an event chains the flow; returning `None` ends it.
3. **The bus recursively publishes handler results** — event chains (`FileCreated → ReviewRequested → ReviewCompleted`) emerge from handler composition, not hardcoded sequences.
4. **Isolate handler failures at the bus**: exceptions inside one handler/callback are caught and logged; the bus keeps serving other handlers and events.
5. **Bridge thread worlds explicitly**: watchdog callbacks run on a watchdog thread — hand events into asyncio via the loop reference passed into `ContractFileEventHandler`.
6. **Filter events at the edge** (`_should_process`: extension check, dedup) so noise never reaches the bus.
7. **Represent failure as an event** (`ContractReviewFailedEvent`), not just a log line — downstream systems (alerts, retries, dead-letter queues) subscribe to failures like any other event.
8. **Shut down gracefully**: signal handlers stop the observer and drain in-flight work.

## Architecture

```
data/ (watched directory)
  │ new .md file
  ▼
watchdog Observer ─▶ ContractFileEventHandler (filter + thread→asyncio bridge)
  ▼ publish
EventBus (in-memory pub/sub)
  ├─ callbacks: event_logger_callback (observes ALL events)
  ├─ FileCreatedHandler:     FileCreatedEvent → ContractReviewRequestedEvent
  └─ ContractReviewHandler:  ReviewRequested → run contract pipeline (extraction→risk→report)
                             → ContractReviewCompletedEvent | ContractReviewFailedEvent
  ▼ (recursive publish of returned events)
outputs/compliance_report_*.md
```

### Directory Structure

```
chapter_5/section_5/
├── src/
│   ├── event_runner.py               # watchdog observer + EventDrivenRunner + CLI + signals
│   ├── service/
│   │   ├── event_handler.py          # EventHandler ABC / handlers / EventBus / factory
│   │   └── service.py                # contract pipeline (as in Chapter 5 Section 4)
│   ├── layer/contract_pipeline/      # extraction / risk_scoring / report agents
│   ├── model/
│   │   ├── event_model.py            # EventType + event dataclasses
│   │   └── model.py                  # pipeline domain models
│   ├── prompt/prompt.py / client/llm_client.py / config.py / logger.py
├── data/                             # watched directory (drop contracts here)
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Typed events with correlation (`src/model/event_model.py`)

```python
class EventType(StrEnum): ...   # FILE_CREATED / CONTRACT_REVIEW_REQUESTED / _COMPLETED / _FAILED

@dataclass
class BaseEvent:
    # event_type, timestamp, correlation_id (uuid) — shared by all events
    def to_dict(self) -> dict[str, Any]: ...

@dataclass
class ContractReviewCompletedEvent(BaseEvent):
    # file_path, report_path, result summary...
```

### 2. Handlers that chain by returning events (`src/service/event_handler.py`)

```python
class EventHandler(ABC):
    @abstractmethod
    def can_handle(self, event: BaseEvent) -> bool: ...
    @abstractmethod
    async def handle(self, event: BaseEvent) -> BaseEvent | None: ...

class FileCreatedHandler(EventHandler):
    async def handle(self, event) -> ContractReviewRequestedEvent | None:
        ...   # validate/transform; None = drop

class ContractReviewHandler(EventHandler):
    async def handle(self, event) -> ContractReviewCompletedEvent | ContractReviewFailedEvent:
        ...   # runs the LLM pipeline; failure is an EVENT, not just a log
```

### 3. Bus with recursive publish + failure isolation

```python
class EventBus:
    async def publish(self, event: BaseEvent) -> None:
        for callback in self._callbacks:            # observers see everything
            try: callback(event)
            except Exception as e: logger.error(f"Callback error: {e}")

        for handler in self._handlers:
            if handler.can_handle(event):
                try:
                    result_event = await handler.handle(event)
                    if result_event:
                        await self.publish(result_event)     # chain continues
                except Exception as e:
                    logger.error(f"Handler {handler.__class__.__name__} error: {e}")
```

### 4. Watchdog → asyncio bridge (`src/event_runner.py`)

```python
class ContractFileEventHandler(FileSystemEventHandler):
    def __init__(self, event_bus, loop: asyncio.AbstractEventLoop): ...
    def _should_process(self, file_path: str) -> bool: ...   # extension + dedup filter
    def on_created(self, event: WatchdogFileCreatedEvent) -> None:
        # runs on watchdog's thread → schedule bus.publish onto the asyncio loop
```

## Data Models

| Model | Purpose |
|-------|---------|
| `EventType` | Closed set of event names |
| `FileCreatedEvent` / `ContractReviewRequestedEvent` / `ContractReviewCompletedEvent` / `ContractReviewFailedEvent` | The event chain |
| Pipeline models | Same as Chapter 5 Section 4 (extraction/risk/report) |

## Setup & Run

```bash
cp .envrc.example .envrc     # set OPENAI_API_KEY
uv sync

# Start the watcher (runs until Ctrl-C / SIGTERM)
uv run python -m src.event_runner -w data/

# In another terminal: drop a contract in — the pipeline triggers automatically
cp somewhere/contract_1.md data/
```

### CLI Options (`src/event_runner.py`)

| Option | Short | Description |
|--------|-------|-------------|
| `--watch-directory` | `-w` | Directory to monitor for new contract files |
| `--model` | `-m` | Pipeline model (default `GPT_5_MINI`) |
| `--output-directory` | `-od` | Report output directory |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
```

## Implementation Notes

- **Why events instead of a polling script**: handlers are independent units — adding "notify Slack on completion" is a new handler subscribing to `ContractReviewCompletedEvent`, zero changes elsewhere. That extensibility is the pattern's core payoff.
- **The in-memory bus is a teaching stand-in**: it loses events on crash and doesn't scale past one process. Production swaps `EventBus` for Kafka/RabbitMQ/EventBridge — the handler contracts (`can_handle`/`handle`/typed events) carry over unchanged.
- **Correlation IDs are non-negotiable** in event chains: when a report is wrong, the correlation ID reconstructs the exact path (which file, which request, which pipeline run) from logs.
- **Recursive publish depth equals chain length** — fine for short chains; add a hop counter if handlers might create cycles.
- **The threading bridge is where event-driven Python breaks first**: watchdog (threads) and the pipeline (asyncio) meet in `ContractFileEventHandler`; pass the loop in explicitly and never call async code directly from the watchdog thread.

## How to Apply This Practice to Your Own Project

1. Enumerate your triggers (file drop, webhook, queue message, cron) and define the event chain as typed dataclasses with correlation IDs.
2. Write handlers with `can_handle`/`handle`; make each return the next event or `None`.
3. Start with the in-memory bus for local development; keep the bus interface thin so a broker can replace it.
4. Model failures as events and add an alerting/dead-letter handler for them.
5. Filter and dedupe at the trigger edge, before publishing.
6. Instrument a logger callback that sees every event — it's your event-flow trace for free.
