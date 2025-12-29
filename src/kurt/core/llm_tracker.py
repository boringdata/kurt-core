"""
Global LLM call tracker for monitoring API usage across workflows.

Tracks embedding and LLM calls with timestamps, enabling:
- Real-time calls/sec monitoring
- Rate limit detection (parallel steps competing for quota)
- Post-workflow analysis via DBOS streams

Usage:
    from kurt.core.llm_tracker import llm_tracker

    # Configure for workflow
    llm_tracker.configure(workflow_id="abc-123")

    # Track a call
    llm_tracker.track_call("embedding", model="text-embedding-3-small", count=100, step_name="entity_clustering")

    # Get current rate
    rate = llm_tracker.get_calls_per_second()

    # Print summary
    llm_tracker.print_summary()
"""

import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import DBOS
try:
    from dbos import DBOS

    HAS_DBOS = True
except ImportError:
    HAS_DBOS = False
    logger.debug("DBOS not available - LLM tracker events will only be logged")


@dataclass
class LLMCall:
    """Record of a single LLM or embedding API call."""

    timestamp: float
    call_type: str  # "embedding" or "llm"
    model: str
    count: int  # Number of items in batch (texts for embeddings, 1 for LLM)
    step_name: Optional[str] = None
    duration_ms: Optional[float] = None
    tokens_prompt: Optional[int] = None  # Input/prompt tokens used
    tokens_completion: Optional[int] = None  # Output/completion tokens used


@dataclass
class TimelineBucket:
    """Aggregated stats for a time bucket."""

    start_time: float
    end_time: float
    total_calls: int = 0
    total_items: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_step: Dict[str, int] = field(default_factory=dict)
    by_model: Dict[str, int] = field(default_factory=dict)


