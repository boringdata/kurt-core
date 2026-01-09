"""
Display utilities for foreground workflow execution.

Provides live progress display with:
- Progress bar + scrolling log window for batch steps (total > 0)
- Scrolling log window only for non-batch steps (total = 0)

Display is automatically enabled in foreground mode and disabled in background mode.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from datetime import datetime
from typing import Any

from rich.console import Console, Group
from rich.live import Live
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn
from rich.text import Text

# Thread-local storage for display enabled flag
_display_context = threading.local()

# Shared console instance for consistent output
_console = Console()


def is_display_enabled() -> bool:
    """Check if display is enabled in current context."""
    return getattr(_display_context, "enabled", False)


def set_display_enabled(enabled: bool) -> None:
    """Set display enabled flag for current context."""
    _display_context.enabled = enabled


def _format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}m {secs:.0f}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def _get_timestamp() -> str:
    """Get current timestamp in HH:MM:SS format."""
    return datetime.now().strftime("%H:%M:%S")


def print_warning(message: str) -> None:
    """Print a warning message with yellow styling."""
    if not is_display_enabled():
        return
    text = Text()
    text.append("⚠ ", style="bold yellow")
    text.append(message, style="yellow")
    _console.print(text)


def print_info(message: str) -> None:
    """Print an info message."""
    if not is_display_enabled():
        return
    text = Text()
    text.append(message, style="dim")
    _console.print(text)


class ConcurrentProgressManager:
    """
    Singleton manager for coordinating multiple concurrent progress trackers.

    Provides a single shared Rich Live display with:
    - Multiple progress bars (one per tracker) at the top
    - A shared scrolling log box below for all events
    """

    _instance = None
    _lock = None

    def __new__(cls):
        if cls._instance is None:
            cls._lock = threading.RLock()
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.console = Console()
        self._trackers: dict[str, dict[str, Any]] = {}
        self._log_buffer: deque = deque(maxlen=5)
        self._live: Live | None = None
        self._started = False

        # Shared progress display for all trackers
        self._progress = Progress(
            TextColumn("  {task.description}"),
            BarColumn(bar_width=30),
            MofNCompleteColumn(),
            console=self.console,
        )

        self._initialized = True

    def _render(self):
        """Render all progress bars + shared log lines."""
        parts = [self._progress]

        for line in self._log_buffer:
            parts.append(line)

        return Group(*parts)

    def _ensure_live_started(self):
        """Start the shared live display if not already started."""
        if not self._started:
            self._live = Live(
                self._render(),
                console=self.console,
                refresh_per_second=4,
                transient=True,
            )
            self._live.start()
            self._started = True

    def _maybe_stop_live(self):
        """Stop live display if no active trackers remain."""
        if self._started and not self._trackers:
            if self._live:
                self._live.stop()
            self._started = False
            self._live = None
            self._log_buffer.clear()

    def register_tracker(
        self, tracker_id: str, description: str, total: int, *, show_progress_bar: bool = True
    ) -> int | None:
        """Register a new progress tracker and return its task_id."""
        with self._lock:
            self._ensure_live_started()

            task_id = None
            if show_progress_bar and total > 0:
                task_id = self._progress.add_task(description, total=total)

            self._trackers[tracker_id] = {
                "task_id": task_id,
                "description": description,
                "total": total,
                "show_progress_bar": show_progress_bar,
            }

            if self._live:
                self._live.update(self._render())

            return task_id

    def update_tracker(self, tracker_id: str, completed: int) -> None:
        """Update progress for a tracker."""
        with self._lock:
            if tracker_id not in self._trackers:
                return

            task_id = self._trackers[tracker_id]["task_id"]
            if task_id is not None:
                self._progress.update(task_id, completed=completed)

            if self._live:
                self._live.update(self._render())

    def add_log(self, tracker_id: str, message: str, style: str = "dim") -> None:
        """Add a log message to the shared buffer with step name prefix."""
        with self._lock:
            step_name = ""
            if tracker_id in self._trackers:
                desc = self._trackers[tracker_id]["description"]
                step_name = desc.split(":")[-1].strip() if ":" in desc else desc

            if step_name:
                log_text = Text()
                log_text.append(f"    [{step_name}] ", style="dim cyan")
                log_text.append(message, style=style)
                self._log_buffer.append(log_text)
            else:
                self._log_buffer.append(Text(f"    {message}", style=style))

            if self._live:
                self._live.update(self._render())

    def unregister_tracker(self, tracker_id: str) -> None:
        """Unregister a tracker when it's done."""
        with self._lock:
            if tracker_id in self._trackers:
                task_id = self._trackers[tracker_id]["task_id"]
                if task_id is not None:
                    self._progress.update(task_id, visible=False)
                del self._trackers[tracker_id]

            self._maybe_stop_live()

    def is_active(self) -> bool:
        """Check if any tracker is active."""
        with self._lock:
            return len(self._trackers) > 0


