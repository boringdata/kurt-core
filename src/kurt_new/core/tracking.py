from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from .hooks import StepHooks

try:
    from dbos import DBOS

    HAS_DBOS = True
except Exception:
    HAS_DBOS = False


def _safe_set_event(key: str, value: Any) -> None:
    if not HAS_DBOS:
        return
    try:
        DBOS.set_event(key, value)
    except Exception:
        return


def _safe_write_stream(key: str, payload: dict[str, Any]) -> None:
    if not HAS_DBOS:
        return
    try:
        DBOS.write_stream(key, payload)
    except Exception:
        return


@dataclass
class WorkflowTracker:
    """DBOS-based tracking using events and streams only."""

    def start_step(
        self,
        step_name: str,
        *,
        step_type: str = "step",
        total: int = 0,
    ) -> None:
        _safe_set_event("current_step", step_name)
        _safe_set_event("stage", step_name)
        _safe_set_event("stage_total", total)
        _safe_set_event("stage_status", "running")
        _safe_write_stream(
            "progress",
            {
                "type": step_type,
                "step": step_name,
                "total": total,
                "status": "start",
                "timestamp": time.time(),
            },
        )

    def update_progress(self, current: int, *, step_name: str | None = None) -> None:
        _safe_set_event("stage_current", current)
        if step_name:
            _safe_write_stream(
                "progress",
                {
                    "step": step_name,
                    "current": current,
                    "status": "progress",
                    "timestamp": time.time(),
                },
            )

    def end_step(
        self, step_name: str, *, status: str = "success", error: str | None = None
    ) -> None:
        _safe_set_event("stage_status", status)
        if error:
            _safe_set_event("stage_error", error)
        _safe_write_stream(
            "progress",
            {
                "step": step_name,
                "status": status,
                "error": error,
                "timestamp": time.time(),
            },
        )

    def log(
        self,
        message: str,
        *,
        level: str = "info",
        step_name: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        _safe_write_stream(
            "logs",
            {
                "step": step_name,
                "level": level,
                "message": message,
                "metadata": metadata,
                "timestamp": time.time(),
            },
        )


class TrackingHooks(StepHooks):
    """Step hooks that emit DBOS events and streams."""

    def __init__(
        self,
        tracker: WorkflowTracker | None = None,
        *,
        step_type: str = "llm_step",
    ) -> None:
        self._tracker = tracker or WorkflowTracker()
        self._step_type = step_type
        self._progress: dict[str, int] = {}

    def on_start(self, *, step_name: str, total: int, concurrency: int) -> None:
        self._tracker.start_step(step_name, step_type=self._step_type, total=total)
        self._tracker.log(
            f"Processing {total} rows (concurrency={concurrency})",
            step_name=step_name,
        )

    def on_row_success(
        self,
        *,
        step_name: str,
        idx: int,
        total: int,
        latency_ms: int,
        prompt: str,
        tokens_in: int,
        tokens_out: int,
        cost: float,
        result: dict[str, Any],
    ) -> None:
        _safe_write_stream(
            "progress",
            {
                "step": step_name,
                "idx": idx,
                "total": total,
                "status": "success",
                "latency_ms": latency_ms,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost": cost,
                "timestamp": time.time(),
            },
        )

    def on_row_error(
        self,
        *,
        step_name: str,
        idx: int,
        total: int,
        latency_ms: int,
        prompt: str,
        tokens_in: int,
        tokens_out: int,
        cost: float,
        error: Exception,
    ) -> None:
        _safe_write_stream(
            "progress",
            {
                "step": step_name,
                "idx": idx,
                "total": total,
                "status": "error",
                "latency_ms": latency_ms,
                "error": str(error),
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost": cost,
                "timestamp": time.time(),
            },
        )

    def on_result(
        self,
        *,
        step_name: str,
        idx: int,
        total: int,
        status: str,
        error: str | None,
    ) -> None:
        current = self._progress.get(step_name, 0) + 1
        self._progress[step_name] = current
        self._tracker.update_progress(current, step_name=step_name)
        if status == "error":
            self._tracker.log(
                f"Row {idx} error: {error}",
                level="error",
                step_name=step_name,
            )

    def on_end(
        self,
        *,
        step_name: str,
        successful: int,
        total: int,
        errors: list[str],
    ) -> None:
        status = "error" if errors else "success"
        self._tracker.log(
            f"Completed: {successful}/{total} successful",
            step_name=step_name,
        )
        self._tracker.end_step(step_name, status=status, error=errors[0] if errors else None)


@contextmanager
def track_step(
    name: str,
    *,
    tracker: WorkflowTracker | None = None,
    step_type: str = "step",
    total: int = 0,
):
    """Context manager for tracking non-LLM steps."""
    tracker = tracker or WorkflowTracker()
    tracker.start_step(name, step_type=step_type, total=total)

    error: str | None = None
    try:
        yield
    except Exception as exc:
        error = str(exc)
        tracker.log(f"Error: {error}", level="error", step_name=name)
        raise
    finally:
        status = "error" if error else "success"
        tracker.end_step(name, status=status, error=error)


def update_step_progress(
    current: int,
    *,
    tracker: WorkflowTracker | None = None,
    step_name: str | None = None,
):
    tracker = tracker or WorkflowTracker()
    tracker.update_progress(current, step_name=step_name)


def step_log(
    message: str,
    *,
    tracker: WorkflowTracker | None = None,
    level: str = "info",
    step_name: str | None = None,
    metadata: dict | None = None,
):
    tracker = tracker or WorkflowTracker()
    tracker.log(message, level=level, step_name=step_name, metadata=metadata)
