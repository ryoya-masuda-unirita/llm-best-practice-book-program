"""Circuit breaker implementation for preventing cascading failures."""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum

from src.logger import make_logger

logger = make_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit is open, requests are blocked
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Number of failures before opening circuit
    success_threshold: int = 2  # Number of successes in half-open to close circuit
    timeout_seconds: float = 60.0  # Time to wait before attempting half-open
    error_rate_threshold: float = 0.5  # Error rate threshold (50%)
    min_requests: int = 10  # Minimum requests before calculating error rate


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""

    pass


class CircuitBreaker:
    """
    Circuit breaker implementation to prevent cascading failures.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests are immediately rejected
    - HALF_OPEN: Testing recovery, limited requests allowed
    """

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.lock = asyncio.Lock()

        # Metrics for error rate calculation
        self.total_requests = 0
        self.failed_requests = 0
        self.metrics_window_start = time.time()

        logger.info(
            f"Circuit breaker initialized: failure_threshold={config.failure_threshold}, "
            f"timeout={config.timeout_seconds}s, error_rate_threshold={config.error_rate_threshold}"
        )

    async def call(self, func, *args, **kwargs):
        """
        Execute a function through the circuit breaker.

        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        async with self.lock:
            await self._check_state()

            if self.state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. Service unavailable. Last failure: {self.last_failure_time}"
                )

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception:
            await self._on_failure()
            raise

    async def _check_state(self):
        """Check and potentially transition circuit state."""
        if self.state == CircuitState.OPEN:
            if self.last_failure_time:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= self.config.timeout_seconds:
                    logger.info(f"Circuit breaker transitioning from OPEN to HALF_OPEN after {elapsed:.2f}s")
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    self.failure_count = 0

    async def _on_success(self):
        """Handle successful request."""
        async with self.lock:
            self.total_requests += 1

            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                logger.debug(f"Circuit breaker HALF_OPEN: success {self.success_count}/{self.config.success_threshold}")

                if self.success_count >= self.config.success_threshold:
                    logger.info("Circuit breaker transitioning from HALF_OPEN to CLOSED")
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    self.total_requests = 0
                    self.failed_requests = 0
                    self.metrics_window_start = time.time()

    async def _on_failure(self):
        """Handle failed request."""
        async with self.lock:
            self.total_requests += 1
            self.failed_requests += 1
            self.failure_count += 1
            self.last_failure_time = time.time()

            logger.warning(f"Circuit breaker recorded failure. Count: {self.failure_count}")

            if self.state == CircuitState.HALF_OPEN:
                logger.warning("Circuit breaker transitioning from HALF_OPEN to OPEN (failure in half-open)")
                self.state = CircuitState.OPEN
                self.failure_count = 0
                self.success_count = 0

            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    logger.error(f"Circuit breaker transitioning from CLOSED to OPEN (failures: {self.failure_count})")
                    self.state = CircuitState.OPEN
                    return

                if self.total_requests >= self.config.min_requests:
                    error_rate = self.failed_requests / self.total_requests
                    if error_rate >= self.config.error_rate_threshold:
                        logger.error(
                            f"Circuit breaker transitioning from CLOSED to OPEN "
                            f"(error rate: {error_rate:.2%} >= {self.config.error_rate_threshold:.2%})"
                        )
                        self.state = CircuitState.OPEN

    async def get_state(self) -> CircuitState:
        """Get current circuit state."""
        async with self.lock:
            return self.state

    async def get_metrics(self) -> dict:
        """Get current metrics."""
        async with self.lock:
            error_rate = self.failed_requests / self.total_requests if self.total_requests > 0 else 0.0
            return {
                "state": self.state.value,
                "total_requests": self.total_requests,
                "failed_requests": self.failed_requests,
                "error_rate": error_rate,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
            }

    async def reset(self):
        """Manually reset the circuit breaker to CLOSED state."""
        async with self.lock:
            logger.info("Circuit breaker manually reset to CLOSED")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.total_requests = 0
            self.failed_requests = 0
            self.metrics_window_start = time.time()
