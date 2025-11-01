"""Background worker for processing queued LLM requests with priority scheduling."""

import asyncio
import random
import time

from src.client.llm_client import LLMProvider
from src.config import config
from src.logger import make_logger
from src.model.model import Priority, QueuedTask, TaskStatus
from src.prompt.prompt import make_prompt
from src.service.queue_manager import queue_manager
from src.service.request_llm import request_gemini, request_openai

logger = make_logger(__name__)


class PriorityWorker:
    """Worker that processes tasks from priority queues with weighted scheduling."""

    def __init__(self):
        """Initialize the worker."""
        self.running = False
        self.processed_count = 0
        self.failed_count = 0

    def _get_next_priority(self) -> Priority:
        """
        Determine which priority queue to process next based on configured ratios.

        Uses weighted random selection based on priority ratios to ensure
        fair distribution while maintaining priority preferences.

        Returns:
            The priority level to process next
        """
        # Create weighted choices based on configured ratios
        priorities = [Priority.HIGH, Priority.MEDIUM, Priority.LOW]
        weights = [
            config.high_priority_ratio,
            config.medium_priority_ratio,
            config.low_priority_ratio,
        ]

        # Normalize weights to sum to 1.0
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        # Weighted random selection
        return random.choices(priorities, weights=normalized_weights, k=1)[0]

    async def _process_task(self, task: QueuedTask) -> None:
        """
        Process a single task by calling the LLM and storing the result.

        Args:
            task: The task to process
        """
        start_time = time.time()

        try:
            # Update task status to processing
            task.status = TaskStatus.PROCESSING
            task.started_at = start_time
            await queue_manager.update_task(task)

            logger.info(
                f"Processing task {task.task_id} "
                f"(priority: {task.priority.value}, provider: {task.provider}/{task.model})"
            )

            # Create prompt
            prompt = make_prompt(character_request=task.character_request)

            # Call LLM based on provider
            if task.provider == LLMProvider.OPENAI.value:
                character = await request_openai(model=task.model, prompt=prompt)
            elif task.provider == LLMProvider.GEMINI.value:
                character = await request_gemini(model=task.model, prompt=prompt)
            else:
                raise ValueError(f"Unsupported provider: {task.provider}")

            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000

            # Store result
            task.result = {
                "character": character.model_dump(),
                "provider": task.provider,
                "model": task.model,
                "processing_time_ms": processing_time,
            }
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()

            await queue_manager.update_task(task)

            self.processed_count += 1
            logger.info(
                f"Successfully processed task {task.task_id} in {processing_time:.2f}ms "
                f"(total processed: {self.processed_count})"
            )

        except Exception as e:
            # Handle failure
            task.retry_count += 1
            task.error_message = str(e)

            if task.retry_count >= config.max_retry_attempts:
                task.status = TaskStatus.FAILED
                task.completed_at = time.time()
                self.failed_count += 1
                logger.error(
                    f"Task {task.task_id} failed after {task.retry_count} attempts: {e} "
                    f"(total failed: {self.failed_count})"
                )
            else:
                # Re-queue for retry
                task.status = TaskStatus.PENDING
                logger.warning(f"Task {task.task_id} failed (attempt {task.retry_count}), re-queuing: {e}")

            await queue_manager.update_task(task)

            # Re-enqueue if not exceeding max retries
            if task.retry_count < config.max_retry_attempts:
                await queue_manager.enqueue_task(task)

    async def _process_next_task(self) -> bool:
        """
        Attempt to process the next task from priority queues.

        Returns:
            True if a task was processed, False if no tasks available
        """
        # Get queue sizes
        queue_sizes = await queue_manager.get_all_queue_sizes()
        total_tasks = sum(queue_sizes.values())

        if total_tasks == 0:
            return False

        # Try to get a task from queues in weighted priority order
        attempts = 0
        max_attempts = 10  # Prevent infinite loops

        while attempts < max_attempts:
            priority = self._get_next_priority()

            # Skip if this queue is empty
            if queue_sizes[priority.value] == 0:
                attempts += 1
                continue

            # Try to dequeue a task
            task = await queue_manager.dequeue_task(priority)

            if task:
                await self._process_task(task)
                return True

            attempts += 1

        return False

    async def run(self, poll_interval: float = 1.0) -> None:
        """
        Run the worker continuously, processing tasks from priority queues.

        Args:
            poll_interval: Time to wait between polling cycles (seconds)
        """
        self.running = True
        logger.info(
            f"Worker started with priority ratios - "
            f"High: {config.high_priority_ratio:.0%}, "
            f"Medium: {config.medium_priority_ratio:.0%}, "
            f"Low: {config.low_priority_ratio:.0%}"
        )

        try:
            while self.running:
                try:
                    # Try to process a task
                    task_processed = await self._process_next_task()

                    if not task_processed:
                        # No tasks available, wait before next poll
                        await asyncio.sleep(poll_interval)
                    else:
                        # Task was processed, check for more immediately
                        await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"Error in worker loop: {e}")
                    await asyncio.sleep(poll_interval)

        except asyncio.CancelledError:
            logger.info("Worker received cancellation signal")
        finally:
            self.running = False
            logger.info(f"Worker stopped. Total processed: {self.processed_count}, Failed: {self.failed_count}")

    def stop(self) -> None:
        """Signal the worker to stop."""
        logger.info("Stopping worker...")
        self.running = False


async def main():
    """Main entry point for running the worker."""
    worker = PriorityWorker()

    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        worker.stop()
    finally:
        await queue_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
