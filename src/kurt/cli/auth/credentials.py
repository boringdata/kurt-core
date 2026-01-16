"""Credential storage for Kurt Cloud authentication."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

# =============================================================================
# Kurt Cloud Configuration
# =============================================================================

# Kurt Cloud API URL - all auth goes through Kurt Cloud, not Supabase directly
KURT_CLOUD_API_URL = "https://kurt-cloud.vercel.app"


@dataclass
class Credentials:
    """Stored authentication credentials."""

    access_token: str
    refresh_token: str
    user_id: str
    email: Optional[str] = None
    workspace_id: Optional[str] = None
    expires_at: Optional[int] = None  # Unix timestamp

    def is_expired(self) -> bool:
        """Check if access token is expired."""
        if self.expires_at is None:
            return False
        # Add 60 second buffer
        return datetime.now().timestamp() > (self.expires_at - 60)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Credentials":
        """Create from dictionary."""
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            user_id=data["user_id"],
            email=data.get("email"),
            workspace_id=data.get("workspace_id"),
            expires_at=data.get("expires_at"),
        )


def get_config_dir() -> Path:
    """Get config directory for Kurt (~/.kurt)."""
    config_dir = Path.home() / ".kurt"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_credentials_path() -> Path:
    """Get path to credentials file."""
    return get_config_dir() / "credentials.json"


def save_credentials(creds: Credentials) -> None:
    """Save credentials to file."""
    path = get_credentials_path()
    with open(path, "w") as f:
        json.dump(creds.to_dict(), f, indent=2)
    # Secure the file (user read/write only)
    os.chmod(path, 0o600)


def load_credentials() -> Optional[Credentials]:
    """Load credentials from file."""
    path = get_credentials_path()
    if not path.exists():
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        return Credentials.from_dict(data)
    except (json.JSONDecodeError, KeyError):
        return None


def clear_credentials() -> None:
    """Delete stored credentials."""
    path = get_credentials_path()
    if path.exists():
        path.unlink()


def get_cloud_api_url() -> str:
    """Get Kurt Cloud API URL (env override or hardcoded default)."""
    return os.environ.get("KURT_CLOUD_URL") or KURT_CLOUD_API_URL


def ensure_fresh_token() -> Optional[Credentials]:
    """Load credentials and refresh token if expired.

    Returns:
        Fresh credentials, or None if not logged in or refresh failed.
    """
    creds = load_credentials()
    if not creds:
        return None

    # If not expired, return as-is
    if not creds.is_expired():
        return creds

    # Token expired - try to refresh
    if not creds.refresh_token:
        return creds  # No refresh token available

    from kurt.cli.auth.commands import refresh_access_token

    result = refresh_access_token(creds.refresh_token)
    if not result:
        return creds  # Refresh failed, return expired creds

    # Update credentials with fresh token
    fresh_creds = Credentials(
        access_token=result["access_token"],
        refresh_token=result.get("refresh_token", creds.refresh_token),
        user_id=result.get("user_id", creds.user_id),
        email=result.get("email", creds.email),
        workspace_id=creds.workspace_id,
        expires_at=int(datetime.now().timestamp()) + result.get("expires_in", 3600),
    )
    save_credentials(fresh_creds)
    return fresh_creds


# =============================================================================
# Workspace Path Tracking
# =============================================================================


def get_workspaces_path() -> Path:
    """Get path to workspaces tracking file."""
    return get_config_dir() / "workspaces.json"


def load_workspaces() -> dict:
    """Load workspace-to-path mappings.

    Returns:
        Dict mapping workspace_id to workspace info:
        {
            "ws-uuid": {
                "paths": ["/path/to/project1", "/path/to/project2"],
                "name": "Optional workspace name",
                "last_used": "2026-01-15T12:00:00"
            }
        }
    """
    path = get_workspaces_path()
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError):
        return {}


def save_workspaces(workspaces: dict) -> None:
    """Save workspace-to-path mappings."""
    path = get_workspaces_path()
    with open(path, "w") as f:
        json.dump(workspaces, f, indent=2)


def register_workspace_path(
    workspace_id: str, project_path: str, name: Optional[str] = None
) -> None:
    """Register a project path for a workspace.

    Args:
        workspace_id: The workspace UUID
        project_path: Absolute path to the project directory
        name: Optional workspace name
    """
    workspaces = load_workspaces()

    if workspace_id not in workspaces:
        workspaces[workspace_id] = {"paths": [], "name": name, "last_used": None}

    # Add path if not already registered
    if project_path not in workspaces[workspace_id]["paths"]:
        workspaces[workspace_id]["paths"].append(project_path)

    # Update last_used and name
    workspaces[workspace_id]["last_used"] = datetime.now().isoformat()
    if name:
        workspaces[workspace_id]["name"] = name

    save_workspaces(workspaces)


def get_workspace_paths(workspace_id: str) -> list[str]:
    """Get all registered paths for a workspace."""
    workspaces = load_workspaces()
    if workspace_id in workspaces:
        return workspaces[workspace_id].get("paths", [])
    return []


def get_all_workspace_paths() -> dict[str, list[str]]:
    """Get all workspace-to-paths mappings."""
    workspaces = load_workspaces()
    return {ws_id: info.get("paths", []) for ws_id, info in workspaces.items()}
