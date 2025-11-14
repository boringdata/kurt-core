"""Display utilities for content commands.

This module provides both interactive and static display utilities:
- LiveProgressDisplay: Interactive progress bars with live log scrolling
- create_fetch_progress_callback: Progress callbacks for batch operations
- display_knowledge_graph: Static knowledge graph formatting
- Reusable display building blocks for consistent CLI UX

REUSABLE DISPLAY BUILDING BLOCKS
---------------------------------
These functions provide a consistent UX structure across fetch, index, and map commands:

1. print_intro_block(console, messages)
   - Prints informational messages before command execution
   - Example: "Limiting to first 10 documents out of 29 found"
   - Use at the start of the command to explain what will happen

2. print_stage_header(console, stage_number, stage_name)
   - Prints a visual stage separator with number and name
   - Example: "━━━ STAGE 1: METADATA EXTRACTION ━━━"
   - Use before each major stage of processing

3. print_stage_summary(console, items)
   - Prints a compact summary after each stage completes
   - Example: "✓ Indexed: 10, ○ Skipped: 0, ✗ Failed: 0"
   - Use after each stage to show stage-level results

4. print_command_summary(console, title, items)
   - Prints a final global summary with divider
   - Example: "Summary ─── ✓ Total indexed: 10, ℹ Time elapsed: 12.3s"
   - Use at the end of the command to show overall results

5. print_divider(console, char="─", length=60)
   - Prints a divider line
   - Use for visual separation

USAGE PATTERN
-------------
1. Print intro block explaining what will be done
2. For each stage:
   a. Print stage header
   b. Run stage with LiveProgressDisplay
   c. Print stage summary
3. Print global command summary at the end

Example structure:
    print_intro_block(console, ["Indexing 10 documents..."])

    # Stage 1
    print_stage_header(console, 1, "METADATA EXTRACTION")
    with LiveProgressDisplay(console) as display:
        # ... do work ...
    print_stage_summary(console, [("✓", "Indexed", "10")])

    # Stage 2
    print_stage_header(console, 2, "ENTITY RESOLUTION")
    with LiveProgressDisplay(console) as display:
        # ... do work ...
    print_stage_summary(console, [("✓", "Entities", "42")])

    # Final summary
    print_command_summary(console, "Summary", [
        ("✓", "Total indexed", "10"),
        ("ℹ", "Time elapsed", "12.3s"),
    ])

Consolidated from _display.py and _live_display.py for cleaner organization.
"""

import time
from collections import deque

from rich.console import Console, Group
from rich.live import Live
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

# ============================================================================
# Display Building Blocks
# ============================================================================


def print_intro_block(console: Console, messages: list[str]):
    """
    Print an intro block explaining what will be done.

    Args:
        console: Rich Console instance
        messages: List of informational messages to display

    Example:
        print_intro_block(console, [
            "Limiting to first 10 documents out of 29 found",
            "Indexing 10 document(s)..."
        ])
    """
    for message in messages:
        console.print(message)


def print_stage_header(console: Console, stage_number: int, stage_name: str):
    """
    Print a consistent stage header.

    Args:
        console: Rich Console instance
        stage_number: Stage number (1, 2, 3, etc.)
        stage_name: Name of the stage (e.g., "METADATA EXTRACTION")
    """
    console.print("\n" + "━" * 60)
    console.print(f"[bold cyan]STAGE {stage_number}: {stage_name.upper()}[/bold cyan]")
    console.print("━" * 60)


def print_stage_summary(console: Console, items: list[tuple[str, str, str]]):
    """
    Print a stage summary (shown after each stage completes).

    Args:
        console: Rich Console instance
        items: List of (icon, label, value) tuples
               icon: "✓", "✗", "○", or "ℹ"
               label: Item label
               value: Item value

    Example:
        print_stage_summary(console, [
            ("✓", "Indexed", "10 documents"),
            ("○", "Skipped", "0 documents"),
            ("✗", "Failed", "0 documents"),
        ])
    """
    console.print()
    for icon, label, value in items:
        if icon == "✓":
            color = "green"
        elif icon == "✗":
            color = "red"
        elif icon == "○":
            color = "yellow"
        else:
            color = "cyan"

        console.print(f"  [{color}]{icon}[/{color}] {label}: {value}")


