"""
Workspace context management for local Dolt mode.

Usage:
    # Set workspace context (typically from config)
    set_workspace_context(workspace_id="ws-123", user_id="user-456")

    # In business logic (automatic)
    workspace_id = get_workspace_id()  # Returns "ws-123"

    # Check cloud mode
    if is_cloud_mode():
        # Route to cloud API

Local Dolt mode:
    Workspace is auto-detected from GitHub repo (owner/repo:branch).
    This ensures data is tagged consistently for later migration to cloud.
"""

from __future__ import annotations

import os
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional

# Use ContextVar for async compatibility (works with both sync and async)
_workspace_context: ContextVar[Optional["WorkspaceContext"]] = ContextVar(
    "workspace_context", default=None
)


@dataclass(frozen=True)
class WorkspaceContext:
    """Immutable workspace context for a request."""

    workspace_id: str
    user_id: Optional[str] = None


def set_workspace_context(
    workspace_id: str,
    user_id: Optional[str] = None,
) -> None:
    """Set workspace context for current request/thread.

    Args:
        workspace_id: The workspace ID for data isolation
        user_id: Optional user ID for audit logging
    """
    _workspace_context.set(
        WorkspaceContext(
            workspace_id=workspace_id,
            user_id=user_id,
        )
    )


def clear_workspace_context() -> None:
    """Clear workspace context (call at end of request)."""
    _workspace_context.set(None)


def get_workspace_context() -> Optional[WorkspaceContext]:
    """Get current workspace context, or None if not set."""
    return _workspace_context.get()


def get_workspace_id() -> Optional[str]:
    """Get current workspace ID, or None if not in multi-tenant mode."""
    ctx = _workspace_context.get()
    return ctx.workspace_id if ctx else None


def get_user_id() -> Optional[str]:
    """Get current user ID, or None if not set."""
    ctx = _workspace_context.get()
    return ctx.user_id if ctx else None


def require_workspace_id() -> str:
    """Get workspace ID or raise if not set.

    Use this in code paths that MUST have a workspace context.

    Raises:
        RuntimeError: If workspace context is not set
    """
    workspace_id = get_workspace_id()
    if workspace_id is None:
        raise RuntimeError(
            "Workspace context required but not set. "
            "Ensure request passed through auth middleware."
        )
    return workspace_id


def is_multi_tenant() -> bool:
    """Check if running in multi-tenant mode.

    Returns True if:
    - DATABASE_URL is set (PostgreSQL mode)
    - OR KURT_MULTI_TENANT=true

    Returns False for local Dolt mode.
    """
    if os.environ.get("KURT_MULTI_TENANT", "").lower() == "true":
        return True
    if os.environ.get("DATABASE_URL"):
        return True
    return False


def is_cloud_mode() -> bool:
    """Check if running in Kurt Cloud API mode.

    Cloud API mode is enabled when DATABASE_URL is set to "kurt".
    """
    if os.environ.get("DATABASE_URL") == "kurt":
        return True
    try:
        from kurt.config import config_file_exists, load_config

        if config_file_exists():
            config = load_config()
            return config.DATABASE_URL == "kurt"
    except Exception:
        pass
    return False


def get_mode() -> str:
    """Get current operating mode.

    Returns:
        "dolt" - Dolt database with git-like versioning (only supported mode)
    """
    return "dolt"


# =============================================================================
# Local Workspace Context (from kurt.config)
# =============================================================================


def init_workspace_from_config() -> bool:
    """Initialize workspace context from kurt.config.

    Reads WORKSPACE_ID from config and sets workspace context.
    If no WORKSPACE_ID exists, generates one and saves it to config.
    Call this at CLI startup for local Dolt mode.

    Returns:
        True if context was set, False if no config file.
    """
    # Don't override if already in cloud mode
    if is_cloud_mode():
        return False

    # Already set?
    if get_workspace_id():
        return True

    try:
        from kurt.config import config_file_exists, load_config

        if not config_file_exists():
            return False

        config = load_config()
        workspace_id = config.WORKSPACE_ID

        # Auto-generate WORKSPACE_ID for older configs that don't have one
        if not workspace_id:
            workspace_id = _ensure_workspace_id_in_config()
            if not workspace_id:
                return False

        set_workspace_context(
            workspace_id=workspace_id,
            user_id="local",  # Local user marker
        )
        return True
    except Exception:
        pass

    return False


