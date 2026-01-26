"""
Retry utilities with exponential backoff.

Provides generic retry logic that can be used across tools.
Extracted from fetch tool but made generic (not HTTP-specific).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts (0 = no retries)
        backoff_ms: Base backoff delay in milliseconds
        max_backoff_ms: Maximum backoff delay (caps exponential growth)
        exponential_base: Base for exponential backoff (default 2)
        jitter: Whether to add random jitter to backoff (not yet implemented)
    """

    max_retries: int = 3
    backoff_ms: int = 1000
    max_backoff_ms: int = 60000
    exponential_base: int = 2
    jitter: bool = False

    # Lists of error types/messages that are retryable
    retryable_exceptions: list[type[Exception]] = field(default_factory=list)
    retryable_messages: list[str] = field(default_factory=list)
    non_retryable_messages: list[str] = field(default_factory=list)


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted."""

    def __init__(
        self,
        message: str,
        last_error: Exception | None = None,
        attempts: int = 0,
    ):
        super().__init__(message)
        self.last_error = last_error
        self.attempts = attempts


def is_retryable_error(
    error: Exception,
    config: RetryConfig | None = None,
) -> bool:
    """
    Determine if an error should trigger a retry.

    Default behavior (when config is None):
    - Retryable: Connection errors, timeouts
    - Not retryable: ValueError, KeyError, other programming errors

    With config:
    - Checks retryable_exceptions list
    - Checks retryable_messages (substring match)
    - Checks non_retryable_messages (substring match, takes precedence)

    Args:
        error: The exception that occurred
        config: Optional retry configuration with error classification

    Returns:
        True if the error should be retried
    """
    error_msg = str(error).lower()

    if config:
        # Check non-retryable messages first (they take precedence)
        for msg in config.non_retryable_messages:
            if msg.lower() in error_msg:
                return False

        # Check retryable exception types
        for exc_type in config.retryable_exceptions:
            if isinstance(error, exc_type):
                return True

        # Check retryable messages
        for msg in config.retryable_messages:
            if msg.lower() in error_msg:
                return True

    # Default behavior: don't retry programming errors
    if isinstance(error, (ValueError, KeyError, TypeError, AttributeError)):
        # But check for specific retryable content errors
        if "content_too_large" in error_msg or "invalid_content_type" in error_msg:
            return False
        return False

    # Connection-related errors are generally retryable
    connection_keywords = ["connection", "timeout", "refused", "reset", "network"]
    for keyword in connection_keywords:
        if keyword in error_msg:
            return True

    # Default: don't retry unknown errors
    return False


def calculate_backoff_ms(
    attempt: int,
    config: RetryConfig,
) -> int:
    """
    Calculate backoff delay for a given attempt.

    Uses exponential backoff: delay = backoff_ms * base^attempt

    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration

    Returns:
        Backoff delay in milliseconds
    """
    delay = config.backoff_ms * (config.exponential_base**attempt)
    return min(delay, config.max_backoff_ms)


async def retry_with_backoff(
    fn: Callable[..., Awaitable[T]],
    config: RetryConfig,
    *args: Any,
    **kwargs: Any,
) -> T:
    """
    Execute an async function with exponential backoff retry.

    Args:
        fn: Async function to execute
        config: Retry configuration
        *args: Positional arguments for fn
        **kwargs: Keyword arguments for fn

    Returns:
        Result from successful function call

    Raises:
        RetryExhaustedError: If all retries are exhausted
        Exception: The last error if it's not retryable
    """
    last_error: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            return await fn(*args, **kwargs)

        except Exception as e:
            last_error = e

            # Check if we should retry
            if attempt < config.max_retries and is_retryable_error(e, config):
                delay_ms = calculate_backoff_ms(attempt, config)
                logger.debug(
                    f"Retry {attempt + 1}/{config.max_retries} after {delay_ms}ms: {e}"
                )
                await asyncio.sleep(delay_ms / 1000)
            else:
                # No more retries or non-retryable error
                raise

    # Should not reach here, but handle edge case
    if last_error:
        raise RetryExhaustedError(
            f"All {config.max_retries + 1} attempts failed",
            last_error=last_error,
            attempts=config.max_retries + 1,
        )
    raise RuntimeError("Unexpected state in retry_with_backoff")


def retry_sync(
    fn: Callable[..., T],
    config: RetryConfig,
    *args: Any,
    **kwargs: Any,
) -> T:
    """
    Execute a sync function with exponential backoff retry.

    Args:
        fn: Sync function to execute
        config: Retry configuration
        *args: Positional arguments for fn
        **kwargs: Keyword arguments for fn

    Returns:
        Result from successful function call

    Raises:
        RetryExhaustedError: If all retries are exhausted
        Exception: The last error if it's not retryable
    """
    import time

    last_error: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            return fn(*args, **kwargs)

        except Exception as e:
            last_error = e

            # Check if we should retry
            if attempt < config.max_retries and is_retryable_error(e, config):
                delay_ms = calculate_backoff_ms(attempt, config)
                logger.debug(
                    f"Retry {attempt + 1}/{config.max_retries} after {delay_ms}ms: {e}"
                )
                time.sleep(delay_ms / 1000)
            else:
                # No more retries or non-retryable error
                raise

    # Should not reach here, but handle edge case
    if last_error:
        raise RetryExhaustedError(
            f"All {config.max_retries + 1} attempts failed",
            last_error=last_error,
            attempts=config.max_retries + 1,
        )
    raise RuntimeError("Unexpected state in retry_sync")
