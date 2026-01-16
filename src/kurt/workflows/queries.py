"""Workflow query functions - used by API and CLI.

These are pure SQLAlchemy queries for workflow data.
Used by:
- CLI in local mode (direct call)
- Web API endpoint (called by CLI in cloud mode and web UI)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from sqlmodel import Session


def list_workflows(
    session: "Session",
    status: Optional[str] = None,
    id_filter: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """
    List workflows with optional filters.

    Args:
        session: Database session
        status: Filter by workflow status (PENDING, SUCCESS, ERROR, etc.)
        id_filter: Substring match on workflow_uuid
        limit: Maximum number of workflows to return

    Returns:
        List of workflow dicts with keys: workflow_id, name, status, created_at, updated_at
    """
    from sqlalchemy import text

    sql = """
        SELECT workflow_uuid, name, status, created_at, updated_at
        FROM workflow_status
    """
    params = {}
    conditions = []

    if status:
        conditions.append("status = :status")
        params["status"] = status

    if id_filter:
        conditions.append("workflow_uuid LIKE :id_filter")
        params["id_filter"] = f"%{id_filter}%"

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY created_at DESC LIMIT :limit"
    params["limit"] = limit

    result = session.execute(text(sql), params)
    workflows = result.fetchall()

    return [
        {
            "workflow_id": wf[0],
            "name": wf[1],
            "status": wf[2],
            "created_at": str(wf[3]) if wf[3] else None,
            "updated_at": str(wf[4]) if wf[4] else None,
        }
        for wf in workflows
    ]


def get_workflow(session: "Session", workflow_id: str) -> Optional[dict]:
    """
    Get a single workflow by ID.

    Args:
        session: Database session
        workflow_id: Workflow UUID

    Returns:
        Workflow dict or None if not found
    """
    from sqlalchemy import text

    sql = """
        SELECT workflow_uuid, name, status, created_at, updated_at
        FROM workflow_status
        WHERE workflow_uuid = :workflow_id
    """

    result = session.execute(text(sql), {"workflow_id": workflow_id})
    wf = result.fetchone()

    if not wf:
        return None

    return {
        "workflow_id": wf[0],
        "name": wf[1],
        "status": wf[2],
        "created_at": str(wf[3]) if wf[3] else None,
        "updated_at": str(wf[4]) if wf[4] else None,
    }


def get_workflow_events(session: "Session", workflow_id: str) -> dict:
    """
    Get workflow events (used for live status).

    Args:
        session: Database session
        workflow_id: Workflow UUID

    Returns:
        Dict with workflow info and events
    """
    from sqlalchemy import text

    # Get workflow info
    workflow = get_workflow(session, workflow_id)
    if not workflow:
        return {}

    # Get events
    sql = """
        SELECT key, value
        FROM workflow_events
        WHERE workflow_uuid = :workflow_id
    """
    result = session.execute(text(sql), {"workflow_id": workflow_id})
    events = result.fetchall()

    # Deserialize event values
    import base64
    import pickle

    event_data = {}
    for key, value in events:
        try:
            event_data[key] = pickle.loads(base64.b64decode(value))
        except Exception:
            event_data[key] = value

    return {
        **workflow,
        "events": event_data,
    }


def get_workflow_streams(
    session: "Session",
    workflow_id: str,
    limit: int = 200,
) -> list[dict]:
    """
    Get workflow streams (logs/progress events).

    Args:
        session: Database session
        workflow_id: Workflow UUID
        limit: Maximum number of stream entries

    Returns:
        List of stream entries
    """
    from sqlalchemy import text

    sql = """
        SELECT key, value, timestamp
        FROM workflow_streams
        WHERE workflow_uuid = :workflow_id
        ORDER BY timestamp DESC
        LIMIT :limit
    """

    result = session.execute(text(sql), {"workflow_id": workflow_id, "limit": limit})
    streams = result.fetchall()

    # Deserialize stream values
    import base64
    import pickle

    stream_data = []
    for key, value, timestamp in streams:
        try:
            data = pickle.loads(base64.b64decode(value))
            if isinstance(data, dict):
                data["timestamp"] = timestamp
                stream_data.append(data)
        except Exception:
            pass

    return stream_data
