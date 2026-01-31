"""Approval routes: request, pretool, posttool, pending, status, decision."""

from __future__ import annotations

import difflib
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from kurt.web.api.server_helpers import (
    APPROVAL_LOCK,
    APPROVAL_TIMEOUT_SECONDS,
    APPROVALS,
    get_storage,
)

router = APIRouter()


# --- Pydantic models ---

class ApprovalRequestPayload(BaseModel):
    tool_name: str
    file_path: str
    diff: str | None = None
    tool_input: dict | None = None
    session_id: str | None = None
    session_provider: str | None = None
    session_name: str | None = None
    requested_at: str | None = None


class ApprovalDecisionPayload(BaseModel):
    request_id: str
    decision: str
    reason: str | None = None


# --- Helper functions ---

def _extract_tool_payload(payload: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
    tool_name = payload.get("tool_name") or payload.get("toolName") or ""
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    session_id = payload.get("session_id") or payload.get("sessionId") or ""
    if not isinstance(tool_input, dict):
        tool_input = {}
    return tool_name, tool_input, session_id


def _extract_path(tool_input: dict[str, Any]) -> str:
    path_value = (
        tool_input.get("file_path")
        or tool_input.get("path")
        or tool_input.get("file")
        or tool_input.get("target_file")
    )
    return path_value if isinstance(path_value, str) else ""


def _project_path_for_file(file_path: str) -> str:
    if not file_path:
        return ""
    try:
        root = Path.cwd().resolve()
        target = Path(file_path).expanduser()
        if not target.is_absolute():
            target = (root / target).resolve()
        else:
            target = target.resolve()
        if root in target.parents or target == root:
            return str(target.relative_to(root))
    except Exception:
        return ""
    return ""


def _load_project_file(project_path: str) -> str:
    if not project_path:
        return ""
    try:
        storage = get_storage()
        return storage.read_file(Path(project_path))
    except Exception:
        return ""


def _hash_content(content: str) -> str:
    if not content:
        return ""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _derive_new_content(old_content: str, tool_input: dict[str, Any]) -> str:
    new_content = (
        tool_input.get("content")
        or tool_input.get("new_content")
        or tool_input.get("new_text")
        or tool_input.get("replacement_text")
        or tool_input.get("newString")
        or tool_input.get("new_string")
    )
    if isinstance(new_content, str):
        return new_content

    old_string = (
        tool_input.get("old_string")
        or tool_input.get("oldString")
        or tool_input.get("old_text")
        or tool_input.get("oldText")
    )
    new_string = (
        tool_input.get("new_string")
        or tool_input.get("newString")
        or tool_input.get("new_text")
        or tool_input.get("newText")
    )
    if isinstance(old_string, str) and isinstance(new_string, str) and old_content:
        if old_string in old_content:
            return old_content.replace(old_string, new_string, 1)
        old_norm = old_content.replace("\r\n", "\n")
        old_string_norm = old_string.replace("\r\n", "\n")
        new_string_norm = new_string.replace("\r\n", "\n")
        if old_string_norm in old_norm:
            return old_norm.replace(old_string_norm, new_string_norm, 1)
    return old_content


def _build_diff_from_strings(path_value: str, old_string: str, new_string: str) -> str:
    rel_path = path_value.lstrip("/")
    diff_lines = list(
        difflib.unified_diff(
            old_string.splitlines(),
            new_string.splitlines(),
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
            lineterm="",
            n=1,
        )
    )
    if not diff_lines:
        return ""
    diff_lines.insert(0, f"diff --git a/{rel_path} b/{rel_path}")
    return "\n".join(diff_lines)


def _build_diff(path_value: str, old_content: str, new_content: str) -> str:
    rel_path = path_value.lstrip("/")
    diff_lines = list(
        difflib.unified_diff(
            old_content.splitlines(),
            new_content.splitlines(),
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
            lineterm="",
            n=1,
        )
    )
    if not diff_lines:
        return ""
    diff_lines.insert(0, f"diff --git a/{rel_path} b/{rel_path}")
    return "\n".join(diff_lines)


def _hook_response(decision: str, reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }


def _cleanup_approvals(now_ts: float) -> None:
    from kurt.web.api.server_helpers import APPROVAL_CLEANUP_SECONDS

    if APPROVAL_CLEANUP_SECONDS <= 0:
        return
    expired_ids = []
    for request_id, req in APPROVALS.items():
        status = req.get("status")
        if status == "pending":
            continue
        updated_ts = req.get("updated_at_ts") or req.get("created_at_ts") or 0
        if now_ts - updated_ts > APPROVAL_CLEANUP_SECONDS:
            expired_ids.append(request_id)
    for request_id in expired_ids:
        APPROVALS.pop(request_id, None)


def _create_approval_record(
    *,
    tool_name: str,
    file_path: str,
    diff: str,
    tool_input: dict[str, Any],
    session_id: str,
    session_provider: str,
    session_name: str,
    requested_at: str | None,
) -> dict[str, Any]:
    request_id = str(uuid4())
    now = datetime.now(timezone.utc)
    now_iso = requested_at or now.isoformat()
    now_ts = time.time()
    project_path = _project_path_for_file(file_path)
    content = _load_project_file(project_path) if project_path else ""
    file_hash = _hash_content(content)
    return {
        "id": request_id,
        "tool_name": tool_name,
        "file_path": file_path,
        "project_path": project_path,
        "diff": diff,
        "tool_input": tool_input,
        "session_id": session_id,
        "session_provider": session_provider,
        "session_name": session_name,
        "requested_at": now_iso,
        "status": "pending",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "created_at_ts": now_ts,
        "updated_at_ts": now_ts,
        "file_hash": file_hash,
    }


# --- Endpoints ---

@router.post("/api/approval/request")
def api_approval_request(payload: ApprovalRequestPayload):
    record = _create_approval_record(
        tool_name=payload.tool_name,
        file_path=payload.file_path,
        diff=payload.diff or "",
        tool_input=payload.tool_input or {},
        session_id=payload.session_id or "",
        session_provider=payload.session_provider or "",
        session_name=payload.session_name or "",
        requested_at=payload.requested_at,
    )
    with APPROVAL_LOCK:
        _cleanup_approvals(time.time())
        APPROVALS[record["id"]] = record
    return {"request_id": record["id"]}


@router.post("/api/approval/pretool")
def api_approval_pretool(payload: dict[str, Any], request: Request):
    tool_name, tool_input, session_id = _extract_tool_payload(payload)
    if not tool_name:
        return _hook_response("ask", "No tool payload received.")

    path_value = _extract_path(tool_input)
    project_path = _project_path_for_file(path_value)
    old_content = _load_project_file(project_path)
    new_content = _derive_new_content(old_content, tool_input)

    old_string = (
        tool_input.get("old_string")
        or tool_input.get("oldString")
        or tool_input.get("old_text")
        or tool_input.get("oldText")
    )
    new_string = (
        tool_input.get("new_string")
        or tool_input.get("newString")
        or tool_input.get("new_text")
        or tool_input.get("newText")
    )
    if isinstance(old_string, str) and isinstance(new_string, str):
        diff_text = _build_diff_from_strings(path_value or "unknown", old_string, new_string)
    else:
        diff_text = _build_diff(path_value or "unknown", old_content, new_content)

    session_provider = payload.get("session_provider") or request.headers.get(
        "x-kurt-session-provider", ""
    )
    session_name = payload.get("session_name") or request.headers.get("x-kurt-session-name", "")

    record = _create_approval_record(
        tool_name=tool_name,
        file_path=path_value,
        diff=diff_text,
        tool_input=tool_input,
        session_id=session_id,
        session_provider=session_provider,
        session_name=session_name,
        requested_at=payload.get("requested_at"),
    )

    with APPROVAL_LOCK:
        _cleanup_approvals(time.time())
        APPROVALS[record["id"]] = record

    deadline = time.time() + APPROVAL_TIMEOUT_SECONDS
    while time.time() < deadline:
        with APPROVAL_LOCK:
            req = APPROVALS.get(record["id"])
        if not req:
            return _hook_response("ask", "Approval request no longer available.")
        status = req.get("status")
        if status in ("allow", "deny"):
            reason = req.get("decision_reason") or "User responded via web UI."
            return _hook_response(status, reason)
        if status in ("stale", "expired"):
            reason = req.get("decision_reason") or "Review expired before approval."
            return _hook_response("ask", reason)
        time.sleep(0.5)

    now = datetime.now(timezone.utc)
    with APPROVAL_LOCK:
        req = APPROVALS.get(record["id"])
        if req and req.get("status") == "pending":
            req["status"] = "expired"
            req["decision_reason"] = "Approval timed out."
            req["updated_at"] = now.isoformat()
            req["updated_at_ts"] = time.time()
            APPROVALS[record["id"]] = req
    return _hook_response("ask", "Approval timed out.")


@router.post("/api/approval/posttool")
def api_approval_posttool(payload: dict[str, Any]):
    tool_name, tool_input, session_id = _extract_tool_payload(payload)
    path_value = _extract_path(tool_input)
    project_path = _project_path_for_file(path_value)
    now = datetime.now(timezone.utc)
    now_ts = time.time()
    expired = []

    if not tool_name and not session_id and not path_value:
        return {"hookSpecificOutput": {"hookEventName": "PostToolUse"}, "expired": expired}

    with APPROVAL_LOCK:
        for request_id, req in APPROVALS.items():
            if req.get("status") != "pending":
                continue
            if session_id and req.get("session_id") != session_id:
                continue
            if tool_name and req.get("tool_name") != tool_name:
                continue
            if path_value:
                if project_path and req.get("project_path") == project_path:
                    pass
                elif req.get("file_path") == path_value:
                    pass
                else:
                    continue
            req["status"] = "expired"
            req["decision_reason"] = "Review cleared after tool completion."
            req["updated_at"] = now.isoformat()
            req["updated_at_ts"] = now_ts
            APPROVALS[request_id] = req
            expired.append(request_id)
        _cleanup_approvals(now_ts)

    return {"hookSpecificOutput": {"hookEventName": "PostToolUse"}, "expired": expired}


@router.get("/api/approval/pending")
def api_approval_pending():
    now = datetime.now(timezone.utc).isoformat()
    now_ts = time.time()
    with APPROVAL_LOCK:
        _cleanup_approvals(now_ts)
        pending = []
        for req in APPROVALS.values():
            if req["status"] != "pending":
                continue
            project_path = req.get("project_path") or ""
            file_hash = req.get("file_hash") or ""
            if project_path and file_hash:
                try:
                    storage = get_storage()
                    content = storage.read_file(Path(project_path))
                    current_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                except Exception:
                    current_hash = ""
                if not current_hash or current_hash != file_hash:
                    req["status"] = "stale"
                    req["updated_at"] = now
                    req["updated_at_ts"] = now_ts
                    APPROVALS[req["id"]] = req
                    continue
            pending.append(req)
    return {"requests": pending}


@router.get("/api/approval/status")
def api_approval_status(request_id: str = Query(...)):
    with APPROVAL_LOCK:
        req = APPROVALS.get(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="request not found")
    return {"status": req["status"], "request": req}


@router.post("/api/approval/decision")
def api_approval_decision(payload: ApprovalDecisionPayload):
    decision = payload.decision.lower()
    if decision not in {"allow", "deny"}:
        raise HTTPException(status_code=400, detail="decision must be allow or deny")

    with APPROVAL_LOCK:
        req = APPROVALS.get(payload.request_id)
        if not req:
            raise HTTPException(status_code=404, detail="request not found")
        req["status"] = decision
        if payload.reason:
            req["decision_reason"] = payload.reason
        req["updated_at"] = datetime.now(timezone.utc).isoformat()
        req["updated_at_ts"] = time.time()
        APPROVALS[payload.request_id] = req

    return {"status": decision}
