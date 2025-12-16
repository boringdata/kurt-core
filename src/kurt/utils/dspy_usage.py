"""Helpers for running DSPy modules with token usage tracking."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Tuple

import dspy
from dspy.utils.usage_tracker import track_usage


def _estimate_total_tokens(stats: Dict[str, Any]) -> float:
    """Best-effort estimate of total tokens from a DSPy usage entry."""
    if not stats:
        return 0.0

    if isinstance(stats.get("total_tokens"), (int, float)):
        return float(stats.get("total_tokens") or 0.0)

    # Sum of typical fields exposed by OpenAI/Anthropic clients
    total = 0.0
    for key in ["prompt_tokens", "completion_tokens", "input_tokens", "output_tokens"]:
        value = stats.get(key)
        if isinstance(value, (int, float)):
            total += float(value)
    return total


def run_with_usage(
    fn: Callable[[], Any],
    *,
    context_kwargs: Dict[str, Any] | None = None,
) -> Tuple[Any, Dict[str, Any] | None]:
    """Execute a DSPy callable while tracking token usage.

    Args:
        fn: Callable that performs the DSPy invocation and returns the model output.
        context_kwargs: Optional kwargs to pass to dspy.context (e.g., {'lm': lm}).

    Returns:
        Tuple of (result, usage_summary). usage_summary is None if no usage data was recorded.
    """
    context_kwargs = dict(context_kwargs or {})
    context_kwargs.setdefault("track_usage", True)

    with track_usage() as usage_tracker:
        start_time = time.time()
        with dspy.context(**context_kwargs):
            result = fn()
        duration = time.time() - start_time

    usage_by_lm = usage_tracker.get_total_tokens()
    if not usage_by_lm:
        return result, None

    usage_summary: Dict[str, Any] = {"models": usage_by_lm, "duration_seconds": duration}
    total_tokens = 0.0
    for stats in usage_by_lm.values():
        total_tokens += _estimate_total_tokens(stats)

    if total_tokens:
        usage_summary["total_tokens"] = total_tokens

    return result, usage_summary
