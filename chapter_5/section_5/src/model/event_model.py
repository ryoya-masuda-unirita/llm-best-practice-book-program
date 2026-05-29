"""
Event models for event-driven AI agent architecture.

This module defines events used in the event-driven contract review system.
Events follow a publish-subscribe pattern where:
- FileCreatedEvent: Published when a new file is detected in the watched directory
- ContractReviewRequestedEvent: Published to trigger contract review pipeline
- ContractReviewCompletedEvent: Published when review is complete
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4


class EventType(StrEnum):
    """Types of events in the system."""

    FILE_CREATED = "file_created"
    CONTRACT_REVIEW_REQUESTED = "contract_review_requested"
    CONTRACT_REVIEW_COMPLETED = "contract_review_completed"
    CONTRACT_REVIEW_FAILED = "contract_review_failed"


@dataclass
class BaseEvent:
    """Base class for all events in the system."""

    event_id: str = field(default_factory=lambda: uuid4().hex)
    correlation_id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: EventType = field(default=EventType.FILE_CREATED)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
        }


@dataclass
class FileCreatedEvent(BaseEvent):
    """Event published when a new file is created in the watched directory."""

    file_path: str = ""
    file_name: str = ""
    file_extension: str = ""
    event_type: EventType = field(default=EventType.FILE_CREATED)

    def __post_init__(self):
        if self.file_path:
            path = Path(self.file_path)
            self.file_name = path.name
            self.file_extension = path.suffix

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "file_path": self.file_path,
                "file_name": self.file_name,
                "file_extension": self.file_extension,
            }
        )
        return base


@dataclass
class ContractReviewRequestedEvent(BaseEvent):
    """Event published to trigger contract review pipeline."""

    contract_file_path: str = ""
    model: str = "gpt-5.4-mini"
    output_directory: str = "outputs"
    event_type: EventType = field(default=EventType.CONTRACT_REVIEW_REQUESTED)

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "contract_file_path": self.contract_file_path,
                "model": self.model,
                "output_directory": self.output_directory,
            }
        )
        return base


@dataclass
class ContractReviewCompletedEvent(BaseEvent):
    """Event published when contract review is completed successfully."""

    contract_file_path: str = ""
    report_id: str = ""
    report_path: str = ""
    overall_status: str = ""
    risk_score: int = 0
    event_type: EventType = field(default=EventType.CONTRACT_REVIEW_COMPLETED)

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "contract_file_path": self.contract_file_path,
                "report_id": self.report_id,
                "report_path": self.report_path,
                "overall_status": self.overall_status,
                "risk_score": self.risk_score,
            }
        )
        return base


@dataclass
class ContractReviewFailedEvent(BaseEvent):
    """Event published when contract review fails."""

    contract_file_path: str = ""
    error_message: str = ""
    event_type: EventType = field(default=EventType.CONTRACT_REVIEW_FAILED)

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "contract_file_path": self.contract_file_path,
                "error_message": self.error_message,
            }
        )
        return base
