"""Redis-based priority queue manager for LLM request processing."""

import time
from typing import Optional

import redis.asyncio as aioredis

from src.config import config
from src.logger import make_logger
from src.model.model import Priority, QueuedTask, TaskStatus, UserTier

logger = make_logger(__name__)


class PriorityQueueManager:
    """
    Manages priority queues using Redis for LLM request processing.

    Uses Redis Sorted Sets for priority queues (score = timestamp for FIFO),
    key-value for task storage, and a Set for tracking processing state.
    """

    QUEUE_PREFIX = "llm:queue"
    TASK_PREFIX = "llm:task"
    PROCESSING_SET = "llm:processing"
    TERMINAL_STATUSES = frozenset({TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT})
    USER_TIER_PRIORITY_MAP = {
        UserTier.ENTERPRISE: Priority.HIGH,
        UserTier.PREMIUM: Priority.MEDIUM,
        UserTier.FREE: Priority.LOW,
    }

    def __init__(self) -> None:
        self._redis: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        """Establish connection to Redis if not already connected."""
        if self._redis is not None:
            return

        self._redis = await aioredis.from_url(
            f"redis://{config.redis_host}:{config.redis_port}/{config.redis_db}",
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info(f"Connected to Redis at {config.redis_host}:{config.redis_port}")

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis is None:
            return

        await self._redis.close()
        self._redis = None
        logger.info("Disconnected from Redis")

    @property
    def is_connected(self) -> bool:
        return self._redis is not None

    async def _ensure_connected(self) -> aioredis.Redis:
        await self.connect()
        return self._redis

    def _get_queue_key(self, priority: Priority) -> str:
        return f"{self.QUEUE_PREFIX}:{priority.value}"

    def _get_task_key(self, task_id: str) -> str:
        return f"{self.TASK_PREFIX}:{task_id}"

    def get_priority_for_user_tier(self, user_tier: UserTier) -> Priority:
        return self.USER_TIER_PRIORITY_MAP.get(user_tier, Priority.LOW)

    async def get_task(self, task_id: str) -> Optional[QueuedTask]:
        """Retrieve a task by its ID."""
        redis = await self._ensure_connected()
        task_data = await redis.get(self._get_task_key(task_id))

        if not task_data:
            return None

        return QueuedTask.model_validate_json(task_data)

    async def update_task(self, task: QueuedTask) -> None:
        """Update task data. Removes from processing set if terminal status."""
        redis = await self._ensure_connected()

        await redis.set(self._get_task_key(task.task_id), task.model_dump_json())

        if task.status in self.TERMINAL_STATUSES:
            await redis.srem(self.PROCESSING_SET, task.task_id)

        logger.debug(f"Updated task {task.task_id} with status {task.status.value}")

    async def enqueue_task(self, task: QueuedTask) -> QueuedTask:
        """Add a task to the appropriate priority queue."""
        redis = await self._ensure_connected()

        if not task.priority:
            task.priority = self.get_priority_for_user_tier(task.user_tier)

        await redis.set(self._get_task_key(task.task_id), task.model_dump_json())
        await redis.zadd(self._get_queue_key(task.priority), {task.task_id: task.created_at})

        logger.info(f"Enqueued task {task.task_id} to {task.priority.value} priority queue")
        return task

    async def dequeue_task(self, priority: Priority) -> Optional[QueuedTask]:
        """Remove and return the oldest task from the specified priority queue."""
        redis = await self._ensure_connected()
        queue_key = self._get_queue_key(priority)

        task_ids = await redis.zrange(queue_key, 0, 0)
        if not task_ids:
            return None

        task_id = task_ids[0]
        await redis.zrem(queue_key, task_id)

        task_data = await redis.get(self._get_task_key(task_id))
        if not task_data:
            logger.warning(f"Task {task_id} found in queue but data missing")
            return None

        task = QueuedTask.model_validate_json(task_data)
        await redis.sadd(self.PROCESSING_SET, task_id)
        task.status = TaskStatus.PROCESSING

        logger.debug(f"Dequeued task {task_id} from {priority.value} priority queue")
        return task

    async def get_queue_position(self, task_id: str) -> Optional[int]:
        """Get the position of a task in its queue (0-indexed)."""
        redis = await self._ensure_connected()

        for priority in Priority:
            rank = await redis.zrank(self._get_queue_key(priority), task_id)
            if rank is not None:
                return rank

        return None

    async def get_queue_size(self, priority: Priority) -> int:
        redis = await self._ensure_connected()
        return await redis.zcard(self._get_queue_key(priority))

    async def get_all_queue_sizes(self) -> dict[str, int]:
        return {priority.value: await self.get_queue_size(priority) for priority in Priority}

    async def get_processing_count(self) -> int:
        redis = await self._ensure_connected()
        return await redis.scard(self.PROCESSING_SET)

    async def cleanup_old_tasks(self, max_age_seconds: int = 86400) -> int:
        """Remove completed/failed tasks older than max_age_seconds (default: 24h)."""
        redis = await self._ensure_connected()

        cutoff_time = time.time() - max_age_seconds
        cleaned = 0

        async for key in redis.scan_iter(match=f"{self.TASK_PREFIX}:*"):
            task_data = await redis.get(key)
            if not task_data:
                continue

            task = QueuedTask.model_validate_json(task_data)
            is_terminal = task.status in self.TERMINAL_STATUSES
            is_old = task.completed_at and task.completed_at < cutoff_time

            if is_terminal and is_old:
                await redis.delete(key)
                cleaned += 1

        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} old tasks")

        return cleaned


queue_manager = PriorityQueueManager()
