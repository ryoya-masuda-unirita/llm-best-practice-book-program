"""Request queue for managing burst traffic and queueing requests."""

import asyncio
from dataclasses import dataclass
from typing import Any

from src.logger import make_logger

logger = make_logger(__name__)


@dataclass
class QueueConfig:
    """Configuration for request queue."""

    max_queue_size: int = 100  # Maximum number of queued requests
    request_timeout: float = 300.0  # Maximum time a request can wait in queue (seconds)


class RequestQueueFullError(Exception):
    """Exception raised when request queue is full."""

    pass


class RequestQueue:
    """
    Request queue for managing burst traffic.

    This queue allows requests to be held temporarily when the system
    is under high load, preventing request rejection and enabling
    graceful degradation.
    """

    def __init__(self, config: QueueConfig):
        """Initialize the request queue."""
        self.config = config
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=config.max_queue_size)
        self.active_requests = 0
        self.total_queued = 0
        self.total_processed = 0
        self.total_timeouts = 0

        logger.info(f"Request queue initialized: max_size={config.max_queue_size}, timeout={config.request_timeout}s")

    async def enqueue(self, request_data: Any) -> Any:
        """
        Add a request to the queue and wait for processing.

        Args:
            request_data: The request data to queue

        Returns:
            The result of processing the request

        Raises:
            RequestQueueFullError: If queue is full
            asyncio.TimeoutError: If request times out
        """
        if self.queue.full():
            logger.error(f"Request queue is full ({self.config.max_queue_size}). Rejecting request.")
            raise RequestQueueFullError(f"Request queue is full. Maximum size: {self.config.max_queue_size}")

        # Create a future for this request
        future = asyncio.Future()
        queue_item = {"data": request_data, "future": future}

        await self.queue.put(queue_item)
        self.total_queued += 1

        queue_size = self.queue.qsize()
        logger.info(f"Request queued. Queue size: {queue_size}/{self.config.max_queue_size}")

        try:
            # Wait for the request to be processed
            result = await asyncio.wait_for(future, timeout=self.config.request_timeout)
            self.total_processed += 1
            return result
        except asyncio.TimeoutError:
            self.total_timeouts += 1
            logger.error(f"Request timed out after {self.config.request_timeout}s in queue")
            raise

    async def dequeue(self) -> dict:
        """
        Get the next request from the queue.

        Returns:
            Dictionary with 'data' and 'future' keys
        """
        item = await self.queue.get()
        queue_size = self.queue.qsize()
        logger.debug(f"Request dequeued. Remaining queue size: {queue_size}")
        return item

    def complete_request(self, future: asyncio.Future, result: Any = None, exception: Exception | None = None):
        """
        Mark a request as completed.

        Args:
            future: The future associated with the request
            result: The result to set (if successful)
            exception: The exception to set (if failed)
        """
        if exception:
            future.set_exception(exception)
        else:
            future.set_result(result)

    def get_size(self) -> int:
        """Get current queue size."""
        return self.queue.qsize()

    def is_full(self) -> bool:
        """Check if queue is full."""
        return self.queue.full()

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self.queue.empty()

    async def get_metrics(self) -> dict:
        """Get queue metrics."""
        return {
            "current_size": self.queue.qsize(),
            "max_size": self.config.max_queue_size,
            "total_queued": self.total_queued,
            "total_processed": self.total_processed,
            "total_timeouts": self.total_timeouts,
            "active_requests": self.active_requests,
        }
