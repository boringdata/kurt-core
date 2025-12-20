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


class LiveProgressTracker:
    """
    Live progress tracker with Rich Live display.

    Shows a progress bar and scrolling log of completed items with
    specialized methods for success/skip/error messages.
    """

    def __init__(self, description: str = "Processing", total: int = 0, max_log_lines: int = 5):
        """
        Initialize progress tracker.

        Args:
            description: Task description
            total: Total number of items
            max_log_lines: Maximum log lines to show
        """
        from collections import deque

        from rich.console import Console
        from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn

        self.description = description
        self.total = total
        self.max_log_lines = max_log_lines
        self.log_buffer = deque(maxlen=max_log_lines)
        self.console = Console()

        self._progress = Progress(
            TextColumn("  {task.description}"),
            BarColumn(bar_width=30),
            MofNCompleteColumn(),
            console=self.console,
        )
        self._task_id = None
        self._live = None
        self._started = False

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
        from rich.live import Live

        if not self._started:
            self._task_id = self._progress.add_task(self.description, total=self.total)
            self._live = Live(
                self._render(),
                console=self.console,
                refresh_per_second=4,
                transient=True,  # Clear when done to avoid conflicts with other output
            )
            self._live.start()
            self._started = True

    def update(self, completed: int, message: str = None) -> None:
        """Update progress and optionally add a log message."""
        if self._started and self._task_id is not None:
            self._progress.update(self._task_id, completed=completed)
            if message:
                self._add_log(message)
            if self._live:
                self._live.update(self._render())

    def _add_log(self, message: str, style: str = "dim") -> None:
        """Add a formatted log message to the buffer."""
        from rich.text import Text

        self.log_buffer.append(Text(f"    {message}", style=style))

    def log(self, message: str, style: str = "dim") -> None:
        """Add a log message without updating progress."""
        if self._started:
            self._add_log(message, style)
            if self._live:
                self._live.update(self._render())

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
        if self._started and self._live:
            self._live.stop()
            self._started = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


def make_progress_callback(prefix: str = "", show_items: bool = True) -> callable:
    """
    Create a progress callback for run_batch_sync with live display.

    Shows a live progress bar and per-item status as items complete.

    Args:
        prefix: Description text for the progress bar
        show_items: Whether to show per-item status messages

    Returns:
        Callback function(completed, total, result)
    """
    tracker = None
    success_count = 0
    error_count = 0
    skip_count = 0
    started = False

    def callback(completed: int, total: int, result: Any) -> None:
        nonlocal tracker, success_count, error_count, skip_count, started

        # Create tracker on first call (including start event with completed=0)
        if tracker is None:
            tracker = LiveProgressTracker(
                description=prefix.strip(": ") or "Processing",
                total=total,
                max_log_lines=5,
            )
            tracker.start()

        # Show start message on first call (completed=0 means start event)
        if not started:
            started = True
            tracker.log_info(f"Processing {total} items...")
            # Force display update for start message
            if tracker._live:
                tracker._live.update(tracker._render())

        # Update progress bar
        tracker._progress.update(tracker._task_id, completed=completed)

        # Log item status if enabled (skip if result is None - start event)
        if show_items and result is not None:
            # Extract identifiers from result payload
            payload = getattr(result, "payload", {}) or {}

            # Build item_id as docid-sN format
            doc_id = str(payload.get("document_id", ""))[:8]
            section_num = payload.get("section_number")

            # Debug: log payload keys if section_number is missing
            if section_num is None:
                logger.debug(f"Payload keys: {list(payload.keys())}")

            if doc_id and section_num is not None:
                item_id = f"{doc_id}-s{section_num}"
            elif doc_id:
                item_id = doc_id
            else:
                item_id = f"item-{completed}"

            title = payload.get("document_title", payload.get("title", ""))

            # Extract timing if available
            telemetry = getattr(result, "telemetry", {}) or {}
            elapsed = telemetry.get("execution_time")

            # Check for skip
            if payload.get("skip"):
                skip_count += 1
                tracker.log_skip(
                    item_id=item_id,
                    title=title,
                    reason=payload.get("skip_reason", "unchanged"),
                    counter=(completed, total),
                )
            elif getattr(result, "error", None):
                error_count += 1
                error_msg = str(getattr(result, "error", "Unknown error"))
                tracker.log_error(
                    item_id=item_id,
                    error=error_msg,
                    counter=(completed, total),
                )
            else:
                success_count += 1
                tracker.log_success(
                    item_id=item_id,
                    title=title,
                    elapsed=elapsed,
                    counter=(completed, total),
                )

        # Update display
        if tracker._live:
            tracker._live.update(tracker._render())

        # Stop when complete and print summary
        if completed >= total:
            tracker.stop()
            # Print a summary line after the live display clears
            desc = prefix.strip(": ") or "Processing"
            parts = []
            if success_count > 0:
                parts.append(f"{success_count} succeeded")
            if skip_count > 0:
                parts.append(f"{skip_count} skipped")
            if error_count > 0:
                parts.append(f"{error_count} failed")

            if parts:
                print(f"  {desc}: {', '.join(parts)}")
            else:
                print(f"  {desc}: {total}/{total} completed")

    return callback


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
