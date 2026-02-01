"""Status streaming for workflow observability.

This module provides real-time event streaming from the step_events table
using a cursor-based polling approach with monotonic IDs.

Usage:
    from kurt.observability import stream_events, format_event, StatusStreamer
    from kurt.db.dolt import DoltDB

    db = DoltDB("/path/to/.dolt")

    # Simple streaming
    for event in stream_events(db, run_id="abc-123"):
        print(format_event(event))

    # With custom options
    streamer = StatusStreamer(db, poll_ms=250)
    for event in streamer.stream(run_id="abc-123"):
        if event is None:  # Workflow terminated
            break
        print(format_event(event, json_output=True))

Cursor Strategy:
    - Uses event 'id' (BIGINT AUTO_INCREMENT) as cursor
    - Monotonic IDs ensure sortable ordering
    - No gaps: cursor ensures all events seen
    - No duplicates: cursor > last_seen_id

Terminal States:
    Streaming stops when workflow_runs.status is one of:
    - completed
    - failed
    - canceled
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    from kurt.db.dolt import DoltDB

logger = logging.getLogger(__name__)

# Default polling interval in milliseconds
DEFAULT_POLL_MS = 500

# Batch limit per poll
DEFAULT_BATCH_LIMIT = 100

# Terminal workflow statuses
TERMINAL_STATUSES = frozenset({"completed", "failed", "canceled"})


@dataclass
class StepEvent:
    """Represents a step event from the step_events table.

    Attributes:
        id: Monotonic event ID (BIGINT)
        run_id: Workflow run ID
        step_id: Step identifier (e.g., "map", "fetch")
        substep: Optional substep name (e.g., "fetch_urls", "parse")
        status: Event status - running, progress, completed, failed
        created_at: Timestamp when event was created
        current: Current progress count (optional)
        total: Total items to process (optional)
        message: Human-readable message (optional)
        metadata: Additional event data (optional)
    """

    id: int
    run_id: str
    step_id: str
    substep: str | None
    status: str
    created_at: datetime | None
    current: int | None
    total: int | None
    message: str | None
    metadata: dict[str, Any] | None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "StepEvent":
        """Create StepEvent from database row.

        Args:
            row: Dictionary from query result.

        Returns:
            StepEvent instance.
        """
        # Parse metadata if present
        metadata = None
        if row.get("metadata"):
            try:
                if isinstance(row["metadata"], str):
                    metadata = json.loads(row["metadata"])
                else:
                    metadata = row["metadata"]
            except (json.JSONDecodeError, TypeError):
                metadata = None

        # Parse created_at if string
        created_at = row.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                created_at = None

        return cls(
            id=int(row["id"]),
            run_id=str(row["run_id"]),
            step_id=str(row["step_id"]),
            substep=row.get("substep"),
            status=str(row.get("status", "progress")),
            created_at=created_at,
            current=row.get("current"),
            total=row.get("total"),
            message=row.get("message"),
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "id": self.id,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "substep": self.substep,
            "status": self.status,
            "current": self.current,
            "total": self.total,
            "message": self.message,
        }
        if self.created_at:
            result["created_at"] = self.created_at.isoformat()
        if self.metadata:
            result["metadata"] = self.metadata
        return result


def format_event(event: StepEvent, *, json_output: bool = False) -> str:
    """Format a step event for CLI display.

    Args:
        event: StepEvent to format.
        json_output: If True, return JSON string instead of formatted text.

    Returns:
        Formatted string for display.

    Format:
        [HH:MM:SS] {step_id}/{substep}: {status} [{current}/{total}] {message}

    Examples:
        [10:00:01] fetch/fetch_urls: running [0/100]
        [10:00:02] fetch/fetch_urls: progress [50/100] Fetching batch 2
        [10:00:03] fetch/fetch_urls: completed [100/100]
    """
    if json_output:
        return json.dumps(event.to_dict())

    # Format timestamp
    if event.created_at:
        timestamp = event.created_at.strftime("%H:%M:%S")
    else:
        timestamp = datetime.now().strftime("%H:%M:%S")

    # Format step path
    if event.substep:
        step_path = f"{event.step_id}/{event.substep}"
    else:
        step_path = event.step_id

    # Format progress
    if event.current is not None and event.total is not None:
        progress = f" [{event.current}/{event.total}]"
    elif event.current is not None:
        progress = f" [{event.current}]"
    else:
        progress = ""

    # Format message
    message_part = f" {event.message}" if event.message else ""

    return f"[{timestamp}] {step_path}: {event.status}{progress}{message_part}"


class StatusStreamer:
    """Real-time event streamer with polling-based subscription.

    Uses cursor-based polling to stream events from step_events table.
    Automatically stops when workflow reaches a terminal state.

    Thread Safety:
        StatusStreamer is NOT thread-safe. Create separate instances
        for concurrent streaming.

    Usage:
        streamer = StatusStreamer(db, poll_ms=250)
        for event in streamer.stream(run_id="abc-123"):
            print(format_event(event))
    """

    def __init__(
        self,
        db: "DoltDB",
        poll_ms: int = DEFAULT_POLL_MS,
        batch_limit: int = DEFAULT_BATCH_LIMIT,
    ):
        """Initialize StatusStreamer.

        Args:
            db: DoltDB instance for querying.
            poll_ms: Polling interval in milliseconds (default: 500).
            batch_limit: Maximum events per poll (default: 100).
        """
        self._db = db
        self._poll_ms = poll_ms
        self._poll_sec = poll_ms / 1000.0
        self._batch_limit = batch_limit

    def _is_workflow_terminated(self, run_id: str) -> bool:
        """Check if workflow is in a terminal state.

        Args:
            run_id: Workflow run ID.

        Returns:
            True if workflow status is terminal (completed/failed/canceled).
        """
        try:
            result = self._db.query_one(
                "SELECT status FROM workflow_runs WHERE id = ?",
                [run_id],
            )
            if result is None:
                # Workflow not found - may not have started yet
                return False
            return result.get("status") in TERMINAL_STATUSES
        except Exception as e:
            logger.debug(f"Error checking workflow status: {e}")
            return False

    def _fetch_events(self, run_id: str, cursor_id: int) -> list[StepEvent]:
        """Fetch events since cursor.

        Args:
            run_id: Workflow run ID.
            cursor_id: Last seen event ID.

        Returns:
            List of StepEvent objects.
        """
        # Query events after cursor, ordered by id for cursor stability
        sql = """
            SELECT * FROM step_events
            WHERE run_id = ?
              AND id > ?
            ORDER BY created_at ASC, id ASC
            LIMIT ?
        """
        result = self._db.query(sql, [run_id, cursor_id, self._batch_limit])

        return [StepEvent.from_row(row) for row in result.rows]

    def stream(
        self,
        run_id: str,
        since_id: int = 0,
    ) -> Iterator[StepEvent]:
        """Stream events for a workflow run.

        Yields events as they appear. Stops when workflow reaches
        a terminal state (completed, failed, canceled).

        Args:
            run_id: Workflow run ID to stream.
            since_id: Start cursor (default: 0, from beginning).

        Yields:
            StepEvent objects as they are available.

        Example:
            for event in streamer.stream("abc-123"):
                print(format_event(event))
        """
        cursor = since_id

        while True:
            # Fetch new events
            events = self._fetch_events(run_id, cursor)

            # Yield events and update cursor
            for event in events:
                yield event
                cursor = event.id

            # Check if workflow terminated
            if self._is_workflow_terminated(run_id):
                # Fetch any remaining events after termination
                final_events = self._fetch_events(run_id, cursor)
                for event in final_events:
                    yield event
                break

            # No new events - wait before next poll
            if not events:
                time.sleep(self._poll_sec)


def stream_events(
    db: "DoltDB",
    run_id: str,
    since_id: int = 0,
    poll_ms: int = DEFAULT_POLL_MS,
) -> Iterator[StepEvent]:
    """Stream events for a workflow run.

    Convenience function that creates a StatusStreamer and streams events.

    Args:
        db: DoltDB instance for querying.
        run_id: Workflow run ID to stream.
        since_id: Start cursor (default: 0, from beginning).
        poll_ms: Polling interval in milliseconds (default: 500).

    Yields:
        StepEvent objects as they are available.

    Example:
        from kurt.db.dolt import DoltDB

        db = DoltDB("/path/to/.dolt")
        for event in stream_events(db, run_id="abc-123"):
            print(format_event(event))
    """
    streamer = StatusStreamer(db, poll_ms=poll_ms)
    yield from streamer.stream(run_id, since_id=since_id)
