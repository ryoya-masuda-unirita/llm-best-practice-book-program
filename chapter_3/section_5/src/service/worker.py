import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Optional

from src.client.llm_client import LLMProvider
from src.config import config
from src.logger import make_logger
from src.model.model import Priority, QueuedTask, TaskStatus
from src.prompt.prompt import make_prompt
from src.service.queue_manager import queue_manager
from src.service.request_llm import request_openai

logger = make_logger(__name__)


@dataclass
class WorkerStats:
    processed_count: int = 0
    failed_count: int = 0
    total_processing_time_ms: float = 0.0

    def record_success(self, processing_time_ms: float) -> None:
        self.processed_count += 1
        self.total_processing_time_ms += processing_time_ms

    def record_failure(self) -> None:
        self.failed_count += 1

    @property
    def average_processing_time_ms(self) -> float:
        if self.processed_count == 0:
            return 0.0
        return self.total_processing_time_ms / self.processed_count


@dataclass
class PriorityWeights:
    high: float = field(default_factory=lambda: config.high_priority_ratio)
    medium: float = field(default_factory=lambda: config.medium_priority_ratio)
    low: float = field(default_factory=lambda: config.low_priority_ratio)

    def as_list(self) -> list[float]:
        return [self.high, self.medium, self.low]

    def normalized(self) -> list[float]:
        total = self.high + self.medium + self.low
        return [w / total for w in self.as_list()]


class WeightedPriorityScheduler:
    PRIORITIES = [Priority.HIGH, Priority.MEDIUM, Priority.LOW]

    def __init__(self, weights: Optional[PriorityWeights] = None) -> None:
        self._weights = weights or PriorityWeights()

    def select_priority(self) -> Priority:
        return random.choices(self.PRIORITIES, weights=self._weights.normalized(), k=1)[0]

    def get_weights_display(self) -> str:
        return f"High: {self._weights.high:.0%}, Medium: {self._weights.medium:.0%}, Low: {self._weights.low:.0%}"


class TaskProcessor:
    def __init__(self, stats: WorkerStats) -> None:
        self._stats = stats

    async def process(self, task: QueuedTask) -> None:
        start_time = time.time()

        try:
            await self._execute_task(task, start_time)
        except Exception as e:
            await self._handle_failure(task, e)

    async def _execute_task(self, task: QueuedTask, start_time: float) -> None:
        task.status = TaskStatus.PROCESSING
        task.started_at = start_time
        await queue_manager.update_task(task)

        logger.info(
            f"Processing task {task.task_id} (priority: {task.priority.value}, provider: {task.provider}/{task.model})"
        )

        if task.provider != LLMProvider.OPENAI.value:
            raise ValueError(f"Unsupported provider: {task.provider}")

        prompt = make_prompt(character_request=task.character_request)
        character = await request_openai(model=task.model, prompt=prompt)

        processing_time_ms = (time.time() - start_time) * 1000

        task.result = {
            "character": character.model_dump(),
            "provider": task.provider,
            "model": task.model,
            "processing_time_ms": processing_time_ms,
        }
        task.status = TaskStatus.COMPLETED
        task.completed_at = time.time()

        await queue_manager.update_task(task)
        self._stats.record_success(processing_time_ms)

        logger.info(
            f"Completed task {task.task_id} in {processing_time_ms:.2f}ms (total: {self._stats.processed_count})"
        )

    async def _handle_failure(self, task: QueuedTask, error: Exception) -> None:
        task.retry_count += 1
        task.error_message = str(error)

        if task.retry_count >= config.max_retry_attempts:
            task.status = TaskStatus.FAILED
            task.completed_at = time.time()
            self._stats.record_failure()
            logger.error(
                f"Task {task.task_id} failed after {task.retry_count} attempts: {error} "
                f"(total failed: {self._stats.failed_count})"
            )
        else:
            task.status = TaskStatus.PENDING
            logger.warning(f"Task {task.task_id} failed (attempt {task.retry_count}), re-queuing: {error}")

        await queue_manager.update_task(task)

        if task.retry_count < config.max_retry_attempts:
            await queue_manager.enqueue_task(task)


class PriorityWorker:
    MAX_DEQUEUE_ATTEMPTS = 10
    BUSY_POLL_INTERVAL = 0.1
    IDLE_POLL_INTERVAL = 1.0

    def __init__(self) -> None:
        self._running = False
        self._stats = WorkerStats()
        self._scheduler = WeightedPriorityScheduler()
        self._processor = TaskProcessor(self._stats)

    @property
    def stats(self) -> WorkerStats:
        return self._stats

    @property
    def is_running(self) -> bool:
        return self._running

    async def run(self, poll_interval: Optional[float] = None) -> None:
        idle_interval = poll_interval or self.IDLE_POLL_INTERVAL
        self._running = True

        logger.info(f"Worker started with priority ratios - {self._scheduler.get_weights_display()}")

        try:
            await self._main_loop(idle_interval)
        except asyncio.CancelledError:
            logger.info("Worker received cancellation signal")
        finally:
            self._running = False
            logger.info(
                f"Worker stopped. Processed: {self._stats.processed_count}, "
                f"Failed: {self._stats.failed_count}, Avg time: {self._stats.average_processing_time_ms:.2f}ms"
            )

    async def _main_loop(self, idle_interval: float) -> None:
        while self._running:
            try:
                task_processed = await self._try_process_next_task()
                await asyncio.sleep(self.BUSY_POLL_INTERVAL if task_processed else idle_interval)
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(idle_interval)

    def stop(self) -> None:
        logger.info("Stopping worker...")
        self._running = False

    async def _try_process_next_task(self) -> bool:
        queue_sizes = await queue_manager.get_all_queue_sizes()

        if sum(queue_sizes.values()) == 0:
            return False

        for _ in range(self.MAX_DEQUEUE_ATTEMPTS):
            priority = self._scheduler.select_priority()

            if queue_sizes[priority.value] == 0:
                continue

            task = await queue_manager.dequeue_task(priority)
            if task:
                await self._processor.process(task)
                return True

        return False


async def main() -> None:
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
