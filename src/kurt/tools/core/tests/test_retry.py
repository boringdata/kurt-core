"""Tests for retry module."""

import asyncio
import time

import pytest

from kurt.tools.core.retry import (
    RetryConfig,
    RetryExhaustedError,
    calculate_backoff_ms,
    is_retryable_error,
    retry_sync,
    retry_with_backoff,
)


# ============================================================================
# Tests for RetryConfig
# ============================================================================


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.backoff_ms == 1000
        assert config.max_backoff_ms == 60000
        assert config.exponential_base == 2
        assert config.jitter is False
        assert config.retryable_exceptions == []
        assert config.retryable_messages == []
        assert config.non_retryable_messages == []

    def test_custom_values(self):
        """Should accept custom values."""
        config = RetryConfig(
            max_retries=5,
            backoff_ms=500,
            max_backoff_ms=30000,
            exponential_base=3,
            retryable_exceptions=[ConnectionError, TimeoutError],
            retryable_messages=["rate limit"],
            non_retryable_messages=["invalid"],
        )
        assert config.max_retries == 5
        assert config.backoff_ms == 500
        assert config.max_backoff_ms == 30000
        assert config.exponential_base == 3
        assert ConnectionError in config.retryable_exceptions
        assert "rate limit" in config.retryable_messages
        assert "invalid" in config.non_retryable_messages


# ============================================================================
# Tests for is_retryable_error
# ============================================================================


class TestIsRetryableError:
    """Tests for is_retryable_error function."""

    def test_default_value_error_not_retryable(self):
        """ValueError should not be retried by default."""
        error = ValueError("bad value")
        assert is_retryable_error(error) is False

    def test_default_key_error_not_retryable(self):
        """KeyError should not be retried by default."""
        error = KeyError("missing_key")
        assert is_retryable_error(error) is False

    def test_default_type_error_not_retryable(self):
        """TypeError should not be retried by default."""
        error = TypeError("wrong type")
        assert is_retryable_error(error) is False

    def test_connection_error_is_retryable(self):
        """Connection errors should be retried."""
        error = Exception("connection refused")
        assert is_retryable_error(error) is True

    def test_timeout_error_is_retryable(self):
        """Timeout errors should be retried."""
        error = Exception("timeout occurred")
        assert is_retryable_error(error) is True

    def test_network_error_is_retryable(self):
        """Network errors should be retried."""
        error = Exception("network unreachable")
        assert is_retryable_error(error) is True

    def test_content_too_large_not_retryable(self):
        """Content too large should not be retried."""
        error = ValueError("content_too_large: 10MB")
        assert is_retryable_error(error) is False

    def test_invalid_content_type_not_retryable(self):
        """Invalid content type should not be retried."""
        error = ValueError("invalid_content_type: application/pdf")
        assert is_retryable_error(error) is False

    def test_config_retryable_exceptions(self):
        """Should use config's retryable_exceptions list."""
        config = RetryConfig(retryable_exceptions=[IOError])
        error = IOError("disk error")
        assert is_retryable_error(error, config) is True

    def test_config_retryable_messages(self):
        """Should use config's retryable_messages list."""
        config = RetryConfig(retryable_messages=["rate limit", "429"])
        error = Exception("rate limit exceeded")
        assert is_retryable_error(error, config) is True

    def test_config_non_retryable_messages_take_precedence(self):
        """Non-retryable messages should override retryable ones."""
        config = RetryConfig(
            retryable_messages=["error"],
            non_retryable_messages=["invalid token"],
        )
        # This has "error" but also "invalid token"
        error = Exception("invalid token error")
        assert is_retryable_error(error, config) is False

    def test_unknown_error_not_retried_by_default(self):
        """Unknown errors should not be retried by default."""

        class CustomError(Exception):
            pass

        error = CustomError("something went wrong")
        assert is_retryable_error(error) is False


# ============================================================================
# Tests for calculate_backoff_ms
# ============================================================================


class TestCalculateBackoffMs:
    """Tests for calculate_backoff_ms function."""

    def test_first_attempt_uses_base_delay(self):
        """Attempt 0 should use base delay."""
        config = RetryConfig(backoff_ms=1000)
        assert calculate_backoff_ms(0, config) == 1000

    def test_exponential_growth(self):
        """Delay should grow exponentially."""
        config = RetryConfig(backoff_ms=1000, exponential_base=2)
        assert calculate_backoff_ms(0, config) == 1000
        assert calculate_backoff_ms(1, config) == 2000
        assert calculate_backoff_ms(2, config) == 4000
        assert calculate_backoff_ms(3, config) == 8000

    def test_respects_max_backoff(self):
        """Should cap at max_backoff_ms."""
        config = RetryConfig(backoff_ms=1000, max_backoff_ms=5000)
        assert calculate_backoff_ms(5, config) == 5000  # Would be 32000
        assert calculate_backoff_ms(10, config) == 5000  # Would be huge

    def test_custom_exponential_base(self):
        """Should use custom exponential base."""
        config = RetryConfig(backoff_ms=100, exponential_base=3)
        assert calculate_backoff_ms(0, config) == 100
        assert calculate_backoff_ms(1, config) == 300
        assert calculate_backoff_ms(2, config) == 900


