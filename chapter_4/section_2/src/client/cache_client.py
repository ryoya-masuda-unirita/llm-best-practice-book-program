"""Cache clients for LLM responses.

This module provides caching functionality for the storage layer,
supporting both in-memory and Redis-based caching strategies.
"""

import json
import time

import redis.asyncio as redis
from src.config import config
from src.logger import make_logger

logger = make_logger(__name__)


class InMemoryCache:
    """Simple in-memory cache implementation with TTL support."""

    def __init__(self):
        self._cache: dict[str, tuple[dict, float]] = {}

    async def get(self, key: str) -> dict | None:
        if key not in self._cache:
            return None

        value, expire_at = self._cache[key]
        if expire_at > 0 and time.time() >= expire_at:
            del self._cache[key]
            return None

        return value

    async def set(self, key: str, value: dict, ttl: int | None = None) -> bool:
        ttl = ttl or config.cache_ttl
        expire_at = time.time() + ttl if ttl > 0 else 0
        self._cache[key] = (value, expire_at)
        return True

    async def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        return await self.get(key) is not None


class RedisClient:
    """Async Redis client for caching operations."""

    def __init__(self):
        self._client: redis.Redis | None = None
        self._connected = False

    async def connect(self) -> None:
        if self._connected:
            return

        password = config.redis_password.get_secret_value() if config.redis_password else None
        self._client = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            password=password,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
        )
        await self._client.ping()
        self._connected = True
        logger.info(f"Connected to Redis: {config.redis_host}:{config.redis_port}")

    async def disconnect(self) -> None:
        if self._client and self._connected:
            await self._client.aclose()
            self._connected = False
            logger.info("Disconnected from Redis")

    async def _ensure_connected(self) -> None:
        if not self._connected:
            await self.connect()

    async def get(self, key: str) -> dict | None:
        await self._ensure_connected()
        try:
            value = await self._client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Error getting cache for key {key}: {e}")
            return None

    async def set(self, key: str, value: dict, ttl: int | None = None) -> bool:
        await self._ensure_connected()
        try:
            ttl = ttl or config.cache_ttl
            json_value = json.dumps(value, ensure_ascii=False)

            if ttl > 0:
                await self._client.setex(key, ttl, json_value)
            else:
                await self._client.set(key, json_value)
            return True
        except Exception as e:
            logger.error(f"Error setting cache for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        await self._ensure_connected()
        try:
            result = await self._client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting cache for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        await self._ensure_connected()
        try:
            result = await self._client.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error checking existence for key {key}: {e}")
            return False


redis_client = RedisClient()
