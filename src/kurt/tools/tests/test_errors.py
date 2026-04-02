"""Tests for error handling patterns."""

import time

import pytest

from kurt.tools.errors import (
    AuthError,
    ContentError,
    EngineError,
    ErrorType,
    ExponentialBackoff,
    RateLimitError,
    TimeoutError,
)


class TestEngineError:
    """Test EngineError base class."""

    def test_base_error_creation(self):
        """Test creating a base EngineError."""
        error = EngineError(
            message="Test error",
            error_type=ErrorType.UNKNOWN,
            retryable=False,
        )
        assert error.message == "Test error"
        assert error.error_type == ErrorType.UNKNOWN
        assert error.retryable is False
        assert error.original_error is None
        assert error.retry_after is None

    def test_error_with_original_error(self):
        """Test wrapping an original exception."""
        original = ValueError("Original error")
        error = EngineError(
            message="Wrapped error",
            original_error=original,
        )
        assert error.original_error is original
        assert isinstance(error.original_error, ValueError)

    def test_error_repr(self):
        """Test string representation of error."""
        error = EngineError(
            message="Test",
            error_type=ErrorType.NETWORK_ERROR,
            retryable=True,
        )
        repr_str = repr(error)
        assert "EngineError" in repr_str
        assert "Test" in repr_str
        assert "network_error" in repr_str


class TestRateLimitError:
    """Test RateLimitError."""

    def test_rate_limit_error_is_retryable(self):
        """Test that rate limit errors are retryable."""
        error = RateLimitError("Rate limited")
        assert error.retryable is True
        assert error.error_type == ErrorType.RATE_LIMIT

    def test_rate_limit_error_with_retry_after(self):
        """Test rate limit error with retry_after hint."""
        error = RateLimitError("Rate limited", retry_after=30.0)
        assert error.retry_after == 30.0

    def test_rate_limit_error_inherits_from_engine_error(self):
        """Test that RateLimitError is an EngineError."""
        error = RateLimitError("Rate limited")
        assert isinstance(error, EngineError)
        assert isinstance(error, Exception)


class TestTimeoutError:
    """Test TimeoutError."""

    def test_timeout_error_is_retryable(self):
        """Test that timeout errors are retryable."""
        error = TimeoutError("Operation timed out")
        assert error.retryable is True
        assert error.error_type == ErrorType.TIMEOUT

    def test_timeout_error_not_retryable_after_max_retries(self):
        """Test that timeouts can be retried."""
        error = TimeoutError("Operation timed out")
        assert error.retryable is True


class TestAuthError:
    """Test AuthError."""

    def test_auth_error_not_retryable(self):
        """Test that auth errors are not retryable."""
        error = AuthError("Invalid API key")
        assert error.retryable is False
        assert error.error_type == ErrorType.AUTH_ERROR

    def test_auth_error_with_context(self):
        """Test auth error provides helpful context."""
        original = Exception("401 Unauthorized")
        error = AuthError(
            "Invalid API key provided",
            original_error=original,
        )
        assert error.message == "Invalid API key provided"
        assert error.original_error is original


class TestContentError:
    """Test ContentError."""

    def test_content_error_creation(self):
        """Test creating content error."""
        error = ContentError(
            "Invalid content format",
            retryable=True,
        )
        assert error.error_type == ErrorType.CONTENT_ERROR
        assert error.retryable is True

    def test_content_error_not_retryable_by_default(self):
        """Test that content errors are not retryable by default."""
        error = ContentError("Invalid content")
        assert error.retryable is False


class TestExponentialBackoff:
    """Test ExponentialBackoff helper."""

    def test_backoff_creation(self):
        """Test creating a backoff helper."""
        backoff = ExponentialBackoff(base=1.0, max_wait=60.0, max_retries=5)
        assert backoff.base == 1.0
        assert backoff.max_wait == 60.0
        assert backoff.max_retries == 5
        assert backoff.attempt == 0

    def test_backoff_validation_negative_base(self):
        """Test that negative base is rejected."""
        with pytest.raises(ValueError, match="base must be >= 0"):
            ExponentialBackoff(base=-1.0)

    def test_backoff_validation_zero_max_wait(self):
        """Test that zero max_wait is rejected."""
        with pytest.raises(ValueError, match="max_wait must be > 0"):
            ExponentialBackoff(max_wait=0.0)

    def test_backoff_validation_negative_max_wait(self):
        """Test that negative max_wait is rejected."""
        with pytest.raises(ValueError, match="max_wait must be > 0"):
            ExponentialBackoff(max_wait=-1.0)

    def test_backoff_zero_base_returns_zero_wait(self):
        """Test that base=0 returns zero wait time."""
        backoff = ExponentialBackoff(base=0.0, max_wait=60.0)
        wait_time = backoff.get_wait_time()
        assert wait_time == 0.0

    def test_backoff_reset(self):
        """Test resetting backoff state."""
        backoff = ExponentialBackoff()
        backoff.attempt = 3
        backoff.reset()
        assert backoff.attempt == 0

    def test_backoff_is_exhausted(self):
        """Test checking if backoff is exhausted."""
        backoff = ExponentialBackoff(max_retries=3)
        assert backoff.is_exhausted is False

        backoff.attempt = 3
        assert backoff.is_exhausted is True

    def test_backoff_raises_on_exhaustion(self):
        """Test that wait raises when max retries exceeded."""
        backoff = ExponentialBackoff(max_retries=1)
        backoff.attempt = 1

        with pytest.raises(RuntimeError, match="Maximum retries"):
            backoff.wait()

    def test_backoff_increments_attempt(self):
        """Test that attempt counter increments."""
        backoff = ExponentialBackoff(base=0.001, max_retries=3)
        assert backoff.attempt == 0

        backoff.wait()
        assert backoff.attempt == 1

        backoff.wait()
        assert backoff.attempt == 2

    def test_backoff_respects_max_wait(self):
        """Test that backoff respects max_wait cap."""
        backoff = ExponentialBackoff(base=1.0, max_wait=5.0, max_retries=10)
        for _ in range(10):
            wait_time = backoff.get_wait_time()
            assert wait_time <= 5.0
            backoff.attempt += 1

    def test_backoff_get_wait_time_without_sleeping(self):
        """Test getting wait time without actually sleeping."""
        backoff = ExponentialBackoff(base=1.0)
        start = time.time()
        wait_time = backoff.get_wait_time()
        elapsed = time.time() - start

        # Should not sleep
        assert elapsed < 0.1
        assert isinstance(wait_time, float)

    def test_backoff_sequence(self):
        """Test a sequence of backoff retries."""
        backoff = ExponentialBackoff(base=0.001, max_retries=5)
        waits = []

        for i in range(backoff.max_retries):
            wait_time = backoff.get_wait_time()
            waits.append(wait_time)
            backoff.attempt += 1

        # Verify we got 5 waits
        assert len(waits) == 5
        # All should be non-negative
        assert all(w >= 0 for w in waits)


class TestErrorTypeEnum:
    """Test ErrorType enumeration."""

    def test_all_error_types_defined(self):
        """Test that all expected error types exist."""
        expected_types = {
            "rate_limit",
            "timeout",
            "auth_error",
            "content_error",
            "network_error",
            "parse_error",
            "validation_error",
            "unknown",
        }
        actual_types = {e.value for e in ErrorType}
        assert expected_types == actual_types

    def test_error_type_values(self):
        """Test error type string values."""
        assert ErrorType.RATE_LIMIT.value == "rate_limit"
        assert ErrorType.TIMEOUT.value == "timeout"
        assert ErrorType.AUTH_ERROR.value == "auth_error"
