"""
DBOS event integration for the indexing pipeline.

This module provides event emission for DBOS workflows to track model execution
and coordinate between different parts of the pipeline.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ModelEvent:
    """Event emitted by a model during execution."""

    model_name: str
    event_type: str  # "started", "completed", "failed", "progress"
    timestamp: datetime
    workflow_id: Optional[str] = None
    run_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DBOSEventEmitter:
    """
    Event emitter for DBOS workflow integration.

    This class emits events that DBOS workflows can listen to for:
    - Model execution lifecycle (start, complete, fail)
    - Progress updates during long-running operations
    - Data availability notifications
    - Error and retry signals
    """

    def __init__(self, workflow_id: Optional[str] = None, run_id: Optional[str] = None):
        """
        Initialize the event emitter.

        Args:
            workflow_id: Current workflow ID
            run_id: Current run ID
        """
        self.workflow_id = workflow_id
        self.run_id = run_id
        self._events = []  # Store events for testing/debugging

    def emit_model_started(self, model_name: str, context: Optional[Dict[str, Any]] = None):
        """
        Emit an event when a model starts execution.

        Args:
            model_name: Name of the model starting
            context: Optional execution context
        """
        event = ModelEvent(
            model_name=model_name,
            event_type="started",
            timestamp=datetime.utcnow(),
            workflow_id=self.workflow_id,
            run_id=self.run_id,
            payload=context,
        )
        self._emit_event(event)

    def emit_model_completed(
        self,
        model_name: str,
        rows_written: int,
        execution_time: float,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Emit an event when a model completes successfully.

        Args:
            model_name: Name of the model
            rows_written: Number of rows written
            execution_time: Execution time in seconds
            metadata: Optional additional metadata
        """
        payload = {
            "rows_written": rows_written,
            "execution_time": execution_time,
        }
        if metadata:
            payload.update(metadata)

        event = ModelEvent(
            model_name=model_name,
            event_type="completed",
            timestamp=datetime.utcnow(),
            workflow_id=self.workflow_id,
            run_id=self.run_id,
            payload=payload,
        )
        self._emit_event(event)

    def emit_model_failed(
        self, model_name: str, error: Exception, context: Optional[Dict[str, Any]] = None
    ):
        """
        Emit an event when a model fails.

        Args:
            model_name: Name of the model
            error: The exception that caused the failure
            context: Optional error context
        """
        event = ModelEvent(
            model_name=model_name,
            event_type="failed",
            timestamp=datetime.utcnow(),
            workflow_id=self.workflow_id,
            run_id=self.run_id,
            payload=context,
            error=str(error),
        )
        self._emit_event(event)

    def emit_progress(
        self, model_name: str, current: int, total: int, message: Optional[str] = None
    ):
        """
        Emit a progress update event.

        Args:
            model_name: Name of the model
            current: Current progress count
            total: Total items to process
            message: Optional progress message
        """
        event = ModelEvent(
            model_name=model_name,
            event_type="progress",
            timestamp=datetime.utcnow(),
            workflow_id=self.workflow_id,
            run_id=self.run_id,
            payload={
                "current": current,
                "total": total,
                "percentage": (current / total * 100) if total > 0 else 0,
                "message": message,
            },
        )
        self._emit_event(event)

    def emit_data_available(
        self, table_name: str, row_count: int, model_name: Optional[str] = None
    ):
        """
        Emit an event when new data is available in a table.

        This allows downstream models to react to data availability.

        Args:
            table_name: Name of the table with new data
            row_count: Number of rows available
            model_name: Optional model that produced the data
        """
        event = ModelEvent(
            model_name=model_name or "system",
            event_type="data_available",
            timestamp=datetime.utcnow(),
            workflow_id=self.workflow_id,
            run_id=self.run_id,
            payload={
                "table_name": table_name,
                "row_count": row_count,
            },
        )
        self._emit_event(event)

    def emit_step_error(
        self,
        model_name: str,
        error_payload: Dict[str, Any],
        workflow_id: Optional[str] = None,
    ):
        """
        Emit an event when a step error occurs.

        This records structured error information for dashboards and CLI surfaces.
        The error_payload should come from WorkflowStepError.to_event_payload().

        Args:
            model_name: Name of the model where the error occurred
            error_payload: Structured error data from WorkflowStepError.to_event_payload()
                Contains: step, message, action, severity, documents, metadata, retryable
            workflow_id: Optional workflow ID override
        """
        event = ModelEvent(
            model_name=model_name,
            event_type="step_error",
            timestamp=datetime.utcnow(),
            workflow_id=workflow_id or self.workflow_id,
            run_id=self.run_id,
            payload=error_payload,
            error=error_payload.get("message"),
        )
        self._emit_event(event)

        # Log with structured context
        doc_count = len(error_payload.get("documents", []))
        action = error_payload.get("action", "unknown")
        severity = error_payload.get("severity", "unknown")

        log_message = (
            f"Step error [{error_payload.get('step')}]: {error_payload.get('message')} "
            f"(action={action}, severity={severity}, documents={doc_count})"
        )

        if severity == "fatal":
            logger.error(log_message)
        elif severity == "recoverable":
            logger.warning(log_message)
        else:
            logger.info(log_message)

    def _emit_event(self, event: ModelEvent):
        """
        Internal method to emit an event.

        In production, this would integrate with DBOS event system.
        For now, it logs the event and stores it for testing.

        Args:
            event: The event to emit
        """
        # Store for testing/debugging
        self._events.append(event)

        # Log the event
        logger.info(
            f"DBOS Event: {event.event_type} for {event.model_name}",
            extra={
                "event_type": event.event_type,
                "model_name": event.model_name,
                "workflow_id": event.workflow_id,
                "run_id": event.run_id,
                "payload": event.payload,
            },
        )

        # TODO: Integrate with actual DBOS event system
        # This would involve sending the event to DBOS for workflow coordination
        # For example:
        # dbos_client.emit_event(
        #     workflow_id=event.workflow_id,
        #     event_type=f"model.{event.event_type}",
        #     data=self._serialize_event(event)
        # )

    def _serialize_event(self, event: ModelEvent) -> str:
        """
        Serialize an event to JSON.

        Args:
            event: Event to serialize

        Returns:
            JSON string representation
        """
        data = {
            "model_name": event.model_name,
            "event_type": event.event_type,
            "timestamp": event.timestamp.isoformat(),
            "workflow_id": event.workflow_id,
            "run_id": event.run_id,
            "payload": event.payload,
            "error": event.error,
        }
        return json.dumps(data, default=str)

    def get_events(self) -> list[ModelEvent]:
        """
        Get all emitted events (for testing/debugging).

        Returns:
            List of emitted events
        """
        return self._events.copy()

    def clear_events(self):
        """Clear stored events (for testing)."""
        self._events.clear()


