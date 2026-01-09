from __future__ import annotations

import difflib
import hashlib
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
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from kurt.web.api.pty_bridge import handle_pty_websocket
from kurt.web.api.storage import LocalStorage, S3Storage

# Ensure working directory is project root (when running from worktree)
project_root = Path(os.environ.get("KURT_PROJECT_ROOT", Path.cwd())).expanduser().resolve()
os.chdir(project_root)


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
    "KURT_WEB_ORIGIN", "http://localhost:5173"
)
allowed_origins = [origin.strip() for origin in allowed_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


def _get_db_session():
    """Get a database session for workflow queries."""
    try:
        from kurt.db.database import check_database_exists, get_session

        if not check_database_exists():
            return None
        return get_session()
    except ImportError:
        return None
    except Exception:
        return None


def _decode_workflow_output(raw_output: Any) -> Any:
    """Decode base64/pickle encoded workflow output."""
    if not raw_output:
        return None
    try:
        import base64
        import pickle

        decoded = base64.b64decode(raw_output)
        return pickle.loads(decoded)
    except Exception:
        # Try JSON if pickle fails
        try:
            import json

            return json.loads(raw_output)
        except Exception:
            return raw_output


@app.get("/api/workflows")
def api_list_workflows(
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
):
    """List workflows with optional filtering."""
    session = _get_db_session()
    if session is None:
        return {"workflows": [], "total": 0, "error": "Database not available"}

    try:
        from sqlalchemy import text

        sql = "SELECT workflow_uuid, name, status, created_at, updated_at FROM workflow_status"
        params: dict[str, Any] = {}
        conditions = []

        if status:
            conditions.append("status = :status")
            params["status"] = status

        if search:
            conditions.append("workflow_uuid LIKE :search")
            params["search"] = f"%{search}%"

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

        result = session.execute(text(sql), params)
        workflows = [
            {
                "workflow_uuid": row[0],
                "name": row[1],
                "status": row[2],
                "created_at": str(row[3]) if row[3] else None,
                "updated_at": str(row[4]) if row[4] else None,
            }
            for row in result.fetchall()
        ]
        session.close()

        return {"workflows": workflows, "total": len(workflows)}
    except Exception as e:
        if session:
            session.close()
        # Handle missing table (no workflows run yet)
        if "no such table" in str(e):
            return {"workflows": [], "total": 0}
        # Return error in response body instead of 500, so frontend can display it
        return {"workflows": [], "total": 0, "error": f"Database error: {e}"}


@app.get("/api/workflows/{workflow_id}")
def api_get_workflow(workflow_id: str):
    """Get detailed workflow information."""
    session = _get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        from sqlalchemy import text

        sql = """
            SELECT workflow_uuid, name, status, created_at, updated_at,
                   authenticated_user, output, error
            FROM workflow_status
            WHERE workflow_uuid LIKE :workflow_id || '%'
            LIMIT 1
        """
        result = session.execute(text(sql), {"workflow_id": workflow_id})
        row = result.fetchone()
        session.close()

        if not row:
            raise HTTPException(status_code=404, detail="Workflow not found")

        return {
            "workflow_uuid": row[0],
            "name": row[1],
            "status": row[2],
            "created_at": str(row[3]) if row[3] else None,
            "updated_at": str(row[4]) if row[4] else None,
            "authenticated_user": row[5],
            "output": _decode_workflow_output(row[6]),
            "error": row[7],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workflows/{workflow_id}/cancel")
def api_cancel_workflow(workflow_id: str):
    """Cancel a workflow."""
    try:
        from kurt.workflows import DBOS_AVAILABLE, get_dbos

        if not DBOS_AVAILABLE:
            raise HTTPException(status_code=503, detail="DBOS not available")

        dbos = get_dbos()
        dbos.cancel_workflow(workflow_id)

        return {"status": "cancelled", "workflow_id": workflow_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows/{workflow_id}/status")
def api_get_workflow_status(workflow_id: str):
    """Get live workflow status with progress information."""
    session = _get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        from sqlalchemy import text

        # Get full workflow ID from prefix
        sql = text("""
            SELECT workflow_uuid FROM workflow_status
            WHERE workflow_uuid LIKE :workflow_id || '%'
            LIMIT 1
        """)
        result = session.execute(sql, {"workflow_id": workflow_id})
        row = result.fetchone()
        session.close()

        if not row:
            raise HTTPException(status_code=404, detail="Workflow not found")

        full_id = row[0]

        # Use the existing get_live_status function
        from kurt.core.status import get_live_status

        status = get_live_status(full_id)
        return status

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
    """Get workflow logs from DBOS streams, optionally filtered by step."""
    session = _get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        from sqlalchemy import text

        # Get full workflow ID from prefix
        sql = text("""
            SELECT workflow_uuid FROM workflow_status
            WHERE workflow_uuid LIKE :workflow_id || '%'
            LIMIT 1
        """)
        result = session.execute(sql, {"workflow_id": workflow_id})
        row = result.fetchone()
        session.close()

        if not row:
            raise HTTPException(status_code=404, detail="Workflow not found")

        full_id = row[0]

        from kurt.core.status import get_step_logs

        logs = get_step_logs(full_id, step_name=step, limit=limit)
        return {"logs": logs, "step": step}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows/{workflow_id}/status/stream")
async def api_stream_workflow_status(workflow_id: str):
    """Stream live workflow status via Server-Sent Events."""
    import asyncio
    import json

    from fastapi.responses import StreamingResponse

    session = _get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        from sqlalchemy import text

        # Get full workflow ID from prefix
        sql = text("""
            SELECT workflow_uuid, status FROM workflow_status
            WHERE workflow_uuid LIKE :workflow_id || '%'
            LIMIT 1
        """)
        result = session.execute(sql, {"workflow_id": workflow_id})
        row = result.fetchone()
        session.close()

        if not row:
            raise HTTPException(status_code=404, detail="Workflow not found")

        full_id = row[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    async def event_generator():
        from kurt.core.status import get_live_status

        last_status = None
        while True:
            try:
                status = get_live_status(full_id)
                status_json = json.dumps(status)

                # Only send if changed
                if status_json != last_status:
                    yield f"data: {status_json}\n\n"
                    last_status = status_json

                # Stop streaming if workflow completed
                if status.get("status") in ("completed", "error", "SUCCESS", "ERROR", "CANCELLED"):
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
    import json

    from fastapi.responses import StreamingResponse

    session = _get_db_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        from sqlalchemy import text

        # Get full workflow ID and status
        sql = text("""
            SELECT workflow_uuid, status FROM workflow_status
            WHERE workflow_uuid LIKE :workflow_id || '%'
            LIMIT 1
        """)
        result = session.execute(sql, {"workflow_id": workflow_id})
        row = result.fetchone()
        session.close()

        if not row:
            raise HTTPException(status_code=404, detail="Workflow not found")

        full_id = row[0]

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
                check_session = _get_db_session()
                if check_session:
                    result = check_session.execute(
                        text("SELECT status FROM workflow_status WHERE workflow_uuid = :id"),
                        {"id": full_id},
                    )
                    status_row = result.fetchone()
                    check_session.close()
                    if status_row and status_row[0] in ("SUCCESS", "ERROR", "CANCELLED"):
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
    # First, get the full workflow ID from the database
    session = _get_db_session()
    full_id = workflow_id

    if session is not None:
        try:
            from sqlalchemy import text

            sql = "SELECT workflow_uuid FROM workflow_status WHERE workflow_uuid LIKE :workflow_id || '%' LIMIT 1"
            result = session.execute(text(sql), {"workflow_id": workflow_id})
            row = result.fetchone()
            if row:
                full_id = row[0]
            session.close()
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
