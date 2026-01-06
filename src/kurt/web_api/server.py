from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from shutil import which
from threading import Lock
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from kurt.storage import LocalStorage, S3Storage

# Ensure working directory is project root (when running from worktree)
os.chdir(Path.cwd())


class FilePayload(BaseModel):
    content: str


class ApprovalRequestPayload(BaseModel):
    tool_name: str
    file_path: str
    diff: str | None = None
    tool_input: dict | None = None
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


@app.post("/api/approval/request")
def api_approval_request(payload: ApprovalRequestPayload):
    request_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    project_path = ""
    if payload.file_path:
        try:
            root = Path.cwd().resolve()
            target = Path(payload.file_path).expanduser().resolve()
            if root in target.parents or target == root:
                project_path = str(target.relative_to(root))
        except Exception:
            project_path = ""
    record = {
        "id": request_id,
        "tool_name": payload.tool_name,
        "file_path": payload.file_path,
        "project_path": project_path,
        "diff": payload.diff or "",
        "tool_input": payload.tool_input or {},
        "requested_at": payload.requested_at or now,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }
    with APPROVAL_LOCK:
        APPROVALS[request_id] = record
    return {"request_id": request_id}


@app.get("/api/approval/pending")
def api_approval_pending():
    with APPROVAL_LOCK:
        pending = [req for req in APPROVALS.values() if req["status"] == "pending"]
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

    root = Path.cwd().resolve()
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"],
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
