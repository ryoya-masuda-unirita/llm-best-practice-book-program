"""Strategy Pattern: Makes node execution methods dynamically interchangeable."""

from typing import Any

from src.logger import make_logger
from src.workflow.base import ExecutionContext, NodeExecutionStrategy

logger = make_logger(__name__)


class DefaultExecutionStrategy(NodeExecutionStrategy):
    """Default execution strategy with no retries."""

    async def execute(self, context: ExecutionContext) -> Any:
        """Execute without retries."""
        # This is overridden by specific node implementations
        pass


class RetryExecutionStrategy(NodeExecutionStrategy):
    """Execution strategy with retry logic."""

    def __init__(self, max_retries: int = 3, backoff_multiplier: float = 2.0):
        """
        Initialize retry strategy.

        Args:
            max_retries: Maximum number of retries
            backoff_multiplier: Exponential backoff multiplier
        """
        self.max_retries = max_retries
        self.backoff_multiplier = backoff_multiplier

    async def execute(self, context: ExecutionContext) -> Any:
        """Execute with retry logic."""
        import asyncio

        retries = 0
        last_error = None

        while retries <= self.max_retries:
            try:
                # The actual execution is delegated to the node
                # This is a placeholder for the pattern
                return None
            except Exception as e:
                last_error = e
                retries += 1
                if retries <= self.max_retries:
                    wait_time = self.backoff_multiplier**retries
                    logger.warning(f"Retry {retries}/{self.max_retries} after {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Max retries reached: {e}")
                    raise

        if last_error:
            raise last_error


class ParallelExecutionStrategy(NodeExecutionStrategy):
    """Execution strategy for parallel execution of multiple operations."""

    async def execute(self, context: ExecutionContext) -> Any:
        """Execute operations in parallel."""
        # Placeholder for parallel execution logic
        pass


class CachedExecutionStrategy(NodeExecutionStrategy):
    """Execution strategy that caches results."""

    def __init__(self, cache_ttl: int = 3600):
        """
        Initialize cached execution strategy.

        Args:
            cache_ttl: Cache time-to-live in seconds
        """
        self.cache_ttl = cache_ttl
        self._cache: dict[str, Any] = {}

    async def execute(self, context: ExecutionContext) -> Any:
        """Execute with caching."""
        # Placeholder for caching logic
        pass
