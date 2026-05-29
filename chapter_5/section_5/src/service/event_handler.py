"""
Event handlers for event-driven AI agent architecture.

This module implements event handlers (consumers) that process events
in the event-driven contract review system.

Architecture:
    FileCreatedEvent
          │
          ▼
    ┌─────────────────────┐
    │ FileCreatedHandler  │  (Filter & transform)
    └──────────┬──────────┘
               │
               ▼
    ContractReviewRequestedEvent
               │
               ▼
    ┌─────────────────────────────┐
    │ ContractReviewHandler       │  (Run pipeline)
    └──────────┬──────────────────┘
               │
               ▼
    ContractReviewCompletedEvent / ContractReviewFailedEvent
"""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable

from src.client.llm_client import OpenAIModel
from src.logger import make_logger
from src.model.event_model import (
    BaseEvent,
    ContractReviewCompletedEvent,
    ContractReviewFailedEvent,
    ContractReviewRequestedEvent,
    EventType,
    FileCreatedEvent,
)
from src.service.service import run_contract_compliance_pipeline

logger = make_logger(__name__)


EventCallback = Callable[[BaseEvent], None]


class EventHandler(ABC):
    """Abstract base class for event handlers."""

    @abstractmethod
    def can_handle(self, event: BaseEvent) -> bool:
        """Check if this handler can process the given event."""
        pass

    @abstractmethod
    async def handle(self, event: BaseEvent) -> BaseEvent | None:
        """Process the event and optionally return a new event to publish."""
        pass


class FileCreatedHandler(EventHandler):
    """
    Handler for FileCreatedEvent.

    Filters file creation events and transforms them into
    ContractReviewRequestedEvent for supported file types.
    """

    SUPPORTED_EXTENSIONS = {".md", ".txt"}

    def __init__(
        self,
        model: str = OpenAIModel.GPT_5_MINI,
        output_directory: str = "outputs",
    ):
        self.model = model
        self.output_directory = output_directory

    def can_handle(self, event: BaseEvent) -> bool:
        return event.event_type == EventType.FILE_CREATED

    async def handle(self, event: BaseEvent) -> ContractReviewRequestedEvent | None:
        if not isinstance(event, FileCreatedEvent):
            return None

        logger.info(f"FileCreatedHandler processing: {event.file_path}")

        if event.file_extension not in self.SUPPORTED_EXTENSIONS:
            logger.info(f"Skipping unsupported file type: {event.file_extension}")
            return None

        if not Path(event.file_path).exists():
            logger.warning(f"File no longer exists: {event.file_path}")
            return None

        logger.info(f"Creating ContractReviewRequestedEvent for: {event.file_name}")

        return ContractReviewRequestedEvent(
            correlation_id=event.correlation_id,
            contract_file_path=event.file_path,
            model=self.model,
            output_directory=self.output_directory,
        )


class ContractReviewHandler(EventHandler):
    """
    Handler for ContractReviewRequestedEvent.

    Executes the contract compliance pipeline and produces
    either ContractReviewCompletedEvent or ContractReviewFailedEvent.
    """

    def can_handle(self, event: BaseEvent) -> bool:
        return event.event_type == EventType.CONTRACT_REVIEW_REQUESTED

    async def handle(self, event: BaseEvent) -> ContractReviewCompletedEvent | ContractReviewFailedEvent:
        if not isinstance(event, ContractReviewRequestedEvent):
            return ContractReviewFailedEvent(
                correlation_id=event.correlation_id,
                contract_file_path="",
                error_message="Invalid event type",
            )

        logger.info(f"ContractReviewHandler processing: {event.contract_file_path}")
        logger.info(f"Using model: {event.model}")

        try:
            report = await run_contract_compliance_pipeline(
                contract_file_path=event.contract_file_path,
                model=event.model,
            )

            if report is None:
                return ContractReviewFailedEvent(
                    correlation_id=event.correlation_id,
                    contract_file_path=event.contract_file_path,
                    error_message="Pipeline returned no report",
                )

            os.makedirs(event.output_directory, exist_ok=True)
            report_path = Path(event.output_directory) / f"compliance_report_{report.report_id}.md"
            report_path.write_text(report.to_markdown(), encoding="utf-8")

            logger.info(f"Report saved: {report_path}")

            return ContractReviewCompletedEvent(
                correlation_id=event.correlation_id,
                contract_file_path=event.contract_file_path,
                report_id=report.report_id,
                report_path=str(report_path),
                overall_status=report.executive_summary.overall_status,
                risk_score=report.executive_summary.overall_risk_score,
            )

        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            return ContractReviewFailedEvent(
                correlation_id=event.correlation_id,
                contract_file_path=event.contract_file_path,
                error_message=f"File not found: {e}",
            )
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            return ContractReviewFailedEvent(
                correlation_id=event.correlation_id,
                contract_file_path=event.contract_file_path,
                error_message=str(e),
            )


class EventBus:
    """
    Simple in-memory event bus for event-driven architecture.

    In production, this would be replaced with a message broker
    like Apache Kafka, RabbitMQ, or AWS EventBridge.
    """

    def __init__(self):
        self._handlers: list[EventHandler] = []
        self._callbacks: list[EventCallback] = []

    def register_handler(self, handler: EventHandler) -> None:
        """Register an event handler."""
        self._handlers.append(handler)
        logger.info(f"Registered handler: {handler.__class__.__name__}")

    def register_callback(self, callback: EventCallback) -> None:
        """Register a callback to be notified of all events."""
        self._callbacks.append(callback)

    async def publish(self, event: BaseEvent) -> None:
        """
        Publish an event to the bus.

        The event is processed by all handlers that can handle it,
        and any resulting events are recursively published.
        """
        logger.info(f"Event published: {event.event_type.value} [correlation_id={event.correlation_id[:8]}...]")

        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Callback error: {e}")

        for handler in self._handlers:
            if handler.can_handle(event):
                logger.info(f"Handler {handler.__class__.__name__} processing event")
                try:
                    result_event = await handler.handle(event)
                    if result_event:
                        await self.publish(result_event)
                except Exception as e:
                    logger.error(f"Handler {handler.__class__.__name__} error: {e}")


def create_default_event_bus(
    model: str = OpenAIModel.GPT_5_MINI,
    output_directory: str = "outputs",
) -> EventBus:
    """Create an event bus with default handlers configured."""
    bus = EventBus()
    bus.register_handler(FileCreatedHandler(model=model, output_directory=output_directory))
    bus.register_handler(ContractReviewHandler())
    return bus
