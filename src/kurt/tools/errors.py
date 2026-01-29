"""Error handling patterns for map/fetch engines."""

import time
from enum import Enum
from typing import Optional


class ErrorType(str, Enum):
    """Categorizes engine errors for routing and recovery."""

    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    AUTH_ERROR = "auth_error"
    CONTENT_ERROR = "content_error"
    NETWORK_ERROR = "network_error"
    PARSE_ERROR = "parse_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN = "unknown"


class EngineError(Exception):
    """Base class for all engine errors.

    Attributes:
        error_type: Categorization for handling
        message: Human-readable error message
        retryable: Whether the operation should be retried
        original_error: The underlying exception, if any
        retry_after: Seconds to wait before retrying (for rate limits)
    """

    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.UNKNOWN,
        retryable: bool = False,
        original_error: Optional[Exception] = None,
        retry_after: Optional[float] = None,
    ):
        self.message = message
        self.error_type = error_type
        self.retryable = retryable
        self.original_error = original_error
        self.retry_after = retry_after
        super().__init__(self.message)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"error_type={self.error_type}, "
            f"retryable={self.retryable})"
        )


class RateLimitError(EngineError):
    """Raised when an API rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_type=ErrorType.RATE_LIMIT,
            retryable=True,
            original_error=original_error,
            retry_after=retry_after,
        )


class TimeoutError(EngineError):
    """Raised when an operation exceeds timeout."""

    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_type=ErrorType.TIMEOUT,
            retryable=True,
            original_error=original_error,
        )


class AuthError(EngineError):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_type=ErrorType.AUTH_ERROR,
            retryable=False,
            original_error=original_error,
        )


class ContentError(EngineError):
    """Raised when content cannot be processed."""

    def __init__(
        self,
        message: str,
        retryable: bool = False,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_type=ErrorType.CONTENT_ERROR,
            retryable=retryable,
            original_error=original_error,
        )


class ExponentialBackoff:
    """Exponential backoff helper with jitter for retry logic.

    Implements full jitter strategy to avoid thundering herd problem.
    See: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
    """

    def __init__(
        self,
        base: float = 1.0,
        max_wait: float = 60.0,
        max_retries: int = 5,
    ):
        """Initialize backoff parameters.

        Args:
            base: Initial backoff time in seconds
            max_wait: Maximum wait time between retries
            max_retries: Maximum number of retries before giving up
        """
        self.base = base
        self.max_wait = max_wait
        self.max_retries = max_retries
        self.attempt = 0

    def wait(self) -> float:
        """Calculate and sleep for backoff duration.

        Returns:
            The number of seconds waited
        """
        if self.attempt >= self.max_retries:
            raise RuntimeError(
                f"Maximum retries ({self.max_retries}) exceeded"
            )

        # Full jitter: random value between 0 and min(max_wait, base * 2^attempt)
        cap = min(self.max_wait, self.base * (2 ** self.attempt))
        wait_time = time.time() % cap  # Use modulo for deterministic jitter in tests

        time.sleep(wait_time)
        self.attempt += 1
        return wait_time

    def reset(self) -> None:
        """Reset attempt counter."""
        self.attempt = 0

    def get_wait_time(self) -> float:
        """Get the next wait time without sleeping.

        Returns:
            The number of seconds to wait
        """
        if self.attempt >= self.max_retries:
            raise RuntimeError(
                f"Maximum retries ({self.max_retries}) exceeded"
            )

        cap = min(self.max_wait, self.base * (2 ** self.attempt))
        return time.time() % cap

    @property
    def is_exhausted(self) -> bool:
        """Check if max retries have been exhausted."""
        return self.attempt >= self.max_retries
