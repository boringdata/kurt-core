from __future__ import annotations

import base64
import os
import pickle
from datetime import datetime
from typing import Any

from sqlalchemy import text

from kurt.db import managed_session


def _get_dbos_schema() -> str:
    """Get DBOS schema name (dbos for Postgres, empty for SQLite)."""
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("postgresql"):
        return "dbos"
    return ""  # SQLite doesn't use schemas


def _dbos_table(table: str) -> str:
    """Return schema-qualified table name for DBOS tables."""
    schema = _get_dbos_schema()
    if schema:
        return f"{schema}.{table}"
    return table


def get_dbos_table_names() -> dict[str, str]:
    """Get schema-qualified DBOS table names.

    Returns dict with keys: workflow_status, workflow_events, streams
    Values are schema-qualified for Postgres, plain for SQLite.
    """
    return {
        "workflow_status": _dbos_table("workflow_status"),
        "workflow_events": _dbos_table("workflow_events"),
        "streams": _dbos_table("streams"),
    }


def _decode_dbos_value(value: Any) -> Any:
    if value is None:
        return None
    raw = value
    if isinstance(raw, memoryview):
        raw = raw.tobytes()
    if isinstance(raw, bytes):
        try:
            decoded = base64.b64decode(raw)
            return pickle.loads(decoded)
        except Exception:
            try:
                return pickle.loads(raw)
            except Exception:
                return raw
    if isinstance(raw, str):
        try:
            decoded = base64.b64decode(raw)
            return pickle.loads(decoded)
        except Exception:
            return raw
    return raw


def read_workflow_events(workflow_id: str) -> dict[str, Any]:
    """
    Read DBOS workflow events into a dict.
    """
    table = _dbos_table("workflow_events")
    with managed_session() as session:
        rows = session.execute(
            text(f"SELECT key, value FROM {table} WHERE workflow_uuid = :workflow_id"),
            {"workflow_id": workflow_id},
        ).all()

    events: dict[str, Any] = {}
    for key, value in rows:
        events[key] = _decode_dbos_value(value)
    return events


def read_workflow_streams(
    workflow_id: str,
    *,
    key: str | None = None,
    since_offset: int | None = None,
    limit: int | None = None,
    desc: bool = False,
) -> list[dict[str, Any]]:
    """
    Read DBOS streams (decoded) for a workflow.
    """
    table = _dbos_table("streams")
    params: dict[str, Any] = {"workflow_id": workflow_id}
    query = f'SELECT key, value, "offset" FROM {table} WHERE workflow_uuid = :workflow_id'
    if key:
        query += " AND key = :key"
        params["key"] = key
    if since_offset is not None:
        query += ' AND "offset" > :since_offset'
        params["since_offset"] = since_offset
    query += ' ORDER BY "offset"' + (" DESC" if desc else "")
    if limit is not None:
        query += " LIMIT :limit"
        params["limit"] = limit

    with managed_session() as session:
        rows = session.execute(text(query), params).all()

    streams: list[dict[str, Any]] = []
    for row_key, value, offset in rows:
        decoded = _decode_dbos_value(value)
        entry = {"key": row_key, "offset": offset}
        if isinstance(decoded, dict):
            entry.update(decoded)
        else:
            entry["value"] = decoded
        streams.append(entry)
    return streams


