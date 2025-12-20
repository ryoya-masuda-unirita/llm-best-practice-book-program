"""Redis client for managing task queues and job status."""

import json
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

import redis.asyncio as redis
from src.config import config
from src.logger import make_logger

logger = make_logger(__name__)

T = TypeVar("T")

DEFAULT_TTL = 86400  # 24 hours


def ensure_connected(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to ensure Redis connection before executing method."""

    @wraps(func)
    async def wrapper(self: "RedisClient", *args: Any, **kwargs: Any) -> T:
        if not self.redis:
            await self.connect()
        return await func(self, *args, **kwargs)

    return wrapper


class RedisClient:
    """Async Redis client wrapper for task queue management."""

    def __init__(self) -> None:
        self.redis: Optional[redis.Redis] = None
        self.host = config.redis_host
        self.port = config.redis_port
        self.db = config.redis_db

    async def connect(self) -> None:
        if self.redis is None:
            self.redis = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True,
            )
            logger.info(f"Connected to Redis at {self.host}:{self.port}")

    async def disconnect(self) -> None:
        if self.redis:
            await self.redis.close()
            self.redis = None
            logger.info("Disconnected from Redis")

    @staticmethod
    def _status_key(job_id: str) -> str:
        return f"job:{job_id}:status"

    @staticmethod
    def _result_key(job_id: str) -> str:
        return f"job:{job_id}:result"

    @ensure_connected
    async def enqueue_job(self, queue_name: str, job_data: dict[str, Any]) -> None:
        job_json = json.dumps(job_data)
        await self.redis.rpush(queue_name, job_json)
        logger.info(f"Enqueued job to {queue_name}: {job_data.get('job_id', 'unknown')}")

    @ensure_connected
    async def dequeue_job(self, queue_name: str, timeout: int = 0) -> Optional[dict[str, Any]]:
        result = await self.redis.blpop(queue_name, timeout=timeout)
        if result:
            _, job_json = result
            job_data = json.loads(job_json)
            logger.info(f"Dequeued job from {queue_name}: {job_data.get('job_id', 'unknown')}")
            return job_data
        return None

    @ensure_connected
    async def set_job_status(self, job_id: str, status_data: dict[str, Any], ttl: int = DEFAULT_TTL) -> None:
        key = self._status_key(job_id)
        status_json = json.dumps(status_data)
        await self.redis.setex(key, ttl, status_json)
        logger.info(f"Set status for job {job_id}: {status_data.get('status', 'unknown')}")

    @ensure_connected
    async def get_job_status(self, job_id: str) -> Optional[dict[str, Any]]:
        key = self._status_key(job_id)
        status_json = await self.redis.get(key)
        if status_json:
            return json.loads(status_json)
        return None

    @ensure_connected
    async def set_job_result(self, job_id: str, result_data: dict[str, Any], ttl: int = DEFAULT_TTL) -> None:
        key = self._result_key(job_id)
        result_json = json.dumps(result_data)
        await self.redis.setex(key, ttl, result_json)
        logger.info(f"Set result for job {job_id}")

    @ensure_connected
    async def get_job_result(self, job_id: str) -> Optional[dict[str, Any]]:
        key = self._result_key(job_id)
        result_json = await self.redis.get(key)
        if result_json:
            return json.loads(result_json)
        return None

    @ensure_connected
    async def get_queue_length(self, queue_name: str) -> int:
        return await self.redis.llen(queue_name)

    @ensure_connected
    async def list_job_ids(self) -> list[str]:
        keys = await self.redis.keys("job:*:status")
        return [key.split(":")[1] for key in keys]


redis_client = RedisClient()
