"""
Database initialization and management.

This module provides a unified interface for database operations.
Uses Dolt for local development with git-like versioning.

Usage:
    from kurt.db import get_database_client, get_session

    # Get the database client
    db = get_database_client()

    # Initialize database
    db.init_database()

    # Get a session
    session = db.get_session()

Or use convenience functions:
    from kurt.db import init_database, get_session, managed_session

    init_database()

    with managed_session() as session:
        session.add(LLMTrace(...))
        # Auto-commits on exit
"""

from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel import Session, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from kurt.db.dolt import DoltDB


# =============================================================================
# Database Client Factory
# =============================================================================


def _get_database_url_from_config() -> str | None:
    """Get DATABASE_URL from kurt.config if available."""
    try:
        from kurt.config import config_file_exists, load_config

        if config_file_exists():
            config = load_config()
            return config.DATABASE_URL
    except Exception:
        pass
    return None


def get_database_client() -> DoltDB:
    """
    Factory function to get the DoltDB client.

    Priority order for DATABASE_URL:
    1. Environment variable DATABASE_URL
    2. kurt.config DATABASE_URL field

    Routing:
    - "mysql://...": DoltDB connecting to remote Dolt server
    - None, empty, or other: DoltDB for local .dolt database

    Returns:
        DoltDB: Database client for the environment
    """
    import os

    # Priority 1: Environment variable
    database_url = os.environ.get("DATABASE_URL")

    # Priority 2: Config file
    if not database_url:
        database_url = _get_database_url_from_config()

    # MySQL/Dolt connection (Dolt exposes MySQL-compatible protocol)
    if database_url and database_url.startswith("mysql"):
        # Parse URL to extract connection params
        # Format: mysql+pymysql://user@host:port/database
        from urllib.parse import urlparse

        parsed = urlparse(database_url)
        return DoltDB(
            path=Path.cwd(),
            mode="server",
            host=parsed.hostname or "localhost",
            port=parsed.port or 3306,
            user=parsed.username or "root",
            password=parsed.password or "",
            database=parsed.path.lstrip("/") if parsed.path else None,
        )

    # Default: Local Dolt database
    return DoltDB(Path.cwd())


def get_engine():
    """Get SQLAlchemy engine from database client."""
    db = get_database_client()
    return db._get_engine()

__all__ = [
    "get_database_client",
    "DoltDB",
    "Session",
    "init_database",
    "get_session",
    "managed_session",
    "get_async_session_maker",
    "async_session_scope",
    "dispose_async_resources",
    "ensure_tables",
]


def init_database() -> None:
    """Initialize the kurt database."""
    db = get_database_client()
    db.init_database()


def get_session() -> Session:
    """Get a database session."""
    db = get_database_client()
    return db.get_session()


def ensure_tables(models: list[type[SQLModel]], session: Optional[Session] = None) -> None:
    """Create tables for the provided SQLModel classes."""
    if not models:
        return

    close_session = False
    if session is None:
        session = get_session()
        close_session = True

    try:
        engine = session.get_bind()
        if engine is None:
            return
        SQLModel.metadata.create_all(bind=engine, tables=[model.__table__ for model in models])
    finally:
        if close_session:
            session.close()


@contextmanager
def managed_session(session: Optional[Session] = None):
    """Transactional context manager with automatic commit/rollback.

    Works with Dolt database backend.

    Args:
        session: Optional existing session to use (will NOT be closed/committed)

    Yields:
        Session: Database session

    Example:
        with managed_session() as session:
            session.add(LLMTrace(workflow_id="123", ...))
            # Auto-commits on exit, rolls back on exception
    """
    if session is not None:
        yield session
    else:
        _session = get_session()
        try:
            yield _session
            _session.commit()
        except Exception:
            _session.rollback()
            raise
        finally:
            _session.close()


# ========== ASYNC FUNCTIONS ==========


def get_async_session_maker() -> async_sessionmaker:
    """Get async session factory.

    Usage:
        async_session = get_async_session_maker()

        async with async_session() as session:
            result = await session.exec(select(LLMTrace).limit(10))
    """
    db = get_database_client()
    return db.get_async_session_maker()


@asynccontextmanager
async def async_session_scope(session: Optional[AsyncSession] = None):
    """Async session context manager.

    Args:
        session: Optional existing session (for nested calls)

    Yields:
        AsyncSession: Database session

    Usage:
        async with async_session_scope() as session:
            result = await session.exec(select(LLMTrace))
    """
    if session is not None:
        yield session
    else:
        async_session_maker = get_async_session_maker()
        async with async_session_maker() as _session:
            yield _session


async def dispose_async_resources():
    """Cleanup async database resources.

    Call this at application shutdown.
    """
    db = get_database_client()
    if hasattr(db, "dispose_async_engine"):
        await db.dispose_async_engine()
