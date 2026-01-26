"""Workflow run lifecycle tracking.

This module provides lifecycle tracking for workflow runs, managing
status transitions and step-level logging.

Usage:
    from kurt.observability import WorkflowLifecycle

    lifecycle = WorkflowLifecycle(db)

    # Start a workflow run
    run_id = lifecycle.create_run("map_workflow", {"url": "https://example.com"})

    # Track step progress
    step_log_id = lifecycle.create_step_log(run_id, "fetch", "FetchTool")
    lifecycle.update_step_log(
        run_id, "fetch",
        status="completed",
        output_count=100,
        error_count=5,
        errors=[{"row_idx": 3, "error_type": "timeout", "message": "Request timed out"}],
    )

    # Complete the workflow
    lifecycle.update_status(run_id, "completed")

Status Transitions:
    - pending -> running -> completed
    - pending -> running -> failed
    - pending -> running -> canceling -> canceled
    - running -> canceling -> canceled

Invalid Transitions (raise InvalidStatusTransition):
    - completed -> running
    - failed -> running
    - canceled -> running
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from kurt.db.dolt import DoltDB, DoltQueryError
from kurt.observability.tracking import EventTracker, track_event

logger = logging.getLogger(__name__)


# Valid workflow statuses
WorkflowStatus = Literal["pending", "running", "completed", "failed", "canceling", "canceled"]

# Valid step statuses
StepStatus = Literal["pending", "running", "completed", "failed", "canceled"]

# Valid status transitions for workflow_runs
VALID_WORKFLOW_TRANSITIONS: dict[WorkflowStatus, set[WorkflowStatus]] = {
    "pending": {"running"},
    "running": {"completed", "failed", "canceling"},
    "canceling": {"canceled"},
    "completed": set(),
    "failed": set(),
    "canceled": set(),
}

# Valid status transitions for step_logs
VALID_STEP_TRANSITIONS: dict[StepStatus, set[StepStatus]] = {
    "pending": {"running"},
    "running": {"completed", "failed", "canceled"},
    "completed": set(),
    "failed": set(),
    "canceled": set(),
}


class LifecycleError(Exception):
    """Base exception for lifecycle operations."""

    pass


class InvalidStatusTransition(LifecycleError):  # noqa: N818
    """Raised when an invalid status transition is attempted."""

    def __init__(self, current: str, target: str, entity: str = "workflow"):
        self.current = current
        self.target = target
        self.entity = entity
        super().__init__(f"Invalid {entity} status transition: {current} -> {target}")


class RunNotFoundError(LifecycleError):
    """Raised when a workflow run is not found."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        super().__init__(f"Workflow run not found: {run_id}")


class StepLogNotFoundError(LifecycleError):
    """Raised when a step log is not found."""

    def __init__(self, run_id: str, step_id: str):
        self.run_id = run_id
        self.step_id = step_id
        super().__init__(f"Step log not found: run_id={run_id}, step_id={step_id}")


