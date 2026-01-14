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

# Kurt Cloud API URL (for hosted auth callback)
KURT_CLOUD_API_URL = "https://api.kurt.cloud"

# Kurt Cloud Supabase project URL
KURT_CLOUD_SUPABASE_URL = "https://hnhlfropgnbskbsojgts.supabase.co"

# Supabase anon/public key - safe to embed in client apps
# Get this from: https://supabase.com/dashboard/project/hnhlfropgnbskbsojgts/settings/api
KURT_CLOUD_SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhuaGxmcm9wZ25ic2tic29qZ3RzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU3Nzg4NTQsImV4cCI6MjA3MTM1NDg1NH0.oYJMF5XA5k68UOWOjDsg0AM85EyKmtAoCQsyuc61s0I"


@dataclass
class Credentials:
    """Stored authentication credentials."""

    access_token: str
    refresh_token: str
    user_id: str
    email: Optional[str] = None
    workspace_id: Optional[str] = None
    expires_at: Optional[int] = None  # Unix timestamp
    supabase_url: Optional[str] = None

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
            supabase_url=data.get("supabase_url"),
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


def get_supabase_url() -> str:
    """Get Supabase URL (env override or hardcoded default)."""
    return (
        os.environ.get("SUPABASE_URL")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
        or KURT_CLOUD_SUPABASE_URL
    )


def get_supabase_anon_key() -> str:
    """Get Supabase anon key (env override or hardcoded default)."""
    return (
        os.environ.get("SUPABASE_ANON_KEY")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        or KURT_CLOUD_SUPABASE_ANON_KEY
    )


def get_cloud_api_url() -> str:
    """Get Kurt Cloud API URL (env override or hardcoded default)."""
    return os.environ.get("KURT_CLOUD_URL") or KURT_CLOUD_API_URL


def get_auth_callback_url(cli_port: int = 9876) -> str:
    """Get the auth callback URL.

    In production, this points to the hosted Kurt Cloud callback.
    The callback page will then post tokens to the local CLI server.

    Args:
        cli_port: Local CLI callback server port

    Returns:
        Callback URL for Supabase magic link
    """
    cloud_url = get_cloud_api_url()
    return f"{cloud_url}/auth/callback?cli_port={cli_port}"
