"""
Base database client interface.

This module provides an abstract interface for database operations.
Supports both SQLite (local dev) and PostgreSQL (production via DBOS).
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlmodel import Session


class DatabaseClient(ABC):
    """
    Abstract base class for database clients.

    This interface allows kurt to work with different database backends:
    - SQLiteClient: Local .kurt/kurt.sqlite database (development)
    - PostgreSQLClient: PostgreSQL database (production, used by DBOS)
    """

    @abstractmethod
    def get_database_url(self) -> str:
        """Get the database connection URL."""
        pass

    @abstractmethod
    def init_database(self) -> None:
        """Initialize the database (create tables, etc.)."""
        pass

    @abstractmethod
    def get_session(self) -> "Session":
        """Get a database session."""
        pass

    @abstractmethod
    def check_database_exists(self) -> bool:
        """Check if the database exists and is accessible."""
        pass

    @abstractmethod
    def get_mode_name(self) -> str:
        """Get the name of this database mode (e.g., 'sqlite', 'postgresql')."""
        pass


def get_database_client() -> DatabaseClient:
    """
    Factory function to get the appropriate database client.

    Checks environment for DATABASE_URL to determine which client to use:
    - If DATABASE_URL is set: PostgreSQLClient (production/DBOS mode)
    - Otherwise: SQLiteClient (local development mode)

    Returns:
        DatabaseClient: Appropriate client for the environment
    """
    import os

    database_url = os.environ.get("DATABASE_URL")

    if database_url and database_url.startswith("postgres"):
        from kurt.db.postgresql import PostgreSQLClient

        return PostgreSQLClient(database_url)
    else:
        from kurt.db.sqlite import SQLiteClient

        return SQLiteClient()