def _set_workspace_id_in_config(workspace_id: str, overwrite: bool = False) -> bool:
    """Set WORKSPACE_ID in kurt.config if missing (or overwrite if requested)."""
    import re

    try:
        from kurt.config import get_config_file_path

        config_path = get_config_file_path()
        if not config_path.exists():
            return False

        content = config_path.read_text()

        if re.search(r"^WORKSPACE_ID\s*=", content, re.MULTILINE):
            if not overwrite:
                return False
            content = re.sub(
                r"^WORKSPACE_ID\s*=.*$",
                f'WORKSPACE_ID="{workspace_id}"',
                content,
                flags=re.MULTILINE,
            )
        else:
            content += f'\n# Auto-generated workspace identifier\nWORKSPACE_ID="{workspace_id}"\n'

        config_path.write_text(content)
        return True
    except Exception:
        return False


def _ensure_workspace_id_in_config() -> Optional[str]:
    """Generate and save WORKSPACE_ID if missing from config.

    Returns:
        The workspace ID (existing or newly generated), or None on error.
    """
    import uuid

    workspace_id = str(uuid.uuid4())
    if _set_workspace_id_in_config(workspace_id):
        return workspace_id
    return None


def load_context_from_credentials() -> bool:
    """Load workspace context from stored CLI credentials.

    Call this at CLI startup to set context from `kurt cloud login` credentials.
    Uses the stored user_id and workspace_id from kurt.config (single source of truth).

    Returns:
        True if context was set, False if no credentials or not logged in.
    """
    try:
        from kurt.auth import load_credentials

        creds = load_credentials()
        if creds is None:
            return False

        # Get workspace_id from config (single source of truth)
        workspace_id = None
        try:
            from kurt.config import config_file_exists, load_config

            if config_file_exists():
                config = load_config()
                workspace_id = config.WORKSPACE_ID
        except Exception:
            workspace_id = None

        # Fall back to user_id if no workspace_id in config
        if not workspace_id:
            workspace_id = creds.user_id

        # Set context from stored credentials
        set_workspace_context(
            workspace_id=workspace_id,
            user_id=creds.user_id,
        )
        return True
    except ImportError:
        return False
    except Exception:
        return False


# =============================================================================
# SQLAlchemy Event Listeners for Auto-Population
# =============================================================================


def _set_tenant_fields(session: "Session", flush_context, instances) -> None:
    """Auto-populate workspace_id and user_id on new records."""
    ctx = get_workspace_context()
    if ctx is None:
        return  # No context = local mode, skip

    for obj in session.new:
        # Set workspace_id if model has the field and it's not already set
        if hasattr(obj, "workspace_id") and obj.workspace_id is None:
            obj.workspace_id = ctx.workspace_id

        # Set user_id if model has the field and it's not already set
        if hasattr(obj, "user_id") and obj.user_id is None:
            obj.user_id = ctx.user_id


def register_tenant_listeners(engine) -> None:
    """Register SQLAlchemy event listeners for tenant auto-population.

    Call this once during database initialization.

    Args:
        engine: SQLAlchemy engine (not used directly, but kept for API consistency)
    """
    from sqlalchemy import event
    from sqlalchemy.orm import Session

    event.listen(Session, "before_flush", _set_tenant_fields)


# =============================================================================
# Helper for Raw SQL Queries
# =============================================================================


def add_workspace_filter(
    sql: str,
    params: dict,
    table_alias: Optional[str] = None,
) -> tuple[str, dict]:
    """Add workspace_id filter to raw SQL query.

    Args:
        sql: SQL query string
        params: Query parameters dict
        table_alias: Optional table alias (e.g., "fd" for "fetch_documents fd")

    Returns:
        Tuple of (modified_sql, modified_params)

    Example:
        sql = "SELECT * FROM fetch_documents WHERE content_path = :path"
        params = {"path": "/some/path"}
        sql, params = add_workspace_filter(sql, params)
        # Now sql includes "AND workspace_id = :workspace_id" if in multi-tenant mode
    """
    workspace_id = get_workspace_id()
    if workspace_id is None:
        return sql, params

    column = "workspace_id"
    if table_alias:
        column = f"{table_alias}.workspace_id"

    # Add AND clause (assumes WHERE already exists)
    sql = f"{sql} AND {column} = :workspace_id"
    params = {**params, "workspace_id": workspace_id}

    return sql, params