def paginate_stream(
    workflow_id: str,
    *,
    key: str | None = None,
    since_offset: int | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """
    Read a stream page and return the next offset for polling.
    """
    items = read_workflow_streams(
        workflow_id,
        key=key,
        since_offset=since_offset,
        limit=limit,
    )
    next_offset = since_offset
    if items:
        next_offset = items[-1]["offset"]
    return {
        "items": items,
        "next_offset": next_offset,
        "has_more": len(items) == limit,
    }


def get_step_logs(
    workflow_id: str,
    *,
    step_name: str | None = None,
    limit: int = 200,
    since_offset: int | None = None,
) -> list[dict[str, Any]]:
    """
    Get logs emitted via DBOS streams.
    """
    logs = read_workflow_streams(
        workflow_id,
        key="logs",
        since_offset=since_offset,
        limit=limit,
    )
    if step_name:
        logs = [entry for entry in logs if entry.get("step") == step_name]
    return logs


def get_step_logs_page(
    workflow_id: str,
    *,
    step_name: str | None = None,
    limit: int = 200,
    since_offset: int | None = None,
) -> dict[str, Any]:
    """
    Paginated logs for live polling.
    """
    page = paginate_stream(
        workflow_id,
        key="logs",
        since_offset=since_offset,
        limit=limit,
    )
    items = page["items"]
    if step_name:
        items = [entry for entry in items if entry.get("step") == step_name]
    page["items"] = items
    return page


def get_progress_page(
    workflow_id: str,
    *,
    step_name: str | None = None,
    limit: int = 200,
    since_offset: int | None = None,
) -> dict[str, Any]:
    """
    Paginated progress events for live polling.
    """
    page = paginate_stream(
        workflow_id,
        key="progress",
        since_offset=since_offset,
        limit=limit,
    )
    items = page["items"]
    if step_name:
        items = [entry for entry in items if entry.get("step") == step_name]
    page["items"] = items
    return page


def get_live_status(workflow_id: str) -> dict[str, Any]:
    """
    Live workflow status derived from DBOS events + progress streams.

    Returns:
        {
            "workflow_id": "...",
            "status": "running|completed|error|unknown",
            "current_step": "...",
            "stage": "...",
            "progress": {"current": 0, "total": 0},
            "steps": [
                {
                    "name": "extract",
                    "status": "running|completed|error",
                    "current": 4,
                    "total": 10,
                    "success": 4,
                    "error": 0,
                    "last_latency_ms": 210
                },
            ],
            "last_log": "...",
            "inputs": {...},
            "duration_ms": 1234,
        }
    """
    events = read_workflow_events(workflow_id)
    progress_events = read_workflow_streams(workflow_id, key="progress")
    # Get most recent log (desc=True to get newest first)
    recent_logs = read_workflow_streams(workflow_id, key="logs", limit=1, desc=True)

    # Fetch workflow metadata (inputs) from workflow_status table
    workflow_inputs = None
    status_table = _dbos_table("workflow_status")
    with managed_session() as session:
        row = session.execute(
            text(f"SELECT inputs FROM {status_table} WHERE workflow_uuid = :id"),
            {"id": workflow_id},
        ).fetchone()
        if row:
            (inputs_raw,) = row
            if inputs_raw:
                decoded = _decode_dbos_value(inputs_raw)
                if isinstance(decoded, dict):
                    # DBOS stores inputs as {"args": [...], "kwargs": {...}}
                    args = decoded.get("args")
                    if isinstance(args, list) and len(args) > 0:
                        # First positional arg is usually the config dict
                        first_arg = args[0]
                        if isinstance(first_arg, dict):
                            workflow_inputs = first_arg
                        else:
                            workflow_inputs = {"args": args}
                    elif args:
                        workflow_inputs = args

    # Calculate duration from workflow events (started_at, completed_at)
    workflow_duration_ms = None
    started_at = events.get("started_at")
    completed_at = events.get("completed_at")
    if started_at is not None and completed_at is not None:
        try:
            workflow_duration_ms = int((float(completed_at) - float(started_at)) * 1000)
        except (TypeError, ValueError):
            pass

    step_state: dict[str, dict[str, Any]] = {}
    for event in progress_events:
        step = event.get("step")
        if not step:
            continue
        state = step_state.setdefault(
            step,
            {
                "seen": set(),
                "seen_success": set(),  # Track unique successful idx values
                "seen_error": set(),  # Track unique error idx values
                "current": 0,
                "total": 0,
                "errors": [],  # List of error messages
                "last_status": None,
                "last_latency_ms": None,
                "start_timestamp": None,
                "end_timestamp": None,
                "last_timestamp": None,
                "step_type": None,
            },
        )

        step_type = event.get("type")
        if step_type:
            state["step_type"] = step_type

        total = event.get("total")
        if isinstance(total, int):
            state["total"] = max(state["total"], total)

        current = event.get("current")
        if isinstance(current, int):
            state["current"] = max(state["current"], current)

        idx = event.get("idx")
        if isinstance(idx, int):
            state["seen"].add(idx)

        status = event.get("status")
        if status:
            state["last_status"] = status
        # Only count success/error if we have an idx (unique per document)
        if status == "success" and idx is not None:
            state["seen_success"].add(idx)
        elif status == "error" and idx is not None:
            state["seen_error"].add(idx)
            # Capture error message if present
            error_msg = event.get("error")
            if error_msg and len(state["errors"]) < 10:  # Limit to 10 errors
                state["errors"].append(error_msg)

        if "latency_ms" in event:
            state["last_latency_ms"] = event.get("latency_ms")
        if "timestamp" in event:
            ts = event.get("timestamp")
            state["last_timestamp"] = ts
            # Track start and end timestamps for duration calculation
            if status == "start" and state["start_timestamp"] is None:
                state["start_timestamp"] = ts
            # Update end timestamp on every event (last one wins)
            state["end_timestamp"] = ts

    steps: list[dict[str, Any]] = []
    for step_name, state in step_state.items():
        seen_count = len(state["seen"])
        current = max(seen_count, state["current"])
        total = state["total"]
        status = state["last_status"]

        # Count unique successes and errors
        success_count = len(state["seen_success"])
        error_count = len(state["seen_error"])

        if status in {"start", "progress"}:
            status = "running"
        elif status in {"success", "error"}:
            if total and current < total and seen_count > 0:
                status = "running"
            else:
                status = status
        else:
            if total and current >= total:
                status = "error" if error_count > 0 else "completed"
            else:
                status = "running"

        # For steps that complete successfully without per-item tracking,
        # use total as success count (e.g., save_content, generate_embeddings)
        if status == "success" and success_count == 0 and total > 0:
            success_count = total
            current = total  # Also update current to match total

        # Calculate duration if we have both start and end timestamps
        duration_ms = None
        if state["start_timestamp"] and state["end_timestamp"]:
            duration_ms = int((state["end_timestamp"] - state["start_timestamp"]) * 1000)

        steps.append(
            {
                "name": step_name,
                "status": status,
                "current": current,
                "total": total,
                "success": success_count,
                "error": error_count,
                "errors": state["errors"],  # Include error messages
                "last_latency_ms": state["last_latency_ms"],
                "duration_ms": duration_ms,
                "last_timestamp": state["last_timestamp"],
                "step_type": state["step_type"],
            }
        )

    steps.sort(key=lambda s: (s["last_timestamp"] is None, s["last_timestamp"] or 0))

    # Get all logs and group by step
    all_logs = read_workflow_streams(workflow_id, key="logs")
    step_logs: dict[str, list[dict[str, Any]]] = {}
    for log in all_logs:
        step_name = log.get("step") or "_general"
        if step_name not in step_logs:
            step_logs[step_name] = []
        step_logs[step_name].append(log)

    # Calculate overall progress from steps
    total_items = sum(s.get("total", 0) for s in steps)
    completed_items = sum(s.get("current", 0) for s in steps)

    return {
        "workflow_id": workflow_id,
        "status": events.get("status", "unknown"),
        "current_step": events.get("current_step"),
        "stage": events.get("stage"),
        "progress": {
            "current": completed_items,
            "total": total_items,
        },
        "steps": steps,
        "step_logs": step_logs,
        "last_log": recent_logs[0].get("message") if recent_logs else None,
        "inputs": workflow_inputs,
        "cli_command": events.get("cli_command"),
        "duration_ms": workflow_duration_ms,
    }


def _format_ts(value: Any) -> str:
    if value is None:
        return "-"
    try:
        ts = float(value)
        return datetime.utcfromtimestamp(ts).isoformat(timespec="seconds") + "Z"
    except Exception:
        return str(value)


def format_live_status(status: dict[str, Any]) -> str:
    """
    Format live status for CLI output.
    """
    workflow_id = status.get("workflow_id", "-")
    state = status.get("status", "unknown")
    progress = status.get("progress", {})
    current = progress.get("current", 0)
    total = progress.get("total", 0)
    pct = int(current / total * 100) if total else 0

    lines = [
        f"Workflow {workflow_id} [{state}]",
        f"Progress: {current}/{total} ({pct}%)",
    ]

    steps = status.get("steps", [])
    step_logs = status.get("step_logs", {})

    if steps:
        lines.append("")
        lines.append("Steps:")
        for step in steps:
            name = step.get("name", "-")
            st = step.get("status", "unknown")
            success = step.get("success", 0)
            error = step.get("error", 0)
            tot = step.get("total", 0)
            duration = step.get("duration_ms")

            # Format step header with status
            if tot > 0:
                parts = []
                if success > 0:
                    parts.append(f"{success} ok")
                if error > 0:
                    parts.append(f"{error} failed")
                result_str = ", ".join(parts) if parts else "done"
            else:
                result_str = "done" if st == "success" else st

            duration_str = f" ({duration}ms)" if duration else ""
            lines.append(f"  {name}: {result_str}{duration_str}")

            # Show logs for this step
            logs = step_logs.get(name, [])
            for log in logs:
                msg = log.get("message", "")
                level = log.get("level", "info")
                prefix = "    ⚠ " if level == "error" else "    → "
                lines.append(f"{prefix}{msg}")

    return "\n".join(lines)


def format_step_logs(logs: list[dict[str, Any]]) -> str:
    """
    Format stream log entries for CLI output.
    """
    lines = []
    for entry in logs:
        ts = _format_ts(entry.get("timestamp"))
        level = entry.get("level", "info")
        step = entry.get("step") or "-"
        message = entry.get("message", "")
        lines.append(f"{ts} [{level}] [{step}] {message}")
    return "\n".join(lines)
