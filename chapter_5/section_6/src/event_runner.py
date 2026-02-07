"""
Event-driven AI Agent Runner.

This module implements the event runner that monitors a directory for new files
and triggers the contract review pipeline when new documents are detected.

Architecture:
    ┌─────────────────────────────────────────────────────────────────┐
    │                    Event-Driven AI Agent                        │
    │                                                                 │
    │  ┌──────────────┐     ┌──────────────┐     ┌────────────────┐  │
    │  │   Watchdog   │────▶│  Event Bus   │────▶│ Event Handlers │  │
    │  │ (File Watch) │     │              │     │                │  │
    │  └──────────────┘     └──────────────┘     └────────────────┘  │
    │         │                    │                     │           │
    │         │                    │                     │           │
    │         ▼                    ▼                     ▼           │
    │  FileCreatedEvent    Publish/Subscribe    ContractPipeline    │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘

Usage:
    # Start watching the data directory
    python -m src.event_runner --watch-directory data/

    # With custom model and output
    python -m src.event_runner -w data/ -m gpt-4o -od reports/
"""

import asyncio
import signal
import time
from functools import wraps
from pathlib import Path

import click
from src.client.llm_client import OpenAIModel
from src.logger import make_logger
from src.model.event_model import (
    BaseEvent,
    ContractReviewCompletedEvent,
    ContractReviewFailedEvent,
    FileCreatedEvent,
)
from src.service.event_handler import create_default_event_bus
from watchdog.events import FileCreatedEvent as WatchdogFileCreatedEvent
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = make_logger(__name__)


class ContractFileEventHandler(FileSystemEventHandler):
    """
    Watchdog event handler that bridges file system events to the event bus.

    This handler:
    1. Monitors file creation events from watchdog
    2. Filters for relevant file types
    3. Publishes FileCreatedEvent to the event bus
    """

    SUPPORTED_EXTENSIONS = {".md", ".txt"}
    DEBOUNCE_SECONDS = 1.0

    def __init__(self, event_bus, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self.event_bus = event_bus
        self.loop = loop
        self._last_events: dict[str, float] = {}

    def _should_process(self, file_path: str) -> bool:
        """Check if the file should be processed (debounce and extension check)."""
        path = Path(file_path)

        if path.suffix not in self.SUPPORTED_EXTENSIONS:
            return False

        current_time = time.time()
        last_time = self._last_events.get(file_path, 0)

        if current_time - last_time < self.DEBOUNCE_SECONDS:
            return False

        self._last_events[file_path] = current_time
        return True

    def on_created(self, event: WatchdogFileCreatedEvent) -> None:
        """Handle file creation events from watchdog."""
        if event.is_directory:
            return

        file_path = str(event.src_path)

        if not self._should_process(file_path):
            logger.debug(f"Skipping file: {file_path}")
            return

        logger.info(f"New file detected: {file_path}")

        file_event = FileCreatedEvent(file_path=file_path)

        asyncio.run_coroutine_threadsafe(
            self.event_bus.publish(file_event),
            self.loop,
        )


def event_logger_callback(event: BaseEvent) -> None:
    """Callback to log all events for observability."""
    event_dict = event.to_dict()
    logger.info(f"EVENT LOG: {event_dict}")

    if isinstance(event, ContractReviewCompletedEvent):
        logger.info("=" * 60)
        logger.info("CONTRACT REVIEW COMPLETED")
        logger.info(f"  File: {event.contract_file_path}")
        logger.info(f"  Report ID: {event.report_id}")
        logger.info(f"  Status: {event.overall_status}")
        logger.info(f"  Risk Score: {event.risk_score}/100")
        logger.info(f"  Report saved to: {event.report_path}")
        logger.info("=" * 60)

    elif isinstance(event, ContractReviewFailedEvent):
        logger.error("=" * 60)
        logger.error("CONTRACT REVIEW FAILED")
        logger.error(f"  File: {event.contract_file_path}")
        logger.error(f"  Error: {event.error_message}")
        logger.error("=" * 60)


class EventDrivenRunner:
    """
    Main runner for the event-driven AI agent system.

    This class coordinates:
    - File system monitoring via watchdog
    - Event bus for publish/subscribe messaging
    - Async event processing loop
    """

    def __init__(
        self,
        watch_directory: str,
        model: str = OpenAIModel.GPT_5_MINI,
        output_directory: str = "outputs",
    ):
        self.watch_directory = Path(watch_directory).resolve()
        self.model = model
        self.output_directory = output_directory
        self._observer: Observer | None = None
        self._running = False

    async def start(self) -> None:
        """Start the event-driven runner."""
        logger.info("=" * 70)
        logger.info("EVENT-DRIVEN AI AGENT STARTING")
        logger.info("=" * 70)
        logger.info(f"Watch directory: {self.watch_directory}")
        logger.info(f"Model: {self.model}")
        logger.info(f"Output directory: {self.output_directory}")
        logger.info("=" * 70)

        if not self.watch_directory.exists():
            self.watch_directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created watch directory: {self.watch_directory}")

        event_bus = create_default_event_bus(
            model=self.model,
            output_directory=self.output_directory,
        )
        event_bus.register_callback(event_logger_callback)

        loop = asyncio.get_event_loop()

        event_handler = ContractFileEventHandler(event_bus, loop)

        self._observer = Observer()
        self._observer.schedule(
            event_handler,
            str(self.watch_directory),
            recursive=False,
        )
        self._observer.start()

        self._running = True
        logger.info("File watcher started. Waiting for new files...")
        logger.info("Press Ctrl+C to stop.")

        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Runner cancelled")
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the event-driven runner."""
        logger.info("Stopping event-driven runner...")
        self._running = False

        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None

        logger.info("Event-driven runner stopped")


def async_cmd(func):
    """Decorator to run async click commands."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.command()
@click.option(
    "--watch-directory",
    "-w",
    type=click.Path(),
    required=False,
    default="data",
    help="Directory to watch for new contract files.",
)
@click.option(
    "--model",
    "-m",
    type=click.Choice(OpenAIModel.list_str()),
    required=False,
    default=OpenAIModel.GPT_5_MINI,
    help="The model to use for contract review.",
)
@click.option(
    "--output-directory",
    "-od",
    type=click.Path(),
    required=False,
    default="outputs",
    help="Directory to save compliance reports.",
)
@async_cmd
async def main(
    watch_directory: str,
    model: str,
    output_directory: str,
) -> None:
    """
    Event-Driven AI Agent Runner

    This system monitors a directory for new contract files and automatically
    triggers the contract risk compliance pipeline when new files are detected.

    Architecture:

    \b
    1. File Watcher: Monitors directory using watchdog
    2. Event Bus: Publishes FileCreatedEvent on new files
    3. FileCreatedHandler: Transforms to ContractReviewRequestedEvent
    4. ContractReviewHandler: Runs the compliance pipeline
    5. Result Events: Publishes completion/failure events

    Examples:

    \b
        # Watch data directory with defaults
        python -m src.event_runner

        # Watch custom directory
        python -m src.event_runner -w contracts/

        # With custom model
        python -m src.event_runner -w data/ -m gpt-4o

        # With custom output directory
        python -m src.event_runner -w data/ -od reports/
    """
    runner = EventDrivenRunner(
        watch_directory=watch_directory,
        model=model,
        output_directory=output_directory,
    )

    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(runner.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    await runner.start()


if __name__ == "__main__":
    main()
