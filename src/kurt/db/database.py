"""
Database initialization and management.

This module provides a unified interface for database operations.
Currently uses SQLite (.kurt/kurt.sqlite) for local storage.

The architecture supports future expansion to other databases (PostgreSQL, etc.)
without changing application code.

Usage:
    from kurt.db.database import get_database_client

    # Get the database client (currently SQLite)
    db = get_database_client()

    # Initialize database
    db.init_database()

    # Get a session
    session = db.get_session()

Or use convenience functions:
    from kurt.db.database import init_database, get_session

    init_database()
    session = get_session()
"""

from contextlib import asynccontextmanager, contextmanager
from typing import Optional

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel import Session
from sqlmodel.ext.asyncio.session import AsyncSession

from kurt.db.base import DatabaseClient, get_database_client

__all__ = [
    "get_database_client",
    "DatabaseClient",
    "Session",
    "init_database",
    "get_session",
    "session_scope",
    "get_async_session_maker",
    "async_session_scope",
    "dispose_async_resources",
]


# Convenience functions
def init_database() -> None:
    """
    Initialize the Kurt database.

    Creates .kurt/kurt.sqlite and all necessary tables.
    Also stamps the database with the current Alembic schema version.
    """
    db = get_database_client()
    db.init_database()

    # Initialize Alembic version tracking
    try:
        from kurt.db.migrations.utils import initialize_alembic

        initialize_alembic()
    except Exception as e:
        # Don't fail database initialization if Alembic setup fails
        print(f"Warning: Could not initialize migration tracking: {e}")


def get_session() -> Session:
    """Get a database session."""
    db = get_database_client()
    return db.get_session()


def check_database_exists() -> bool:
    """Check if the database exists."""
    db = get_database_client()
    return db.check_database_exists()


@contextmanager
def session_scope(session: Optional[Session] = None):
    """Context manager for database session lifecycle.

    If a session is provided, yields it without closing.
    If no session is provided, creates a new one and closes it when done.

    Args:
        session: Optional existing session to use

    Yields:
        Session: Database session

    Example:
        with session_scope() as s:
            result = s.exec(select(Entity)).all()
    """
    if session is not None:
        yield session
    else:
        _session = get_session()
        try:
            yield _session
        finally:
            _session.close()


# ========== ASYNC FUNCTIONS ==========


def get_async_session_maker() -> async_sessionmaker:
    """Get async session factory.

    Returns:
        async_sessionmaker: Factory for creating AsyncSession instances

    Usage:
        from kurt.db import get_async_session_maker

        async_session = get_async_session_maker()

        async with async_session() as session:
            result = await session.exec(select(Entity).limit(10))
            entities = result.all()
    """
    db = get_database_client()
    return db.get_async_session_maker()


@asynccontextmanager
async def async_session_scope(session: Optional[AsyncSession] = None):
    """Async session context manager (mirrors sync session_scope).

    This follows the official SQLAlchemy async pattern:
    - Each concurrent task should create its own AsyncSession
    - Never share AsyncSession across concurrent tasks

    Args:
        session: Optional existing session (for nested calls that want to
                 reuse the same session, e.g., multiple queries in one transaction)

    Yields:
        AsyncSession: Database session

    Usage:
        # Create new session (most common)
        async def fetch_entity(entity_id: str):
            async with async_session_scope() as session:
                result = await session.exec(
                    select(Entity).where(Entity.id == entity_id)
                )
                return result.first()

        # Reuse existing session (nested operations)
        async def complex_operation():
            async with async_session_scope() as session:
                # Multiple queries in same transaction
                entity = await fetch_entity_with_session(session)
                await update_entity_with_session(entity, session)
                await session.commit()

        async def fetch_entity_with_session(session: AsyncSession):
            async with async_session_scope(session) as s:
                # Reuses provided session
                result = await s.exec(select(Entity))
                return result.first()
    """
    if session is not None:
        # Reuse provided session (nested call)
        yield session
    else:
        # Create new session
        async_session_maker = get_async_session_maker()
        async with async_session_maker() as _session:
            yield _session


async def dispose_async_resources():
    """Cleanup async database resources.

    Call this at application shutdown to properly close async connections.

    Example:
        # In CLI shutdown handler
        import asyncio
        from kurt.db import dispose_async_resources

        async def shutdown():
            await dispose_async_resources()

        asyncio.run(shutdown())
    """
    db = get_database_client()
    if hasattr(db, "dispose_async_engine"):
        await db.dispose_async_engine()
