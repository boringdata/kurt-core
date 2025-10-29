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

from sqlmodel import Session

from kurt.db.base import DatabaseClient, get_database_client

__all__ = ["get_database_client", "DatabaseClient", "Session", "init_database", "get_session"]


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
