"""Redis client for managing task queues and job status."""

import json
from typing import Any, Optional

import redis.asyncio as redis

from src.config import config
from src.logger import make_logger

logger = make_logger(__name__)


class RedisClient:
    """Async Redis client wrapper for task queue management."""

    def __init__(self) -> None:
        """Initialize Redis client."""
        self.redis: Optional[redis.Redis] = None
        self.host = config.redis_host
        self.port = config.redis_port
        self.db = config.redis_db

    async def connect(self) -> None:
        """Connect to Redis."""
        if self.redis is None:
            self.redis = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True,
            )
            logger.info(f"Connected to Redis at {self.host}:{self.port}")

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis")

    async def enqueue_job(self, queue_name: str, job_data: dict[str, Any]) -> None:
        """
        Add a job to the queue.

        Args:
            queue_name: Name of the queue
            job_data: Job data to enqueue
        """
        if not self.redis:
            await self.connect()
        assert self.redis is not None

        job_json = json.dumps(job_data)
        await self.redis.rpush(queue_name, job_json)
        logger.info(f"Enqueued job to {queue_name}: {job_data.get('job_id', 'unknown')}")

    async def dequeue_job(self, queue_name: str, timeout: int = 0) -> Optional[dict[str, Any]]:
        """
        Remove and return a job from the queue.

        Args:
            queue_name: Name of the queue
            timeout: Block timeout in seconds (0 = wait forever)

        Returns:
            Job data or None if timeout
        """
        if not self.redis:
            await self.connect()
        assert self.redis is not None

        result = await self.redis.blpop(queue_name, timeout=timeout)
        if result:
            _, job_json = result
            job_data = json.loads(job_json)
            logger.info(f"Dequeued job from {queue_name}: {job_data.get('job_id', 'unknown')}")
            return job_data
        return None

    async def set_job_status(self, job_id: str, status_data: dict[str, Any], ttl: int = 86400) -> None:
        """
        Set job status in Redis.

        Args:
            job_id: Job ID
            status_data: Status data to store
            ttl: Time to live in seconds (default: 24 hours)
        """
        if not self.redis:
            await self.connect()
        assert self.redis is not None

        key = f"job:{job_id}:status"
        status_json = json.dumps(status_data)
        await self.redis.setex(key, ttl, status_json)
        logger.info(f"Set status for job {job_id}: {status_data.get('status', 'unknown')}")

    async def get_job_status(self, job_id: str) -> Optional[dict[str, Any]]:
        """
        Get job status from Redis.

        Args:
            job_id: Job ID

        Returns:
            Status data or None if not found
        """
        if not self.redis:
            await self.connect()
        assert self.redis is not None

        key = f"job:{job_id}:status"
        status_json = await self.redis.get(key)
        if status_json:
            return json.loads(status_json)
        return None

    async def set_job_result(self, job_id: str, result_data: dict[str, Any], ttl: int = 86400) -> None:
        """
        Set job result in Redis.

        Args:
            job_id: Job ID
            result_data: Result data to store
            ttl: Time to live in seconds (default: 24 hours)
        """
        if not self.redis:
            await self.connect()
        assert self.redis is not None

        key = f"job:{job_id}:result"
        result_json = json.dumps(result_data)
        await self.redis.setex(key, ttl, result_json)
        logger.info(f"Set result for job {job_id}")

    async def get_job_result(self, job_id: str) -> Optional[dict[str, Any]]:
        """
        Get job result from Redis.

        Args:
            job_id: Job ID

        Returns:
            Result data or None if not found
        """
        if not self.redis:
            await self.connect()
        assert self.redis is not None

        key = f"job:{job_id}:result"
        result_json = await self.redis.get(key)
        if result_json:
            return json.loads(result_json)
        return None

    async def get_queue_length(self, queue_name: str) -> int:
        """
        Get the length of a queue.

        Args:
            queue_name: Name of the queue

        Returns:
            Queue length
        """
        if not self.redis:
            await self.connect()
        assert self.redis is not None

        return await self.redis.llen(queue_name)


# Global Redis client instance
redis_client = RedisClient()
