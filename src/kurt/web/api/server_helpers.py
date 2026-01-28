"""Shared helpers and state for the Kurt Web API.

This module contains shared utilities, Pydantic models, and global state
that are used across multiple route modules. It exists to avoid circular
imports between server.py and route modules.
"""

from __future__ import annotations

import os
from pathlib import Path
from threading import Lock

from fastapi import Request

from kurt.web.api.storage import LocalStorage, S3Storage

# --- Project root ---
# Ensure working directory is project root (when running from worktree)
# Skip in cloud deployments where filesystem may be read-only
try:
    project_root = Path(os.environ.get("KURT_PROJECT_ROOT", Path.cwd())).expanduser().resolve()
except Exception:
    project_root = Path.cwd().resolve()


# --- Shared state ---
APPROVAL_LOCK = Lock()
APPROVALS: dict[str, dict] = {}
APPROVAL_TIMEOUT_SECONDS = int(os.environ.get("KURT_APPROVAL_TIMEOUT", "600"))
APPROVAL_CLEANUP_SECONDS = int(os.environ.get("KURT_APPROVAL_CLEANUP_SECONDS", "600"))


# --- Shared functions ---

def get_session_for_request(request: Request):
    """Get database session for API request.

    In cloud mode (when DATABASE_URL env var is set), uses PostgreSQL.
    In local mode, uses SQLite via managed_session.

    Returns:
        Session for database queries
    """
    import logging
    import os
    from contextlib import contextmanager

    # Check if DATABASE_URL is set (cloud/PostgreSQL mode)
    database_url = os.environ.get("DATABASE_URL")

    logging.info(f"DATABASE_URL present: {database_url is not None}")
    if database_url:
        logging.info(f"DATABASE_URL value: {database_url[:20]}...")
        logging.info(f"Starts with 'postgresql': {database_url.startswith('postgresql')}")

    if database_url and database_url.startswith("postgresql"):
        # Cloud mode: direct PostgreSQL connection
        logging.info("Using PostgreSQL connection")
        from sqlalchemy import create_engine
        from sqlmodel import Session

        engine = create_engine(database_url)

        @contextmanager
        def _postgres_session():
            with Session(engine) as session:
                yield session

        return _postgres_session()

    # Local mode: use managed_session (SQLite)
    logging.warning("Falling back to managed_session (SQLite)")
    from kurt.db import managed_session

    return managed_session()


def get_storage():
    mode = os.environ.get("KURT_STORAGE", "local")
    if mode == "s3":
        bucket = os.environ.get("KURT_S3_BUCKET")
        if not bucket:
            raise RuntimeError("KURT_S3_BUCKET must be set for s3 storage")
        prefix = os.environ.get("KURT_S3_PREFIX", "")
        return S3Storage(bucket=bucket, prefix=prefix)
    return LocalStorage(project_root=Path.cwd())
