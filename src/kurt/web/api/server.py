from __future__ import annotations

import asyncio
import difflib
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from shutil import which
from threading import Lock
from typing import Any, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from kurt.cloud.auth import (
    get_cloud_api_url,
    get_workspace_id_from_config,
    load_credentials,
)
from kurt.db.tenant import is_cloud_mode
from kurt.web.api.auth import (
    auth_middleware_setup,
    get_authenticated_user,
)
from kurt.web.api.pty_bridge import build_claude_args, handle_pty_websocket
from kurt.web.api.storage import LocalStorage, S3Storage
from kurt.web.api.stream_bridge import handle_stream_websocket

# Ensure working directory is project root (when running from worktree)
# Skip in cloud deployments where filesystem may be read-only
try:
    project_root = Path(os.environ.get("KURT_PROJECT_ROOT", Path.cwd())).expanduser().resolve()
    if project_root.exists():
        os.chdir(project_root)
except Exception:
    # Skip chdir in environments where it's not needed (e.g., Vercel)
    pass


def get_session_for_request(request: Request):
    """Get database session for API request.

    In cloud mode (when DATABASE_URL env var is set), uses PostgreSQL.
    In local mode, uses SQLite via managed_session.

    Returns:
        Session for database queries
    """
    import logging
    import os
    from contextlib import contextmanager

    # Check if DATABASE_URL is set (cloud/PostgreSQL mode)
    database_url = os.environ.get("DATABASE_URL")

    logging.info(f"DATABASE_URL present: {database_url is not None}")
    if database_url:
        logging.info(f"DATABASE_URL value: {database_url[:20]}...")
        logging.info(f"Starts with 'postgresql': {database_url.startswith('postgresql')}")

    if database_url and database_url.startswith("postgresql"):
        # Cloud mode: direct PostgreSQL connection
        logging.info("Using PostgreSQL connection")
        from sqlalchemy import create_engine
        from sqlmodel import Session

        engine = create_engine(database_url)

        @contextmanager
        def _postgres_session():
            with Session(engine) as session:
                yield session

        return _postgres_session()

    # Local mode: use managed_session (SQLite)
    logging.warning("Falling back to managed_session (SQLite)")
    from kurt.db import managed_session

    return managed_session()


class FilePayload(BaseModel):
    content: str


class RenamePayload(BaseModel):
    old_path: str
    new_path: str


class MovePayload(BaseModel):
    src_path: str
    dest_dir: str


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


class ClaudeStreamPayload(BaseModel):
    prompt: str
    session_id: str | None = None
    resume: bool = False
    fork_session: str | None = None
    output_format: str = "stream-json"


def get_storage():
    mode = os.environ.get("KURT_STORAGE", "local")
    if mode == "s3":
        bucket = os.environ.get("KURT_S3_BUCKET")
        if not bucket:
            raise RuntimeError("KURT_S3_BUCKET must be set for s3 storage")
        prefix = os.environ.get("KURT_S3_PREFIX", "")
        return S3Storage(bucket=bucket, prefix=prefix)
    return LocalStorage(project_root=Path.cwd())


app = FastAPI(title="Kurt Web API")

APPROVAL_LOCK = Lock()
APPROVALS: dict[str, dict] = {}
APPROVAL_TIMEOUT_SECONDS = int(os.environ.get("KURT_APPROVAL_TIMEOUT", "600"))
APPROVAL_CLEANUP_SECONDS = int(os.environ.get("KURT_APPROVAL_CLEANUP_SECONDS", "600"))

