"""System routes: project, sessions, config, me, search, settings."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from kurt.cloud.auth import (
    get_cloud_api_url,
    get_workspace_id_from_config,
    load_credentials,
)
from kurt.cloud.tenant import is_cloud_mode
from kurt.web.api.auth import get_authenticated_user
from kurt.web.api.server_helpers import get_session_for_request, get_storage, project_root

router = APIRouter()


# --- Pydantic models ---

class PermissionPayload(BaseModel):
    permission: str


# --- Helper functions ---

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


# --- Endpoints ---

@router.get("/api/project")
def api_project():
    return {"root": str(Path.cwd().resolve())}


@router.get("/api/sessions")
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


@router.post("/api/sessions")
async def api_create_session():
    """Create a new session ID (client will connect via WebSocket)."""
    import uuid

    session_id = str(uuid.uuid4())
    return {"session_id": session_id}


@router.get("/api/config")
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


@router.get("/api/me")
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


@router.get("/api/status")
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


@router.get("/api/search")
def api_search(q: str = Query(..., min_length=1)):
    try:
        results = _search_files(q)
        return {"query": q, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/settings/permission")
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


@router.get("/api/settings/permissions")
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
