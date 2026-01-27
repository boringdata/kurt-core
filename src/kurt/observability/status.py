"""Live workflow status queries for Dolt-based observability.

This module provides functions to query workflow status, step details,
and progress information from Dolt tables.

Usage:
    from kurt.observability.status import get_live_status

    db = DoltDB(".dolt")
    status = get_live_status(db, "abc-123")
    print(status["steps"])  # List of step details
    print(status["progress"])  # {current: 10, total: 100}

The returned structure matches what the frontend WorkflowRow component expects.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kurt.db.dolt import DoltDB

logger = logging.getLogger(__name__)


def get_live_status(db: "DoltDB", workflow_id: str) -> dict[str, Any] | None:
    """Get comprehensive live status for a workflow.

    Queries workflow_runs, step_logs, and step_events tables to build
    a complete status view suitable for the frontend.

    Args:
        db: DoltDB instance.
        workflow_id: Full or partial workflow UUID.

    Returns:
        Dict with workflow status, or None if not found.

        Structure:
        {
            "workflow_id": str,
            "name": str,
            "status": str,
            "stage": str | None,
            "progress": {"current": int, "total": int},
            "steps": [
                {
                    "name": str,
                    "status": str,
                    "success": int,
                    "error": int,
                    "duration_ms": int | None,
                    "errors": list[str],
                    "step_type": str,
                }
            ],
            "duration_ms": int | None,
            "inputs": dict | None,
            "cli_command": str | None,
            "error": str | None,
            "started_at": str | None,
            "completed_at": str | None,
        }
    """
    # Get workflow run (supports partial ID matching)
    workflow_row = _get_workflow_run(db, workflow_id)
    if workflow_row is None:
        return None

    full_id = workflow_row["id"]

    # Get step logs
    step_logs = _get_step_logs(db, full_id)

    # Get latest events for progress tracking
    latest_events = _get_latest_events(db, full_id)

    # Build steps array
    steps = _build_steps_array(step_logs)

    # Extract current stage and progress from latest events
    stage, progress = _extract_stage_progress(latest_events, steps)

    # Calculate overall duration
    duration_ms = _calculate_duration(workflow_row)

    # Parse inputs
    inputs = _parse_json_field(workflow_row.get("inputs"))

    # Parse metadata for cli_command
    metadata = _parse_json_field(workflow_row.get("metadata_json"))
    cli_command = metadata.get("cli_command") if metadata else None

    # Determine effective status
    status = _determine_effective_status(workflow_row["status"], steps)

    return {
        "workflow_id": full_id,
        "name": workflow_row.get("workflow", "unknown"),
        "status": status,
        "stage": stage,
        "progress": progress,
        "steps": steps,
        "duration_ms": duration_ms,
        "inputs": inputs,
        "cli_command": cli_command,
        "error": workflow_row.get("error"),
        "started_at": _format_datetime(workflow_row.get("started_at")),
        "completed_at": _format_datetime(workflow_row.get("completed_at")),
    }


def _get_workflow_run(db: "DoltDB", workflow_id: str) -> dict[str, Any] | None:
    """Get workflow run by ID (supports partial matching)."""
    try:
        # Try exact match first
        result = db.query(
            "SELECT * FROM workflow_runs WHERE id = ?",
            [workflow_id],
        )
        if result.rows:
            return result.rows[0]

        # Fall back to prefix match
        result = db.query(
            "SELECT * FROM workflow_runs WHERE id LIKE CONCAT(?, '%') LIMIT 1",
            [workflow_id],
        )
        return result.rows[0] if result.rows else None
    except Exception as e:
        logger.warning(f"Failed to query workflow run: {e}")
        return None


def _get_step_logs(db: "DoltDB", run_id: str) -> list[dict[str, Any]]:
    """Get all step logs for a workflow run."""
    try:
        result = db.query(
            """
            SELECT
                step_id,
                tool,
                status,
                started_at,
                completed_at,
                input_count,
                output_count,
                error_count,
                errors,
                metadata_json
            FROM step_logs
            WHERE run_id = ?
            ORDER BY started_at ASC
            """,
            [run_id],
        )
        return result.rows
    except Exception as e:
        logger.warning(f"Failed to query step logs: {e}")
        return []


def _get_latest_events(db: "DoltDB", run_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """Get latest events for a workflow run."""
    try:
        result = db.query(
            """
            SELECT
                step_id,
                substep,
                status,
                current,
                total,
                message,
                metadata_json,
                created_at
            FROM step_events
            WHERE run_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            [run_id, limit],
        )
        return result.rows
    except Exception as e:
        logger.warning(f"Failed to query step events: {e}")
        return []