class LLMTracker:
    """
    Thread-safe singleton tracker for LLM and embedding API calls.

    Maintains a sliding window of recent calls for real-time rate monitoring
    and emits events to DBOS streams for post-workflow analysis.
    """

    def __init__(self, window_seconds: float = 60.0):
        """
        Initialize the tracker.

        Args:
            window_seconds: How long to keep calls in the sliding window (default 60s)
        """
        # Use RLock (reentrant lock) so that get_stats() can call other methods that also lock
        self._lock = threading.RLock()
        self._window_seconds = window_seconds
        self._calls: Deque[LLMCall] = deque()
        self._workflow_id: Optional[str] = None
        self._start_time: Optional[float] = None

        # Cumulative totals (not affected by sliding window pruning)
        self._total_calls = 0
        self._total_items = 0
        self._total_tokens_prompt = 0
        self._total_tokens_completion = 0
        self._totals_by_type: Dict[str, int] = {}
        self._totals_by_step: Dict[str, int] = {}
        self._totals_by_model: Dict[str, int] = {}
        self._items_by_type: Dict[str, int] = {}
        self._items_by_step: Dict[str, int] = {}
        self._items_by_model: Dict[str, int] = {}
        self._tokens_prompt_by_step: Dict[str, int] = {}
        self._tokens_completion_by_step: Dict[str, int] = {}
        self._tokens_prompt_by_model: Dict[str, int] = {}
        self._tokens_completion_by_model: Dict[str, int] = {}

    def configure(self, workflow_id: Optional[str] = None) -> None:
        """
        Configure tracker for a new workflow.

        Resets all tracking data and binds to the specified workflow ID.

        Args:
            workflow_id: DBOS workflow ID for stream naming
        """
        with self._lock:
            self._workflow_id = workflow_id
            self._calls.clear()
            self._start_time = time.time()

            # Reset cumulative totals
            self._total_calls = 0
            self._total_items = 0
            self._total_tokens_prompt = 0
            self._total_tokens_completion = 0
            self._totals_by_type = {}
            self._totals_by_step = {}
            self._totals_by_model = {}
            self._items_by_type = {}
            self._items_by_step = {}
            self._items_by_model = {}
            self._tokens_prompt_by_step = {}
            self._tokens_completion_by_step = {}
            self._tokens_prompt_by_model = {}
            self._tokens_completion_by_model = {}

            logger.debug(f"LLM tracker configured for workflow: {workflow_id}")

    def track_call(
        self,
        call_type: str,
        model: str,
        count: int = 1,
        step_name: Optional[str] = None,
        duration_ms: Optional[float] = None,
        tokens_prompt: Optional[int] = None,
        tokens_completion: Optional[int] = None,
    ) -> None:
        """
        Record an LLM or embedding API call.

        Args:
            call_type: Type of call ("embedding" or "llm")
            model: Model identifier (e.g., "text-embedding-3-small")
            count: Number of items in batch (texts for embeddings, 1 for LLM)
            step_name: Optional pipeline step name (e.g., "entity_clustering")
            duration_ms: Optional call duration in milliseconds
            tokens_prompt: Optional number of input/prompt tokens used
            tokens_completion: Optional number of output/completion tokens used
        """
        now = time.time()
        call = LLMCall(
            timestamp=now,
            call_type=call_type,
            model=model,
            count=count,
            step_name=step_name,
            duration_ms=duration_ms,
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
        )

        with self._lock:
            # Add to sliding window
            self._calls.append(call)

            # Update cumulative totals
            self._total_calls += 1
            self._total_items += count
            if tokens_prompt:
                self._total_tokens_prompt += tokens_prompt
            if tokens_completion:
                self._total_tokens_completion += tokens_completion

            self._totals_by_type[call_type] = self._totals_by_type.get(call_type, 0) + 1
            self._items_by_type[call_type] = self._items_by_type.get(call_type, 0) + count

            if step_name:
                self._totals_by_step[step_name] = self._totals_by_step.get(step_name, 0) + 1
                self._items_by_step[step_name] = self._items_by_step.get(step_name, 0) + count
                if tokens_prompt:
                    self._tokens_prompt_by_step[step_name] = (
                        self._tokens_prompt_by_step.get(step_name, 0) + tokens_prompt
                    )
                if tokens_completion:
                    self._tokens_completion_by_step[step_name] = (
                        self._tokens_completion_by_step.get(step_name, 0) + tokens_completion
                    )

            self._totals_by_model[model] = self._totals_by_model.get(model, 0) + 1
            self._items_by_model[model] = self._items_by_model.get(model, 0) + count
            if tokens_prompt:
                self._tokens_prompt_by_model[model] = (
                    self._tokens_prompt_by_model.get(model, 0) + tokens_prompt
                )
            if tokens_completion:
                self._tokens_completion_by_model[model] = (
                    self._tokens_completion_by_model.get(model, 0) + tokens_completion
                )

            # Prune old calls outside sliding window
            self._prune_old_calls(now)

        # Emit to DBOS stream (outside lock to avoid blocking)
        self._emit_to_dbos(call)

        logger.debug(
            f"Tracked {call_type} call: model={model}, count={count}, "
            f"step={step_name}, duration={duration_ms}ms, "
            f"tokens_prompt={tokens_prompt}, tokens_completion={tokens_completion}"
        )

    def _prune_old_calls(self, now: float) -> None:
        """Remove calls older than the sliding window. Must be called with lock held."""
        cutoff = now - self._window_seconds
        while self._calls and self._calls[0].timestamp < cutoff:
            self._calls.popleft()

    def _emit_to_dbos(self, call: LLMCall) -> None:
        """Emit a call event to DBOS stream."""
        if not HAS_DBOS or not self._workflow_id:
            return

        stream_name = f"llm_calls_{self._workflow_id}"
        event = {
            "timestamp": datetime.utcfromtimestamp(call.timestamp).isoformat(),
            "type": "llm_call",
            "call_type": call.call_type,
            "model": call.model,
            "count": call.count,
            "step_name": call.step_name,
            "duration_ms": call.duration_ms,
            "tokens_prompt": call.tokens_prompt,
            "tokens_completion": call.tokens_completion,
        }

        try:
            DBOS.write_stream(stream_name, json.dumps(event))
            logger.debug(f"Emitted LLM call event to DBOS stream {stream_name}")
        except Exception as e:
            logger.debug(f"Failed to emit to DBOS stream: {e}")

    def get_calls_per_second(self, window: float = 5.0) -> float:
        """
        Get the current call rate (calls per second).

        Args:
            window: Time window in seconds for rate calculation (default 5s)

        Returns:
            Calls per second over the specified window
        """
        now = time.time()
        cutoff = now - window

        with self._lock:
            self._prune_old_calls(now)
            count = sum(1 for call in self._calls if call.timestamp >= cutoff)

        return count / window if window > 0 else 0.0

    def get_items_per_second(self, window: float = 5.0) -> float:
        """
        Get the current item rate (items per second).

        For embeddings, this is texts/second. For LLM calls, this is calls/second.

        Args:
            window: Time window in seconds for rate calculation (default 5s)

        Returns:
            Items per second over the specified window
        """
        now = time.time()
        cutoff = now - window

        with self._lock:
            self._prune_old_calls(now)
            total_items = sum(call.count for call in self._calls if call.timestamp >= cutoff)

        return total_items / window if window > 0 else 0.0

    def get_rate_by_step(self, window: float = 5.0) -> Dict[str, Dict[str, float]]:
        """
        Get call and item rates broken down by step.

        Args:
            window: Time window in seconds for rate calculation (default 5s)

        Returns:
            Dict mapping step_name -> {"calls_per_sec": float, "items_per_sec": float}
        """
        now = time.time()
        cutoff = now - window

        with self._lock:
            self._prune_old_calls(now)
            step_calls: Dict[str, int] = {}
            step_items: Dict[str, int] = {}

            for call in self._calls:
                if call.timestamp >= cutoff:
                    step = call.step_name or "unknown"
                    step_calls[step] = step_calls.get(step, 0) + 1
                    step_items[step] = step_items.get(step, 0) + call.count

        result = {}
        for step in set(step_calls.keys()) | set(step_items.keys()):
            result[step] = {
                "calls_per_sec": step_calls.get(step, 0) / window if window > 0 else 0.0,
                "items_per_sec": step_items.get(step, 0) / window if window > 0 else 0.0,
            }
        return result

    def get_rate_by_model(self, window: float = 5.0) -> Dict[str, Dict[str, float]]:
        """
        Get call and item rates broken down by model.

        Args:
            window: Time window in seconds for rate calculation (default 5s)

        Returns:
            Dict mapping model -> {"calls_per_sec": float, "items_per_sec": float}
        """
        now = time.time()
        cutoff = now - window

        with self._lock:
            self._prune_old_calls(now)
            model_calls: Dict[str, int] = {}
            model_items: Dict[str, int] = {}

            for call in self._calls:
                if call.timestamp >= cutoff:
                    model_calls[call.model] = model_calls.get(call.model, 0) + 1
                    model_items[call.model] = model_items.get(call.model, 0) + call.count

        result = {}
        for model in set(model_calls.keys()) | set(model_items.keys()):
            result[model] = {
                "calls_per_sec": model_calls.get(model, 0) / window if window > 0 else 0.0,
                "items_per_sec": model_items.get(model, 0) / window if window > 0 else 0.0,
            }
        return result

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about tracked calls.

        Returns:
            Dict with:
                - total_calls: Total number of API calls
                - total_items: Total items processed (texts, tokens, etc.)
                - total_tokens_prompt: Total prompt/input tokens used
                - total_tokens_completion: Total completion/output tokens used
                - total_tokens: Total tokens (prompt + completion)
                - calls_per_second: Current call rate (5s window)
                - items_per_second: Current item rate (5s window)
                - by_type: Breakdown by call type
                - by_step: Breakdown by pipeline step (includes tokens)
                - by_model: Breakdown by model (includes tokens)
                - rate_by_step: Current rates per step
                - rate_by_model: Current rates per model
                - duration_seconds: Time since configure() was called
        """
        with self._lock:
            now = time.time()
            self._prune_old_calls(now)

            duration = now - self._start_time if self._start_time else 0

            return {
                "total_calls": self._total_calls,
                "total_items": self._total_items,
                "total_tokens_prompt": self._total_tokens_prompt,
                "total_tokens_completion": self._total_tokens_completion,
                "total_tokens": self._total_tokens_prompt + self._total_tokens_completion,
                "calls_per_second": self.get_calls_per_second(),
                "items_per_second": self.get_items_per_second(),
                "by_type": {
                    call_type: {
                        "calls": self._totals_by_type.get(call_type, 0),
                        "items": self._items_by_type.get(call_type, 0),
                    }
                    for call_type in set(self._totals_by_type.keys())
                    | set(self._items_by_type.keys())
                },
                "by_step": {
                    step: {
                        "calls": self._totals_by_step.get(step, 0),
                        "items": self._items_by_step.get(step, 0),
                        "tokens_prompt": self._tokens_prompt_by_step.get(step, 0),
                        "tokens_completion": self._tokens_completion_by_step.get(step, 0),
                        "tokens_total": (
                            self._tokens_prompt_by_step.get(step, 0)
                            + self._tokens_completion_by_step.get(step, 0)
                        ),
                    }
                    for step in set(self._totals_by_step.keys()) | set(self._items_by_step.keys())
                },
                "by_model": {
                    model: {
                        "calls": self._totals_by_model.get(model, 0),
                        "items": self._items_by_model.get(model, 0),
                        "tokens_prompt": self._tokens_prompt_by_model.get(model, 0),
                        "tokens_completion": self._tokens_completion_by_model.get(model, 0),
                        "tokens_total": (
                            self._tokens_prompt_by_model.get(model, 0)
                            + self._tokens_completion_by_model.get(model, 0)
                        ),
                    }
                    for model in set(self._totals_by_model.keys())
                    | set(self._items_by_model.keys())
                },
                "rate_by_step": self.get_rate_by_step(),
                "rate_by_model": self.get_rate_by_model(),
                "duration_seconds": duration,
                "workflow_id": self._workflow_id,
            }

    def get_timeline(self, bucket_seconds: float = 1.0) -> List[TimelineBucket]:
        """
        Get time-bucketed view of calls for visualization.

        Args:
            bucket_seconds: Size of each time bucket in seconds (default 1s)

        Returns:
            List of TimelineBucket objects, one per time bucket
        """
        with self._lock:
            if not self._calls:
                return []

            now = time.time()
            self._prune_old_calls(now)

            if not self._calls:
                return []

            # Find time range
            min_time = self._calls[0].timestamp
            max_time = self._calls[-1].timestamp

            # Create buckets
            buckets: List[TimelineBucket] = []
            bucket_start = min_time

            while bucket_start <= max_time:
                bucket_end = bucket_start + bucket_seconds
                bucket = TimelineBucket(start_time=bucket_start, end_time=bucket_end)

                # Aggregate calls in this bucket
                for call in self._calls:
                    if bucket_start <= call.timestamp < bucket_end:
                        bucket.total_calls += 1
                        bucket.total_items += call.count

                        bucket.by_type[call.call_type] = bucket.by_type.get(call.call_type, 0) + 1
                        if call.step_name:
                            bucket.by_step[call.step_name] = (
                                bucket.by_step.get(call.step_name, 0) + 1
                            )
                        bucket.by_model[call.model] = bucket.by_model.get(call.model, 0) + 1

                buckets.append(bucket)
                bucket_start = bucket_end

            return buckets

    def print_summary(self) -> None:
        """Print a human-readable summary of LLM usage to console."""
        stats = self.get_stats()

        print("\n" + "=" * 60)
        print("LLM Call Tracker Summary")
        print("=" * 60)

        if stats["workflow_id"]:
            print(f"Workflow ID: {stats['workflow_id']}")

        duration = stats["duration_seconds"]
        if duration > 0:
            print(f"Duration: {duration:.1f}s")

        print(f"\nTotal Calls: {stats['total_calls']}")
        print(f"Total Items: {stats['total_items']}")
        if stats["total_tokens"] > 0:
            print(
                f"Total Tokens: {stats['total_tokens']:,} "
                f"(prompt: {stats['total_tokens_prompt']:,}, "
                f"completion: {stats['total_tokens_completion']:,})"
            )
        print(
            f"Current Rate: {stats['calls_per_second']:.2f} calls/sec, "
            f"{stats['items_per_second']:.2f} items/sec"
        )

        if stats["by_type"]:
            print("\nBy Type:")
            for call_type, data in stats["by_type"].items():
                print(f"  {call_type}: {data['calls']} calls, {data['items']} items")

        if stats["by_step"]:
            print("\nBy Step:")
            for step, data in stats["by_step"].items():
                rate = stats["rate_by_step"].get(step, {})
                tokens_str = ""
                if data.get("tokens_total", 0) > 0:
                    tokens_str = f", {data['tokens_total']:,} tokens"
                print(
                    f"  {step}: {data['calls']} calls, {data['items']} items{tokens_str} "
                    f"({rate.get('calls_per_sec', 0):.2f}/sec)"
                )

        if stats["by_model"]:
            print("\nBy Model:")
            for model, data in stats["by_model"].items():
                rate = stats["rate_by_model"].get(model, {})
                tokens_str = ""
                if data.get("tokens_total", 0) > 0:
                    tokens_str = f", {data['tokens_total']:,} tokens"
                print(
                    f"  {model}: {data['calls']} calls, {data['items']} items{tokens_str} "
                    f"({rate.get('calls_per_sec', 0):.2f}/sec)"
                )

        print("=" * 60 + "\n")


# Global singleton instance
llm_tracker = LLMTracker()


# Convenience functions for common use cases
def track_embedding_call(
    model: str,
    count: int,
    step_name: Optional[str] = None,
    duration_ms: Optional[float] = None,
) -> None:
    """
    Track an embedding API call.

    Args:
        model: Model identifier (e.g., "text-embedding-3-small")
        count: Number of texts embedded
        step_name: Optional pipeline step name
        duration_ms: Optional call duration in milliseconds
    """
    llm_tracker.track_call(
        call_type="embedding",
        model=model,
        count=count,
        step_name=step_name,
        duration_ms=duration_ms,
    )


def track_llm_call(
    model: str,
    step_name: Optional[str] = None,
    duration_ms: Optional[float] = None,
    tokens_prompt: Optional[int] = None,
    tokens_completion: Optional[int] = None,
) -> None:
    """
    Track an LLM API call.

    Args:
        model: Model identifier (e.g., "gpt-4o-mini")
        step_name: Optional pipeline step name
        duration_ms: Optional call duration in milliseconds
        tokens_prompt: Optional number of input/prompt tokens used
        tokens_completion: Optional number of output/completion tokens used
    """
    llm_tracker.track_call(
        call_type="llm",
        model=model,
        count=1,
        step_name=step_name,
        duration_ms=duration_ms,
        tokens_prompt=tokens_prompt,
        tokens_completion=tokens_completion,
    )
