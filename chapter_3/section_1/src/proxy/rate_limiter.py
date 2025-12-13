"""Rate limiter implementation using token bucket algorithm."""

import asyncio
import time
from dataclasses import dataclass

from src.logger import make_logger

logger = make_logger(__name__)


@dataclass
class RateLimiterConfig:
    """Configuration for rate limiter."""

    max_requests: int = 10  # Maximum number of requests per window
    window_seconds: float = 1.0  # Time window in seconds


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter implementation.

    This implements a token bucket algorithm where tokens are replenished at a constant rate.
    Each request consumes one token. If no tokens are available, the request must wait.
    """

    def __init__(self, config: RateLimiterConfig):
        self.config = config
        self.tokens = float(config.max_requests)
        self.last_update = time.time()
        self.lock = asyncio.Lock()

        # Calculate the rate at which tokens are replenished
        self.refill_rate = config.max_requests / config.window_seconds

        logger.info(
            f"Rate limiter initialized: {config.max_requests} requests per {config.window_seconds}s "
            f"(refill rate: {self.refill_rate:.2f} tokens/s)"
        )

    async def acquire(self, timeout: float | None = None) -> bool:
        """
        Acquire a token for making a request.

        Args:
            timeout: Maximum time to wait for a token (None = wait indefinitely)

        Returns:
            True if token acquired, False if timeout occurred
        """
        start_time = time.time()

        async with self.lock:
            while True:
                now = time.time()
                elapsed = now - self.last_update
                self.tokens = min(self.config.max_requests, self.tokens + elapsed * self.refill_rate)
                self.last_update = now

                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    logger.debug(f"Token acquired. Remaining tokens: {self.tokens:.2f}")
                    return True

                if timeout is not None:
                    elapsed_wait = time.time() - start_time
                    if elapsed_wait >= timeout:
                        logger.warning(f"Rate limiter timeout after {elapsed_wait:.2f}s")
                        return False

                tokens_needed = 1.0 - self.tokens
                wait_time = tokens_needed / self.refill_rate
                wait_time = min(wait_time, 0.1)

                logger.debug(f"Waiting {wait_time:.3f}s for token. Current tokens: {self.tokens:.2f}")

                self.lock.release()
                try:
                    await asyncio.sleep(wait_time)
                finally:
                    await self.lock.acquire()

    async def get_available_tokens(self) -> float:
        """Get the current number of available tokens."""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            return min(self.config.max_requests, self.tokens + elapsed * self.refill_rate)
