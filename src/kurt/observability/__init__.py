"""Kurt observability module - tracking and monitoring for workflows.

This module provides:
- Event tracking for workflow steps (track_event)
- EventTracker class for batched event insertion
- WorkflowLifecycle class for workflow run lifecycle management
- Real-time event streaming (stream_events, format_event)
- Live status queries (get_live_status)

Usage:
    from kurt.observability import track_event, EventTracker
    from kurt.observability import WorkflowLifecycle
    from kurt.observability import stream_events, format_event
    from kurt.observability import get_live_status

    # Simple event tracking
    event_id = track_event(
        run_id="abc-123",
        step_id="map",
        status="progress",
        current=5,
        total=10,
    )

    # Batched tracking (high throughput)
    with EventTracker(db) as tracker:
        for i in range(1000):
            tracker.track(run_id="abc-123", step_id="map", status="progress", current=i)

    # Workflow lifecycle tracking
    lifecycle = WorkflowLifecycle(db)
    run_id = lifecycle.create_run("map_workflow", {"url": "https://example.com"})
    lifecycle.create_step_log(run_id, "fetch", "FetchTool")
    lifecycle.update_step_log(run_id, "fetch", status="completed", output_count=100)
    lifecycle.update_status(run_id, "completed")

    # Real-time streaming (--follow mode)
    for event in stream_events(db, run_id="abc-123"):
        print(format_event(event))

    # Live status queries
    status = get_live_status(db, "abc-123")
    print(status["steps"])  # List of step details with progress
"""

from .lifecycle import WorkflowLifecycle
from .status import get_live_status, get_step_events_for_workflow, get_step_logs_for_workflow
from .streaming import TERMINAL_STATUSES, format_event, stream_events
from .tracking import EventTracker, track_event

__all__ = [
    "track_event",
    "EventTracker",
    "WorkflowLifecycle",
    "stream_events",
    "format_event",
    "TERMINAL_STATUSES",
    "get_live_status",
    "get_step_logs_for_workflow",
    "get_step_events_for_workflow",
]
