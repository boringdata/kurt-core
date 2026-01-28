"""Kurt Cloud authentication module.

This module provides:
- Credential storage and management
- API helpers for Kurt Cloud authentication
- CLI commands for auth operations

Public API:
- Credentials: Dataclass for stored credentials
- load_credentials, save_credentials, clear_credentials: Credential file operations
- ensure_fresh_token: Get credentials with auto-refresh
- get_cloud_api_url: Get the Kurt Cloud API URL
- get_workspace_id_from_config: Get workspace ID from project config
- get_user_info, refresh_access_token: API helpers
- auth: Click group for CLI commands
"""

from kurt.cloud.auth.api import get_user_info, refresh_access_token
from kurt.cloud.auth.credentials import (
    Credentials,
    clear_credentials,
    ensure_fresh_token,
    get_cloud_api_url,
    get_workspace_id_from_config,
    get_workspace_paths,
    load_credentials,
    register_workspace_path,
    save_credentials,
)

__all__ = [
    # Credentials
    "Credentials",
    "load_credentials",
    "save_credentials",
    "clear_credentials",
    "ensure_fresh_token",
    "get_cloud_api_url",
    "get_workspace_id_from_config",
    # Workspace tracking
    "register_workspace_path",
    "get_workspace_paths",
    # API helpers
    "get_user_info",
    "refresh_access_token",
]
