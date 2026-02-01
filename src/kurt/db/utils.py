"""Shared database utilities for obtaining a DoltDB instance.

Consolidates the various _get_dolt_db() patterns found across the codebase
into a single, flexible function.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kurt.db.dolt import DoltDB


def get_dolt_db(
    *,
    project_root: Path | None = None,
    init_schema: bool = False,
    use_database_client: bool = False,
    error_if_missing: bool = False,
    error_message: str = "Dolt database not initialized",
    error_hint: str = "Run 'kurt init' to initialize the project",
    return_none_if_missing: bool = False,
) -> DoltDB | None:
    """Get a DoltDB instance with configurable behavior.

    This is the single source of truth for obtaining a DoltDB client.
    It supports all usage patterns found in the codebase:

    - DOLT_PATH env var with project root resolution (default behavior)
    - DATABASE_URL-aware client via get_database_client() (use_database_client=True)
    - Error on missing database (error_if_missing=True)
    - Return None on missing database (return_none_if_missing=True)
    - Auto-initialize observability schema (init_schema=True)

    The Dolt database path is resolved as follows (when use_database_client=False):
    1. Read DOLT_PATH from environment variable (defaults to ".")
    2. If the path is relative, resolve it against project_root
    3. If project_root is not provided, detect it from kurt config or cwd

    Args:
        project_root: Optional project root directory. If not provided,
            determined from get_config_file_path() or falls back to cwd.
        init_schema: If True, initialize observability schema if missing.
            When the database doesn't exist and init_schema is True, the
            database is also created (init + schema) in embedded mode.
        use_database_client: If True, use get_database_client() factory
            which respects DATABASE_URL env var for server mode (MySQL).
            This is used by tools/core/runner.py.
        error_if_missing: If True, raise click.Abort() with error messages
            when the database doesn't exist.
        error_message: Error message for Rich console when error_if_missing=True.
        error_hint: Hint message for Rich console when error_if_missing=True.
        return_none_if_missing: If True, return None when database doesn't exist
            instead of raising an error.

    Returns:
        DoltDB instance, or None if return_none_if_missing=True and db is missing.

    Raises:
        click.Abort: If error_if_missing=True and database doesn't exist.
    """
    if use_database_client:
        return _get_dolt_db_via_client(init_schema=init_schema)

    from kurt.db.dolt import DoltDB

    # Resolve Dolt database path from DOLT_PATH env var
    dolt_path_str = os.environ.get("DOLT_PATH", ".")
    path = Path(dolt_path_str)

    if not path.is_absolute():
        if project_root is None:
            project_root = _resolve_project_root()
        path = project_root / path

    db = DoltDB(path)

    if not db.exists():
        if error_if_missing:
            import click
            from rich.console import Console

            console = Console()
            console.print(f"[red]Error: {error_message}[/red]")
            console.print(f"[dim]{error_hint}[/dim]")
            raise click.Abort()

        if return_none_if_missing:
            return None

        if init_schema:
            # Initialize the database and schema
            from kurt.db.dolt import init_observability_schema

            db.init()
            init_observability_schema(db)
            return db

        # Default: return the db object even if it doesn't exist yet
        # (some callers handle this themselves)
        return db

    # Database exists - optionally ensure schema
    if init_schema:
        _ensure_schema(db)

    return db


def _get_dolt_db_via_client(*, init_schema: bool = False) -> "DoltDB":
    """Get DoltDB via get_database_client(), respecting DATABASE_URL.

    This handles server mode (MySQL) and embedded mode, and optionally
    initializes the observability schema.
    """
    from kurt.db.database import get_database_client
    from kurt.db.dolt import init_observability_schema

    db = get_database_client()

    if init_schema:
        if db.mode == "embedded":
            if not db.exists():
                db.init()
                init_observability_schema(db)
            else:
                _ensure_schema(db)
        else:
            # Server mode - check schema exists
            _ensure_schema(db)

    return db


def _ensure_schema(db: "DoltDB") -> None:
    """Ensure observability schema exists on an existing DoltDB."""
    from kurt.db.dolt import check_schema_exists, init_observability_schema

    schema_status = check_schema_exists(db)
    if not all(schema_status.values()):
        init_observability_schema(db)


def _resolve_project_root() -> Path:
    """Resolve project root from config file or fall back to cwd."""
    try:
        from kurt.config import get_config_file_path

        return get_config_file_path().parent
    except Exception:
        return Path.cwd()