allowed_origins_raw = os.environ.get("KURT_WEB_ORIGINS") or os.environ.get(
    "KURT_WEB_ORIGIN",
    "http://localhost:5173,http://127.0.0.1:5173",
)
allowed_origins = [origin.strip() for origin in allowed_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add auth middleware for cloud mode (DATABASE_URL="kurt")
if is_cloud_mode():
    app.middleware("http")(auth_middleware_setup)


# --- Production static file serving ---
# Detect if built frontend assets exist
CLIENT_DIST = Path(__file__).parent.parent / "client" / "dist"

if CLIENT_DIST.exists() and (CLIENT_DIST / "index.html").exists():
    # Mount assets directory for JS/CSS bundles
    assets_dir = CLIENT_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


@app.get("/api/project")
def api_project():
    return {"root": str(Path.cwd().resolve())}


@app.get("/api/sessions")
async def api_sessions():
    """List active Claude stream sessions."""
    from kurt.web.api.stream_bridge import _SESSION_REGISTRY

    sessions = []
    for session_id, session in _SESSION_REGISTRY.items():
        sessions.append(
            {
                "id": session_id,
                "alive": session.is_alive(),
                "clients": len(session.clients),
                "history_count": len(session.history),
            }
        )
    return {"sessions": sessions}


@app.post("/api/sessions")
async def api_create_session():
    """Create a new session ID (client will connect via WebSocket)."""
    import uuid

    session_id = str(uuid.uuid4())
    return {"session_id": session_id}


@app.get("/api/config")
def api_config():
    """Get Kurt project configuration for frontend sections."""
    try:
        from kurt.config import config_file_exists, load_config

        if not config_file_exists():
            return {
                "available": False,
                "paths": {
                    "sources": "sources",
                    "projects": "projects",
                    "workflows": "workflows",
                    "rules": "rules",
                    "kurt": ".kurt",
                },
            }

        config = load_config()
        return {
            "available": True,
            "paths": {
                "sources": config.PATH_SOURCES,
                "projects": config.PATH_PROJECTS,
                "workflows": config.PATH_WORKFLOWS,
                "rules": config.PATH_RULES,
                "kurt": str(Path(config.PATH_DB).parent),
            },
        }
    except Exception:
        return {
            "available": False,
            "paths": {
                "sources": "sources",
                "projects": "projects",
                "rules": "rules",
                "kurt": ".kurt",
            },
        }


def _fetch_workspace_name(workspace_id: str, access_token: str) -> Optional[str]:
    """Fetch workspace name from cloud API."""
    import json as json_module
    import urllib.request

    try:
        cloud_url = get_cloud_api_url()
        if not cloud_url:
            return None

        url = f"{cloud_url}/api/v1/workspaces/{workspace_id}"
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {access_token}")

        with urllib.request.urlopen(req, timeout=5) as resp:
            workspace = json_module.loads(resp.read().decode())
            return workspace.get("name")
    except Exception:
        return None


@app.get("/api/me")
def api_me(request: Request):
    """Get current user context.

    Priority:
    1. JWT token in Authorization header (cloud deployment)
    2. CLI credentials from ~/.kurt/credentials.json (local with cloud login)
    3. No auth (local mode)
    """
    # Try JWT auth first (cloud deployment with Supabase)
    user = get_authenticated_user(request)
    if user is not None:
        workspace_name = user.workspace_id  # Default to ID
        return {
            "is_cloud_mode": True,
            "user": {"id": user.user_id, "email": user.email},
            "workspace": {"id": user.workspace_id, "name": workspace_name},
        }

    # Fallback: CLI credentials (~/.kurt/credentials.json) + config workspace
    creds = load_credentials()
    if creds and creds.email:
        # Workspace ID comes from project config (kurt.config), not credentials
        workspace_id = get_workspace_id_from_config()

        # Try to fetch workspace name from cloud API
        workspace_name = None
        if workspace_id and creds.access_token:
            workspace_name = _fetch_workspace_name(workspace_id, creds.access_token)

        return {
            "is_cloud_mode": True,
            "user": {"id": creds.user_id, "email": creds.email},
            "workspace": {
                "id": workspace_id,
                "name": workspace_name,  # None if not fetched
            },
        }

    # No auth available
    return {"is_cloud_mode": is_cloud_mode(), "user": None}


@app.get("/api/status")
def api_status(request: Request):
    """
    Get comprehensive project status.

    Returns document counts, status breakdown, and domain distribution.
    Used by both CLI (in cloud mode) and web UI.
    """
    import logging
    import traceback

    from fastapi import HTTPException

    from kurt.status.queries import get_status_data

    try:
        with get_session_for_request(request) as session:
            return get_status_data(session)
    except Exception as e:
        logging.error(f"Status API error: {e}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Status query failed: {str(e)}")


@app.get("/api/documents")
def api_list_documents(
    request: Request,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    url_pattern: Optional[str] = None,
):
    """
    List documents with optional filters.

    Used by both CLI (in cloud mode) and web UI.
    """
    import logging
    import traceback
    from dataclasses import asdict

    from kurt.documents import DocumentFilters, DocumentRegistry

    try:
        filters = DocumentFilters(
            fetch_status=status,
            limit=limit,
            offset=offset,
            url_contains=url_pattern,
        )

        registry = DocumentRegistry()
        with get_session_for_request(request) as session:
            docs = registry.list(session, filters)
            return [asdict(doc) for doc in docs]
    except Exception as e:
        logging.error(f"Documents API error: {e}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Documents query failed: {str(e)}")


@app.get("/api/documents/count")
def api_count_documents(
    request: Request,
    status: Optional[str] = None,
    url_pattern: Optional[str] = None,
):
    """
    Count documents matching filters.

    Used by both CLI (in cloud mode) and web UI.
    """
    from kurt.documents import DocumentFilters, DocumentRegistry

    filters = DocumentFilters(
        fetch_status=status,
        url_contains=url_pattern,
    )

    registry = DocumentRegistry()
    with get_session_for_request(request) as session:
        return {"count": registry.count(session, filters)}


@app.get("/api/documents/{document_id}")
def api_get_document(request: Request, document_id: str):
    """
    Get a single document's full lifecycle view.

    Used by both CLI (in cloud mode) and web UI.
    """
    from dataclasses import asdict

    from kurt.documents import DocumentRegistry

    registry = DocumentRegistry()
    with get_session_for_request(request) as session:
        doc = registry.get(session, document_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return asdict(doc)


@app.get("/api/tree")
def api_tree(path: Optional[str] = Query(".")):
    try:
        storage = get_storage()
        entries = storage.list_dir(Path.cwd(), Path(path))
        return {"path": path, "entries": entries}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/file")
def api_get_file(path: str = Query(...)):
    try:
        storage = get_storage()
        content = storage.read_file(Path(path))
        return {"path": path, "content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/file")
def api_put_file(path: str = Query(...), payload: FilePayload = None):
    try:
        storage = get_storage()
        if payload is None:
            raise HTTPException(status_code=400, detail="No payload provided")
        storage.write_file(Path(path), payload.content)
        return {"path": path, "status": "ok"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/file")
def api_delete_file(path: str = Query(...)):
    try:
        storage = get_storage()
        storage.delete(Path(path))
        return {"path": path, "status": "deleted"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/file/rename")
def api_rename_file(payload: RenamePayload):
    try:
        storage = get_storage()
        storage.rename(Path(payload.old_path), Path(payload.new_path))
        return {"old_path": payload.old_path, "new_path": payload.new_path, "status": "renamed"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/file/move")
def api_move_file(payload: MovePayload):
    try:
        storage = get_storage()
        new_path = storage.move(Path(payload.src_path), Path(payload.dest_dir))
        return {"src_path": payload.src_path, "dest_path": str(new_path), "status": "moved"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Source not found")
    except NotADirectoryError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


def _resolve_path(path_value: str) -> Path:
    root = Path.cwd().resolve()
    target = (root / path_value).resolve()
    if root not in target.parents and target != root:
        raise ValueError("Path outside of project root")
    return target


def _git_available() -> bool:
    return which("git") is not None


def _is_git_repo() -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(Path.cwd()), "rev-parse", "--is-inside-work-tree"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() == "true"
    except Exception:
        return False


def _git_diff_for_path(path_value: str) -> str:
    if not _git_available():
        raise RuntimeError("git is not available")
    if not _is_git_repo():
        raise RuntimeError("not a git repository")

    root = Path.cwd().resolve()
    target = _resolve_path(path_value)
    if not target.exists():
        raise RuntimeError("file does not exist")
    rel_path = target.relative_to(root)

    status = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--", str(rel_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if status.stdout.strip().startswith("??"):
        diff = subprocess.run(
            ["git", "-C", str(root), "diff", "--no-index", os.devnull, str(rel_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        return diff.stdout

    diff = subprocess.run(
        ["git", "-C", str(root), "diff", "--", str(rel_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    return diff.stdout


@app.get("/api/git/diff")
def api_git_diff(path: str = Query(...)):
    try:
        diff = _git_diff_for_path(path)
        return {"path": path, "diff": diff}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@app.post("/api/approval/request")
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


@app.post("/api/approval/pretool")
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


@app.post("/api/approval/posttool")
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


@app.get("/api/approval/pending")
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


@app.get("/api/approval/status")
def api_approval_status(request_id: str = Query(...)):
    with APPROVAL_LOCK:
        req = APPROVALS.get(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="request not found")
    return {"status": req["status"], "request": req}


@app.post("/api/approval/decision")
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


class PermissionPayload(BaseModel):
    permission: str


@app.post("/api/settings/permission")
def api_add_permission(payload: PermissionPayload):
    """Add a permission to .claude/settings.json."""
    settings_path = project_root / ".claude" / "settings.json"

    # Read existing settings
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except json.JSONDecodeError:
            settings = {}
    else:
        settings = {}

    # Ensure permissions.allow list exists
    if "permissions" not in settings:
        settings["permissions"] = {}
    if "allow" not in settings["permissions"]:
        settings["permissions"]["allow"] = []

    # Add permission if not already present
    allow_list = settings["permissions"]["allow"]
    if payload.permission not in allow_list:
        allow_list.append(payload.permission)
        settings["permissions"]["allow"] = allow_list

        # Write back
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")

    return {"status": "added", "permission": payload.permission, "all_permissions": allow_list}


@app.get("/api/settings/permissions")
def api_get_permissions():
    """Get current permissions from .claude/settings.json."""
    settings_path = project_root / ".claude" / "settings.json"

    if not settings_path.exists():
        return {"permissions": []}

    try:
        settings = json.loads(settings_path.read_text())
        return {"permissions": settings.get("permissions", {}).get("allow", [])}
    except json.JSONDecodeError:
        return {"permissions": []}


@app.post("/api/claude")
async def api_claude_stream(payload: ClaudeStreamPayload, request: Request):
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    cmd = os.environ.get("KURT_CLAUDE_CMD", "claude")
    base_args = os.environ.get("KURT_CLAUDE_ARGS", "").split()
    output_flag = os.environ.get("KURT_CLAUDE_OUTPUT_FLAG", "--output-format")
    prompt_flag = os.environ.get("KURT_CLAUDE_PROMPT_FLAG", "").strip()

    if output_flag and output_flag not in base_args:
        base_args += [output_flag, payload.output_format]

    args = build_claude_args(
        base_args,
        payload.session_id,
        payload.resume,
        False,
        payload.fork_session,
        cwd=str(Path.cwd()),
    )

    send_stdin = True
    if prompt_flag:
        args += [prompt_flag, prompt]
        send_stdin = False

    env = os.environ.copy()
    env.setdefault("CLAUDE_CODE_REMOTE", "true")
    env["KURT_SESSION_PROVIDER"] = "claude"
    if payload.session_id:
        env["KURT_SESSION_NAME"] = payload.session_id

    try:
        proc = await asyncio.create_subprocess_exec(
            cmd,
            *args,
            cwd=str(Path.cwd()),
            stdin=asyncio.subprocess.PIPE if send_stdin else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"Claude CLI not found: {exc}") from exc

    async def stream():
        if send_stdin and proc.stdin:
            proc.stdin.write((prompt + "\n").encode("utf-8"))
            await proc.stdin.drain()
            proc.stdin.close()

        try:
            while True:
                if await request.is_disconnected():
                    proc.terminate()
                    break
                chunk = await proc.stdout.read(1024)
                if not chunk:
                    break
                yield chunk

            stderr = await proc.stderr.read()
            await proc.wait()
            if proc.returncode and stderr:
                detail = stderr.decode("utf-8", errors="replace").strip()
                if detail:
                    error_line = json.dumps(
                        {
                            "type": "result",
                            "subtype": "error",
                            "result": f"Claude exited with code {proc.returncode}: {detail}",
                        }
                    )
                    yield (error_line + "\n").encode("utf-8")
        finally:
            if proc.returncode is None:
                proc.terminate()

    return StreamingResponse(stream(), media_type="text/plain")


def _search_files(query: str, limit: int = 50) -> list[dict]:
    """Search for files matching the query in filename."""
    if not query or len(query) < 1:
        return []

    root = Path.cwd().resolve()
    results = []
    query_lower = query.lower()

    # Common patterns to ignore
    ignore_dirs = {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".mypy_cache",
        ".pytest_cache",
        "dist",
        "build",
        ".next",
        ".nuxt",
        "coverage",
        ".tox",
        "eggs",
        "*.egg-info",
    }

    def should_ignore(path: Path) -> bool:
        return any(part in ignore_dirs or part.startswith(".") for part in path.parts)

    for file_path in root.rglob("*"):
        if len(results) >= limit:
            break
        if file_path.is_dir():
            continue
        rel_path = file_path.relative_to(root)
        if should_ignore(rel_path):
            continue
        if query_lower in file_path.name.lower():
            results.append(
                {
                    "name": file_path.name,
                    "path": str(rel_path),
                    "dir": str(rel_path.parent) if str(rel_path.parent) != "." else "",
                }
            )

    # Sort: exact prefix matches first, then by path length
    results.sort(key=lambda r: (not r["name"].lower().startswith(query_lower), len(r["path"])))

    return results[:limit]


@app.get("/api/search")
def api_search(q: str = Query(..., min_length=1)):
    try:
        results = _search_files(q)
        return {"query": q, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _git_status() -> dict[str, str]:
    """Get git status for all changed files. Returns dict of path -> status code."""
    if not _git_available() or not _is_git_repo():
        return {}

    cwd = Path.cwd().resolve()

    # Get git repo root to calculate relative paths
    git_root_result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd),
    )
    if git_root_result.returncode != 0:
        return {}
    git_root = Path(git_root_result.stdout.strip()).resolve()

    # Calculate prefix to strip from git paths to get paths relative to cwd
    try:
        cwd_relative_to_git = cwd.relative_to(git_root)
        prefix = str(cwd_relative_to_git) + "/" if str(cwd_relative_to_git) != "." else ""
    except ValueError:
        # cwd is not under git root
        prefix = ""

    result = subprocess.run(
        ["git", "-C", str(cwd), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )

    status_map = {}
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        # Format: XY filename (where X=index, Y=worktree)
        status_code = line[:2]
        file_path = line[3:].strip()
        # Handle renamed files (old -> new)
        if " -> " in file_path:
            file_path = file_path.split(" -> ")[1]
        # Remove quotes if present
        if file_path.startswith('"') and file_path.endswith('"'):
            file_path = file_path[1:-1]

        # Convert git-relative path to cwd-relative path
        if prefix and file_path.startswith(prefix):
            file_path = file_path[len(prefix) :]
        elif prefix:
            # File is outside cwd, skip it
            continue

        # Map status codes to simple categories
        # M = modified, A = added, D = deleted, R = renamed, C = copied
        # ?? = untracked, !! = ignored
        if status_code == "??":
            status_map[file_path] = "U"  # Untracked
        elif "D" in status_code:
            status_map[file_path] = "D"  # Deleted
        elif "A" in status_code or status_code[0] == "A":
            status_map[file_path] = "A"  # Added (staged)
        else:
            status_map[file_path] = "M"  # Modified

    return status_map


@app.get("/api/git/status")
def api_git_status():
    try:
        if not _git_available():
            return {"available": False, "files": {}}
        if not _is_git_repo():
            return {"available": False, "files": {}}
        status = _git_status()
        return {"available": True, "files": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/git/show")
def api_git_show(path: str = Query(..., description="File path relative to repo root")):
    """Get the original (HEAD) version of a file from git."""
    try:
        if not _git_available() or not _is_git_repo():
            raise HTTPException(status_code=404, detail="Git not available")

        # Sanitize path - remove leading slashes and ..
        clean_path = path.lstrip("/")
        if ".." in clean_path:
            raise HTTPException(status_code=400, detail="Invalid path")

        result = subprocess.run(
            ["git", "show", f"HEAD:{clean_path}"],
            capture_output=True,
            text=True,
            cwd=str(Path.cwd()),
        )

        if result.returncode != 0:
            # File doesn't exist in HEAD (new file)
            # Various error patterns for untracked/new files:
            # - "does not exist" - file not in git at all
            # - "exists on disk" - file exists but not tracked
            # - "exists, but not" - path mismatch hint from git
            stderr = result.stderr
            if (
                "does not exist" in stderr
                or "exists on disk" in stderr
                or "exists, but not" in stderr
            ):
                return {"content": None, "is_new": True}
            raise HTTPException(status_code=404, detail=f"File not in git: {stderr}")

        return {"content": result.stdout, "is_new": False}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Workflow API endpoints ---
# Uses Dolt observability tables (workflow_runs, step_logs, step_events)


def _get_dolt_db():
    """Get a DoltDB instance for workflow queries."""
    from pathlib import Path

    from kurt.config import get_config_file_path
    from kurt.db.dolt import DoltDB

    try:
        project_root = get_config_file_path().parent
    except Exception:
        project_root = Path.cwd()

    dolt_path = os.environ.get("DOLT_PATH", ".")
    path = Path(dolt_path)
    if not path.is_absolute():
        path = project_root / path

    db = DoltDB(path)
    if not db.exists():
        return None
    return db


@app.get("/api/workflows")
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
            conditions.append("status = ?")
            params.append(status)

        if search:
            conditions.append("id LIKE ?")
            params.append(f"%{search}%")

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY started_at DESC LIMIT ? OFFSET ?"
        params.append(limit)
        params.append(offset)

        result = db.query(sql, params)
        workflows = []

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
                "status": row.get("status", "unknown"),
                "created_at": str(row.get("started_at")) if row.get("started_at") else None,
                "updated_at": str(row.get("completed_at")) if row.get("completed_at") else None,
                "error": row.get("error"),
                "parent_workflow_id": parent_workflow_id,
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

        return {"workflows": workflows, "total": len(workflows)}
    except Exception as e:
        # Handle missing table (no workflows run yet)
        if "no such table" in str(e).lower() or "doesn't exist" in str(e).lower():
            return {"workflows": [], "total": 0}
        return {"workflows": [], "total": 0, "error": f"Database error: {e}"}


@app.get("/api/workflows/{workflow_id}")
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
            "status": row.get("status"),
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


@app.post("/api/workflows/{workflow_id}/cancel")
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


@app.get("/api/workflows/{workflow_id}/status")
def api_get_workflow_status(workflow_id: str):
    """Get live workflow status with progress information from Dolt."""
    db = _get_dolt_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # Get workflow run
        result = db.query(
            """
            SELECT id, workflow, status, started_at, completed_at, error, metadata_json
            FROM workflow_runs
            WHERE id LIKE CONCAT(?, '%')
            LIMIT 1
            """,
            [workflow_id],
        )

        if not result.rows:
            raise HTTPException(status_code=404, detail="Workflow not found")

        row = result.rows[0]
        full_id = row.get("id")

        # Parse metadata
        metadata = {}
        raw_metadata = row.get("metadata_json") or row.get("metadata")
        if raw_metadata:
            try:
                metadata = json.loads(raw_metadata) if isinstance(raw_metadata, str) else raw_metadata
            except Exception:
                pass

        # Get step logs for progress info
        step_result = db.query(
            """
            SELECT step_id, step_type, status, started_at, completed_at, input_count, output_count, error_count
            FROM step_logs
            WHERE run_id = ?
            ORDER BY started_at
            """,
            [full_id],
        )

        steps = []
        for step_row in step_result.rows:
            steps.append({
                "step_id": step_row.get("step_id"),
                "step_type": step_row.get("step_type"),
                "status": step_row.get("status"),
                "started_at": str(step_row.get("started_at")) if step_row.get("started_at") else None,
                "completed_at": str(step_row.get("completed_at")) if step_row.get("completed_at") else None,
                "input_count": step_row.get("input_count"),
                "output_count": step_row.get("output_count"),
                "error_count": step_row.get("error_count"),
            })

        # Get latest events for current step progress
        events_result = db.query(
            """
            SELECT step_id, event_type, event_data, created_at
            FROM step_events
            WHERE run_id = ?
            ORDER BY id DESC
            LIMIT 10
            """,
            [full_id],
        )

        latest_events = []
        for event_row in events_result.rows:
            event_data = {}
            if event_row.get("event_data"):
                try:
                    event_data = json.loads(event_row["event_data"]) if isinstance(event_row["event_data"], str) else event_row["event_data"]
                except Exception:
                    pass
            latest_events.append({
                "step_id": event_row.get("step_id"),
                "event_type": event_row.get("event_type"),
                "event_data": event_data,
                "created_at": str(event_row.get("created_at")) if event_row.get("created_at") else None,
            })

        return {
            "workflow_id": full_id,
            "workflow": row.get("workflow"),
            "status": row.get("status"),
            "started_at": str(row.get("started_at")) if row.get("started_at") else None,
            "completed_at": str(row.get("completed_at")) if row.get("completed_at") else None,
            "error": row.get("error"),
            "metadata": metadata,
            "steps": steps,
            "latest_events": latest_events,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows/{workflow_id}/step-logs")
def api_get_step_logs(
    workflow_id: str,
    step: str | None = Query(None, description="Filter by step name"),
    limit: int = Query(100, le=500),
):
    """Get step logs from Dolt step_logs table, optionally filtered by step."""
    db = _get_dolt_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # Get full workflow ID
        wf_result = db.query(
            "SELECT id FROM workflow_runs WHERE id LIKE CONCAT(?, '%') LIMIT 1",
            [workflow_id],
        )

        if not wf_result.rows:
            raise HTTPException(status_code=404, detail="Workflow not found")

        full_id = wf_result.rows[0].get("id")

        # Query step logs
        sql = """
            SELECT step_id, step_type, status, started_at, completed_at,
                   input_count, output_count, error_count, errors, metadata
            FROM step_logs
            WHERE run_id = ?
        """
        params: list[Any] = [full_id]

        if step:
            sql += " AND step_id = ?"
            params.append(step)

        sql += " ORDER BY started_at LIMIT ?"
        params.append(limit)

        result = db.query(sql, params)

        logs = []
        for row in result.rows:
            # Parse JSON fields
            errors = []
            if row.get("errors"):
                try:
                    errors = json.loads(row["errors"]) if isinstance(row["errors"], str) else row["errors"]
                except Exception:
                    pass

            metadata = {}
            if row.get("metadata"):
                try:
                    metadata = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"]
                except Exception:
                    pass

            logs.append({
                "step_id": row.get("step_id"),
                "step_type": row.get("step_type"),
                "status": row.get("status"),
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


@app.get("/api/workflows/{workflow_id}/status/stream")
async def api_stream_workflow_status(workflow_id: str):
    """Stream live workflow status via Server-Sent Events."""
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

    async def event_generator():
        last_status = None
        while True:
            try:
                # Re-fetch status from Dolt
                db_inner = _get_dolt_db()
                if db_inner is None:
                    break

                status_result = db_inner.query(
                    """
                    SELECT id, workflow, status, started_at, completed_at, error
                    FROM workflow_runs WHERE id = ?
                    """,
                    [full_id],
                )

                if not status_result.rows:
                    break

                row = status_result.rows[0]
                status = {
                    "workflow_id": row.get("id"),
                    "workflow": row.get("workflow"),
                    "status": row.get("status"),
                    "started_at": str(row.get("started_at")) if row.get("started_at") else None,
                    "completed_at": str(row.get("completed_at")) if row.get("completed_at") else None,
                    "error": row.get("error"),
                }

                status_json = json.dumps(status)

                # Only send if changed
                if status_json != last_status:
                    yield f"data: {status_json}\n\n"
                    last_status = status_json

                # Stop streaming if workflow completed
                if status.get("status") in ("completed", "failed", "canceled"):
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


@app.get("/api/workflows/{workflow_id}/logs/stream")
async def api_stream_workflow_logs(workflow_id: str):
    """Stream workflow logs via Server-Sent Events."""
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
        last_size = 0
        while True:
            try:
                if log_file.exists():
                    current_size = log_file.stat().st_size
                    if current_size > last_size:
                        with open(log_file, "r") as f:
                            f.seek(last_size)
                            new_content = f.read()
                            if new_content:
                                yield f"data: {json.dumps({'content': new_content})}\n\n"
                        last_size = current_size

                # Check if workflow is done
                db_inner = _get_dolt_db()
                if db_inner:
                    status_result = db_inner.query(
                        "SELECT status FROM workflow_runs WHERE id = ?",
                        [full_id],
                    )
                    if status_result.rows:
                        status = status_result.rows[0].get("status")
                        if status in ("completed", "failed", "canceled"):
                            # Send final content and close
                            await asyncio.sleep(0.5)
                            if log_file.exists():
                                current_size = log_file.stat().st_size
                                if current_size > last_size:
                                    with open(log_file, "r") as f:
                                        f.seek(last_size)
                                        new_content = f.read()
                                        if new_content:
                                            yield f"data: {json.dumps({'content': new_content})}\n\n"
                            yield f"data: {json.dumps({'done': True})}\n\n"
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


@app.get("/api/workflows/{workflow_id}/logs")
def api_get_workflow_logs(
    workflow_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(500, le=5000),
):
    """Read workflow log file in chunks."""
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

    log_file = Path(".kurt") / "logs" / f"workflow-{full_id}.log"

    if not log_file.exists():
        return {"content": "", "total_lines": 0, "has_more": False, "offset": offset}

    try:
        with open(log_file, "r") as f:
            lines = f.readlines()

        total_lines = len(lines)
        selected_lines = lines[offset : offset + limit]
        has_more = offset + limit < total_lines

        return {
            "content": "".join(selected_lines),
            "total_lines": total_lines,
            "offset": offset,
            "limit": limit,
            "has_more": has_more,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# PTY WebSocket endpoint for terminal sessions
PTY_CMD = os.environ.get("KURT_PTY_CMD", "claude")
PTY_ARGS = os.environ.get("KURT_PTY_ARGS", "").split()


@app.websocket("/ws/pty")
async def websocket_pty(websocket: WebSocket):
    """WebSocket endpoint for PTY terminal sessions."""
    await handle_pty_websocket(
        websocket,
        cmd=PTY_CMD,
        base_args=[a for a in PTY_ARGS if a],
        cwd=str(Path.cwd()),
    )


# Stream-JSON WebSocket endpoint for structured Claude communication
STREAM_CMD = os.environ.get("KURT_STREAM_CMD", os.environ.get("KURT_CLAUDE_CMD", "claude"))
STREAM_ARGS = os.environ.get("KURT_STREAM_ARGS", "").split()


@app.websocket("/ws/claude-stream")
async def websocket_claude_stream(websocket: WebSocket):
    """WebSocket endpoint for Claude stream-json sessions.

    Uses pipe-based I/O (not PTY) for structured JSON communication.
    Client sends: {"type": "user", "message": "..."}
    Server forwards Claude's stream-json output directly.
    """
    await handle_stream_websocket(
        websocket,
        cmd=STREAM_CMD,
        base_args=[a for a in STREAM_ARGS if a],
        cwd=str(Path.cwd()),
    )


# --- SPA catch-all route for production ---
# This must be registered LAST to not interfere with API routes
if CLIENT_DIST.exists() and (CLIENT_DIST / "index.html").exists():

    @app.get("/{path:path}")
    async def serve_spa(path: str = ""):
        """Serve the SPA for all non-API routes."""
        # Don't serve SPA for API or WebSocket routes
        if path.startswith("api/") or path.startswith("ws/"):
            raise HTTPException(status_code=404, detail="Not found")
        # Serve index.html for client-side routing
        return FileResponse(str(CLIENT_DIST / "index.html"))