def _build_steps_array(step_logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build steps array from step logs with frontend-expected structure."""
    steps = []
    for log in step_logs:
        # Parse errors
        errors_raw = log.get("errors")
        errors_list = []
        if errors_raw:
            parsed = _parse_json_field(errors_raw)
            if isinstance(parsed, list):
                for err in parsed:
                    if isinstance(err, dict):
                        errors_list.append(err.get("message", str(err)))
                    else:
                        errors_list.append(str(err))

        # Calculate duration
        duration_ms = _calculate_step_duration(
            log.get("started_at"),
            log.get("completed_at"),
        )

        # Map status to frontend expectations
        status = _map_step_status(log.get("status", "pending"))

        # Success count is output_count - error_count (or 0 if not available)
        output_count = log.get("output_count") or 0
        error_count = log.get("error_count") or 0
        success_count = max(0, output_count - error_count)

        # Get step type from metadata if available
        metadata = _parse_json_field(log.get("metadata_json"))
        step_type = metadata.get("step_type", "step") if metadata else "step"

        steps.append({
            "name": log.get("step_id", "unknown"),
            "status": status,
            "success": success_count,
            "error": error_count,
            "duration_ms": duration_ms,
            "errors": errors_list,
            "step_type": step_type,
            "input_count": log.get("input_count"),
            "output_count": output_count,
        })

    return steps


def _extract_stage_progress(
    events: list[dict[str, Any]],
    steps: list[dict[str, Any]],
) -> tuple[str | None, dict[str, int]]:
    """Extract current stage and progress from events.

    Returns:
        Tuple of (stage_name, progress_dict).
    """
    # Default progress
    progress = {"current": 0, "total": 0}
    stage = None

    # Find the most recent running step for stage
    for step in reversed(steps):
        if step["status"] == "running":
            stage = step["name"]
            break

    # Look through events for progress info
    for event in events:
        if event.get("current") is not None and event.get("total") is not None:
            progress = {
                "current": event["current"],
                "total": event["total"],
            }
            # Use the event's step_id as stage if we haven't found one
            if stage is None:
                stage = event.get("step_id")
            break

        # Check metadata for progress
        metadata = _parse_json_field(event.get("metadata_json"))
        if metadata:
            if "current" in metadata and "total" in metadata:
                progress = {
                    "current": metadata["current"],
                    "total": metadata["total"],
                }
                if stage is None:
                    stage = event.get("step_id")
                break

    return stage, progress


def _calculate_duration(workflow_row: dict[str, Any]) -> int | None:
    """Calculate workflow duration in milliseconds."""
    started_at = workflow_row.get("started_at")
    completed_at = workflow_row.get("completed_at")

    if not started_at:
        return None

    start = _parse_datetime(started_at)
    if start is None:
        return None

    if completed_at:
        end = _parse_datetime(completed_at)
        if end:
            return int((end - start).total_seconds() * 1000)

    # Workflow still running - calculate from now
    now = datetime.utcnow()
    return int((now - start).total_seconds() * 1000)


def _calculate_step_duration(
    started_at: Any,
    completed_at: Any,
) -> int | None:
    """Calculate step duration in milliseconds."""
    if not started_at:
        return None

    start = _parse_datetime(started_at)
    if start is None:
        return None

    if completed_at:
        end = _parse_datetime(completed_at)
        if end:
            return int((end - start).total_seconds() * 1000)

    # Step still running
    now = datetime.utcnow()
    return int((now - start).total_seconds() * 1000)


def _determine_effective_status(
    workflow_status: str,
    steps: list[dict[str, Any]],
) -> str:
    """Determine effective status, considering step errors.

    If workflow shows as completed but has steps with errors,
    return 'completed_with_errors'.
    """
    if workflow_status == "completed":
        has_errors = any(step.get("error", 0) > 0 for step in steps)
        if has_errors:
            return "completed_with_errors"
    return workflow_status


def _map_step_status(status: str) -> str:
    """Map step status to frontend-expected values."""
    status_map = {
        "pending": "pending",
        "running": "running",
        "completed": "success",
        "failed": "error",
        "canceled": "error",
        "skipped": "skipped",
    }
    return status_map.get(status, status)


def _parse_json_field(value: Any) -> Any:
    """Parse a JSON field that may be string or already parsed."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return None
    return None


def _parse_datetime(value: Any) -> datetime | None:
    """Parse datetime from various formats."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        # Try common formats
        for fmt in [
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
        ]:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None


def _format_datetime(value: Any) -> str | None:
    """Format datetime for JSON output."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return str(value)


def get_step_logs_for_workflow(
    db: "DoltDB",
    workflow_id: str,
    step_name: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get step logs for a workflow, optionally filtered by step name.

    Args:
        db: DoltDB instance.
        workflow_id: Full or partial workflow UUID.
        step_name: Optional step name to filter by.
        limit: Maximum number of logs to return.

    Returns:
        List of step log entries.
    """
    # Get full workflow ID
    workflow_row = _get_workflow_run(db, workflow_id)
    if workflow_row is None:
        return []

    full_id = workflow_row["id"]

    try:
        if step_name:
            result = db.query(
                """
                SELECT * FROM step_logs
                WHERE run_id = ? AND step_id = ?
                ORDER BY started_at ASC
                LIMIT ?
                """,
                [full_id, step_name, limit],
            )
        else:
            result = db.query(
                """
                SELECT * FROM step_logs
                WHERE run_id = ?
                ORDER BY started_at ASC
                LIMIT ?
                """,
                [full_id, limit],
            )
        return result.rows
    except Exception as e:
        logger.warning(f"Failed to query step logs: {e}")
        return []


def get_step_events_for_workflow(
    db: "DoltDB",
    workflow_id: str,
    step_name: str | None = None,
    since_id: int | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get step events for a workflow, optionally filtered.

    Args:
        db: DoltDB instance.
        workflow_id: Full or partial workflow UUID.
        step_name: Optional step name to filter by.
        since_id: Return events after this ID (for pagination).
        limit: Maximum number of events to return.

    Returns:
        List of step event entries.
    """
    # Get full workflow ID
    workflow_row = _get_workflow_run(db, workflow_id)
    if workflow_row is None:
        return []

    full_id = workflow_row["id"]

    try:
        conditions = ["run_id = ?"]
        params: list[Any] = [full_id]

        if step_name:
            conditions.append("step_id = ?")
            params.append(step_name)

        if since_id is not None:
            conditions.append("id > ?")
            params.append(since_id)

        params.append(limit)

        sql = f"""
            SELECT * FROM step_events
            WHERE {' AND '.join(conditions)}
            ORDER BY id ASC
            LIMIT ?
        """
        result = db.query(sql, params)
        return result.rows
    except Exception as e:
        logger.warning(f"Failed to query step events: {e}")
        return []


__all__ = [
    "get_live_status",
    "get_step_logs_for_workflow",
    "get_step_events_for_workflow",
]
