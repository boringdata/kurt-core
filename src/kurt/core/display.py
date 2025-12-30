"""
Display utilities for model execution progress.

Provides a simple API for displaying model execution progress,
with DBOS streaming integration for CLI consumption.
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict

from rich.console import Console
from rich.text import Text

from .dbos_integration import get_dbos_writer

logger = logging.getLogger(__name__)

# Shared console instance for consistent output
_console = Console()


def _format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}m {secs:.1f}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def _get_timestamp() -> str:
    """Get current timestamp in HH:MM:SS format."""
    return datetime.now().strftime("%H:%M:%S")


class Display:
    """
    Display manager for model execution progress with DBOS streaming.

    This provides both console output and DBOS event streaming for
    real-time progress updates in the CLI.

    Supports parallel step execution - multiple steps can be active simultaneously.

    Output format:
        [HH:MM:SS] ▶ model.name: Description
        [HH:MM:SS] ✓ model.name (2.5s)
    """

    def __init__(self):
        """Initialize display manager."""
        # Track multiple concurrent steps: {step_name: {"context": {}, "start_time": float}}
        self.active_steps: Dict[str, Dict[str, Any]] = {}
        self.dbos_writer = get_dbos_writer()

    def start_step(self, step_name: str, description: str = "") -> None:
        """
        Start a new step in the display.

        Args:
            step_name: Name of the step
            description: Optional description of what the step does
        """
        # Track this step in active_steps dict (supports parallel execution)
        self.active_steps[step_name] = {
            "context": {"description": description},
            "start_time": time.time(),
        }

        # Build Rich text with colors
        timestamp = _get_timestamp()
        text = Text()
        text.append(f"[{timestamp}] ", style="dim")
        text.append("▶ ", style="bold blue")
        text.append(step_name, style="bold cyan")
        if description:
            text.append(f": {description}", style="dim")

        logger.info(f"▶ {step_name}: {description}")
        _console.print(text)

        # Stream to DBOS
        self.dbos_writer.write_model_started(step_name, description)

    def update(self, step_name: str = None, updates: Dict[str, Any] = None) -> None:
        """
        Update a step's progress.

        Args:
            step_name: Name of step to update (uses first active step if None)
            updates: Dictionary of progress updates
        """
        if updates is None:
            updates = {}

        # Find the step to update
        if step_name is None:
            if not self.active_steps:
                return
            step_name = next(iter(self.active_steps))

        if step_name not in self.active_steps:
            return

        # Update context
        self.active_steps[step_name]["context"].update(updates)

        # Log updates
        logger.debug(
            f"Progress update for {step_name}",
            extra={"step": step_name, **updates},
        )

        # Stream progress to DBOS if we have current/total
        if "current" in updates and "total" in updates:
            message = updates.get("message", "")
            self.dbos_writer.write_model_progress(
                step_name, updates["current"], updates["total"], message
            )

    def end_step(self, step_name: str, summary: Dict[str, Any]) -> None:
        """
        End a step and display summary.

        Args:
            step_name: Name of the step to end
            summary: Summary information to display
        """
        # Get step info from active_steps
        step_info = self.active_steps.get(step_name)
        if step_info is None:
            logger.debug(f"Ending step {step_name} that was not tracked (may be expected)")

        # Calculate execution time from tracked start time
        exec_time = None
        if step_info and step_info.get("start_time"):
            exec_time = time.time() - step_info["start_time"]

        # Use provided execution time if available, otherwise use calculated
        exec_time_str = summary.get("execution_time")
        if exec_time_str:
            try:
                exec_time = float(exec_time_str.rstrip("s"))
            except (ValueError, AttributeError):
                pass

        # Determine status and styling
        status = summary.get("status", "completed")
        timestamp = _get_timestamp()

        text = Text()
        text.append(f"[{timestamp}] ", style="dim")

        if status == "completed":
            text.append("✓ ", style="bold green")
            text.append(step_name, style="green")
        elif status == "failed":
            text.append("✗ ", style="bold red")
            text.append(step_name, style="red")
        else:
            text.append("? ", style="bold yellow")
            text.append(step_name, style="yellow")

        # Add execution time
        if exec_time is not None:
            text.append(f" ({_format_duration(exec_time)})", style="dim")

        # Add stats summary if available (skip internal keys, show all others)
        stats_parts = []
        internal_keys = {"status", "rows_written", "execution_time", "error"}
        for key, value in summary.items():
            if key not in internal_keys and isinstance(value, (int, float)) and value:
                stats_parts.append(f"{value} {key}")
        if stats_parts:
            text.append(f" [{', '.join(stats_parts)}]", style="dim cyan")

        # Add error if failed
        if status == "failed" and "error" in summary:
            text.append(f" - {summary['error']}", style="dim red")

        logger.info(f"{status}: {step_name}")
        _console.print(text)

        # Stream to DBOS
        if status == "completed":
            rows_written = summary.get("rows_written", 0)
            self.dbos_writer.write_model_completed(step_name, rows_written, exec_time or 0.0)
        elif status == "failed":
            error = summary.get("error", "Unknown error")
            self.dbos_writer.write_model_failed(step_name, error)

        # Remove from active steps
        if step_name in self.active_steps:
            del self.active_steps[step_name]


# Global display instance
display = Display()


def print_warning(message: str) -> None:
    """Print a warning message with yellow styling."""
    text = Text()
    text.append("         ", style="dim")  # Indent to align with timestamps
    text.append("⚠ ", style="bold yellow")
    text.append(message, style="yellow")
    _console.print(text)


def print_info(message: str) -> None:
    """Print an info message."""
    text = Text()
    text.append("         ", style="dim")  # Indent to align with timestamps
    text.append(message, style="dim")
    _console.print(text)


def print_dim(message: str) -> None:
    """Print a dim/muted message."""
    text = Text()
    text.append("         ", style="dim")  # Indent to align with timestamps
    text.append(message, style="dim")
    _console.print(text)


def print_inline_table(
    items: list[dict],
    columns: list[str],
    max_items: int = 10,
    cli_command: str = None,
    column_widths: dict[str, int] = None,
) -> None:
    """Print an inline summary table of items.

    Args:
        items: List of dicts with data to display
        columns: List of column keys to show
        max_items: Maximum items to show before truncating (default 10)
        cli_command: CLI command to show for getting full details (if truncated)
        column_widths: Optional dict of column name -> max width (default 50 for first col, 20 for others)
    """
    if not items:
        return

    from rich import box
    from rich.table import Table

    # Default column widths: first column wider (for statements), others narrower
    if column_widths is None:
        column_widths = {}
    default_first_width = 60
    default_other_width = 15

    # Truncate if needed
    show_truncation = len(items) > max_items
    display_items = items[:max_items]

    # Build table with nice box style
    table = Table(
        show_header=True,
        header_style="bold dim",
        box=box.SIMPLE,
        padding=(0, 1),
        expand=False,
    )

    for i, col in enumerate(columns):
        width = column_widths.get(col, default_first_width if i == 0 else default_other_width)
        table.add_column(
            col.replace("_", " ").title(),
            style="dim" if i > 0 else "",
            max_width=width,
            overflow="ellipsis",
        )

    for item in display_items:
        row = []
        for i, col in enumerate(columns):
            val = item.get(col, "")
            row.append(str(val) if val else "-")
        table.add_row(*row)

    # Print with indent
    _console.print("         ", end="")  # Indent to align with timestamps
    _console.print(table)

    # Show truncation message with CLI command
    if show_truncation and cli_command:
        text = Text()
        text.append("         ", style="dim")
        text.append(f"... and {len(items) - max_items} more. ", style="dim")
        text.append("Run: ", style="dim")
        text.append(cli_command, style="cyan")
        _console.print(text)


def print_progress(current: int, total: int, prefix: str = "") -> None:
    """
    Print a progress update. Only prints on completion to avoid terminal issues.

    Args:
        current: Current progress count
        total: Total items to process
        prefix: Optional prefix text
    """
    # Only print when complete to avoid terminal buffering issues
    # The progress bar is shown at the end with the final count
    if current >= total:
        text = Text()
        text.append("         ", style="dim")  # Indent to align with timestamps
        text.append(prefix, style="dim")
        text.append("━" * 30, style="green")
        text.append("╸", style="green")
        text.append(f" {current}/{total}", style="dim")
        text.append(" (100%)", style="dim green")
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
            import threading

            cls._instance = super().__new__(cls)
            cls._lock = threading.RLock()  # Use RLock to allow nested locking
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        from collections import deque

        from rich.console import Console
        from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn

        self.console = Console()
        self._trackers: Dict[
            str, Dict[str, Any]
        ] = {}  # tracker_id -> {task_id, description, total}
        self._log_buffer: deque = deque(maxlen=5)  # Shared log buffer
        self._live = None
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
        from rich.console import Group

        parts = [self._progress]

        # Add shared log lines below progress bars
        for line in self._log_buffer:
            parts.append(line)

        return Group(*parts)

    def _ensure_live_started(self):
        """Start the shared live display if not already started."""
        from rich.live import Live

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
            # Clear the log buffer for next use
            self._log_buffer.clear()

    def register_tracker(self, tracker_id: str, description: str, total: int) -> int:
        """Register a new progress tracker and return its task_id."""
        with self._lock:
            self._ensure_live_started()

            task_id = self._progress.add_task(description, total=total)
            self._trackers[tracker_id] = {
                "task_id": task_id,
                "description": description,
                "total": total,
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
            self._progress.update(task_id, completed=completed)

            if self._live:
                self._live.update(self._render())

    def add_log(self, tracker_id: str, message: str, style: str = "dim") -> None:
        """Add a log message to the shared buffer with step name prefix."""
        from rich.text import Text

        with self._lock:
            # Get the step name from the tracker
            step_name = ""
            if tracker_id in self._trackers:
                desc = self._trackers[tracker_id]["description"]
                # Use short name (last part after colon or the whole thing)
                step_name = desc.split(":")[-1].strip() if ":" in desc else desc

            # Format: "    [step_name] message"
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
                # Hide the completed task
                self._progress.update(task_id, visible=False)
                del self._trackers[tracker_id]

            self._maybe_stop_live()

    def is_active(self) -> bool:
        """Check if any tracker is active."""
        with self._lock:
            return len(self._trackers) > 0


# Global concurrent progress manager
_concurrent_manager = None


def get_concurrent_manager() -> ConcurrentProgressManager:
    """Get or create the global concurrent progress manager."""
    global _concurrent_manager
    if _concurrent_manager is None:
        _concurrent_manager = ConcurrentProgressManager()
    return _concurrent_manager


class LiveProgressTracker:
    """
    Live progress tracker with Rich Live display.

    Shows a progress bar and scrolling log of completed items with
    specialized methods for success/skip/error messages.

    When multiple trackers are active concurrently, they coordinate through
    ConcurrentProgressManager to share a single Live display.
    """

    def __init__(self, description: str = "Processing", total: int = 0, max_log_lines: int = 5):
        """
        Initialize progress tracker.

        Args:
            description: Task description
            total: Total number of items
            max_log_lines: Maximum log lines to show
        """
        import uuid
        from collections import deque

        from rich.console import Console
        from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn

        self.description = description
        self.total = total
        self.max_log_lines = max_log_lines
        self.log_buffer = deque(maxlen=max_log_lines)
        self.console = Console()

        # Unique ID for this tracker
        self._tracker_id = str(uuid.uuid4())

        self._progress = Progress(
            TextColumn("  {task.description}"),
            BarColumn(bar_width=30),
            MofNCompleteColumn(),
            console=self.console,
        )
        self._task_id = None
        self._live = None
        self._started = False

        # Check if we should use concurrent mode
        self._use_concurrent = False
        self._manager = None

    def _render(self):
        """Render progress bar + log lines."""
        from rich.console import Group

        parts = [self._progress]

        # Add log lines (already formatted with Rich markup)
        for line in self.log_buffer:
            parts.append(line)

        return Group(*parts)

    def start(self) -> None:
        """Start the live display."""
        if self._started:
            return

        # Always use the shared concurrent manager for consistent display
        self._manager = get_concurrent_manager()
        self._use_concurrent = True
        self._task_id = self._manager.register_tracker(
            self._tracker_id, self.description, self.total
        )
        self._started = True

    def update(self, completed: int, message: str = None) -> None:
        """Update progress and optionally add a log message."""
        if not self._started:
            return

        self._manager.update_tracker(self._tracker_id, completed)
        if message:
            self._manager.add_log(self._tracker_id, message)

    def _add_log(self, message: str, style: str = "dim") -> None:
        """Add a formatted log message to the buffer."""
        from rich.text import Text

        self.log_buffer.append(Text(f"    {message}", style=style))

    def log(self, message: str, style: str = "dim") -> None:
        """Add a log message without updating progress."""
        if not self._started:
            return

        self._manager.add_log(self._tracker_id, message, style)

    def log_success(
        self,
        item_id: str,
        title: str = "",
        elapsed: float = None,
        counter: tuple[int, int] = None,
    ) -> None:
        """
        Log successful operation.

        Args:
            item_id: Item identifier (will be truncated to 8 chars)
            title: Item title (optional, will be truncated to 50 chars)
            elapsed: Elapsed time in seconds
            counter: Tuple of (current, total) for progress counter
        """
        short_id = item_id[:8] if len(item_id) > 8 else item_id
        short_title = (title[:47] + "...") if len(title) > 50 else title

        counter_prefix = f"{counter[0]}/{counter[1]} " if counter else ""

        if elapsed:
            msg = f"{counter_prefix}✓ [{short_id}] {short_title} ({elapsed:.1f}s)"
        elif short_title:
            msg = f"{counter_prefix}✓ [{short_id}] {short_title}"
        else:
            msg = f"{counter_prefix}✓ {short_id}"

        self.log(msg, style="dim green")

    def log_skip(
        self,
        item_id: str,
        title: str = "",
        reason: str = "unchanged",
        counter: tuple[int, int] = None,
    ) -> None:
        """
        Log skipped operation.

        Args:
            item_id: Item identifier
            title: Item title (optional)
            reason: Skip reason
            counter: Tuple of (current, total)
        """
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
        error: str,
        counter: tuple[int, int] = None,
    ) -> None:
        """
        Log error.

        Args:
            item_id: Item identifier
            error: Error message
            counter: Tuple of (current, total)
        """
        short_id = item_id[:8] if len(item_id) > 8 else item_id
        short_error = (error[:60] + "...") if len(error) > 60 else error

        counter_prefix = f"{counter[0]}/{counter[1]} " if counter else ""
        msg = f"{counter_prefix}✗ [{short_id}] {short_error}"

        self.log(msg, style="dim red")

    def log_info(self, message: str) -> None:
        """Log informational message."""
        self.log(f"ℹ {message}", style="dim cyan")

    def stop(self) -> None:
        """Stop the live display."""
        if not self._started:
            return

        # Unregister from manager (this will stop live display if last tracker)
        if self._manager:
            self._manager.unregister_tracker(self._tracker_id)

        self._started = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


def make_progress_callback(prefix: str = "", show_items: bool = True) -> callable:
    """
    Create a progress callback for run_batch_sync with live display.

    Shows a live progress bar with per-item status. Items are shown during
    execution and cleared when complete, leaving just a summary line with elapsed time.

    Args:
        prefix: Description text for the progress bar
        show_items: Whether to show per-item status messages (default: True)

    Returns:
        Callback function(completed, total, result)
    """
    import time

    tracker = None
    success_count = 0
    error_count = 0
    skip_count = 0
    start_time = None
    last_item_time = None

    def _get_item_id(payload: dict, fallback_index: int) -> str:
        """Extract a meaningful item identifier from payload."""
        # Try entity name first (for entity resolution/clustering)
        if payload.get("entity_name"):
            name = payload["entity_name"]
            return name[:20] + "..." if len(name) > 20 else name

        # Try group_entities (for similarity search results)
        if payload.get("group_entities") and len(payload["group_entities"]) > 0:
            name = payload["group_entities"][0].get("name", "")
            if name:
                return name[:20] + "..." if len(name) > 20 else name

        # Try claim statement (for claim clustering)
        if payload.get("statement"):
            stmt = payload["statement"]
            return stmt[:25] + "..." if len(stmt) > 25 else stmt

        # Try cluster_claims (for claim similarity search)
        if payload.get("cluster_claims") and len(payload["cluster_claims"]) > 0:
            stmt = payload["cluster_claims"][0].get("statement", "")
            if stmt:
                return stmt[:25] + "..." if len(stmt) > 25 else stmt

        # Try section extraction format: doc_id:section N/total
        if payload.get("section_number") is not None and payload.get("document_id"):
            doc_id = str(payload["document_id"])[:6]
            section_num = payload["section_number"]
            total = payload.get("total_sections", "?")
            return f"{doc_id}:§{section_num}/{total}"

        # Try section_id with doc prefix (for section-based operations)
        if payload.get("section_id"):
            section_id = str(payload["section_id"])[:8]
            doc_id = str(payload.get("document_id", ""))[:6]
            if doc_id:
                return f"{doc_id}:{section_id}"
            return section_id

        # Try document_id (for document-based operations)
        if payload.get("document_id"):
            return str(payload["document_id"])[:8]

        # Try generic id
        if payload.get("id"):
            return str(payload["id"])[:8]

        # Fallback to index
        return f"#{fallback_index}"

    def callback(completed: int, total: int, result: Any) -> None:
        nonlocal tracker, success_count, error_count, skip_count, start_time, last_item_time

        # Create tracker on first call (including start event with completed=0)
        if tracker is None:
            start_time = time.time()
            last_item_time = start_time
            tracker = LiveProgressTracker(
                description=prefix.strip(": ") or "Processing",
                total=total,
                max_log_lines=5,
            )
            tracker.start()

        # Update progress bar
        tracker.update(completed)

        # Log item status (skip if result is None - start event)
        if result is not None:
            payload = getattr(result, "payload", {}) or {}

            # Calculate time since last item
            now = time.time()
            item_elapsed = now - last_item_time
            last_item_time = now
            time_suffix = f" ({item_elapsed:.1f}s)" if item_elapsed >= 0.1 else ""

            # Build meaningful item identifier
            item_id = _get_item_id(payload, completed)

            if payload.get("skip"):
                skip_count += 1
                if show_items:
                    tracker.log(f"{completed}/{total} ○ {item_id}{time_suffix}", style="dim yellow")
            elif getattr(result, "error", None):
                error_count += 1
                error_msg = str(getattr(result, "error", "Unknown error"))[:40]
                tracker.log(
                    f"{completed}/{total} ✗ {item_id}: {error_msg}{time_suffix}", style="dim red"
                )
            else:
                success_count += 1
                if show_items:
                    tracker.log(f"{completed}/{total} ✓ {item_id}{time_suffix}", style="dim green")

        # Stop when complete - live display clears, then print summary
        if completed >= total:
            # Calculate elapsed time before stopping (need tracker for console)
            elapsed = time.time() - start_time if start_time else 0
            if elapsed >= 60:
                time_str = f"{elapsed / 60:.1f}m"
            else:
                time_str = f"{elapsed:.1f}s"

            # Build summary line
            desc = prefix.strip(": ") or "Processing"
            parts = []
            if success_count > 0:
                parts.append(f"{success_count} succeeded")
            if skip_count > 0:
                parts.append(f"{skip_count} skipped")
            if error_count > 0:
                parts.append(f"{error_count} failed")

            if parts:
                summary = f"  {desc}: {', '.join(parts)} ({time_str})"
            else:
                summary = f"  {desc}: {total}/{total} completed ({time_str})"

            # Get manager reference before stopping
            manager = tracker._manager

            # Stop this tracker (unregisters from manager)
            tracker.stop()

            # Print summary using Rich console to coordinate with any remaining live displays
            if manager and manager.is_active():
                # Other trackers still running - use manager's console
                manager.console.print(summary)
            else:
                # No other trackers - safe to print directly
                print(summary)

    return callback


def display_summary(
    stats: dict,
    console=None,
    title: str = "Summary",
    show_time: bool = True,
) -> None:
    """
    Display a standardized command summary.

    Args:
        stats: Dictionary with stat keys and values. Special keys:
            - elapsed: Time in seconds (shown as "Time elapsed: Xs")
            - Any key with value > 0 shown as "✓ Key: value"
            - Keys ending with "_failed" or "_errors" shown in red with ✗
            - Keys ending with "_skipped" shown with ○
        console: Rich Console instance (uses global if None)
        title: Summary title (default: "Summary")
        show_time: Whether to show elapsed time if present

    Usage:
        display_summary({
            "fetched": 10,
            "indexed": 8,
            "skipped": 2,
            "failed": 0,
            "elapsed": 12.5,
        })
    """
    c = console or _console

    c.print()
    c.print(f"[bold]{title}[/bold]")

    elapsed = stats.pop("elapsed", None)

    for key, value in stats.items():
        if value is None or (isinstance(value, (int, float)) and value == 0):
            continue

        # Format the key for display
        display_key = key.replace("_", " ").title()

        # Choose icon and style based on key name
        if "failed" in key.lower() or "error" in key.lower():
            c.print(f"  [red]✗ {display_key}: {value}[/red]")
        elif "skipped" in key.lower():
            c.print(f"  ○ {display_key}: {value}")
        else:
            c.print(f"  ✓ {display_key}: {value}")

    # Show elapsed time
    if show_time and elapsed is not None:
        c.print(f"  [dim]ℹ Time elapsed: {elapsed:.1f}s[/dim]")


def display_knowledge_graph(kg: dict, console=None, title: str = "Knowledge Graph"):
    """Display knowledge graph using inline tables.

    Args:
        kg: Knowledge graph data with stats, entities, and relationships
        console: Rich Console instance for output (uses global if None)
        title: Title to display (default: "Knowledge Graph")
    """
    if not kg:
        return

    c = console or _console
    stats = kg.get("stats", {})

    # Header
    entity_count = stats.get("entity_count", 0)
    rel_count = stats.get("relationship_count", 0)
    claim_count = stats.get("claim_count", len(kg.get("claims", [])))

    c.print(f"\n[bold cyan]{title}[/bold cyan]")
    c.print(f"[dim]{entity_count} entities, {rel_count} relationships, {claim_count} claims[/dim]")

    # Claims table
    if kg.get("claims"):
        c.print("\n[bold]Claims[/bold]")
        claims_data = [
            {
                "statement": claim["statement"],
                "type": claim["claim_type"].replace("ClaimType.", "").replace("DEFINITION", "DEF"),
                "confidence": f"{claim['confidence']:.2f}",
            }
            for claim in kg["claims"]
        ]
        print_inline_table(
            claims_data,
            columns=["statement", "type", "confidence"],
            max_items=10,
            column_widths={"statement": 70, "type": 12, "confidence": 8},
        )

    # Entities table
    if kg.get("entities"):
        c.print("\n[bold]Entities[/bold]")
        entities_data = [
            {
                "name": entity["name"],
                "type": entity["type"],
                "confidence": f"{entity['confidence']:.2f}",
                "mentions": entity.get("mentions_in_doc", 0),
            }
            for entity in kg["entities"]
        ]
        print_inline_table(
            entities_data,
            columns=["name", "type", "confidence", "mentions"],
            max_items=10,
            column_widths={"name": 30, "type": 15, "confidence": 8, "mentions": 8},
        )

    # Relationships table
    if kg.get("relationships"):
        c.print("\n[bold]Relationships[/bold]")
        rels_data = [
            {
                "source": rel["source_entity"],
                "relationship": rel.get("relationship_type", "related_to"),
                "target": rel["target_entity"],
                "confidence": f"{rel['confidence']:.2f}",
            }
            for rel in kg["relationships"]
        ]
        print_inline_table(
            rels_data,
            columns=["source", "relationship", "target", "confidence"],
            max_items=10,
            column_widths={"source": 25, "relationship": 20, "target": 25, "confidence": 8},
        )
