from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .hooks import StepHooks

if TYPE_CHECKING:
    from .display import PlainStepDisplay, StepDisplay

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


def _format_item_log(
    item_id: str,
    *,
    status: str,
    message: str,
    elapsed: float,
    counter: tuple[int, int] | None,
) -> tuple[str, str]:
    message = str(message or "")
    short_id = item_id[:8] if len(item_id) > 8 else item_id
    counter_prefix = f"{counter[0]}/{counter[1]} " if counter else ""

    if status == "success":
        short_title = (message[:47] + "...") if len(message) > 50 else message
        time_suffix = f" ({elapsed:.1f}s)" if elapsed >= 0.1 else ""
        if short_title:
            return f"{counter_prefix}✓ [{short_id}] {short_title}{time_suffix}", "info"
        return f"{counter_prefix}✓ {short_id}{time_suffix}", "info"

    if status == "skip":
        short_reason = (message[:47] + "...") if len(message) > 50 else message
        if short_reason:
            return f"{counter_prefix}○ [{short_id}] {short_reason} (skipped)", "info"
        return f"{counter_prefix}○ {short_id} (skipped)", "info"

    if status == "error":
        short_error = (message[:60] + "...") if len(message) > 60 else message
        if short_error:
            return f"{counter_prefix}✗ [{short_id}] {short_error}", "error"
        return f"{counter_prefix}✗ [{short_id}] error", "error"

    return f"{counter_prefix}{short_id} {message}".strip(), "info"


@dataclass
class WorkflowTracker:
    """DBOS-based tracking with optional console display."""

    _display: StepDisplay | PlainStepDisplay | None = field(default=None, init=False, repr=False)
    _current_step: str | None = field(default=None, init=False, repr=False)

    def start_step(
        self,
        step_name: str,
        *,
        step_type: str = "step",
        total: int = 0,
    ) -> None:
        # DBOS tracking
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

        # Console display if enabled
        self._current_step = step_name
        from .display import PlainStepDisplay, StepDisplay, get_display_mode, is_display_enabled

        if is_display_enabled():
            if get_display_mode() == "plain":
                self._display = PlainStepDisplay(step_name, total=total)
            else:
                self._display = StepDisplay(step_name, total=total)
            self._display.start()

    def update_progress(
        self,
        current: int,
        *,
        step_name: str | None = None,
        emit_stream: bool = True,
    ) -> None:
        # DBOS tracking
        _safe_set_event("stage_current", current)
        if step_name and emit_stream:
            _safe_write_stream(
                "progress",
                {
                    "step": step_name,
                    "current": current,
                    "status": "progress",
                    "timestamp": time.time(),
                },
            )

        # Console display
        if self._display:
            self._display.update(current)

    def log_item(
        self,
        item_id: str,
        *,
        status: str,
        message: str = "",
        elapsed: float = 0,
        counter: tuple[int, int] | None = None,
        step_name: str | None = None,
    ) -> None:
        """Log individual item progress (for batch operations)."""
        log_step = step_name or self._current_step
        log_message, level = _format_item_log(
            item_id,
            status=status,
            message=message,
            elapsed=elapsed,
            counter=counter,
        )

        _safe_write_stream(
            "logs",
            {
                "step": log_step,
                "level": level,
                "message": log_message,
                "metadata": {
                    "item_id": item_id,
                    "status": status,
                },
                "timestamp": time.time(),
            },
        )

        if self._display:
            if status == "success":
                self._display.log_success(item_id, title=message, elapsed=elapsed, counter=counter)
            elif status == "skip":
                self._display.log_skip(item_id, reason=message, counter=counter)
            elif status == "error":
                self._display.log_error(item_id, error=message, counter=counter)

    def end_step(
        self, step_name: str, *, status: str = "success", error: str | None = None
    ) -> None:
        # DBOS tracking
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

        # Console display
        if self._display:
            total = getattr(self._display, "_total", 0)
            if isinstance(total, int) and total > 0:
                self._display.update(total)
            self._display.stop()
            self._display = None
        self._current_step = None

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

        # Also log to display if enabled
        if self._display:
            style = "dim red" if level == "error" else "dim"
            self._display.log(message, style=style)


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


