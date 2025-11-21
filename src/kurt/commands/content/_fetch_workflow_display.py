"""Workflow stream display helpers for fetch command.

Handles complex stream reading and event formatting for fetch workflow progress display.
"""

import queue
import threading
import time

from dbos import DBOS


def format_fetch_event(update: dict, doc_id: str) -> tuple[str, str, str] | None:
    """
    Format a fetch workflow event for display.

    Returns:
        Tuple of (timestamp, message, style) or None if event should be skipped
    """
    status = update.get("status")
    duration_ms = update.get("duration_ms")
    timing = f" ({duration_ms}ms)" if duration_ms else ""
    timestamp = update.get("timestamp", "")

    if timestamp:
        time_str = timestamp.split("T")[1][:12]
        ts_display = f"[{time_str}] "
    else:
        ts_display = ""

    if status == "started":
        return (timestamp, f"{ts_display}⠋ Started [{doc_id}]", "dim")
    elif status == "resolved":
        return (timestamp, f"{ts_display}→ Resolved [{doc_id}]{timing}", "dim")
    elif status == "fetched":
        return (timestamp, f"{ts_display}⠋ Fetched [{doc_id}]{timing}", "dim cyan")
    elif status == "embedded":
        return (timestamp, f"{ts_display}⠋ Embeddings extracted [{doc_id}]{timing}", "dim")
    elif status == "saved":
        return (timestamp, f"{ts_display}⠋ Saved [{doc_id}]{timing}", "dim")
    elif status == "links_extracted":
        return (timestamp, f"{ts_display}→ Extracted links [{doc_id}]{timing}", "dim")
    elif status == "completed":
        return (timestamp, f"{ts_display}✓ Completed [{doc_id}]{timing}", "dim green")
    elif status == "error":
        error = update.get("error", "Unknown error")
        error_short = error[:60] + "..." if len(error) > 60 else error
        return (timestamp, f"✗ Error [{doc_id}] {error_short}", "dim red")
    return None


def read_fetch_streams_with_sorted_display(workflow_id: str, doc_count: int, display) -> None:
    """
    Read fetch workflow streams in parallel with sorted event display.

    Args:
        workflow_id: DBOS workflow ID
        doc_count: Number of documents being fetched
        display: LiveProgressDisplay instance
    """
    completed_count = 0
    completed_lock = threading.Lock()

    # Event queue for sorting by timestamp
    event_queue = queue.Queue()
    display_thread_stop = threading.Event()

    def display_sorted_events():
        """Periodically flush events sorted by timestamp."""
        buffer = []
        while not display_thread_stop.is_set() or not event_queue.empty():
            # Collect events for 100ms
            deadline = time.time() + 0.1
            while time.time() < deadline:
                try:
                    event = event_queue.get(timeout=0.01)
                    buffer.append(event)
                except queue.Empty:
                    pass

            # Sort by timestamp and display
            if buffer:
                buffer.sort(key=lambda x: x[0] if x[0] else "")
                for timestamp, message, style in buffer:
                    display.log(message, style=style)
                buffer = []

    def read_progress_stream(index: int):
        """Read progress stream for one document."""
        nonlocal completed_count
        doc_id = "..."

        try:
            for update in DBOS.read_stream(workflow_id, f"doc_{index}_progress"):
                status = update.get("status")

                # Extract document ID from stream if available
                if "identifier" in update:
                    identifier = update["identifier"]
                    doc_id = identifier[:8] if len(identifier) > 8 else identifier
                elif "document_id" in update:
                    document_id = update["document_id"]
                    doc_id = document_id[:8] if len(document_id) > 8 else document_id

                # Format and queue event
                formatted = format_fetch_event(update, doc_id)
                if formatted:
                    event_queue.put(formatted)

                # Update progress for terminal statuses
                if status in ("completed", "error"):
                    display.update_progress(advance=1)
                    with completed_lock:
                        completed_count += 1

        except Exception as e:
            event_queue.put(("", f"Stream error for doc_{index}: {str(e)}", "dim red"))

    # Start display thread
    display_thread = threading.Thread(target=display_sorted_events)
    display_thread.start()

    # Start thread for each document stream
    threads = []
    for i in range(doc_count):
        t = threading.Thread(target=read_progress_stream, args=(i,))
        t.start()
        threads.append(t)

    # Wait for all streams to complete
    for t in threads:
        t.join()

    # Stop display thread and wait for final flush
    display_thread_stop.set()
    display_thread.join()
