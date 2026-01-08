from __future__ import annotations

import base64
import pickle
from datetime import datetime
from typing import Any

from sqlalchemy import text

from kurt_new.db import managed_session


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
    with managed_session() as session:
        rows = session.execute(
            text("SELECT key, value FROM workflow_events WHERE workflow_uuid = :workflow_id"),
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
) -> list[dict[str, Any]]:
    """
    Read DBOS streams (decoded) for a workflow.
    """
    params: dict[str, Any] = {"workflow_id": workflow_id}
    query = 'SELECT key, value, "offset" FROM streams WHERE workflow_uuid = :workflow_id'
    if key:
        query += " AND key = :key"
        params["key"] = key
    if since_offset is not None:
        query += ' AND "offset" > :since_offset'
        params["since_offset"] = since_offset
    query += ' ORDER BY "offset"'
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
        }
    """
    events = read_workflow_events(workflow_id)
    progress_events = read_workflow_streams(workflow_id, key="progress")
    logs = get_step_logs(workflow_id, limit=1)

    step_state: dict[str, dict[str, Any]] = {}
    for event in progress_events:
        step = event.get("step")
        if not step:
            continue
        state = step_state.setdefault(
            step,
            {
                "seen": set(),
                "current": 0,
                "total": 0,
                "success": 0,
                "error": 0,
                "last_status": None,
                "last_latency_ms": None,
                "last_timestamp": None,
            },
        )

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
        if status == "success":
            state["success"] += 1
        elif status == "error":
            state["error"] += 1

        if "latency_ms" in event:
            state["last_latency_ms"] = event.get("latency_ms")
        if "timestamp" in event:
            state["last_timestamp"] = event.get("timestamp")

    steps: list[dict[str, Any]] = []
    for step_name, state in step_state.items():
        seen_count = len(state["seen"])
        current = max(seen_count, state["current"])
        total = state["total"]
        status = state["last_status"]

        if status in {"start", "progress"}:
            status = "running"
        elif status in {"success", "error"}:
            status = status
        else:
            if total and current >= total:
                status = "error" if state["error"] else "completed"
            else:
                status = "running"

        steps.append(
            {
                "name": step_name,
                "status": status,
                "current": current,
                "total": total,
                "success": state["success"],
                "error": state["error"],
                "last_latency_ms": state["last_latency_ms"],
                "last_timestamp": state["last_timestamp"],
            }
        )

    steps.sort(key=lambda s: (s["last_timestamp"] is None, s["last_timestamp"] or 0))

    return {
        "workflow_id": workflow_id,
        "status": events.get("status", "unknown"),
        "current_step": events.get("current_step"),
        "stage": events.get("stage"),
        "progress": {
            "current": events.get("stage_current", 0),
            "total": events.get("stage_total", 0),
        },
        "steps": steps,
        "last_log": logs[0]["message"] if logs else None,
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
    current_step = status.get("current_step") or "-"
    progress = status.get("progress", {})
    current = progress.get("current", 0)
    total = progress.get("total", 0)
    pct = int(current / total * 100) if total else 0

    lines = [
        f"Workflow {workflow_id} [{state}]",
        f"Current step: {current_step}",
        f"Stage progress: {current}/{total} ({pct}%)",
    ]

    steps = status.get("steps", [])
    if steps:
        lines.append("Steps:")
        for step in steps:
            name = step.get("name", "-")
            st = step.get("status", "unknown")
            cur = step.get("current", 0)
            tot = step.get("total", 0)
            lines.append(f"  - {name}: {st} {cur}/{tot}")

    last_log = status.get("last_log")
    if last_log:
        lines.append(f"Last log: {last_log}")

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