class QueueStepTracker:
    """Tracker for steps that process items via queue with progress updates.

    Use this for steps that process items one-by-one (e.g., fetch URLs via queue).
    Emits per-item progress events with idx for accurate progress tracking.

    Usage:
        tracker = QueueStepTracker("fetch_documents", total=len(docs))
        tracker.start("Fetching documents")

        for idx, item in enumerate(items):
            if success:
                tracker.item_success(idx, item_id, metadata={"chars": 1234})
            else:
                tracker.item_error(idx, item_id, error="Connection failed")

        tracker.end()  # Logs completion summary automatically
    """

    def __init__(self, step_name: str, total: int = 0):
        self.step_name = step_name
        self.total = total
        self._success_count = 0
        self._error_count = 0
        self._tracker = WorkflowTracker()

    def start(self, message: str | None = None) -> None:
        """Start the step with optional log message."""
        self._tracker.start_step(self.step_name, step_type="queue", total=self.total)
        if message:
            self._tracker.log(message, step_name=self.step_name)

    def item_success(
        self,
        idx: int,
        item_id: str,
        *,
        metadata: dict | None = None,
    ) -> None:
        """Record successful processing of an item."""
        self._success_count += 1
        payload: dict[str, Any] = {
            "step": self.step_name,
            "idx": idx,
            "total": self.total,
            "status": "success",
            "document_id": item_id,
            "timestamp": time.time(),
        }
        if metadata:
            payload.update(metadata)
        _safe_write_stream("progress", payload)
        message = ""
        if metadata and "content_length" in metadata:
            message = f"{metadata['content_length']} chars"
        self._tracker.log_item(
            item_id,
            status="success",
            message=message,
            counter=(idx + 1, self.total) if self.total else None,
            step_name=self.step_name,
        )
        self._tracker.update_progress(idx + 1, step_name=self.step_name, emit_stream=False)

    def item_error(
        self,
        idx: int,
        item_id: str,
        *,
        error: str,
    ) -> None:
        """Record failed processing of an item."""
        self._error_count += 1
        _safe_write_stream(
            "progress",
            {
                "step": self.step_name,
                "idx": idx,
                "total": self.total,
                "status": "error",
                "document_id": item_id,
                "error": error,
                "timestamp": time.time(),
            },
        )
        self._tracker.log_item(
            item_id,
            status="error",
            message=error,
            counter=(idx + 1, self.total) if self.total else None,
            step_name=self.step_name,
        )
        self._tracker.update_progress(idx + 1, step_name=self.step_name, emit_stream=False)

    def end(self, message: str | None = None) -> None:
        """End the step with completion summary."""
        if message is None:
            message = f"Complete: {self._success_count} ok, {self._error_count} failed"
        self._tracker.log(message, step_name=self.step_name)
        status = "error" if self._error_count > 0 and self._success_count == 0 else "success"
        self._tracker.end_step(self.step_name, status=status)


@contextmanager
def track_batch_step(name: str, *, message: str | None = None, total: int = 0):
    """Context manager for simple batch steps (no per-item progress).

    Use this for steps that process all items at once (e.g., save_content, embeddings).
    Does NOT emit per-item progress - just start/done status.

    Usage:
        with track_batch_step("save_content", message="Saving 10 documents", total=10):
            save_all_documents(docs)
        # Automatically logs completion

    For steps that process items one-by-one with progress, use QueueStepTracker instead.
    """
    tracker = WorkflowTracker()
    tracker.start_step(name, step_type="batch", total=total)
    if message:
        tracker.log(message, step_name=name)

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
    emit_stream: bool = True,
):
    tracker = tracker or WorkflowTracker()
    tracker.update_progress(current, step_name=step_name, emit_stream=emit_stream)


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


def log_item(
    item_id: str,
    *,
    status: str,
    message: str = "",
    elapsed: float = 0,
    counter: tuple[int, int] | None = None,
    step_name: str | None = None,
    tracker: WorkflowTracker | None = None,
):
    """Log individual item progress (for batch operations).

    Args:
        item_id: Unique identifier for the item
        status: One of "success", "skip", or "error"
        message: Additional message (title for success, reason for skip, error message for error)
        elapsed: Elapsed time in seconds
        counter: Tuple of (current, total) for progress counter
        tracker: WorkflowTracker instance (creates new one if None)
    """
    tracker = tracker or WorkflowTracker()
    tracker.log_item(
        item_id,
        status=status,
        message=message,
        elapsed=elapsed,
        counter=counter,
        step_name=step_name,
    )