@dataclass
class StepSummary:
    """Summary data for a step log.

    Attributes:
        input_count: Number of input items processed.
        output_count: Number of output items produced.
        error_count: Number of errors encountered.
        errors: List of error details [{row_idx, error_type, message}].
        metadata: Additional step metadata.
    """

    input_count: int | None = None
    output_count: int | None = None
    error_count: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkflowLifecycle:
    """Manages workflow run lifecycle and step tracking.

    This class provides methods to:
    - Create and update workflow runs in workflow_runs table
    - Create and update step logs in step_logs table
    - Validate status transitions
    - Optionally emit events via EventTracker

    Thread Safety:
        WorkflowLifecycle methods are thread-safe as they use DoltDB
        which handles its own synchronization.

    Example:
        db = DoltDB(".dolt")
        lifecycle = WorkflowLifecycle(db)

        # Start workflow
        run_id = lifecycle.create_run("map_workflow", {"url": "https://example.com"})

        # Track steps
        lifecycle.create_step_log(run_id, "fetch", "FetchTool")
        lifecycle.update_step_log(run_id, "fetch", status="completed", output_count=100)

        # Complete workflow
        lifecycle.update_status(run_id, "completed")
    """

    def __init__(
        self,
        db: DoltDB,
        tracker: EventTracker | None = None,
        emit_events: bool = True,
    ):
        """Initialize WorkflowLifecycle.

        Args:
            db: DoltDB instance for persistence.
            tracker: Optional EventTracker for emitting events.
                     If None, uses track_event() for individual events.
            emit_events: Whether to emit events to step_events table.
                        Set to False to only update workflow_runs/step_logs.
        """
        self._db = db
        self._tracker = tracker
        self._emit_events = emit_events

    # =========================================================================
    # Workflow Run Management
    # =========================================================================

    def create_run(
        self,
        workflow: str,
        inputs: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        run_id: str | None = None,
        status: WorkflowStatus = "running",
    ) -> str:
        """Create a new workflow run.

        Inserts a row into workflow_runs with the specified status.

        Args:
            workflow: Workflow name (e.g., "map_workflow", "fetch_workflow").
            inputs: Input parameters for the workflow (stored as JSON).
            metadata: Additional metadata (stored as JSON).
            run_id: Optional run ID. If not provided, generates a UUID.
            status: Initial status (default: "running").

        Returns:
            The run ID (UUID string).

        Raises:
            DoltQueryError: If database insert fails.

        Example:
            run_id = lifecycle.create_run(
                "map_workflow",
                inputs={"url": "https://example.com", "max_pages": 100},
            )
        """
        if run_id is None:
            run_id = str(uuid.uuid4())

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        inputs_json = json.dumps(inputs) if inputs else None
        metadata_json = json.dumps(metadata) if metadata else None

        sql = """
            INSERT INTO workflow_runs (id, workflow, status, started_at, inputs, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = [run_id, workflow, status, now, inputs_json, metadata_json]

        try:
            self._db.execute(sql, params)
            logger.info(f"Created workflow run: {run_id} ({workflow}) status={status}")

            # Emit event if enabled
            if self._emit_events:
                self._emit_event(
                    run_id=run_id,
                    step_id="workflow",
                    status="running",
                    message=f"Workflow {workflow} started",
                    metadata={"workflow": workflow, "inputs": inputs},
                )

            return run_id
        except DoltQueryError as e:
            logger.error(f"Failed to create workflow run: {e}")
            raise

    def update_status(
        self,
        run_id: str,
        status: WorkflowStatus,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update the status of a workflow run.

        Validates the status transition before updating. Updates completed_at
        timestamp for terminal states (completed, failed, canceled).

        Args:
            run_id: The workflow run ID.
            status: New status to set.
            error: Error message (for failed status).
            metadata: Additional metadata to merge with existing.

        Raises:
            RunNotFoundError: If run_id does not exist.
            InvalidStatusTransition: If the transition is not allowed.
            DoltQueryError: If database update fails.

        Example:
            # Complete successfully
            lifecycle.update_status(run_id, "completed")

            # Mark as failed with error
            lifecycle.update_status(run_id, "failed", error="Fetch failed: timeout")
        """
        # Get current status
        current_row = self._db.query_one(
            "SELECT status, metadata_json FROM workflow_runs WHERE id = ?", [run_id]
        )
        if current_row is None:
            raise RunNotFoundError(run_id)

        current_status = current_row["status"]

        # Validate transition
        if status not in VALID_WORKFLOW_TRANSITIONS.get(current_status, set()):
            raise InvalidStatusTransition(current_status, status, entity="workflow")

        # Build update
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        is_terminal = status in ("completed", "failed", "canceled")

        # Merge metadata if provided
        merged_metadata = None
        if metadata:
            existing = json.loads(current_row["metadata_json"]) if current_row.get("metadata_json") else {}
            merged_metadata = json.dumps({**existing, **metadata})

        if is_terminal:
            if merged_metadata:
                sql = "UPDATE workflow_runs SET status = ?, completed_at = ?, error = ?, metadata_json = ? WHERE id = ?"
                params = [status, now, error, merged_metadata, run_id]
            else:
                sql = "UPDATE workflow_runs SET status = ?, completed_at = ?, error = ? WHERE id = ?"
                params = [status, now, error, run_id]
        else:
            if merged_metadata:
                sql = "UPDATE workflow_runs SET status = ?, metadata_json = ? WHERE id = ?"
                params = [status, merged_metadata, run_id]
            else:
                sql = "UPDATE workflow_runs SET status = ? WHERE id = ?"
                params = [status, run_id]

        try:
            self._db.execute(sql, params)
            logger.info(f"Updated workflow run {run_id}: status={status}")

            # Emit event if enabled
            if self._emit_events:
                event_status = "completed" if status == "completed" else "failed" if status in ("failed", "canceled") else "running"
                self._emit_event(
                    run_id=run_id,
                    step_id="workflow",
                    status=event_status,
                    message=f"Workflow status changed to {status}" + (f": {error}" if error else ""),
                    metadata={"status": status, "error": error} if error else {"status": status},
                )

        except DoltQueryError as e:
            logger.error(f"Failed to update workflow status: {e}")
            raise

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Get a workflow run by ID.

        Args:
            run_id: The workflow run ID.

        Returns:
            Dict with run data, or None if not found.
        """
        return self._db.query_one("SELECT * FROM workflow_runs WHERE id = ?", [run_id])

    # =========================================================================
    # Step Log Management
    # =========================================================================

    def create_step_log(
        self,
        run_id: str,
        step_id: str,
        tool: str,
        status: StepStatus = "running",
        input_count: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create a step log entry.

        Inserts a row into step_logs table.

        Args:
            run_id: The workflow run ID.
            step_id: Step identifier (e.g., "fetch", "extract").
            tool: Tool name (e.g., "FetchTool", "MapTool").
            status: Initial status (default: "running").
            input_count: Number of input items (optional).
            metadata: Additional metadata (stored as JSON).

        Returns:
            The step log ID (UUID string).

        Raises:
            DoltQueryError: If database insert fails.

        Example:
            step_log_id = lifecycle.create_step_log(
                run_id,
                step_id="fetch",
                tool="FetchTool",
                input_count=50,
            )
        """
        step_log_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        metadata_json = json.dumps(metadata) if metadata else None

        sql = """
            INSERT INTO step_logs (id, run_id, step_id, tool, status, started_at, input_count, error_count, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = [step_log_id, run_id, step_id, tool, status, now, input_count, 0, metadata_json]

        try:
            self._db.execute(sql, params)
            logger.debug(f"Created step log: {step_log_id} (run={run_id}, step={step_id})")

            # Emit event if enabled
            if self._emit_events:
                self._emit_event(
                    run_id=run_id,
                    step_id=step_id,
                    status="running",
                    message=f"Step {step_id} started (tool={tool})",
                    metadata={"tool": tool, "input_count": input_count},
                )

            return step_log_id
        except DoltQueryError as e:
            logger.error(f"Failed to create step log: {e}")
            raise

    def update_step_log(
        self,
        run_id: str,
        step_id: str,
        status: StepStatus | None = None,
        output_count: int | None = None,
        error_count: int | None = None,
        errors: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update a step log entry.

        Updates the step_logs row identified by (run_id, step_id).
        Sets completed_at for terminal states.

        Args:
            run_id: The workflow run ID.
            step_id: Step identifier.
            status: New status (optional).
            output_count: Number of output items produced.
            error_count: Number of errors encountered.
            errors: List of error details [{row_idx, error_type, message}].
            metadata: Additional metadata to merge with existing.

        Raises:
            StepLogNotFoundError: If step log does not exist.
            InvalidStatusTransition: If status transition is invalid.
            DoltQueryError: If database update fails.

        Example:
            lifecycle.update_step_log(
                run_id,
                "fetch",
                status="completed",
                output_count=95,
                error_count=5,
                errors=[
                    {"row_idx": 3, "error_type": "timeout", "message": "Request timed out"},
                    {"row_idx": 12, "error_type": "http_error", "message": "404 Not Found"},
                ],
            )
        """
        # Get current state
        current_row = self._db.query_one(
            "SELECT status, metadata_json FROM step_logs WHERE run_id = ? AND step_id = ?",
            [run_id, step_id],
        )
        if current_row is None:
            raise StepLogNotFoundError(run_id, step_id)

        # Validate status transition if status is being changed
        if status is not None:
            current_status = current_row["status"]
            if status not in VALID_STEP_TRANSITIONS.get(current_status, set()):
                raise InvalidStatusTransition(current_status, status, entity="step")

        # Build dynamic UPDATE
        updates = []
        params = []

        if status is not None:
            updates.append("status = ?")
            params.append(status)

            # Set completed_at for terminal states
            if status in ("completed", "failed", "canceled"):
                now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                updates.append("completed_at = ?")
                params.append(now)

        if output_count is not None:
            updates.append("output_count = ?")
            params.append(output_count)

        if error_count is not None:
            updates.append("error_count = ?")
            params.append(error_count)

        if errors is not None:
            updates.append("errors = ?")
            params.append(json.dumps(errors))

        if metadata is not None:
            existing = json.loads(current_row["metadata_json"]) if current_row.get("metadata_json") else {}
            merged = {**existing, **metadata}
            updates.append("metadata_json = ?")
            params.append(json.dumps(merged))

        if not updates:
            return  # Nothing to update

        sql = f"UPDATE step_logs SET {', '.join(updates)} WHERE run_id = ? AND step_id = ?"
        params.extend([run_id, step_id])

        try:
            self._db.execute(sql, params)
            logger.debug(f"Updated step log: run={run_id}, step={step_id}, status={status}")

            # Emit event if enabled and status changed to terminal
            if self._emit_events and status in ("completed", "failed", "canceled"):
                event_status = "completed" if status == "completed" else "failed"
                error_msg = errors[0]["message"] if errors and len(errors) > 0 else None
                self._emit_event(
                    run_id=run_id,
                    step_id=step_id,
                    status=event_status,
                    message=f"Step {step_id} {status}" + (f": {error_msg}" if error_msg else ""),
                    metadata={
                        "output_count": output_count,
                        "error_count": error_count,
                    },
                )

        except DoltQueryError as e:
            logger.error(f"Failed to update step log: {e}")
            raise

    def get_step_log(self, run_id: str, step_id: str) -> dict[str, Any] | None:
        """Get a step log by run_id and step_id.

        Args:
            run_id: The workflow run ID.
            step_id: Step identifier.

        Returns:
            Dict with step log data, or None if not found.
        """
        return self._db.query_one(
            "SELECT * FROM step_logs WHERE run_id = ? AND step_id = ?",
            [run_id, step_id],
        )

    def get_step_logs(self, run_id: str) -> list[dict[str, Any]]:
        """Get all step logs for a workflow run.

        Args:
            run_id: The workflow run ID.

        Returns:
            List of step log dicts.
        """
        result = self._db.query(
            "SELECT * FROM step_logs WHERE run_id = ? ORDER BY started_at ASC",
            [run_id],
        )
        return result.rows

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def on_workflow_start(
        self,
        workflow: str,
        inputs: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> str:
        """Callback for workflow start (creates run with status='running').

        This is a convenience alias for create_run().

        Args:
            workflow: Workflow name.
            inputs: Input parameters.
            run_id: Optional run ID.

        Returns:
            The run ID.
        """
        return self.create_run(workflow, inputs=inputs, run_id=run_id, status="running")

    def on_step_start(
        self,
        run_id: str,
        step_id: str,
        tool: str,
        input_count: int | None = None,
    ) -> str:
        """Callback for step start (creates step log with status='running').

        Args:
            run_id: The workflow run ID.
            step_id: Step identifier.
            tool: Tool name.
            input_count: Number of input items.

        Returns:
            The step log ID.
        """
        return self.create_step_log(
            run_id, step_id, tool,
            status="running",
            input_count=input_count,
        )

    def on_step_complete(
        self,
        run_id: str,
        step_id: str,
        output_count: int,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        """Callback for step completion.

        Args:
            run_id: The workflow run ID.
            step_id: Step identifier.
            output_count: Number of output items.
            errors: Optional list of non-fatal errors.
        """
        error_count = len(errors) if errors else 0
        self.update_step_log(
            run_id, step_id,
            status="completed",
            output_count=output_count,
            error_count=error_count,
            errors=errors,
        )

    def on_step_fail(
        self,
        run_id: str,
        step_id: str,
        error: str,
        error_type: str = "error",
    ) -> None:
        """Callback for step failure.

        Args:
            run_id: The workflow run ID.
            step_id: Step identifier.
            error: Error message.
            error_type: Error type classification.
        """
        self.update_step_log(
            run_id, step_id,
            status="failed",
            error_count=1,
            errors=[{"row_idx": None, "error_type": error_type, "message": error}],
        )

    def on_workflow_complete(self, run_id: str) -> None:
        """Callback for workflow completion.

        Args:
            run_id: The workflow run ID.
        """
        self.update_status(run_id, "completed")

    def on_workflow_fail(self, run_id: str, error: str) -> None:
        """Callback for workflow failure.

        Args:
            run_id: The workflow run ID.
            error: Error message.
        """
        self.update_status(run_id, "failed", error=error)

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _emit_event(
        self,
        run_id: str,
        step_id: str,
        status: str,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Emit an event to step_events table.

        Uses EventTracker if available, otherwise falls back to track_event().
        """
        if self._tracker is not None:
            self._tracker.track(
                run_id=run_id,
                step_id=step_id,
                status=status,
                message=message,
                metadata=metadata,
            )
        else:
            track_event(
                run_id=run_id,
                step_id=step_id,
                status=status,
                message=message,
                metadata=metadata,
                db=self._db,
            )
