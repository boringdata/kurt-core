"""Workflow routes: list, get, cancel, retry, status, logs, streaming."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

router = APIRouter()


# --- Helper functions ---

def _get_dolt_db():
    """Get a DoltDB instance for workflow queries."""
    from kurt.db.utils import get_dolt_db

    return get_dolt_db(return_none_if_missing=True)


def _normalize_workflow_status(dolt_status: str) -> str:
    """Normalize Dolt workflow status to frontend-expected format.

    Dolt uses lowercase: pending, running, completed, failed, canceling, canceled
    Frontend expects uppercase: PENDING, SUCCESS, ERROR, CANCELLED, WARNING

    Mapping:
    - pending -> PENDING
    - running -> PENDING (show as active/running)
    - completed -> SUCCESS
    - completed_with_errors -> WARNING
    - failed -> ERROR
    - canceling -> PENDING
    - canceled -> CANCELLED
    """
    status_map = {
        "pending": "PENDING",
        "running": "PENDING",  # Frontend treats PENDING as active
        "completed": "SUCCESS",
        "completed_with_errors": "WARNING",
        "failed": "ERROR",
        "canceling": "PENDING",
        "canceled": "CANCELLED",
    }
    normalized = dolt_status.lower() if dolt_status else "unknown"
    return status_map.get(normalized, normalized.upper())


def _denormalize_status_filter(frontend_status: str) -> list[str]:
    """Convert frontend status filter to database status values.

    Reverse mapping of _normalize_workflow_status for filtering queries.
    Returns a list since some frontend statuses map to multiple DB values.
    """
    reverse_map = {
        "PENDING": ["pending", "running", "canceling"],  # All active states
        "SUCCESS": ["completed"],
        "WARNING": ["completed_with_errors"],
        "ERROR": ["failed"],
        "CANCELLED": ["canceled"],
        "ENQUEUED": ["pending"],  # Queued jobs are pending
    }
    # Try uppercase first, then original value
    key = frontend_status.upper() if frontend_status else ""
    if key in reverse_map:
        return reverse_map[key]
    # Fallback: pass through as-is (lowercase)
    return [frontend_status.lower()] if frontend_status else []


def _normalize_step_status(db_status: str | None) -> str:
    """Normalize step/event status to frontend-expected format.

    Step statuses use lowercase: pending, running, completed, failed, progress
    Frontend expects: pending, running, success, error, progress

    Consistent with _map_step_status in observability/status.py
    """
    if not db_status:
        return "pending"
    status_map = {
        "pending": "pending",
        "running": "running",
        "progress": "progress",
        "completed": "success",
        "failed": "error",
        "canceled": "error",
        "skipped": "skipped",
    }
    return status_map.get(db_status.lower(), db_status.lower())


# --- Endpoints ---

@router.get("/api/workflows")
def api_list_workflows(
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    workflow_type: Optional[str] = Query(None),
    parent_id: Optional[str] = Query(None, description="Filter by parent workflow ID"),
):
    """List workflows with optional filtering."""
    db = _get_dolt_db()
    if db is None:
        return {"workflows": [], "total": 0, "error": "Database not available"}

    try:
        # Build query against workflow_runs table (Dolt observability schema)
        sql = "SELECT id, workflow, status, started_at, completed_at, error, inputs, metadata_json FROM workflow_runs"
        params: list[Any] = []
        conditions = []

        if status:
            # Convert frontend status to DB status values
            db_statuses = _denormalize_status_filter(status)
            if db_statuses:
                placeholders = ", ".join("?" * len(db_statuses))
                conditions.append(f"status IN ({placeholders})")
                params.extend(db_statuses)

        if search:
            # Search by ID or workflow name
            conditions.append("(id LIKE ? OR workflow LIKE ?)")
            params.append(f"%{search}%")
            params.append(f"%{search}%")

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY started_at DESC LIMIT ? OFFSET ?"
        params.append(limit)
        params.append(offset)

        result = db.query(sql, params)
        workflows = []
        raw_count = len(result.rows)  # Count before Python filtering

        for row in result.rows:
            workflow_id = row.get("id", "")

            # Parse metadata for workflow_type and parent info
            metadata = {}
            raw_metadata = row.get("metadata_json") or row.get("metadata")
            if raw_metadata:
                try:
                    metadata = json.loads(raw_metadata) if isinstance(raw_metadata, str) else raw_metadata
                except Exception:
                    pass

            parent_workflow_id = metadata.get("parent_workflow_id")

            # If filtering by parent_id, only include matching children
            if parent_id and parent_workflow_id != parent_id:
                continue

            # If NOT filtering by parent_id, hide child workflows
            if not parent_id and parent_workflow_id:
                continue

            wf_type = metadata.get("workflow_type")

            # Apply workflow_type filter if specified
            if workflow_type:
                if workflow_type == "agent":
                    if wf_type != "agent":
                        continue
                elif workflow_type == "tool":
                    if wf_type == "agent":
                        continue
                else:
                    if wf_type != workflow_type:
                        continue

            workflow = {
                "workflow_uuid": workflow_id,
                "name": row.get("workflow", ""),
                "status": _normalize_workflow_status(row.get("status", "unknown")),
                "created_at": str(row.get("started_at")) if row.get("started_at") else None,
                "updated_at": str(row.get("completed_at")) if row.get("completed_at") else None,
                "error": row.get("error"),
                "parent_workflow_id": parent_workflow_id,
                "parent_step_name": metadata.get("parent_step_name"),
                "workflow_type": wf_type,
            }

            # Add metadata fields for agent workflows
            if wf_type == "agent":
                workflow["definition_name"] = metadata.get("definition_name")
                workflow["trigger"] = metadata.get("trigger")
                workflow["agent_turns"] = metadata.get("agent_turns")
                workflow["tokens_in"] = metadata.get("tokens_in")
                workflow["tokens_out"] = metadata.get("tokens_out")
                workflow["cost_usd"] = metadata.get("cost_usd")
            elif wf_type in ("map", "fetch"):
                workflow["cli_command"] = metadata.get("cli_command")

            workflows.append(workflow)

        # has_more is True if the raw SQL query returned 'limit' rows
        # (there might be more in the database)
        has_more = raw_count >= limit

        return {
            "workflows": workflows,
            "total": len(workflows),
            "has_more": has_more,
            "offset": offset,
            "limit": limit,
        }
    except Exception as e:
        # Handle missing table (no workflows run yet)
        if "no such table" in str(e).lower() or "doesn't exist" in str(e).lower():
            return {"workflows": [], "total": 0, "has_more": False}
        return {"workflows": [], "total": 0, "has_more": False, "error": f"Database error: {e}"}


@router.get("/api/workflows/{workflow_id}")
def api_get_workflow(workflow_id: str):
    """Get detailed workflow information."""
    db = _get_dolt_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        sql = """
            SELECT id, workflow, status, started_at, completed_at, error, inputs, metadata_json
            FROM workflow_runs
            WHERE id LIKE CONCAT(?, '%')
            LIMIT 1
        """
        result = db.query(sql, [workflow_id])

        if not result.rows:
            raise HTTPException(status_code=404, detail="Workflow not found")

        row = result.rows[0]

        # Parse metadata
        metadata = {}
        raw_metadata = row.get("metadata_json") or row.get("metadata")
        if raw_metadata:
            try:
                metadata = json.loads(raw_metadata) if isinstance(raw_metadata, str) else raw_metadata
            except Exception:
                pass

        return {
            "workflow_uuid": row.get("id"),
            "name": row.get("workflow"),
            "status": _normalize_workflow_status(row.get("status")),
            "created_at": str(row.get("started_at")) if row.get("started_at") else None,
            "updated_at": str(row.get("completed_at")) if row.get("completed_at") else None,
            "error": row.get("error"),
            "inputs": row.get("inputs"),
            "metadata": metadata,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/workflows/{workflow_id}/cancel")
def api_cancel_workflow(workflow_id: str):
    """Cancel a workflow by updating its status to 'canceling'.

    The workflow runner is responsible for detecting this status change
    and terminating gracefully.
    """
    db = _get_dolt_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # Check workflow exists and is running
        result = db.query("SELECT id, status FROM workflow_runs WHERE id = ?", [workflow_id])
        if not result.rows:
            raise HTTPException(status_code=404, detail="Workflow not found")

        current_status = result.rows[0].get("status")
        if current_status not in ("pending", "running"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel workflow with status '{current_status}'",
            )

        # Update status to canceling
        db.execute("UPDATE workflow_runs SET status = 'canceling' WHERE id = ?", [workflow_id])

        return {"status": "canceling", "workflow_id": workflow_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/workflows/{workflow_id}/retry")
def api_retry_workflow(workflow_id: str):
    """Retry a workflow by starting a new run with the same inputs.

    Reads the original workflow's inputs from workflow_runs table,
    then starts a new workflow run with the same configuration.

    Only works for completed (success, error, cancelled) workflows.
    """
    db = _get_dolt_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # Get original workflow details
        result = db.query(
            "SELECT id, workflow, status, inputs, metadata_json FROM workflow_runs WHERE id LIKE CONCAT(?, '%') LIMIT 1",
            [workflow_id],
        )
        if not result.rows:
            raise HTTPException(status_code=404, detail="Workflow not found")

        row = result.rows[0]
        current_status = row.get("status")

        # Only allow retry for terminal states
        if current_status in ("pending", "running", "canceling"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot retry workflow with status '{current_status}'. Wait for it to complete.",
            )

        workflow_name = row.get("workflow", "")
        original_id = row.get("id")

        # Parse inputs
        raw_inputs = row.get("inputs")
        inputs = {}
        if raw_inputs:
            try:
                inputs = json.loads(raw_inputs) if isinstance(raw_inputs, str) else raw_inputs
            except Exception:
                pass

        # Parse metadata to get workflow type and definition name
        metadata = {}
        raw_metadata = row.get("metadata_json")
        if raw_metadata:
            try:
                metadata = json.loads(raw_metadata) if isinstance(raw_metadata, str) else raw_metadata
            except Exception:
                pass

        workflow_type = metadata.get("workflow_type")
        definition_name = metadata.get("definition_name")

        # Handle agent workflows
        if workflow_type == "agent" and definition_name:
            from kurt.workflows.agents import run_definition

            # Extract original inputs from the inputs dict (if they were stored there)
            agent_inputs = inputs.get("inputs") if isinstance(inputs.get("inputs"), dict) else {}

            result = run_definition(
                definition_name=definition_name,
                inputs=agent_inputs,
                background=True,
                trigger="retry",
            )
            return {
                "status": "started",
                "workflow_id": result.get("workflow_id"),
                "original_workflow_id": original_id,
            }

        # Handle map/fetch workflows via CLI subprocess
        if workflow_name in ("map_workflow", "fetch_workflow"):
            # Build CLI command from inputs
            cmd = ["kurt", "content"]

            if workflow_name == "map_workflow":
                cmd.append("map")
                if inputs.get("source_url"):
                    cmd.append(inputs["source_url"])
                elif inputs.get("url"):
                    cmd.append(inputs["url"])
                if inputs.get("max_depth") is not None:
                    cmd.extend(["--max-depth", str(inputs["max_depth"])])
                if inputs.get("max_pages") is not None:
                    cmd.extend(["--max-pages", str(inputs["max_pages"])])
                if inputs.get("include_pattern"):
                    cmd.extend(["--include", inputs["include_pattern"]])
                if inputs.get("exclude_pattern"):
                    cmd.extend(["--exclude", inputs["exclude_pattern"]])
            elif workflow_name == "fetch_workflow":
                cmd.append("fetch")
                if inputs.get("fetch_engine"):
                    cmd.extend(["--engine", inputs["fetch_engine"]])

            # Always run in background
            cmd.append("--background")

            # Run the CLI command
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(Path.cwd()),
            )

            stdout, stderr = proc.communicate(timeout=30)

            if proc.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace").strip() if stderr else "Unknown error"
                raise HTTPException(status_code=500, detail=f"Failed to start workflow: {error_msg}")

            # Try to extract workflow ID from output
            output = stdout.decode("utf-8", errors="replace").strip()
            new_workflow_id = None

            # Look for workflow ID in output (format: "Workflow started: <uuid>")
            match = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", output, re.IGNORECASE)
            if match:
                new_workflow_id = match.group(0)

            return {
                "status": "started",
                "workflow_id": new_workflow_id,
                "original_workflow_id": original_id,
            }

        # Unsupported workflow type
        raise HTTPException(
            status_code=400,
            detail=f"Retry not supported for workflow type: {workflow_name}",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/workflows/{workflow_id}/status")
def api_get_workflow_status(workflow_id: str):
    """Get live workflow status with progress information from Dolt.

    Returns comprehensive status including:
    - Workflow metadata (id, name, status, timestamps)
    - Steps array with success/error counts, duration, and errors
    - Current stage and progress for running workflows
    - CLI command and inputs
    """
    from kurt.observability.status import get_live_status

    db = _get_dolt_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        status = get_live_status(db, workflow_id)
        if status is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/workflows/{workflow_id}/step-logs")
def api_get_step_logs(
    workflow_id: str,
    step: str | None = Query(None, description="Filter by step name"),
    limit: int = Query(100, le=500),
):
    """Get step logs from Dolt step_logs table, optionally filtered by step."""
    from kurt.observability.status import get_step_logs_for_workflow

    db = _get_dolt_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        logs_raw = get_step_logs_for_workflow(db, workflow_id, step_name=step, limit=limit)

        if not logs_raw and step:
            # Check if workflow exists
            result = db.query(
                "SELECT id FROM workflow_runs WHERE id LIKE CONCAT(?, '%') LIMIT 1",
                [workflow_id],
            )
            if not result.rows:
                raise HTTPException(status_code=404, detail="Workflow not found")

        logs = []
        for row in logs_raw:
            # Parse JSON fields
            errors = []
            raw_errors = row.get("errors")
            if raw_errors:
                try:
                    parsed = json.loads(raw_errors) if isinstance(raw_errors, str) else raw_errors
                    if isinstance(parsed, list):
                        errors = parsed
                except Exception:
                    pass

            metadata = {}
            raw_metadata = row.get("metadata_json")
            if raw_metadata:
                try:
                    metadata = json.loads(raw_metadata) if isinstance(raw_metadata, str) else raw_metadata
                except Exception:
                    pass

            logs.append({
                "step_id": row.get("step_id"),
                "tool": row.get("tool"),
                "status": _normalize_step_status(row.get("status")),
                "started_at": str(row.get("started_at")) if row.get("started_at") else None,
                "completed_at": str(row.get("completed_at")) if row.get("completed_at") else None,
                "input_count": row.get("input_count"),
                "output_count": row.get("output_count"),
                "error_count": row.get("error_count"),
                "errors": errors,
                "metadata": metadata,
            })

        return {"logs": logs, "step": step}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/workflows/{workflow_id}/status/stream")
async def api_stream_workflow_status(workflow_id: str):
    """Stream live workflow status via Server-Sent Events.

    Streams the same comprehensive status as /api/workflows/{id}/status
    but continuously until the workflow completes.
    """
    import asyncio

    from fastapi.responses import StreamingResponse

    from kurt.observability.status import get_live_status

    db = _get_dolt_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # Verify workflow exists
        status = get_live_status(db, workflow_id)
        if status is None:
            raise HTTPException(status_code=404, detail="Workflow not found")

        full_id = status["workflow_id"]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    async def event_generator():
        last_status_json = None
        while True:
            try:
                # Re-fetch status from Dolt
                db_inner = _get_dolt_db()
                if db_inner is None:
                    break

                status = get_live_status(db_inner, full_id)
                if status is None:
                    break

                status_json = json.dumps(status)

                # Only send if changed
                if status_json != last_status_json:
                    yield f"data: {status_json}\n\n"
                    last_status_json = status_json

                # Stop streaming if workflow completed
                if status.get("status") in ("completed", "completed_with_errors", "failed", "canceled"):
                    break

                await asyncio.sleep(0.5)
            except Exception:
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/api/workflows/{workflow_id}/logs/stream")
async def api_stream_workflow_logs(
    workflow_id: str,
    step_id: Optional[str] = Query(None, description="Filter by step ID"),
):
    """Stream workflow logs via Server-Sent Events.

    Streams step_events with messages as structured log entries.
    Also checks for and streams file-based logs as fallback.

    Events are JSON with format:
        {"type": "event", "event": {...}}  - Structured step event
        {"type": "log", "content": "..."}  - File-based log content
        {"done": true}                     - Stream complete
    """
    import asyncio

    from fastapi.responses import StreamingResponse

    db = _get_dolt_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # Get full workflow ID
        result = db.query(
            "SELECT id, status FROM workflow_runs WHERE id LIKE CONCAT(?, '%') LIMIT 1",
            [workflow_id],
        )

        if not result.rows:
            raise HTTPException(status_code=404, detail="Workflow not found")

        full_id = result.rows[0].get("id")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    log_file = Path(".kurt") / "logs" / f"workflow-{full_id}.log"

    async def event_generator():
        cursor_id = 0
        last_file_size = 0
        terminal_statuses = ("completed", "failed", "canceled")

        while True:
            try:
                db_inner = _get_dolt_db()
                if not db_inner:
                    await asyncio.sleep(0.5)
                    continue

                # Fetch new step_events since cursor
                conditions = ["run_id = ?", "id > ?"]
                params: list[Any] = [full_id, cursor_id]

                if step_id:
                    conditions.append("step_id = ?")
                    params.append(step_id)

                params.append(50)  # Batch limit

                sql = f"""
                    SELECT id, step_id, substep, status, current, total, message,
                           metadata_json, created_at
                    FROM step_events
                    WHERE {' AND '.join(conditions)}
                    ORDER BY id ASC
                    LIMIT ?
                """
                events_result = db_inner.query(sql, params)

                # Yield new events
                for row in events_result.rows:
                    event_data = {
                        "id": row.get("id"),
                        "step_id": row.get("step_id"),
                        "substep": row.get("substep"),
                        "status": _normalize_step_status(row.get("status")),
                        "current": row.get("current"),
                        "total": row.get("total"),
                        "message": row.get("message"),
                        "created_at": str(row.get("created_at")) if row.get("created_at") else None,
                    }
                    # Parse metadata if present
                    metadata_raw = row.get("metadata_json")
                    if metadata_raw:
                        try:
                            if isinstance(metadata_raw, str):
                                event_data["metadata"] = json.loads(metadata_raw)
                            else:
                                event_data["metadata"] = metadata_raw
                        except (json.JSONDecodeError, TypeError):
                            pass

                    yield f"data: {json.dumps({'type': 'event', 'event': event_data})}\n\n"
                    cursor_id = max(cursor_id, row.get("id", 0))

                # Also check file-based logs
                if log_file.exists():
                    current_size = log_file.stat().st_size
                    if current_size > last_file_size:
                        with open(log_file, "r") as f:
                            f.seek(last_file_size)
                            new_content = f.read()
                            if new_content:
                                yield f"data: {json.dumps({'type': 'log', 'content': new_content})}\n\n"
                        last_file_size = current_size

                # Check if workflow is done
                status_result = db_inner.query(
                    "SELECT status FROM workflow_runs WHERE id = ?",
                    [full_id],
                )
                if status_result.rows:
                    status = status_result.rows[0].get("status")
                    if status in terminal_statuses:
                        # Final poll for any remaining events
                        await asyncio.sleep(0.3)

                        # Fetch final events
                        final_result = db_inner.query(sql, [full_id, cursor_id, step_id, 50] if step_id else [full_id, cursor_id, 50])
                        for row in final_result.rows:
                            event_data = {
                                "id": row.get("id"),
                                "step_id": row.get("step_id"),
                                "substep": row.get("substep"),
                                "status": _normalize_step_status(row.get("status")),
                                "current": row.get("current"),
                                "total": row.get("total"),
                                "message": row.get("message"),
                                "created_at": str(row.get("created_at")) if row.get("created_at") else None,
                            }
                            yield f"data: {json.dumps({'type': 'event', 'event': event_data})}\n\n"

                        # Final file content
                        if log_file.exists():
                            current_size = log_file.stat().st_size
                            if current_size > last_file_size:
                                with open(log_file, "r") as f:
                                    f.seek(last_file_size)
                                    new_content = f.read()
                                    if new_content:
                                        yield f"data: {json.dumps({'type': 'log', 'content': new_content})}\n\n"

                        yield f"data: {json.dumps({'done': True, 'status': _normalize_workflow_status(status)})}\n\n"
                        break

                await asyncio.sleep(0.5)
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/api/workflows/{workflow_id}/logs")
def api_get_workflow_logs(
    workflow_id: str,
    step_id: Optional[str] = Query(None, description="Filter by step ID"),
    since_id: int = Query(0, ge=0, description="Return events after this ID"),
    limit: int = Query(100, le=1000),
    include_file_logs: bool = Query(True, description="Include file-based logs"),
):
    """Get workflow logs from step_events and optional file logs.

    Returns structured events from step_events table plus optional
    file-based log content.
    """
    db = _get_dolt_db()
    full_id = workflow_id

    if db is not None:
        try:
            result = db.query(
                "SELECT id FROM workflow_runs WHERE id LIKE CONCAT(?, '%') LIMIT 1",
                [workflow_id],
            )
            if result.rows:
                full_id = result.rows[0].get("id")
        except Exception:
            pass

    events: list[dict[str, Any]] = []
    file_content = ""
    has_more = False

    # Query step_events from database
    if db is not None:
        try:
            conditions = ["run_id = ?"]
            params: list[Any] = [full_id]

            if step_id:
                conditions.append("step_id = ?")
                params.append(step_id)

            if since_id > 0:
                conditions.append("id > ?")
                params.append(since_id)

            params.append(limit + 1)  # Fetch one extra to check has_more

            sql = f"""
                SELECT id, step_id, substep, status, current, total, message,
                       metadata_json, created_at
                FROM step_events
                WHERE {' AND '.join(conditions)}
                ORDER BY id ASC
                LIMIT ?
            """
            events_result = db.query(sql, params)

            for row in events_result.rows[:limit]:
                event_data = {
                    "id": row.get("id"),
                    "step_id": row.get("step_id"),
                    "substep": row.get("substep"),
                    "status": _normalize_step_status(row.get("status")),
                    "current": row.get("current"),
                    "total": row.get("total"),
                    "message": row.get("message"),
                    "created_at": str(row.get("created_at")) if row.get("created_at") else None,
                }
                # Parse metadata if present
                metadata_raw = row.get("metadata_json")
                if metadata_raw:
                    try:
                        if isinstance(metadata_raw, str):
                            event_data["metadata"] = json.loads(metadata_raw)
                        else:
                            event_data["metadata"] = metadata_raw
                    except (json.JSONDecodeError, TypeError):
                        pass
                events.append(event_data)

            has_more = len(events_result.rows) > limit
        except Exception:
            pass

    # Also include file-based logs if requested
    if include_file_logs:
        log_file = Path(".kurt") / "logs" / f"workflow-{full_id}.log"
        if log_file.exists():
            try:
                with open(log_file, "r") as f:
                    file_content = f.read()
            except Exception:
                pass

    return {
        "workflow_id": full_id,
        "events": events,
        "total_events": len(events),
        "has_more": has_more,
        "since_id": since_id,
        "limit": limit,
        "file_content": file_content if include_file_logs else None,
    }
