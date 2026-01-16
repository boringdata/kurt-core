"""
Database initialization and management.

This module provides a unified interface for database operations.
Supports both SQLite (local dev) and PostgreSQL (production via DBOS).

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
from typing import Optional

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel import Session, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from kurt.db.base import DatabaseClient, get_database_client

__all__ = [
    "get_database_client",
    "DatabaseClient",
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


def check_database_exists() -> bool:
    """Check if the database exists."""
    db = get_database_client()
    return db.check_database_exists()


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

    Works with all database backends:
    - SQLite: Standard SQLModel session
    - PostgreSQL: SQLModel session + RLS context via SET LOCAL

    Args:
        session: Optional existing session to use (will NOT be closed/committed)

    Yields:
        Session: Database session

    Example:
        with managed_session() as session:
            session.add(LLMTrace(workflow_id="123", ...))
            # Auto-commits on exit, rolls back on exception
    """
    from kurt.db.tenant import set_rls_context

    if session is not None:
        # Set RLS context on existing session
        set_rls_context(session)
        yield session
    else:
        _session = get_session()
        try:
            # Set RLS context for PostgreSQL mode
            set_rls_context(_session)
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