# Global concurrent progress manager
_concurrent_manager: ConcurrentProgressManager | None = None


def get_concurrent_manager() -> ConcurrentProgressManager:
    """Get or create the global concurrent progress manager."""
    global _concurrent_manager
    if _concurrent_manager is None:
        _concurrent_manager = ConcurrentProgressManager()
    return _concurrent_manager


class StepDisplay:
    """
    Display for workflow steps with progress tracking.

    When total > 0: Shows progress bar + scrolling log window
    When total = 0: Shows scrolling log window only (no progress bar)
    """

    def __init__(
        self,
        step_name: str,
        *,
        total: int = 0,
        description: str = "",
        max_log_lines: int = 5,
    ):
        self._step_name = step_name
        self._total = total
        self._description = description
        self._max_log_lines = max_log_lines
        self._tracker_id = str(uuid.uuid4())
        self._manager: ConcurrentProgressManager | None = None
        self._started = False
        self._start_time: float = 0

    def start(self) -> None:
        """Start the display."""
        if self._started or not is_display_enabled():
            return

        self._start_time = time.time()
        self._manager = get_concurrent_manager()
        self._manager.register_tracker(
            self._tracker_id,
            self._step_name,
            self._total,
            show_progress_bar=self._total > 0,
        )
        self._started = True

    def update(self, completed: int) -> None:
        """Update progress bar (only if total > 0)."""
        if not self._started or not self._manager:
            return
        self._manager.update_tracker(self._tracker_id, completed)

    def log(self, message: str, style: str = "dim") -> None:
        """Add a log message to the scrolling window."""
        if not self._started or not self._manager:
            return
        self._manager.add_log(self._tracker_id, message, style)

    def log_success(
        self,
        item_id: str,
        *,
        title: str = "",
        elapsed: float = 0,
        counter: tuple[int, int] | None = None,
    ) -> None:
        """Log successful operation."""
        short_id = item_id[:8] if len(item_id) > 8 else item_id
        short_title = (title[:47] + "...") if len(title) > 50 else title

        counter_prefix = f"{counter[0]}/{counter[1]} " if counter else ""
        time_suffix = f" ({elapsed:.1f}s)" if elapsed >= 0.1 else ""

        if short_title:
            msg = f"{counter_prefix}✓ [{short_id}] {short_title}{time_suffix}"
        else:
            msg = f"{counter_prefix}✓ {short_id}{time_suffix}"

        self.log(msg, style="dim green")

    def log_skip(
        self,
        item_id: str,
        *,
        reason: str = "unchanged",
        title: str = "",
        counter: tuple[int, int] | None = None,
    ) -> None:
        """Log skipped operation."""
        short_id = item_id[:8] if len(item_id) > 8 else item_id
        short_title = (title[:47] + "...") if len(title) > 50 else title

        counter_prefix = f"{counter[0]}/{counter[1]} " if counter else ""

        if short_title:
            msg = f"{counter_prefix}○ [{short_id}] {short_title} ({reason})"
        else:
            msg = f"{counter_prefix}○ {short_id} ({reason})"

        self.log(msg, style="dim yellow")

    def log_error(
        self,
        item_id: str,
        *,
        error: str,
        counter: tuple[int, int] | None = None,
    ) -> None:
        """Log error."""
        short_id = item_id[:8] if len(item_id) > 8 else item_id
        short_error = (error[:60] + "...") if len(error) > 60 else error

        counter_prefix = f"{counter[0]}/{counter[1]} " if counter else ""
        msg = f"{counter_prefix}✗ [{short_id}] {short_error}"

        self.log(msg, style="dim red")

    def log_info(self, message: str) -> None:
        """Log informational message."""
        self.log(f"ℹ {message}", style="dim cyan")

    def stop(self) -> None:
        """Stop the display."""
        if not self._started:
            return

        if self._manager:
            self._manager.unregister_tracker(self._tracker_id)

        self._started = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
