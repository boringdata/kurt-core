"""Display utilities for content commands.

This module provides both interactive and static display utilities:
- LiveProgressDisplay: Interactive progress bars with live log scrolling
- display_knowledge_graph: Static knowledge graph formatting
- Generic stream display framework for reading DBOS workflow streams
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
# Generic Stream Display Framework
# ============================================================================


def format_display_timestamp() -> str:
    """
    Get current timestamp formatted for display in messages.

    Returns:
        "[HH:MM:SS.mmm] " for message prefix

    Example:
        ts = format_display_timestamp()
        # ts = "[15:03:12.123] "

    Note: DBOS automatically attaches timestamps to stream events.
          This is only for formatting the message prefix for display.
    """
    from datetime import datetime

    now = datetime.now()
    iso_timestamp = now.isoformat()
    time_str = iso_timestamp.split("T")[1][:12]  # Get HH:MM:SS.mmm

    return f"[{time_str}] "


def read_stream_with_display(
    workflow_id: str,
    stream_name: str,
    display: "LiveProgressDisplay",
    on_event: callable = None,
):
    """
    Generic stream reader - just displays what the workflow emits.

    The workflow is responsible for formatting messages. This just reads and displays.

    Args:
        workflow_id: DBOS workflow ID
        stream_name: Name of the stream (e.g., "doc_0_progress", "entity_resolution_progress")
        display: LiveProgressDisplay instance
        on_event: Optional callback(event) called for each event (e.g., to update progress bar)

    Event format (from workflow):
        {
            "message": "[15:03:12.123] ⠋ Fetched [abc123] (2543ms)",  # Display-ready message
            "style": "dim cyan",                                        # Rich style
            "advance_progress": True,                                   # Optional: advance progress bar
            ...  # Any other fields for callback
        }

    Note:
    - DBOS automatically attaches timestamps to stream events for sorting
    - Use format_display_timestamp() to add timestamp prefix to messages
    - CLI can sort events by DBOS native timestamp if needed

    Example:
        def on_event(event):
            if event.get("advance_progress"):
                display.update_progress(advance=1)

        read_stream_with_display(
            workflow_id="abc-123",
            stream_name="doc_0_progress",
            display=display,
            on_event=on_event
        )
    """
    from dbos import DBOS

    try:
        for event in DBOS.read_stream(workflow_id, stream_name):
            # Display the message
            message = event.get("message", "")
            style = event.get("style", "dim")

            if message:
                display.log(message, style=style)

            # Call event callback if provided
            if on_event:
                on_event(event)

    except Exception as e:
        display.log(f"Stream error for {stream_name}: {str(e)}", style="dim red")


def read_multiple_streams_parallel(
    workflow_id: str,
    stream_names: list[str],
    display: "LiveProgressDisplay",
    on_event: callable = None,
):
    """
    Read multiple streams in parallel using threads.

    Args:
        workflow_id: DBOS workflow ID
        stream_names: List of stream names to read
        display: LiveProgressDisplay instance
        on_event: Optional callback(stream_name, event) called for each event

    Example:
        # Read doc_0_progress, doc_1_progress, doc_2_progress in parallel
        def on_event(stream_name, event):
            if event.get("advance_progress"):
                display.update_progress(advance=1)

        read_multiple_streams_parallel(
            workflow_id="abc-123",
            stream_names=["doc_0_progress", "doc_1_progress", "doc_2_progress"],
            display=display,
            on_event=on_event
        )
    """
    import threading

    def read_one_stream(stream_name: str):
        """Read a single stream."""

        def wrapped_on_event(event):
            if on_event:
                on_event(stream_name, event)

        read_stream_with_display(
            workflow_id=workflow_id,
            stream_name=stream_name,
            display=display,
            on_event=wrapped_on_event,
        )

    # Start thread for each stream
    threads = []
    for stream_name in stream_names:
        t = threading.Thread(target=read_one_stream, args=(stream_name,))
        t.start()
        threads.append(t)

    # Wait for all to complete
    for t in threads:
        t.join()


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

    # Build entity name to ID mapping for highlighting
    entity_map = {}
    if kg.get("entities"):
        for entity in kg["entities"]:
            entity_map[entity["name"].lower()] = entity

    # Claims section (first)
    if kg.get("claims"):
        claim_count = len(kg["claims"])
        console.print(f"\n[bold cyan]Claims ({claim_count})[/bold cyan]")
        console.print(f"[dim]{'─' * 60}[/dim]")

        for claim in kg["claims"][:10]:
            # Highlight entities in the claim statement
            statement = claim["statement"]

            # Find and highlight entities mentioned in the statement
            highlighted_statement = statement

            # First highlight entities from the referenced_entities list (these are properly linked)
            entities_in_claim = claim.get("referenced_entities", [])
            for entity_name in entities_in_claim:
                import re

                pattern = re.compile(r"\b" + re.escape(entity_name) + r"\b", re.IGNORECASE)
                highlighted_statement = pattern.sub(
                    f"[bold magenta]{entity_name}[/bold magenta]", highlighted_statement
                )

            # Also highlight any entities from the entity_map that appear in the text
            for entity_name, entity_info in entity_map.items():
                # Skip if already highlighted
                if entity_info["name"] not in entities_in_claim:
                    import re

                    pattern = re.compile(
                        r"\b" + re.escape(entity_info["name"]) + r"\b", re.IGNORECASE
                    )
                    # Use dim magenta for entities not properly linked
                    highlighted_statement = pattern.sub(
                        f"[dim magenta]{entity_info['name']}[/dim magenta]", highlighted_statement
                    )

            # Format claim type more compactly
            claim_type_short = (
                claim["claim_type"].replace("ClaimType.", "").replace("DEFINITION", "DEF")
            )
            console.print(f"• [[dim]{claim_type_short}[/dim]] {highlighted_statement}")

            # Show all entities referenced in this claim
            entities_in_claim = claim.get("referenced_entities", [])

            if entities_in_claim:
                console.print(f"  [dim]Entities: {', '.join(entities_in_claim)}[/dim]")
            console.print(f"  [dim]Confidence: {claim['confidence']:.2f}[/dim]")
            console.print()

    # Entities & Relationships section
    entity_count = kg["stats"]["entity_count"]
    rel_count = kg["stats"]["relationship_count"]
    console.print(
        f"[bold cyan]Entities & Relationships ({entity_count} entities, {rel_count} relationships)[/bold cyan]"
    )
    console.print(f"[dim]{'─' * 60}[/dim]")

    # Group relationships by source entity
    relationships_by_entity = {}
    if kg.get("relationships"):
        for rel in kg["relationships"]:
            source = rel["source_entity"]
            if source not in relationships_by_entity:
                relationships_by_entity[source] = []
            relationships_by_entity[source].append(rel)

    # Display entities with their relationships
    if kg.get("entities"):
        for entity in kg["entities"][:10]:
            # Compact entity line
            console.print(
                f"• [bold]{entity['name']}[/bold] [{entity['type']}] • "
                f"Conf: {entity['confidence']:.2f} • Mentions: {entity['mentions_in_doc']}"
            )

            # Show relationships for this entity
            entity_rels = relationships_by_entity.get(entity["name"], [])
            for rel in entity_rels[:3]:  # Show up to 3 relationships per entity
                rel_type = rel.get("relationship_type", "related_to")
                arrow = "→"
                if len(rel.get("context", "")) > 60:
                    console.print(
                        f"  {arrow} [italic]{rel_type}[/italic] → {rel['target_entity']} "
                        f"[dim]({rel['confidence']:.2f}): "
                        f"{rel['context'][:60]}...[/dim]"
                    )
                else:
                    console.print(
                        f"  {arrow} [italic]{rel_type}[/italic] → {rel['target_entity']} "
                        f"[dim]({rel['confidence']:.2f})[/dim]"
                    )

            # If entity has no relationships, note it
            if not entity_rels:
                console.print("  [dim](no relationships)[/dim]")

    # Summary line
    console.print()
    avg_conf = kg["stats"].get("avg_entity_confidence", 0)
    claim_count = kg["stats"].get("claim_count", 0)
    console.print(
        f"[dim]Summary: {entity_count} entities • {rel_count} relationships • "
        f"{claim_count} claims • Avg confidence: {avg_conf:.2f}[/dim]"
    )


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
    import time

    from kurt.config import load_config

    # Extract document IDs
    document_ids = [str(doc.id) for doc in documents]
    config = load_config()
    max_concurrent = config.MAX_CONCURRENT_INDEXING

    start_time = time.time()

    # ====================================================================
    # Run workflow with live display
    # ====================================================================
    from dbos import DBOS

    from kurt.content.indexing.workflow_indexing import complete_indexing_workflow
    from kurt.workflows import get_dbos

    # Initialize DBOS
    get_dbos()

    print_stage_header(console, 1, "METADATA EXTRACTION")

    # Start indexing workflow (runs both metadata extraction + entity resolution)
    index_handle = DBOS.start_workflow(
        complete_indexing_workflow,
        document_ids=document_ids,
        force=force,
        enable_kg=True,
        max_concurrent=max_concurrent,
    )

    with LiveProgressDisplay(console, max_log_lines=10) as display:
        # Stage 1: Metadata extraction
        display.start_stage("Metadata extraction", total=len(document_ids))

        # Read document progress streams in parallel
        read_multiple_streams_parallel(
            workflow_id=index_handle.workflow_id,
            stream_names=[f"doc_{i}_progress" for i in range(len(document_ids))],
            display=display,
            on_event=lambda _stream, event: display.update_progress(advance=1)
            if event.get("advance_progress")
            else None,
        )

        display.complete_stage()

        # Stage 2: Entity resolution
        print_stage_header(console, 2, "ENTITY RESOLUTION")
        display.start_stage("Entity resolution", total=1)

        # Read entity resolution stream
        read_stream_with_display(
            workflow_id=index_handle.workflow_id,
            stream_name="entity_resolution_progress",
            display=display,
            on_event=None,
        )

        display.complete_stage()

    # Get final result (workflow should be complete now)
    index_result = index_handle.get_result()

    # Extract batch_result from workflow result
    batch_result = index_result.get("extract_results", {})

    # Stage 1 summary
    # Note: In workflow_indexing.py, "succeeded" already excludes skipped documents
    # (unlike the legacy extract.py which included them)
    indexed_count = batch_result["succeeded"]
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

    # Stage 2 summary
    kg_result = index_result.get("kg_stats")

    if kg_result:
        print_stage_summary(
            console,
            [
                ("✓", "Entities created", str(kg_result.get("entities_created", 0))),
                ("✓", "Entities linked", str(kg_result.get("entities_linked_existing", 0))),
                (
                    "✓",
                    "Relationships created",
                    str(kg_result.get("relationships_created", 0)),
                ),
            ],
        )

    # Stage 3 summary - Claims
    claim_stats = index_result.get("claim_stats")

    if claim_stats and claim_stats.get("claims_processed", 0) > 0:
        print_stage_header(console, 3, "CLAIMS EXTRACTION")
        print_stage_summary(
            console,
            [
                ("✓", "Claims processed", str(claim_stats.get("claims_processed", 0))),
                (
                    "✓",
                    "Claims created",
                    str(claim_stats.get("claims_created", 0))
                    if "claims_created" in claim_stats
                    else str(claim_stats.get("claims_processed", 0)),
                ),
                ("⚠", "Unresolved entities", str(claim_stats.get("unresolved_entities", 0))),
                ("⚠", "Conflicts detected", str(claim_stats.get("conflicts_detected", 0))),
                ("○", "Duplicates skipped", str(claim_stats.get("duplicates_skipped", 0))),
                ("✓", "Documents with claims", str(claim_stats.get("documents_with_claims", 0))),
            ],
        )

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
                ("✓", "Entities linked", str(kg_result.get("entities_linked_existing", 0))),
                (
                    "✓",
                    "Relationships created",
                    str(kg_result.get("relationships_created", 0)),
                ),
            ]
        )

    # Add claims to summary if present
    claim_stats = index_result.get("claim_stats")
    if claim_stats and claim_stats.get("claims_processed", 0) > 0:
        summary_items.extend(
            [
                ("✓", "Claims processed", str(claim_stats.get("claims_processed", 0))),
            ]
        )
        if claim_stats.get("unresolved_entities", 0) > 0:
            summary_items.append(
                ("⚠", "Unresolved claim entities", str(claim_stats.get("unresolved_entities", 0)))
            )
        if claim_stats.get("conflicts_detected", 0) > 0:
            summary_items.append(
                ("⚠", "Conflicts detected", str(claim_stats.get("conflicts_detected", 0)))
            )

    summary_items.append(("ℹ", "Time elapsed", f"{elapsed:.1f}s"))

    # Add token usage if available
    import dspy

    total_tokens = 0
    try:
        if hasattr(dspy.settings, "lm") and hasattr(dspy.settings.lm, "history"):
            for call in dspy.settings.lm.history:
                if isinstance(call, dict) and "usage" in call:
                    usage = call["usage"]
                    if "total_tokens" in usage:
                        total_tokens += usage["total_tokens"]
            if total_tokens > 0:
                summary_items.append(("ℹ", "Tokens used", f"{total_tokens:,}"))
    except Exception:
        pass  # Token tracking is optional

    print_command_summary(console, "Summary", summary_items)

    # Add elapsed time
    batch_result["elapsed_time"] = time.time() - start_time

    return {
        "indexing": batch_result,
        "kg_result": kg_result,
    }
