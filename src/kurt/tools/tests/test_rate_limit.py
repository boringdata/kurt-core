"""Tests for rate limiting infrastructure."""

import threading
import time

import pytest

from kurt.tools.rate_limit import (
    CostSummary,
    RateLimitConfig,
    RateLimiter,
    TokenBucket,
)


class TestTokenBucket:
    """Test TokenBucket implementation."""

    def test_bucket_creation(self):
        """Test creating a token bucket."""
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0)
        assert bucket.capacity == 10.0
        assert bucket.refill_rate == 1.0
        assert bucket.tokens == 10.0

    def test_consume_tokens(self):
        """Test consuming tokens."""
        bucket = TokenBucket(capacity=10.0, refill_rate=0.0)  # No refill
        assert bucket.consume(5.0) is True
        assert abs(bucket.tokens - 5.0) < 0.01
        assert bucket.consume(5.0) is True
        assert abs(bucket.tokens - 0.0) < 0.01

    def test_consume_insufficient_tokens(self):
        """Test consumption fails when insufficient tokens."""
        bucket = TokenBucket(capacity=10.0, refill_rate=0.0)  # No refill
        bucket.tokens = 3.0
        assert bucket.consume(5.0) is False
        assert abs(bucket.tokens - 3.0) < 0.01  # Not consumed

    def test_token_refill(self):
        """Test tokens refill over time."""
        bucket = TokenBucket(capacity=10.0, refill_rate=10.0)  # 10 tokens/sec
        bucket.tokens = 0.0
        bucket.last_refill = time.time() - 1.0  # 1 second ago

        bucket._refill()
        # Should have refilled ~10 tokens
        assert bucket.tokens >= 9.5

    def test_available_property(self):
        """Test available property."""
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0)
        available = bucket.available
        assert available == 10.0

    def test_bucket_capacity_respected(self):
        """Test that capacity is never exceeded."""
        bucket = TokenBucket(capacity=5.0, refill_rate=100.0)
        bucket.tokens = 0.0
        bucket.last_refill = time.time() - 2.0

        bucket._refill()
        # Should not exceed capacity
        assert bucket.tokens <= 5.0

    def test_thread_safe_consume(self):
        """Test thread-safe token consumption."""
        bucket = TokenBucket(capacity=100.0, refill_rate=0.0)  # No refill
        results = []

        def consume_tokens():
            for _ in range(10):
                results.append(bucket.consume(1.0))

        threads = [threading.Thread(target=consume_tokens) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All 50 consumes should succeed (bucket had 100 tokens, 50 requested)
        assert len(results) == 50
        assert all(results)
        # Should have consumed 50 tokens from 100
        assert 45.0 <= bucket.tokens <= 55.0


class TestRateLimitConfig:
    """Test RateLimitConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = RateLimitConfig()
        assert config.requests_per_second == 10.0
        assert config.burst_size == 10
        assert config.cost_per_request == 1.0

    def test_custom_config(self):
        """Test custom configuration."""
        config = RateLimitConfig(
            requests_per_second=5.0,
            burst_size=20,
            cost_per_request=0.5,
        )
        assert config.requests_per_second == 5.0
        assert config.burst_size == 20
        assert config.cost_per_request == 0.5


class TestCostSummary:
    """Test CostSummary tracking."""

    def test_cost_summary_creation(self):
        """Test creating cost summary."""
        summary = CostSummary()
        assert summary.total_requests == 0
        assert summary.total_cost == 0.0
        assert summary.cost_breakdown == {}

    def test_add_cost(self):
        """Test adding costs."""
        summary = CostSummary()
        summary.add_cost("apify", 0.50)
        summary.add_cost("apify", 0.50)
        summary.add_cost("firecrawl", 0.25)

        assert summary.total_requests == 3
        assert summary.total_cost == 1.25
        assert summary.cost_breakdown["apify"] == 1.0
        assert summary.cost_breakdown["firecrawl"] == 0.25


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_limiter_creation(self):
        """Test creating a rate limiter."""
        limiter = RateLimiter()
        assert limiter._buckets == {}
        assert limiter._configs == {}

    def test_configure_engine(self):
        """Test configuring an engine."""
        limiter = RateLimiter()
        config = RateLimitConfig(requests_per_second=5.0)
        limiter.configure("test_engine", config)

        assert "test_engine" in limiter._buckets
        assert "test_engine" in limiter._configs
        assert limiter._configs["test_engine"] == config

    def test_acquire_token(self):
        """Test acquiring tokens."""
        limiter = RateLimiter()
        limiter.configure("test", RateLimitConfig(requests_per_second=10.0))

        # Should succeed with blocking=False initially
        assert limiter.acquire("test", blocking=False) is True
        assert limiter.acquire("test", blocking=False) is True

    def test_acquire_unconfigured_engine(self):
        """Test acquiring from unconfigured engine raises."""
        limiter = RateLimiter()
        with pytest.raises(KeyError, match="not configured"):
            limiter.acquire("unconfigured", blocking=False)

    def test_cost_hook(self):
        """Test cost tracking hook."""
        costs = []

        def track_cost(engine: str, cost: float):
            costs.append((engine, cost))

        limiter = RateLimiter(cost_hook=track_cost)
        limiter.configure(
            "apify",
            RateLimitConfig(cost_per_request=0.50),
        )

        limiter.acquire("apify", cost=2.0, blocking=False)
        assert len(costs) == 1
        assert costs[0] == ("apify", 1.0)  # 2.0 * 0.50

    def test_context_manager(self):
        """Test context manager for rate limiting."""
        limiter = RateLimiter()
        limiter.configure("test", RateLimitConfig())

        # Should not raise
        with limiter.rate_limited("test", cost=1.0):
            pass

    def test_context_manager_exception(self):
        """Test context manager with exception."""
        limiter = RateLimiter()
        limiter.configure("test", RateLimitConfig())

        with pytest.raises(ValueError):
            with limiter.rate_limited("test", cost=1.0):
                raise ValueError("Test error")

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager."""
        limiter = RateLimiter()
        limiter.configure("test", RateLimitConfig())

        # Should not raise
        async with limiter.async_rate_limited("test", cost=1.0):
            pass

    @pytest.mark.asyncio
    async def test_async_context_manager_exception(self):
        """Test async context manager with exception."""
        limiter = RateLimiter()
        limiter.configure("test", RateLimitConfig())

        with pytest.raises(ValueError):
            async with limiter.async_rate_limited("test", cost=1.0):
                raise ValueError("Test error")

    def test_get_bucket(self):
        """Test getting bucket reference."""
        limiter = RateLimiter()
        limiter.configure("test", RateLimitConfig())

        bucket = limiter.get_bucket("test")
        assert bucket is not None
        assert bucket.capacity == 10.0

    def test_get_bucket_nonexistent(self):
        """Test getting nonexistent bucket."""
        limiter = RateLimiter()
        bucket = limiter.get_bucket("nonexistent")
        assert bucket is None

    def test_reset_specific_engine(self):
        """Test resetting specific engine."""
        limiter = RateLimiter()
        limiter.configure("test1", RateLimitConfig())
        limiter.configure("test2", RateLimitConfig())

        bucket1_before = limiter.get_bucket("test1")
        bucket1_before.tokens = 0.0

        limiter.reset("test1")

        bucket1_after = limiter.get_bucket("test1")
        assert bucket1_after.tokens == 10.0  # Reset to capacity

    def test_reset_all_engines(self):
        """Test resetting all engines."""
        limiter = RateLimiter()
        limiter.configure("test1", RateLimitConfig())
        limiter.configure("test2", RateLimitConfig())

        limiter.get_bucket("test1").tokens = 0.0
        limiter.get_bucket("test2").tokens = 0.0

        limiter.reset()

        assert limiter.get_bucket("test1").tokens == 10.0
        assert limiter.get_bucket("test2").tokens == 10.0

    def test_multi_engine_isolation(self):
        """Test that engines are isolated."""
        limiter = RateLimiter()
        # Use no refill rate for predictable token counts
        limiter.configure(
            "engine1",
            RateLimitConfig(requests_per_second=0.0, burst_size=1),
        )
        limiter.configure(
            "engine2",
            RateLimitConfig(requests_per_second=0.0, burst_size=10),
        )

        # Both should succeed
        assert limiter.acquire("engine1", blocking=False) is True
        assert limiter.acquire("engine2", blocking=False) is True

        # Now engine1 has 0 tokens, engine2 has many
        assert limiter.acquire("engine1", blocking=False) is False
        assert limiter.acquire("engine2", blocking=False) is True

    def test_cost_multiplier(self):
        """Test cost multiplier application."""
        costs = []

        def track(engine: str, cost: float):
            costs.append(cost)

        limiter = RateLimiter(cost_hook=track)
        limiter.configure(
            "apify",
            RateLimitConfig(cost_per_request=0.50),
        )

        # Cost of 2.0 * 0.50 = 1.0
        limiter.acquire("apify", cost=2.0, blocking=False)
        assert costs[0] == 1.0

        # Cost of 4.0 * 0.50 = 2.0
        limiter.acquire("apify", cost=4.0, blocking=False)
        assert costs[1] == 2.0


class TestThreadSafety:
    """Test thread-safety of RateLimiter."""

    def test_concurrent_acquire(self):
        """Test concurrent token acquisition."""
        limiter = RateLimiter()
        limiter.configure(
            "test",
            RateLimitConfig(requests_per_second=0.0, burst_size=100),
        )

        successes = []

        def acquire_tokens():
            for _ in range(50):
                result = limiter.acquire("test", cost=1.0, blocking=False)
                successes.append(result)

        threads = [threading.Thread(target=acquire_tokens) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should succeed up to burst size (100 tokens, 250 total attempts)
        successful = len([s for s in successes if s])
        assert 90 <= successful <= 100  # Allow some tolerance for ordering
