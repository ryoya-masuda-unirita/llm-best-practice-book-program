"""Redis client for caching LLM responses.

This module provides Redis-based caching functionality for the storage layer.
"""

import json
import time
from typing import Optional

import redis.asyncio as redis

from src.config import config
from src.logger import make_logger

logger = make_logger(__name__)


class InMemoryCache:
    """
    Simple in-memory cache implementation with TTL support.

    This is used for development/testing or when Redis is not available.
    """

    def __init__(self):
        self._cache: dict[str, tuple[dict, float]] = {}

    async def get(self, key: str) -> Optional[dict]:
        """Get cached value if not expired."""
        if key in self._cache:
            value, expire_at = self._cache[key]
            if expire_at == 0 or time.time() < expire_at:
                logger.debug(f"In-memory cache hit for key: {key}")
                return value
            else:
                # Expired, remove it
                del self._cache[key]
                logger.debug(f"In-memory cache expired for key: {key}")
        logger.debug(f"In-memory cache miss for key: {key}")
        return None

    async def set(self, key: str, value: dict, ttl: Optional[int] = None) -> bool:
        """Set cached value with optional TTL."""
        ttl = ttl or config.cache_ttl
        expire_at = time.time() + ttl if ttl > 0 else 0
        self._cache[key] = (value, expire_at)
        logger.debug(f"In-memory cache set for key: {key} (TTL: {ttl}s)")
        return True

    async def delete(self, key: str) -> bool:
        """Delete cached value."""
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"In-memory cache invalidated for key: {key}")
            return True
        return False

    async def exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        value = await self.get(key)
        return value is not None


class RedisClient:
    """
    Async Redis client for caching operations.

    This class manages Redis connections and provides methods for
    storing and retrieving cached LLM responses.
    """

    def __init__(self):
        """Initialize Redis client with configuration."""
        self._client: Optional[redis.Redis] = None
        self._connected = False

    async def connect(self):
        """Establish connection to Redis server."""
        if self._connected:
            return

        try:
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

            # Test connection
            await self._client.ping()
            self._connected = True
            logger.info(f"Connected to Redis: {config.redis_host}:{config.redis_port}")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Close Redis connection."""
        if self._client and self._connected:
            await self._client.aclose()
            self._connected = False
            logger.info("Disconnected from Redis")

    async def get(self, key: str) -> Optional[dict]:
        """
        Get cached value from Redis.

        Args:
            key: Cache key

        Returns:
            Optional[dict]: Cached data if exists, None otherwise
        """
        if not self._connected:
            await self.connect()

        try:
            value = await self._client.get(key)
            if value:
                logger.debug(f"Cache hit for key: {key}")
                return json.loads(value)
            else:
                logger.debug(f"Cache miss for key: {key}")
                return None
        except Exception as e:
            logger.error(f"Error getting cache for key {key}: {e}")
            return None

    async def set(self, key: str, value: dict, ttl: Optional[int] = None) -> bool:
        """
        Set cache value in Redis with optional TTL.

        Args:
            key: Cache key
            value: Data to cache (will be JSON serialized)
            ttl: Time to live in seconds (uses config default if not specified)

        Returns:
            bool: True if successful, False otherwise
        """
        if not self._connected:
            await self.connect()

        try:
            ttl = ttl or config.cache_ttl
            json_value = json.dumps(value, ensure_ascii=False)

            if ttl > 0:
                await self._client.setex(key, ttl, json_value)
            else:
                await self._client.set(key, json_value)

            logger.debug(f"Cache set for key: {key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Error setting cache for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete cached value from Redis.

        Args:
            key: Cache key

        Returns:
            bool: True if key was deleted, False otherwise
        """
        if not self._connected:
            await self.connect()

        try:
            result = await self._client.delete(key)
            if result > 0:
                logger.debug(f"Cache invalidated for key: {key}")
                return True
            else:
                logger.debug(f"Cache key not found: {key}")
                return False
        except Exception as e:
            logger.error(f"Error deleting cache for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in Redis.

        Args:
            key: Cache key

        Returns:
            bool: True if key exists, False otherwise
        """
        if not self._connected:
            await self.connect()

        try:
            result = await self._client.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error checking existence for key {key}: {e}")
            return False


# Global Redis client instance
redis_client = RedisClient()
