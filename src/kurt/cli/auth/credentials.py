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
