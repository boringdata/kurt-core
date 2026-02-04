"""Rate limiting infrastructure for API engines.

Implements token bucket algorithm for managing API rate limits across engines.
Supports thread-safe operations and cost tracking for paid APIs.
"""

import asyncio
import threading
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting.

    Attributes:
        requests_per_second: Max requests per second
        burst_size: Max tokens in bucket (for bursts)
        cost_per_request: Cost multiplier for this endpoint (1.0 = standard rate)
    """

    requests_per_second: float = 10.0
    burst_size: int = 10
    cost_per_request: float = 1.0


@dataclass
class CostSummary:
    """Summary of API costs incurred.

    Attributes:
        total_requests: Total number of requests made
        total_cost: Total monetary cost (in USD or relevant currency)
        cost_breakdown: Per-engine cost breakdown
    """

    total_requests: int = 0
    total_cost: float = 0.0
    cost_breakdown: Dict[str, float] = field(default_factory=dict)

    def add_cost(self, engine: str, amount: float) -> None:
        """Add cost for an engine."""
        if engine not in self.cost_breakdown:
            self.cost_breakdown[engine] = 0.0
        self.cost_breakdown[engine] += amount
        self.total_cost += amount
        self.total_requests += 1


class TokenBucket:
    """Token bucket for rate limiting.

    Implements the token bucket algorithm with refill capability.
    Thread-safe using locks.
    """

    def __init__(
        self,
        capacity: float,
        refill_rate: float,
    ):
        """Initialize token bucket.

        Args:
            capacity: Maximum tokens (burst size)
            refill_rate: Tokens per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = threading.RLock()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate,
        )
        self.last_refill = now

    def consume(self, tokens: float = 1.0) -> bool:
        """Try to consume tokens.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if consumption succeeded, False otherwise
        """
        with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def wait_available(self, tokens: float = 1.0) -> float:
        """Wait until tokens are available.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            Time waited in seconds
        """
        start = time.time()
        while True:
            with self._lock:
                self._refill()
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return time.time() - start

            # Release lock and sleep briefly before retrying to avoid busy-waiting
            time.sleep(0.001)

    @property
    def available(self) -> float:
        """Get currently available tokens."""
        with self._lock:
            self._refill()
            return self.tokens


class RateLimiter:
    """Manages API rate limits across multiple engines.

    Supports per-engine configuration, thread-safe operations,
    and cost tracking for paid APIs.
    """

    def __init__(self, cost_hook: Optional[Callable[[str, float], None]] = None):
        """Initialize rate limiter.

        Args:
            cost_hook: Optional callback for cost tracking (engine, cost)
        """
        self._buckets: Dict[str, TokenBucket] = {}
        self._configs: Dict[str, RateLimitConfig] = {}
        self._cost_hook = cost_hook
        self._lock = threading.RLock()

    def configure(
        self,
        engine: str,
        config: RateLimitConfig,
    ) -> None:
        """Configure rate limiting for an engine.

        Args:
            engine: Engine name
            config: Rate limit configuration
        """
        with self._lock:
            self._configs[engine] = config
            self._buckets[engine] = TokenBucket(
                capacity=config.burst_size,
                refill_rate=config.requests_per_second,
            )

    def acquire(
        self,
        engine: str,
        cost: float = 1.0,
        blocking: bool = True,
    ) -> bool:
        """Acquire a token for an API call.

        Args:
            engine: Engine name
            cost: Token cost (multiplier of requests_per_second)
            blocking: Wait for token if unavailable

        Returns:
            True if token acquired, False otherwise

        Raises:
            KeyError: If engine not configured
        """
        if engine not in self._buckets:
            raise KeyError(f"Engine not configured: {engine}")

        bucket = self._buckets[engine]
        config = self._configs[engine]

        # Cost is applied as a multiplier to token consumption
        tokens_needed = cost * config.cost_per_request

        if blocking:
            bucket.wait_available(tokens_needed)
            if self._cost_hook:
                self._cost_hook(engine, config.cost_per_request * cost)
            return True
        else:
            if bucket.consume(tokens_needed):
                if self._cost_hook:
                    self._cost_hook(engine, config.cost_per_request * cost)
                return True
            return False

    @contextmanager
    def rate_limited(
        self,
        engine: str,
        cost: float = 1.0,
    ):
        """Context manager for rate-limited operations.

        Usage:
            with limiter.rate_limited("apify", cost=2.0):
                # API call here
                ...

        Args:
            engine: Engine name
            cost: Token cost for this operation
        """
        self.acquire(engine, cost=cost, blocking=True)
        try:
            yield
        except Exception:
            # Don't release on error - cost was already incurred
            raise

    @asynccontextmanager
    async def async_rate_limited(
        self,
        engine: str,
        cost: float = 1.0,
    ):
        """Async context manager for rate-limited operations.

        Usage:
            async with limiter.async_rate_limited("apify", cost=2.0):
                # API call here
                ...

        Args:
            engine: Engine name
            cost: Token cost for this operation
        """
        # Run blocking acquire in thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self.acquire,
            engine,
            cost,
            True,
        )
        try:
            yield
        except Exception:
            # Don't release on error - cost was already incurred
            raise

    def get_bucket(self, engine: str) -> Optional[TokenBucket]:
        """Get token bucket for an engine (for testing/monitoring)."""
        with self._lock:
            return self._buckets.get(engine)

    def reset(self, engine: Optional[str] = None) -> None:
        """Reset rate limiter state.

        Args:
            engine: Specific engine to reset, or None for all engines
        """
        with self._lock:
            if engine:
                if engine in self._buckets:
                    config = self._configs[engine]
                    self._buckets[engine] = TokenBucket(
                        capacity=config.burst_size,
                        refill_rate=config.requests_per_second,
                    )
            else:
                # Reset all
                for eng, config in self._configs.items():
                    self._buckets[eng] = TokenBucket(
                        capacity=config.burst_size,
                        refill_rate=config.requests_per_second,
                    )