def print_command_summary(console: Console, title: str, items: list[tuple[str, str, str]]):
    """
    Print a global command summary (shown at the end of the command).

    Args:
        console: Rich Console instance
        title: Summary title (e.g., "Summary")
        items: List of (icon, label, value) tuples
               icon: "✓", "✗", "○", or "ℹ"
               label: Item label
               value: Item value

    Example:
        print_command_summary(console, "Summary", [
            ("✓", "Total indexed", "10 documents"),
            ("✓", "Entities created", "42 entities"),
            ("✓", "Relationships created", "89 relationships"),
            ("ℹ", "Time elapsed", "12.3s"),
        ])
    """
    console.print(f"\n[bold]{title}[/bold]")
    print_divider(console)
    for icon, label, value in items:
        if icon == "✓":
            color = "green"
        elif icon == "✗":
            color = "red"
        elif icon == "○":
            color = "yellow"
        else:
            color = "cyan"

        console.print(f"  [{color}]{icon}[/{color}] {label}: {value}")


def print_divider(console: Console, char: str = "─", length: int = 60):
    """
    Print a divider line.

    Args:
        console: Rich Console instance
        char: Character to use for divider
        length: Length of divider
    """
    console.print(f"[dim]{char * length}[/dim]")


# ============================================================================
# LiveProgressDisplay Class
# ============================================================================


