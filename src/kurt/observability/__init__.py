"""Kurt observability module - tracking and monitoring for workflows.

This module provides:
- Event tracking for workflow steps (track_event, write_event)
- EventTracker class for batched event insertion
- WorkflowLifecycle class for workflow run lifecycle management
- Real-time event streaming (stream_events, StatusStreamer)
- LLM call tracing (trace_llm_call, get_traces, LLMTrace)
- Integration with DoltDB for persistent storage

Usage:
    from kurt.observability import track_event, EventTracker, init_tracking
    from kurt.observability import WorkflowLifecycle
    from kurt.observability import trace_llm_call, get_traces, LLMTrace
    from kurt.db.dolt import DoltDB

    # Initialize global tracking DB
    db = DoltDB("/path/to/.dolt")
    init_tracking(db)

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
    from kurt.observability import stream_events, format_event

    for event in stream_events(db, run_id="abc-123"):
        print(format_event(event))

    # LLM call tracing
    trace_id = trace_llm_call(
        run_id="abc-123",
        step_id="extract",
        model="gpt-4",
        provider="openai",
        prompt="Extract entities...",
        response="{'entities': [...]}",
        tokens_in=120,
        tokens_out=34,
        cost=0.0023,
        latency_ms=450,
    )
"""

from .lifecycle import (
    InvalidStatusTransition,
    LifecycleError,
    RunNotFoundError,
    StepLogNotFoundError,
    StepStatus,
    StepSummary,
    WorkflowLifecycle,
    WorkflowStatus,
)
from .streaming import (
    DEFAULT_BATCH_LIMIT,
    DEFAULT_POLL_MS,
    TERMINAL_STATUSES,
    StatusStreamer,
    StepEvent,
    format_event,
    stream_events,
)
from .traces import (
    LLMTrace,
    get_trace,
    get_traces,
    get_traces_summary,
    get_tracing_db,
    init_tracing,
    trace_llm_call,
)
from .tracking import (
    EVENT_KEY_CUSTOM,
    EVENT_KEY_ERROR,
    EVENT_KEY_PROGRESS,
    EVENT_KEY_STATUS,
    EventStatus,
    EventTracker,
    SubstepEvent,
    get_global_tracker,
    get_tracking_db,
    init_global_tracker,
    init_tracking,
    track_batched,
    track_event,
    write_event,
)

__all__ = [
    # Core functions
    "track_event",
    "write_event",
    "track_batched",
    # Streaming functions
    "stream_events",
    "format_event",
    # LLM tracing functions
    "trace_llm_call",
    "get_traces",
    "get_trace",
    "get_traces_summary",
    "init_tracing",
    "get_tracing_db",
    # Classes
    "EventTracker",
    "SubstepEvent",
    "StatusStreamer",
    "StepEvent",
    "WorkflowLifecycle",
    "StepSummary",
    "LLMTrace",
    # Exceptions
    "LifecycleError",
    "InvalidStatusTransition",
    "RunNotFoundError",
    "StepLogNotFoundError",
    # Initialization
    "init_tracking",
    "get_tracking_db",
    "init_global_tracker",
    "get_global_tracker",
    # Event keys (legacy)
    "EVENT_KEY_STATUS",
    "EVENT_KEY_PROGRESS",
    "EVENT_KEY_ERROR",
    "EVENT_KEY_CUSTOM",
    # Type aliases
    "EventStatus",
    "WorkflowStatus",
    "StepStatus",
    # Constants
    "DEFAULT_POLL_MS",
    "DEFAULT_BATCH_LIMIT",
    "TERMINAL_STATUSES",
]
