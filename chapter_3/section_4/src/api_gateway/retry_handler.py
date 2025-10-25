"""Retry handler with exponential backoff for LLM API Gateway.

This module provides robust error handling and retry logic for LLM API calls,
implementing exponential backoff to handle transient failures gracefully.
"""

import asyncio
import time
from typing import Any, Callable, Optional, TypeVar

from src.config import config
from src.logger import make_logger

logger = make_logger(__name__)

T = TypeVar("T")


class RetryHandler:
    """Handles retry logic with exponential backoff for API requests.

    This centralizes retry behavior so that all services using the gateway
    benefit from consistent, robust error handling without implementing it themselves.
    """

    def __init__(
        self,
        max_retries: Optional[int] = None,
        backoff_factor: Optional[float] = None,
        timeout: Optional[float] = None,
    ):
        """Initialize the retry handler.

        Args:
            max_retries: Maximum number of retry attempts (defaults to config value)
            backoff_factor: Exponential backoff factor (defaults to config value)
            timeout: Request timeout in seconds (defaults to config value)
        """
        self.max_retries = max_retries or config.gateway_max_retries
        self.backoff_factor = backoff_factor or config.gateway_retry_backoff
        self.timeout = timeout or config.gateway_timeout
        logger.info(
            f"RetryHandler initialized: max_retries={self.max_retries}, "
            f"backoff_factor={self.backoff_factor}, timeout={self.timeout}"
        )

    def _calculate_wait_time(self, attempt: int) -> float:
        """Calculate exponential backoff wait time.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Wait time in seconds
        """
        return self.backoff_factor**attempt

    async def execute_with_retry(
        self,
        func: Callable[..., Any],
        *args,
        **kwargs,
    ) -> Any:
        """Execute a function with retry logic and exponential backoff.

        Args:
            func: The async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            The result of the function call

        Raises:
            Exception: If all retry attempts are exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.time()
                logger.debug(f"Executing attempt {attempt + 1}/{self.max_retries + 1}")

                # Execute with timeout
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.timeout)

                elapsed_time = (time.time() - start_time) * 1000
                logger.info(f"Request succeeded on attempt {attempt + 1} (took {elapsed_time:.2f}ms)")
                return result

            except asyncio.TimeoutError as e:
                last_exception = e
                logger.warning(
                    f"Request timeout on attempt {attempt + 1}/{self.max_retries + 1} (timeout: {self.timeout}s)"
                )

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Request failed on attempt {attempt + 1}/{self.max_retries + 1}: {type(e).__name__}: {str(e)}"
                )

            # Don't sleep after the last attempt
            if attempt < self.max_retries:
                wait_time = self._calculate_wait_time(attempt)
                logger.info(f"Waiting {wait_time:.2f}s before retry...")
                await asyncio.sleep(wait_time)

        # All retries exhausted
        logger.error(
            f"All {self.max_retries + 1} attempts failed. "
            f"Last error: {type(last_exception).__name__}: {str(last_exception)}"
        )
        raise last_exception


# Global retry handler instance
retry_handler = RetryHandler()