# Global event emitter instance (can be configured per workflow)
_global_emitter = None


def get_event_emitter() -> DBOSEventEmitter:
    """
    Get the global event emitter instance.

    Returns:
        The global DBOSEventEmitter instance
    """
    global _global_emitter
    if _global_emitter is None:
        _global_emitter = DBOSEventEmitter()
    return _global_emitter


def configure_event_emitter(workflow_id: Optional[str] = None, run_id: Optional[str] = None):
    """
    Configure the global event emitter with workflow context.

    Args:
        workflow_id: Workflow ID to use
        run_id: Run ID to use
    """
    global _global_emitter
    _global_emitter = DBOSEventEmitter(workflow_id=workflow_id, run_id=run_id)


async def emit_batch_status(status_data: Dict[str, Any]):
    """
    Emit a batch status event for DBOS display.

    This function emits status updates that DBOS uses to display workflow progress
    in the UI, including batch totals, current status, and completion state.

    Args:
        status_data: Dict containing status information:
            - batch_total: Total number of items in batch
            - batch_status: Current status string (e.g., "splitting", "extracting", "complete")
            - active_docs: Number of documents being processed
            - skipped_docs: Number of documents skipped
            - workflow_done: Whether the workflow is complete
    """
    # Log for debugging (always works)
    logger.info(
        f"Batch status: {status_data.get('batch_status', 'unknown')} "
        f"(total: {status_data.get('batch_total', 0)}, "
        f"active: {status_data.get('active_docs', 0)}, "
        f"skipped: {status_data.get('skipped_docs', 0)})"
    )

    try:
        from dbos import DBOS

        # Check if write_stream exists and is callable
        if hasattr(DBOS, "write_stream"):
            result = DBOS.write_stream("display", status_data)
            # Handle both sync and async versions
            if hasattr(result, "__await__"):
                await result

    except Exception as e:
        # Don't fail the workflow if status emission fails
        logger.debug(f"DBOS stream write skipped: {e}")
