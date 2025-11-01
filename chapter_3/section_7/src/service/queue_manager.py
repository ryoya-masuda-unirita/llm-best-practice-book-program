"""Redis-based priority queue manager for LLM request processing."""

from typing import Optional

import redis.asyncio as aioredis

from src.config import config
from src.logger import make_logger
from src.model.model import Priority, QueuedTask, TaskStatus, UserTier

logger = make_logger(__name__)


class PriorityQueueManager:
    """Manages priority queues using Redis for LLM request processing."""

    # Redis key prefixes
    QUEUE_PREFIX = "llm:queue"
    TASK_PREFIX = "llm:task"
    PROCESSING_SET = "llm:processing"

    def __init__(self):
        """Initialize the queue manager with Redis connection."""
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        """Establish connection to Redis."""
        if self.redis is None:
            self.redis = await aioredis.from_url(
                f"redis://{config.redis_host}:{config.redis_port}/{config.redis_db}",
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info(f"Connected to Redis at {config.redis_host}:{config.redis_port}")

    async def disconnect(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            self.redis = None
            logger.info("Disconnected from Redis")

    def _get_queue_key(self, priority: Priority) -> str:
        """Get the Redis key for a specific priority queue."""
        return f"{self.QUEUE_PREFIX}:{priority.value}"

    def _get_task_key(self, task_id: str) -> str:
        """Get the Redis key for a specific task."""
        return f"{self.TASK_PREFIX}:{task_id}"

    def _priority_from_user_tier(self, user_tier: UserTier) -> Priority:
        """Map user tier to priority level."""
        mapping = {
            UserTier.ENTERPRISE: Priority.HIGH,
            UserTier.PREMIUM: Priority.MEDIUM,
            UserTier.FREE: Priority.LOW,
        }
        return mapping.get(user_tier, Priority.LOW)

    async def enqueue_task(self, task: QueuedTask) -> QueuedTask:
        """
        Add a task to the appropriate priority queue.

        Args:
            task: The task to enqueue

        Returns:
            The enqueued task with updated metadata
        """
        await self.connect()

        # Determine priority from user tier if not explicitly set
        if not task.priority:
            task.priority = self._priority_from_user_tier(task.user_tier)

        # Store task data in Redis
        task_key = self._get_task_key(task.task_id)
        task_data = task.model_dump_json()
        await self.redis.set(task_key, task_data)

        # Add task ID to the appropriate priority queue (using sorted set with timestamp as score)
        queue_key = self._get_queue_key(task.priority)
        await self.redis.zadd(queue_key, {task.task_id: task.created_at})

        logger.info(f"Enqueued task {task.task_id} to {task.priority.value} priority queue")
        return task

    async def dequeue_task(self, priority: Priority) -> Optional[QueuedTask]:
        """
        Remove and return the oldest task from the specified priority queue.

        Args:
            priority: The priority queue to dequeue from

        Returns:
            The dequeued task or None if queue is empty
        """
        await self.connect()

        queue_key = self._get_queue_key(priority)

        # Get the oldest task (lowest score/timestamp)
        tasks = await self.redis.zrange(queue_key, 0, 0)
        if not tasks:
            return None

        task_id = tasks[0]

        # Remove from queue
        await self.redis.zrem(queue_key, task_id)

        # Get task data
        task_key = self._get_task_key(task_id)
        task_data = await self.redis.get(task_key)

        if not task_data:
            logger.warning(f"Task {task_id} found in queue but data missing")
            return None

        task = QueuedTask.model_validate_json(task_data)

        # Mark as processing
        await self.redis.sadd(self.PROCESSING_SET, task_id)
        task.status = TaskStatus.PROCESSING

        logger.info(f"Dequeued task {task_id} from {priority.value} priority queue")
        return task

    async def get_task(self, task_id: str) -> Optional[QueuedTask]:
        """
        Retrieve a task by its ID.

        Args:
            task_id: The task identifier

        Returns:
            The task or None if not found
        """
        await self.connect()

        task_key = self._get_task_key(task_id)
        task_data = await self.redis.get(task_key)

        if not task_data:
            return None

        return QueuedTask.model_validate_json(task_data)

    async def update_task(self, task: QueuedTask) -> None:
        """
        Update a task's data in Redis.

        Args:
            task: The task with updated data
        """
        await self.connect()

        task_key = self._get_task_key(task.task_id)
        task_data = task.model_dump_json()
        await self.redis.set(task_key, task_data)

        # If task is completed or failed, remove from processing set
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT]:
            await self.redis.srem(self.PROCESSING_SET, task.task_id)

        logger.info(f"Updated task {task.task_id} with status {task.status.value}")

    async def get_queue_size(self, priority: Priority) -> int:
        """
        Get the number of tasks in a specific priority queue.

        Args:
            priority: The priority queue to check

        Returns:
            Number of tasks in the queue
        """
        await self.connect()

        queue_key = self._get_queue_key(priority)
        return await self.redis.zcard(queue_key)

    async def get_all_queue_sizes(self) -> dict[str, int]:
        """
        Get the sizes of all priority queues.

        Returns:
            Dictionary mapping priority levels to queue sizes
        """
        sizes = {}
        for priority in Priority:
            sizes[priority.value] = await self.get_queue_size(priority)
        return sizes

    async def get_processing_count(self) -> int:
        """
        Get the number of tasks currently being processed.

        Returns:
            Number of tasks in processing state
        """
        await self.connect()

        return await self.redis.scard(self.PROCESSING_SET)

    async def get_queue_position(self, task_id: str) -> Optional[int]:
        """
        Get the position of a task in its queue.

        Args:
            task_id: The task identifier

        Returns:
            Position in queue (0-indexed) or None if not in queue
        """
        await self.connect()

        # Check all priority queues
        for priority in Priority:
            queue_key = self._get_queue_key(priority)
            rank = await self.redis.zrank(queue_key, task_id)
            if rank is not None:
                return rank

        return None

    async def cleanup_old_tasks(self, max_age_seconds: int = 86400) -> int:
        """
        Remove completed/failed tasks older than specified age.

        Args:
            max_age_seconds: Maximum age of tasks to keep (default 24 hours)

        Returns:
            Number of tasks cleaned up
        """
        await self.connect()

        import time

        current_time = time.time()
        cutoff_time = current_time - max_age_seconds

        # Scan for old task keys
        cleaned = 0
        async for key in self.redis.scan_iter(match=f"{self.TASK_PREFIX}:*"):
            task_data = await self.redis.get(key)
            if task_data:
                task = QueuedTask.model_validate_json(task_data)
                if (
                    task.completed_at
                    and task.completed_at < cutoff_time
                    and task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT]
                ):
                    await self.redis.delete(key)
                    cleaned += 1

        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} old tasks")

        return cleaned


# Global queue manager instance
queue_manager = PriorityQueueManager()
