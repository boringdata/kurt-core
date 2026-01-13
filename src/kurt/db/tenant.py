"""
Workspace context management for multi-tenant isolation.

Usage:
    # In middleware/auth
    set_workspace_context(workspace_id="ws-123", user_id="user-456")

    # In business logic (automatic)
    workspace_id = get_workspace_id()  # Returns "ws-123"

    # Check if multi-tenant mode is enabled
    if is_multi_tenant():
        # Enforce workspace filtering
"""

from __future__ import annotations

import os
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

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

    Returns False for local SQLite mode.
    """
    if os.environ.get("KURT_MULTI_TENANT", "").lower() == "true":
        return True
    if os.environ.get("DATABASE_URL"):
        return True
    return False


def load_context_from_credentials() -> bool:
    """Load workspace context from stored CLI credentials.

    Call this at CLI startup to set context from `kurt auth login` credentials.

    Returns:
        True if context was set, False if no credentials or not logged in.
    """
    try:
        from kurt.cli.auth.credentials import load_credentials

        creds = load_credentials()
        if creds is None:
            return False

        # Set context from stored credentials
        set_workspace_context(
            workspace_id=creds.workspace_id or creds.user_id,
            user_id=creds.user_id,
        )
        return True
    except ImportError:
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