class LiveProgressDisplay:
    """
    Live display with single progress bar and scrolling log window.

    Shows:
    - Top: One progress bar for current stage
    - Bottom: Scrolling log window (max 10 lines) showing recent activity
    """

    def __init__(self, console: Console = None, max_log_lines: int = 10):
        """
        Initialize live progress display.

        Args:
            console: Rich Console instance
            max_log_lines: Maximum number of log lines to show (default: 10)
        """
        self.console = console or Console()
        self.max_log_lines = max_log_lines
        self.log_buffer = deque(maxlen=max_log_lines)

        # Create progress bar
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
        )

        # Current task
        self.current_task = None
        self.live = None

    def __enter__(self):
        """Start live display."""
        self.live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=4,
            vertical_overflow="visible",
        )
        self.live.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop live display."""
        if self.live:
            self.live.__exit__(exc_type, exc_val, exc_tb)

    def _render(self):
        """Render progress bar + log lines (no frame)."""
        # Build log lines (no panel, just plain text)
        log_lines = []
        for line in self.log_buffer:
            log_lines.append(line)

        # Combine progress + log lines
        if log_lines:
            return Group(
                self.progress,
                "",  # Empty line for spacing
                *log_lines,  # Unpack log lines directly
            )
        else:
            return self.progress

    def update_display(self):
        """Update the live display."""
        if self.live:
            self.live.update(self._render())

    def start_stage(self, description: str, total: int = None):
        """
        Start a new stage with progress bar.

        Args:
            description: Stage description (e.g., "Fetching content")
            total: Total items (None for indeterminate)

        Returns:
            Task ID
        """
        if self.current_task is not None:
            # Keep previous task visible but completed
            # Don't hide it, just mark it as complete
            pass

        self.current_task = self.progress.add_task(description, total=total)
        self.update_display()
        return self.current_task

    def update_stage_total(self, total: int):
        """
        Update the total for the current stage (useful when total is not known at start).

        Args:
            total: Total items
        """
        if self.current_task is not None:
            self.progress.update(self.current_task, total=total)
            self.update_display()

    def update_progress(
        self,
        task_id: int = None,
        advance: int = None,
        completed: int = None,
        description: str = None,
    ):
        """
        Update progress bar.

        Args:
            task_id: Task ID (uses current task if None)
            advance: Increment progress by N
            completed: Set progress to N
            description: Update description
        """
        if task_id is None:
            task_id = self.current_task

        if task_id is not None:
            kwargs = {}
            if advance is not None:
                kwargs["advance"] = advance
            if completed is not None:
                kwargs["completed"] = completed
            if description is not None:
                kwargs["description"] = description

            self.progress.update(task_id, **kwargs)
            self.update_display()

    def complete_stage(self, task_id: int = None):
        """
        Complete current stage.

        Args:
            task_id: Task ID (uses current task if None)
        """
        if task_id is None:
            task_id = self.current_task

        if task_id is not None:
            self.progress.update(task_id, completed=self.progress.tasks[task_id].total or 100)
            self.update_display()

    def log(self, message: str, style: str = ""):
        """
        Add a log message to scrolling window.

        Args:
            message: Log message
            style: Rich style (e.g., "green", "red", "dim")
        """
        # Escape square brackets in message to prevent Rich from interpreting them as markup
        # Replace [ with \[ and ] with \] but only in the message content, not in style tags
        from rich.markup import escape

        escaped_message = escape(message)

        if style:
            formatted = f"[{style}]{escaped_message}[/{style}]"
        else:
            formatted = escaped_message

        self.log_buffer.append(formatted)
        self.update_display()

    def log_success(
        self,
        doc_id: str,
        title: str,
        elapsed: float = None,
        timing_breakdown: dict = None,
        operation: str = None,
        counter: tuple[int, int] = None,
    ):
        """
        Log successful operation.

        Args:
            doc_id: Document ID (short form)
            title: Document title
            elapsed: Total elapsed time
            timing_breakdown: Dict of step timings (e.g., {"load": 0.5, "llm": 2.0, "db": 0.1})
            operation: Operation type (e.g., "Fetched", "Indexed") - optional
            counter: Tuple of (current, total) for progress counter (e.g., (1, 29))
        """
        # Ensure doc_id is not empty
        if not doc_id or not doc_id.strip():
            short_id = "????????"
        else:
            short_id = doc_id[:8] if len(doc_id) > 8 else doc_id

        # Extra safety: ensure short_id is never empty (would break Rich markup)
        if not short_id or not short_id.strip():
            short_id = "????????"

        short_title = title[:50] + "..." if len(title) > 50 else title

        # Add counter prefix if provided
        counter_prefix = f"{counter[0]}/{counter[1]} " if counter else ""

        # Add operation prefix if provided
        prefix = f"{operation}: " if operation else ""

        if timing_breakdown:
            timing_str = ", ".join([f"{k}={v:.1f}s" for k, v in timing_breakdown.items()])
            msg = f"{counter_prefix}✓ {prefix}[{short_id}] {short_title} ({elapsed:.1f}s: {timing_str})"
        elif elapsed:
            msg = f"{counter_prefix}✓ {prefix}[{short_id}] {short_title} ({elapsed:.1f}s)"
        else:
            msg = f"{counter_prefix}✓ {prefix}[{short_id}] {short_title}"

        self.log(msg, style="dim green")

    def log_skip(
        self,
        doc_id: str,
        title: str,
        reason: str = "content unchanged",
        operation: str = None,
        counter: tuple[int, int] = None,
    ):
        """
        Log skipped operation.

        Args:
            doc_id: Document ID (short form)
            title: Document title
            reason: Skip reason
            operation: Operation type (e.g., "Skipped") - optional
            counter: Tuple of (current, total) for progress counter (e.g., (1, 29))
        """
        # Ensure doc_id is not empty
        if not doc_id or not doc_id.strip():
            short_id = "????????"
        else:
            short_id = doc_id[:8] if len(doc_id) > 8 else doc_id

        # Extra safety: ensure short_id is never empty (would break Rich markup)
        if not short_id or not short_id.strip():
            short_id = "????????"

        short_title = title[:50] + "..." if len(title) > 50 else title
        counter_prefix = f"{counter[0]}/{counter[1]} " if counter else ""
        prefix = f"{operation}: " if operation else ""
        msg = f"{counter_prefix}○ {prefix}[{short_id}] {short_title} ({reason})"
        self.log(msg, style="dim yellow")

    def log_error(
        self, doc_id: str, error: str, operation: str = None, counter: tuple[int, int] = None
    ):
        """
        Log error.

        Args:
            doc_id: Document ID (short form)
            error: Error message
            operation: Operation type (e.g., "Fetch failed", "Index failed") - optional
            counter: Tuple of (current, total) for progress counter (e.g., (1, 29))
        """
        # Ensure doc_id is not empty
        if not doc_id or not doc_id.strip():
            short_id = "????????"
        else:
            short_id = doc_id[:8] if len(doc_id) > 8 else doc_id

        # Extra safety: ensure short_id is never empty (would break Rich markup)
        if not short_id or not short_id.strip():
            short_id = "????????"

        counter_prefix = f"{counter[0]}/{counter[1]} " if counter else ""
        prefix = f"{operation}: " if operation else ""
        msg = f"{counter_prefix}✗ {prefix}[{short_id}] {error}"
        self.log(msg, style="dim red")

    def log_info(self, message: str):
        """
        Log informational message.

        Args:
            message: Info message
        """
        self.log(f"ℹ {message}", style="dim cyan")

    def clear_logs(self):
        """Clear the log buffer (useful between stages)."""
        self.log_buffer.clear()
        self.update_display()


def create_fetch_progress_callback(display: LiveProgressDisplay, total_docs: int):
    """
    Create progress callback for fetch + index operations.

    Args:
        display: LiveProgressDisplay instance
        total_docs: Total documents to process

    Returns:
        Callback function
    """
    indexed_count = 0
    doc_start_times = {}
    doc_step_times = {}

    def callback(
        doc_id: str, title: str, status: str, activity: str = None, skip_reason: str = None
    ):
        nonlocal indexed_count

        if activity:
            # Activity update - track timing
            if doc_id not in doc_start_times:
                doc_start_times[doc_id] = time.time()
                doc_step_times[doc_id] = {}

            doc_step_times[doc_id][activity] = time.time()

            # Update progress bar description
            display.update_progress(
                description=f"Indexing ({indexed_count}/{total_docs}): {activity}"
            )
        else:
            # Completion update
            indexed_count += 1

            # Use doc_id and title directly (no prefix extraction needed)
            display_doc_id = doc_id
            display_title = title

            # Calculate timing
            if doc_id in doc_start_times:
                total_time = time.time() - doc_start_times[doc_id]

                # Calculate step timings
                step_times = doc_step_times.get(doc_id, {})
                steps = list(step_times.keys())

                timing_breakdown = {}
                for i, step in enumerate(steps):
                    step_start = step_times[step]
                    if i < len(steps) - 1:
                        step_end = step_times[steps[i + 1]]
                    else:
                        step_end = time.time()

                    duration = step_end - step_start

                    # Shorten step names
                    step_short = step.replace("Loading existing entities...", "load")
                    step_short = step_short.replace("Calling LLM to extract metadata...", "llm")
                    step_short = step_short.replace("Updating database...", "db")

                    timing_breakdown[step_short] = duration

                # Log based on status (use display_doc_id for showing, display_title for text)
                counter = (indexed_count, total_docs)
                if status == "success":
                    display.log_success(
                        display_doc_id,
                        display_title,
                        total_time,
                        timing_breakdown,
                        operation="Indexed",
                        counter=counter,
                    )
                elif status == "skipped":
                    display.log_skip(
                        display_doc_id,
                        display_title,
                        skip_reason or "content unchanged",
                        operation="Skipped",
                        counter=counter,
                    )
                elif status == "error":
                    display.log_error(
                        display_doc_id, display_title, operation="Index failed", counter=counter
                    )

                # Cleanup
                doc_start_times.pop(doc_id, None)
                doc_step_times.pop(doc_id, None)
            else:
                # No timing info, just log
                counter = (indexed_count, total_docs)
                if status == "success":
                    display.log_success(
                        display_doc_id, display_title, operation="Indexed", counter=counter
                    )
                elif status == "skipped":
                    display.log_skip(
                        display_doc_id,
                        display_title,
                        skip_reason or "content unchanged",
                        operation="Skipped",
                        counter=counter,
                    )
                elif status == "error":
                    display.log_error(
                        display_doc_id, display_title, operation="Index failed", counter=counter
                    )

            # Update progress bar
            display.update_progress(completed=indexed_count)

    return callback


def display_knowledge_graph(kg: dict, console: Console, title: str = "Knowledge Graph"):
    """
    Display knowledge graph in a consistent format.

    This is a static display utility (moved from _display.py).

    Args:
        kg: Knowledge graph data with stats, entities, and relationships
        console: Rich Console instance for output
        title: Title to display (default: "Knowledge Graph")
    """
    if not kg:
        return

    console.print(f"\n[bold cyan]{title}[/bold cyan]")
    console.print(f"[dim]{'─' * 60}[/dim]")

    # Stats
    console.print(f"[bold]Entities:[/bold] {kg['stats']['entity_count']}")
    console.print(f"[bold]Relationships:[/bold] {kg['stats']['relationship_count']}")

    if kg["stats"]["entity_count"] > 0:
        console.print(
            f"[bold]Avg Entity Confidence:[/bold] {kg['stats']['avg_entity_confidence']:.2f}"
        )

    # Top entities
    if kg["entities"]:
        console.print("\n[bold]Top Entities:[/bold]")
        for entity in kg["entities"][:10]:
            aliases_str = (
                f" (aliases: {', '.join(entity['aliases'][:2])})" if entity["aliases"] else ""
            )
            console.print(f"  • {entity['name']} [{entity['type']}]{aliases_str}")
            console.print(
                f"    [dim]Confidence: {entity['confidence']:.2f}, "
                f"Mentions: {entity['mentions_in_doc']}[/dim]"
            )
            if entity.get("mention_context"):
                quote = (
                    entity["mention_context"][:100] + "..."
                    if len(entity["mention_context"]) > 100
                    else entity["mention_context"]
                )
                console.print(f'    [dim italic]"{quote}"[/dim italic]')

    # Relationships
    if kg["relationships"]:
        console.print("\n[bold]Relationships:[/bold]")
        for rel in kg["relationships"][:10]:
            console.print(
                f"  • {rel['source_entity']} --[{rel['relationship_type']}]--> "
                f"{rel['target_entity']}"
            )
            console.print(f"    [dim]Confidence: {rel['confidence']:.2f}[/dim]")
            if rel.get("context"):
                context = (
                    rel["context"][:100] + "..." if len(rel["context"]) > 100 else rel["context"]
                )
                console.print(f'    [dim italic]"{context}"[/dim italic]')


def index_single_document_with_progress(doc, console, force: bool = False):
    """
    Index a single document with live display and activity tracking.

    This is a CLI display helper that wraps the indexing service
    with interactive progress display.

    Args:
        doc: Document object to index
        console: Rich Console instance
        force: Force re-indexing even if already indexed

    Returns:
        dict with keys:
            - success: bool
            - result: dict (if successful)
            - error: str (if failed)
            - skipped: bool
    """
    import time

    from kurt.content.indexing import extract_document_metadata

    doc_id = str(doc.id)

    with LiveProgressDisplay(console, max_log_lines=10) as display:
        display.start_stage("Indexing document", total=None)

        try:
            # Activity callback for single document
            def activity_callback(activity: str):
                display.log_info(activity)

            # Extract and persist metadata + entities with activity tracking
            start_time = time.time()

            result = extract_document_metadata(
                doc_id, force=force, activity_callback=activity_callback
            )

            elapsed = time.time() - start_time

            if result.get("skipped", False):
                skip_reason = result.get("skip_reason", "content unchanged")
                title = result.get("title", "Untitled")
                display.log_skip(doc_id, title, skip_reason)
                display.complete_stage()
                return {"success": True, "result": result, "skipped": True}
            else:
                display.log_success(doc_id, result["title"], elapsed)
                display.complete_stage()
                return {"success": True, "result": result, "skipped": False}

        except Exception as e:
            display.log_error(doc_id, str(e))
            display.complete_stage()
            return {"success": False, "error": str(e), "skipped": False}


def index_multiple_documents_with_progress(documents, console, force: bool = False):
    """
    Index multiple documents with live display and activity tracking.

    This is a CLI display helper that wraps the batch indexing service
    with interactive progress display.

    Args:
        documents: List of Document objects to index
        console: Rich Console instance
        force: Force re-indexing even if already indexed

    Returns:
        dict with keys from batch_extract_document_metadata:
            - results: list of result dicts
            - errors: list of error dicts
            - succeeded: int
            - failed: int
            - skipped: int
            - elapsed_time: float (total seconds)
    """
    import asyncio
    import time

    from kurt.config import load_config
    from kurt.content.indexing import batch_extract_document_metadata

    # Extract document IDs
    document_ids = [str(doc.id) for doc in documents]

    # Get max concurrent from config
    config = load_config()
    max_concurrent = config.MAX_CONCURRENT_INDEXING

    # Track overall timing
    start_time = time.time()

    with LiveProgressDisplay(console, max_log_lines=10) as display:
        # Start indexing stage
        display.start_stage("Indexing documents", total=len(document_ids))

        # Create progress callback with activity updates and logging
        update_progress = create_fetch_progress_callback(display, len(document_ids))

        # Run async batch extraction with progress callback
        batch_result = asyncio.run(
            batch_extract_document_metadata(
                document_ids,
                max_concurrent=max_concurrent,
                force=force,
                progress_callback=update_progress,
            )
        )

        display.complete_stage()

    # Add elapsed time to result
    batch_result["elapsed_time"] = time.time() - start_time

    return batch_result


def finalize_knowledge_graph_with_progress(index_results, console, display=None):
    """
    Finalize knowledge graph with live progress display.

    This wraps the entity resolution process with an interactive progress bar
    and scrolling log window showing entity resolution decisions.

    Args:
        index_results: List of indexing results to finalize
        console: Rich Console instance
        display: Optional existing LiveProgressDisplay instance (for multi-stage display)

    Returns:
        Result dict from finalize_knowledge_graph_from_index_results
    """
    import re

    from kurt.content.indexing_entity_resolution import finalize_knowledge_graph_from_index_results

    # Use provided display or create a new one
    own_display = display is None
    if own_display:
        display = LiveProgressDisplay(console, max_log_lines=10)
        display.__enter__()

    try:
        # Start stage (total will be updated when we know group count)
        display.start_stage("Entity resolution", total=None)

        # Track current stage for progress updates
        group_count = 0
        stage_started = False  # Track if we've set the total

        def activity_callback(activity: str):
            nonlocal group_count, stage_started

            # Parse different activity messages and update display accordingly
            if "Aggregating" in activity:
                display.log_info(activity)

            elif "Linking" in activity and "existing entities" in activity:
                # Extract count from message like "Linking 5 existing entities..."
                match = re.search(r"(\d+) existing entities", activity)
                count = match.group(1) if match else "?"
                display.log_info(f"→ Linking {count} existing entities")

            elif "Resolving" in activity and "new entities" in activity:
                # Extract count from message like "Resolving 110 new entities..."
                match = re.search(r"(\d+) new entities", activity)
                count = match.group(1) if match else "?"
                display.log_info(f"→ Resolving {count} new entities")

            elif "Clustering" in activity:
                display.log_info(f"→ {activity}")

            elif "Found" in activity and "entity groups" in activity:
                # Extract group count from message like "Found 29 entity groups, resolving entities with LLM..."
                match = re.search(r"(\d+) entity groups", activity)
                if match and not stage_started:
                    group_count = int(match.group(1))
                    # Update the total instead of starting a new stage
                    display.update_stage_total(group_count)
                    stage_started = True

            elif "Resolved group" in activity:
                # Parse: "Resolved group 1/29: Dagster → NEW, Dagster Cloud → MERGE(Dagster) (2.4s)"
                match = re.search(r"Resolved group (\d+)/(\d+): (.+) \((.+?)\)$", activity)
                if match:
                    current, total, decisions, timing = match.groups()
                    display.update_progress(completed=int(current))
                    display.log(f"{decisions} ({timing})", style="dim green")
                else:
                    display.log(activity, style="dim")

            elif "Creating entities and relationships" in activity:
                display.log_info(f"→ {activity}")

            elif "Resolved:" in activity:
                # Final summary: "Resolved: 42 new entities, 55 merged with existing"
                display.log_info(f"→ {activity}")

            else:
                # Generic activity message
                display.log_info(activity)

        # Run the finalization with our activity callback
        kg_result = finalize_knowledge_graph_from_index_results(
            index_results, activity_callback=activity_callback
        )

        display.complete_stage()

    finally:
        # Only exit if we created the display
        if own_display:
            display.__exit__(None, None, None)

    # Print final summary (only if we created our own display)
    if own_display:
        console.print("\n[bold]Finalizing knowledge graph...[/bold]")
        if "error" in kg_result:
            console.print(f"  [red]✗[/red] KG finalization failed: {kg_result['error']}")
        else:
            console.print(f"  [green]✓[/green] Created {kg_result['entities_created']} entities")
            console.print(f"  [green]✓[/green] Linked {kg_result['entities_linked']} entities")
            if kg_result.get("relationships_created", 0) > 0:
                console.print(
                    f"  [green]✓[/green] Created {kg_result['relationships_created']} relationships"
                )

    return kg_result


def index_and_finalize_with_two_stage_progress(documents, console, force: bool = False):
    """
    Index documents and finalize KG with two-stage live progress display.

    Stage 1: Document indexing (metadata extraction)
    Stage 2: Entity resolution

    Args:
        documents: List of Document objects to index
        console: Rich Console instance
        force: Force re-indexing even if already indexed

    Returns:
        dict with both indexing and KG results
    """
    import asyncio
    import time

    from kurt.config import load_config
    from kurt.content.indexing import batch_extract_document_metadata

    # Extract document IDs
    document_ids = [str(doc.id) for doc in documents]
    config = load_config()
    max_concurrent = config.MAX_CONCURRENT_INDEXING

    start_time = time.time()

    # ====================================================================
    # STAGE 1: Document Indexing (Metadata Extraction)
    # ====================================================================
    print_stage_header(console, 1, "METADATA EXTRACTION")

    with LiveProgressDisplay(console, max_log_lines=10) as display:
        display.start_stage("Metadata extraction", total=len(document_ids))

        # Create progress callback for indexing
        update_progress = create_fetch_progress_callback(display, len(document_ids))

        # Run async batch extraction
        batch_result = asyncio.run(
            batch_extract_document_metadata(
                document_ids,
                max_concurrent=max_concurrent,
                force=force,
                progress_callback=update_progress,
            )
        )

        display.complete_stage()

    # Stage 1 summary
    indexed_count = batch_result["succeeded"] - batch_result["skipped"]
    skipped_count = batch_result["skipped"]
    error_count = batch_result["failed"]

    print_stage_summary(
        console,
        [
            ("✓", "Indexed", f"{indexed_count} document(s)"),
            ("○", "Skipped", f"{skipped_count} document(s)"),
            ("✗", "Failed", f"{error_count} document(s)"),
        ],
    )

    # ====================================================================
    # STAGE 2: Entity Resolution
    # ====================================================================
    results_for_kg = [
        r
        for r in batch_result.get("results", [])
        if not r.get("skipped", False) and "error" not in r
    ]

    if results_for_kg:
        print_stage_header(console, 2, "ENTITY RESOLUTION")

        # New live display for stage 2
        with LiveProgressDisplay(console, max_log_lines=10) as display:
            kg_result = finalize_knowledge_graph_with_progress(
                results_for_kg, console, display=display
            )

        # Stage 2 summary
        print_stage_summary(
            console,
            [
                ("✓", "Entities created", str(kg_result["entities_created"])),
                ("✓", "Entities linked", str(kg_result["entities_linked"])),
                (
                    "✓",
                    "Relationships created",
                    str(kg_result.get("relationships_created", 0)),
                ),
            ],
        )
    else:
        kg_result = None

    # ====================================================================
    # Global Command Summary
    # ====================================================================
    elapsed = time.time() - start_time
    summary_items = [
        ("✓", "Total indexed", f"{indexed_count} document(s)"),
    ]

    if kg_result:
        summary_items.extend(
            [
                ("✓", "Entities created", str(kg_result["entities_created"])),
                ("✓", "Entities linked", str(kg_result["entities_linked"])),
                (
                    "✓",
                    "Relationships created",
                    str(kg_result.get("relationships_created", 0)),
                ),
            ]
        )

    summary_items.append(("ℹ", "Time elapsed", f"{elapsed:.1f}s"))

    print_command_summary(console, "Summary", summary_items)

    # Add elapsed time
    batch_result["elapsed_time"] = time.time() - start_time

    return {
        "indexing": batch_result,
        "kg_result": kg_result,
    }


def display_kg_finalization_summary(kg_result, console):
    """
    Display knowledge graph finalization summary (static version).

    This is a display utility for CLI commands (legacy static version).
    Use finalize_knowledge_graph_with_progress for interactive display.

    Args:
        kg_result: Result dict from finalize_knowledge_graph_from_index_results
        console: Rich Console instance
    """
    console.print("\n[bold]Finalizing knowledge graph...[/bold]")

    if "error" in kg_result:
        console.print(f"  [red]✗[/red] KG finalization failed: {kg_result['error']}")
    else:
        console.print(f"  [green]✓[/green] Created {kg_result['entities_created']} entities")
        console.print(f"  [green]✓[/green] Linked {kg_result['entities_linked']} entities")
        if kg_result.get("relationships_created", 0) > 0:
            console.print(
                f"  [green]✓[/green] Created {kg_result['relationships_created']} relationships"
            )