# ============================================================================
# Tests for retry_with_backoff (async)
# ============================================================================


class TestRetryWithBackoff:
    """Tests for async retry_with_backoff function."""

    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self):
        """Should return result without retrying if first call succeeds."""
        call_count = 0

        async def succeeds():
            nonlocal call_count
            call_count += 1
            return "success"

        config = RetryConfig(max_retries=3, backoff_ms=10)
        result = await retry_with_backoff(succeeds, config)

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_retryable_error(self):
        """Should retry on retryable errors."""
        call_count = 0

        async def fails_then_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("connection refused")
            return "success"

        config = RetryConfig(max_retries=5, backoff_ms=10)
        result = await retry_with_backoff(fails_then_succeeds, config)

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_non_retryable_error_immediately(self):
        """Should not retry non-retryable errors."""
        call_count = 0

        async def fails_with_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("bad input")

        config = RetryConfig(max_retries=5, backoff_ms=10)

        with pytest.raises(ValueError, match="bad input"):
            await retry_with_backoff(fails_with_value_error, config)

        assert call_count == 1  # No retries

    @pytest.mark.asyncio
    async def test_exhausts_retries(self):
        """Should raise last error after exhausting retries."""
        call_count = 0

        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise Exception("connection timeout")

        config = RetryConfig(max_retries=3, backoff_ms=10)

        with pytest.raises(Exception, match="connection timeout"):
            await retry_with_backoff(always_fails, config)

        assert call_count == 4  # 1 + 3 retries

    @pytest.mark.asyncio
    async def test_passes_args_and_kwargs(self):
        """Should pass args and kwargs to function."""

        async def echo(a, b, c=None):
            return f"{a}-{b}-{c}"

        config = RetryConfig(max_retries=1, backoff_ms=10)
        result = await retry_with_backoff(echo, config, "x", "y", c="z")

        assert result == "x-y-z"

    @pytest.mark.asyncio
    async def test_respects_backoff_timing(self):
        """Should wait between retries."""
        call_times = []

        async def fails_twice():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise Exception("connection error")
            return "done"

        config = RetryConfig(max_retries=3, backoff_ms=50)  # 50ms base
        await retry_with_backoff(fails_twice, config)

        # Check delays (with some tolerance)
        assert len(call_times) == 3
        # First retry: ~50ms, second retry: ~100ms
        delay1 = (call_times[1] - call_times[0]) * 1000  # ms
        delay2 = (call_times[2] - call_times[1]) * 1000  # ms

        assert delay1 >= 40  # Allow some tolerance
        assert delay2 >= 80  # Second delay should be ~100ms


# ============================================================================
# Tests for retry_sync
# ============================================================================


class TestRetrySync:
    """Tests for sync retry_sync function."""

    def test_succeeds_on_first_try(self):
        """Should return result without retrying if first call succeeds."""
        call_count = 0

        def succeeds():
            nonlocal call_count
            call_count += 1
            return "sync_success"

        config = RetryConfig(max_retries=3, backoff_ms=10)
        result = retry_sync(succeeds, config)

        assert result == "sync_success"
        assert call_count == 1

    def test_retries_on_retryable_error(self):
        """Should retry on retryable errors."""
        call_count = 0

        def fails_then_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("timeout")
            return "recovered"

        config = RetryConfig(max_retries=3, backoff_ms=10)
        result = retry_sync(fails_then_succeeds, config)

        assert result == "recovered"
        assert call_count == 2

    def test_raises_non_retryable_error_immediately(self):
        """Should not retry non-retryable errors."""
        call_count = 0

        def fails_with_key_error():
            nonlocal call_count
            call_count += 1
            raise KeyError("missing")

        config = RetryConfig(max_retries=5, backoff_ms=10)

        with pytest.raises(KeyError):
            retry_sync(fails_with_key_error, config)

        assert call_count == 1


# ============================================================================
# Tests for RetryExhaustedError
# ============================================================================


class TestRetryExhaustedError:
    """Tests for RetryExhaustedError exception."""

    def test_stores_last_error(self):
        """Should store the last error."""
        original = ValueError("original error")
        error = RetryExhaustedError("retries exhausted", last_error=original)

        assert error.last_error is original
        assert "retries exhausted" in str(error)

    def test_stores_attempt_count(self):
        """Should store attempt count."""
        error = RetryExhaustedError("failed", attempts=5)
        assert error.attempts == 5
