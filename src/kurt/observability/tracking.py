"""Event tracking for workflow observability.

This module provides event tracking for workflow steps using DoltDB.
Events are inserted into the step_events table with monotonic IDs
for cursor-based streaming.

Usage:
    from kurt.observability import track_event, EventTracker

    # Simple single event
    event_id = track_event(
        run_id="abc-123",
        step_id="map",
        substep="fetch",
        status="progress",
        current=5,
        total=10,
        message="Processing page 5 of 10",
    )

    # Batched events (high throughput)
    with EventTracker(db) as tracker:
        tracker.track(run_id="abc-123", step_id="map", status="running")
        tracker.track(run_id="abc-123", step_id="map", status="progress", current=1, total=10)
        # Auto-flushes on exit

Thread Safety:
    - track_event() is thread-safe (uses internal locking)
    - EventTracker is thread-safe (uses queue + background thread)

Batching:
    EventTracker batches events for performance. Events are flushed when:
    - Batch reaches MAX_BATCH_SIZE (1000 events)
    - FLUSH_TIMEOUT_MS (100ms) expires since last event
    - explicit flush() is called
    - context manager exits
"""

from __future__ import annotations

import atexit
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from queue import Empty, Queue
from typing import Any, Literal

from kurt.db.dolt import DoltDB, DoltQueryError

logger = logging.getLogger(__name__)

# Batching constants
MAX_BATCH_SIZE = 1000
FLUSH_TIMEOUT_MS = 100
FLUSH_TIMEOUT_SEC = FLUSH_TIMEOUT_MS / 1000.0

# Event status values
EventStatus = Literal["running", "progress", "completed", "failed"]

# Predefined event keys for legacy compatibility
EVENT_KEY_STATUS = "status"
EVENT_KEY_PROGRESS = "progress"
EVENT_KEY_ERROR = "error"
EVENT_KEY_CUSTOM = "custom"


@dataclass
class SubstepEvent:
    """Standard event value schema.

    Matches the step_events table structure for consistent event format.
    """

    substep: str | None = None
    status: EventStatus = "progress"
    current: int | None = None
    total: int | None = None
    message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "substep": self.substep,
            "status": self.status,
            "current": self.current,
            "total": self.total,
            "message": self.message,
            "metadata": self.metadata,
        }


# Global default DB instance (set by init_tracking)
_default_db: DoltDB | None = None
_db_lock = threading.Lock()


def init_tracking(db: DoltDB) -> None:
    """Initialize the global tracking database.

    Call this once at application startup to set the default DB
    used by track_event() and write_event().

    Args:
        db: DoltDB instance to use for event storage.
    """
    global _default_db
    with _db_lock:
        _default_db = db


def get_tracking_db() -> DoltDB | None:
    """Get the global tracking database.

    Returns:
        DoltDB instance or None if not initialized.
    """
    with _db_lock:
        return _default_db


