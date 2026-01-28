"""File and git routes: tree, file CRUD, git diff/status/show."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from shutil import which
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from kurt.web.api.server_helpers import get_storage

router = APIRouter()


# --- Pydantic models ---

class FilePayload(BaseModel):
    content: str


class RenamePayload(BaseModel):
    old_path: str
    new_path: str


class MovePayload(BaseModel):
    src_path: str
    dest_dir: str


# --- Helper functions ---

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
            file_path = file_path[len(prefix):]
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


# --- Endpoints ---

@router.get("/api/tree")
def api_tree(path: Optional[str] = Query(".")):
    try:
        storage = get_storage()
        entries = storage.list_dir(Path.cwd(), Path(path))
        return {"path": path, "entries": entries}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/file")
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


@router.put("/api/file")
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


@router.delete("/api/file")
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


@router.post("/api/file/rename")
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


@router.post("/api/file/move")
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


@router.get("/api/git/diff")
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


@router.get("/api/git/status")
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


@router.get("/api/git/show")
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