def track_event(
    run_id: str,
    step_id: str,
    substep: str | None = None,
    status: EventStatus = "progress",
    current: int | None = None,
    total: int | None = None,
    message: str | None = None,
    metadata: dict[str, Any] | None = None,
    *,
    db: DoltDB | None = None,
) -> int | None:
    """Track a workflow step event.

    Inserts a single event into step_events table and returns the
    generated event ID for cursor-based streaming.

    Args:
        run_id: Workflow run ID (foreign key to workflow_runs).
        step_id: Step identifier (e.g., "map", "extract").
        substep: Optional substep name (e.g., "fetch", "parse").
        status: Event status - one of "running", "progress", "completed", "failed".
        current: Current progress count (e.g., 5 of 10).
        total: Total items to process.
        message: Optional human-readable message.
        metadata: Optional additional data (stored as JSON).
        db: DoltDB instance. Uses global default if not provided.

    Returns:
        Inserted event ID (BIGINT), or None if insert failed.

    Raises:
        ValueError: If run_id or step_id is empty.
        DoltQueryError: If database insert fails.

    Example:
        event_id = track_event(
            run_id="abc-123",
            step_id="map",
            substep="fetch",
            status="progress",
            current=5,
            total=10,
            message="Fetched page 5",
        )
    """
    if not run_id:
        raise ValueError("run_id is required")
    if not step_id:
        raise ValueError("step_id is required")

    target_db = db or get_tracking_db()
    if target_db is None:
        logger.warning("Tracking DB not initialized, event not stored")
        return None

    metadata_json = json.dumps(metadata) if metadata else None

    sql = """
        INSERT INTO step_events (run_id, step_id, substep, status, current, total, message, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = [run_id, step_id, substep, status, current, total, message, metadata_json]

    try:
        result = target_db.execute(sql, params)
        return result.last_insert_id
    except DoltQueryError as e:
        logger.error(f"Failed to track event: {e}")
        raise


def write_event(
    run_id: str,
    key: str,
    payload: dict[str, Any],
    *,
    db: DoltDB | None = None,
) -> int | None:
    """Write an event using legacy key-based format.

    This is a compatibility wrapper for older code that uses
    key-based event writing. Maps to track_event() with appropriate
    field extraction from payload.

    Args:
        run_id: Workflow run ID.
        key: Event key (status, progress, error, custom).
        payload: Event payload dict with optional fields:
            - step_id: Step identifier (required if not in payload)
            - substep: Substep name
            - status: Event status
            - current: Progress count
            - total: Total count
            - message: Human-readable message
            - Any additional fields go to metadata

    Returns:
        Inserted event ID, or None if insert failed.

    Example:
        # Legacy style
        write_event("abc-123", "progress", {
            "step_id": "map",
            "current": 5,
            "total": 10,
        })

        # Maps to:
        track_event("abc-123", "map", status="progress", current=5, total=10)
    """
    # Extract standard fields
    step_id = payload.get("step_id", key)  # Use key as step_id if not provided
    substep = payload.get("substep")

    # Map key to status if not in payload
    status = payload.get("status")
    if status is None:
        status_map = {
            EVENT_KEY_STATUS: "running",
            EVENT_KEY_PROGRESS: "progress",
            EVENT_KEY_ERROR: "failed",
            EVENT_KEY_CUSTOM: "progress",
        }
        status = status_map.get(key, "progress")

    current = payload.get("current")
    total = payload.get("total")
    message = payload.get("message")

    # Remaining fields go to metadata
    standard_fields = {"step_id", "substep", "status", "current", "total", "message"}
    metadata = {k: v for k, v in payload.items() if k not in standard_fields}

    return track_event(
        run_id=run_id,
        step_id=step_id,
        substep=substep,
        status=status,
        current=current,
        total=total,
        message=message,
        metadata=metadata if metadata else None,
        db=db,
    )


@dataclass
class _BatchEvent:
    """Internal event for batching."""

    run_id: str
    step_id: str
    substep: str | None
    status: str
    current: int | None
    total: int | None
    message: str | None
    metadata_json: str | None


class EventTracker:
    """Batched event tracker for high-throughput scenarios.

    EventTracker uses a background thread to batch events and flush
    them efficiently. This reduces database round-trips when tracking
    many events in quick succession.

    Thread Safety:
        EventTracker is fully thread-safe. Multiple threads can call
        track() concurrently.

    Batching Behavior:
        Events are flushed when:
        - Batch reaches MAX_BATCH_SIZE (1000 events)
        - FLUSH_TIMEOUT_MS (100ms) expires since last event
        - explicit flush() is called
        - close() is called or context manager exits

    Usage:
        # As context manager (recommended)
        with EventTracker(db) as tracker:
            for i in range(1000):
                tracker.track(run_id="abc", step_id="step", status="progress", current=i)
            # Auto-flushes on exit

        # Manual management
        tracker = EventTracker(db)
        tracker.start()
        tracker.track(run_id="abc", step_id="step", status="running")
        tracker.flush()  # Force flush
        tracker.close()  # Stop background thread
    """

    def __init__(self, db: DoltDB, max_batch_size: int = MAX_BATCH_SIZE):
        """Initialize EventTracker.

        Args:
            db: DoltDB instance for event storage.
            max_batch_size: Maximum events per batch (default: 1000).
        """
        self._db = db
        self._max_batch_size = max_batch_size

        self._queue: Queue[_BatchEvent | None] = Queue()
        self._thread: threading.Thread | None = None
        self._running = False
        self._lock = threading.Lock()

        # For flush synchronization
        self._flush_event = threading.Event()
        self._flush_complete = threading.Event()

    def start(self) -> None:
        """Start the background flush thread.

        Called automatically when used as context manager.
        """
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._flush_loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stop the background flush thread.

        Flushes remaining events before stopping. Called automatically
        when context manager exits.
        """
        with self._lock:
            if not self._running:
                return
            self._running = False

        # Signal thread to stop
        self._queue.put(None)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

    def close(self) -> None:
        """Close the tracker (alias for stop)."""
        self.stop()

    def __enter__(self) -> "EventTracker":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()

    def track(
        self,
        run_id: str,
        step_id: str,
        substep: str | None = None,
        status: EventStatus = "progress",
        current: int | None = None,
        total: int | None = None,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Queue an event for batched insertion.

        This method is non-blocking and thread-safe. Events are queued
        and flushed by the background thread.

        Args:
            run_id: Workflow run ID.
            step_id: Step identifier.
            substep: Optional substep name.
            status: Event status.
            current: Current progress count.
            total: Total items to process.
            message: Human-readable message.
            metadata: Additional data (stored as JSON).

        Raises:
            RuntimeError: If tracker is not started.
        """
        if not self._running:
            raise RuntimeError("EventTracker not started. Use as context manager or call start().")

        metadata_json = json.dumps(metadata) if metadata else None

        event = _BatchEvent(
            run_id=run_id,
            step_id=step_id,
            substep=substep,
            status=status,
            current=current,
            total=total,
            message=message,
            metadata_json=metadata_json,
        )
        self._queue.put(event)

    def flush(self, timeout: float = 5.0) -> None:
        """Force flush all pending events.

        Blocks until all queued events are written to the database.

        Args:
            timeout: Maximum time to wait for flush (seconds).

        Raises:
            TimeoutError: If flush doesn't complete within timeout.
        """
        if not self._running:
            return

        # Signal flush request
        self._flush_complete.clear()
        self._flush_event.set()

        # Wait for flush to complete
        if not self._flush_complete.wait(timeout=timeout):
            raise TimeoutError(f"Flush did not complete within {timeout} seconds")

    def _flush_loop(self) -> None:
        """Background thread that batches and flushes events."""
        batch: list[_BatchEvent] = []
        last_event_time = time.monotonic()

        while True:
            try:
                # Wait for event with timeout
                try:
                    event = self._queue.get(timeout=FLUSH_TIMEOUT_SEC)
                except Empty:
                    event = None

                # Check for stop signal
                if event is None and not self._running:
                    # Final flush before exit
                    if batch:
                        self._flush_batch(batch)
                    self._flush_complete.set()
                    break

                # Check for flush request
                if self._flush_event.is_set():
                    self._flush_event.clear()
                    if batch:
                        self._flush_batch(batch)
                        batch = []
                    self._flush_complete.set()

                # Add event to batch
                if event is not None:
                    batch.append(event)
                    last_event_time = time.monotonic()

                # Check batch size
                if len(batch) >= self._max_batch_size:
                    self._flush_batch(batch)
                    batch = []

                # Check timeout since last event
                elif batch and (time.monotonic() - last_event_time) >= FLUSH_TIMEOUT_SEC:
                    self._flush_batch(batch)
                    batch = []

            except Exception as e:
                logger.error(f"Error in flush loop: {e}")
                # Clear batch to avoid infinite retry
                batch = []

    def _flush_batch(self, batch: list[_BatchEvent]) -> None:
        """Insert a batch of events into the database.

        Uses a single multi-row INSERT for efficiency.

        Args:
            batch: List of events to insert.
        """
        if not batch:
            return

        # Build multi-row INSERT
        # INSERT INTO step_events (run_id, step_id, ...) VALUES (?, ?, ...), (?, ?, ...), ...
        placeholders = "(?, ?, ?, ?, ?, ?, ?, ?)"
        values_clause = ", ".join([placeholders] * len(batch))

        sql = f"""
            INSERT INTO step_events (run_id, step_id, substep, status, current, total, message, metadata)
            VALUES {values_clause}
        """

        params: list[Any] = []
        for event in batch:
            params.extend(
                [
                    event.run_id,
                    event.step_id,
                    event.substep,
                    event.status,
                    event.current,
                    event.total,
                    event.message,
                    event.metadata_json,
                ]
            )

        try:
            self._db.execute(sql, params)
            logger.debug(f"Flushed batch of {len(batch)} events")
        except DoltQueryError as e:
            logger.error(f"Failed to flush batch: {e}")
            # Retry once
            try:
                self._db.execute(sql, params)
            except DoltQueryError as retry_e:
                logger.error(f"Retry failed, dropping batch: {retry_e}")
                raise


# Global tracker instance for convenience
_global_tracker: EventTracker | None = None
_tracker_lock = threading.Lock()


def get_global_tracker() -> EventTracker | None:
    """Get the global EventTracker instance.

    Returns:
        EventTracker instance or None if not initialized.
    """
    with _tracker_lock:
        return _global_tracker


def init_global_tracker(db: DoltDB) -> EventTracker:
    """Initialize and start the global EventTracker.

    Call this once at application startup for batched event tracking.
    The tracker is automatically stopped at program exit.

    Args:
        db: DoltDB instance for event storage.

    Returns:
        The global EventTracker instance.
    """
    global _global_tracker

    with _tracker_lock:
        if _global_tracker is not None:
            return _global_tracker

        _global_tracker = EventTracker(db)
        _global_tracker.start()

        # Register cleanup
        def _cleanup():
            global _global_tracker
            if _global_tracker:
                _global_tracker.stop()
                _global_tracker = None

        atexit.register(_cleanup)

        return _global_tracker


def track_batched(
    run_id: str,
    step_id: str,
    substep: str | None = None,
    status: EventStatus = "progress",
    current: int | None = None,
    total: int | None = None,
    message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Track an event using the global batched tracker.

    This is a convenience function that uses the global EventTracker
    for batched event insertion. If the global tracker is not initialized,
    falls back to track_event() for immediate insertion.

    Args:
        run_id: Workflow run ID.
        step_id: Step identifier.
        substep: Optional substep name.
        status: Event status.
        current: Current progress count.
        total: Total items to process.
        message: Human-readable message.
        metadata: Additional data.
    """
    tracker = get_global_tracker()

    if tracker is not None:
        tracker.track(
            run_id=run_id,
            step_id=step_id,
            substep=substep,
            status=status,
            current=current,
            total=total,
            message=message,
            metadata=metadata,
        )
    else:
        # Fallback to immediate insertion
        track_event(
            run_id=run_id,
            step_id=step_id,
            substep=substep,
            status=status,
            current=current,
            total=total,
            message=message,
            metadata=metadata,
        )
