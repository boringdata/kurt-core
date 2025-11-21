"""
Base database client interface.

This module provides an abstract interface for database operations.
Currently only SQLite is implemented, but the structure allows for
easy addition of other databases (PostgreSQL, etc.) in the future.
"""

from abc import ABC, abstractmethod

from sqlmodel import Session


class DatabaseClient(ABC):
    """
    Abstract base class for database clients.

    This interface allows Kurt to work with different database backends
    without changing application code. Currently implemented:
    - SQLiteClient: Local .kurt/kurt.sqlite database

    Future implementations could include:
    - PostgreSQLClient: Remote PostgreSQL database
    - MySQLClient: MySQL/MariaDB support
    - etc.
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
    def get_session(self) -> Session:
        """Get a database session."""
        pass

    @abstractmethod
    def check_database_exists(self) -> bool:
        """Check if the database exists and is accessible."""
        pass

    @abstractmethod
    def get_mode_name(self) -> str:
        """Get the name of this database mode (e.g., 'local', 'remote')."""
        pass


def get_database_client() -> DatabaseClient:
    """
    Factory function to get the appropriate database client.

    Checks configuration to determine which database backend to use:
    - If DATABASE_URL is set: Returns PostgreSQLClient (cloud mode)
    - Otherwise: Returns SQLiteClient (local mode)

    Returns:
        DatabaseClient: Either PostgreSQLClient or SQLiteClient
    """
    from kurt.config import get_config_or_default

    config = get_config_or_default()

    # If DATABASE_URL is set, use PostgreSQL
    if config.DATABASE_URL:
        from kurt.db.postgresql import PostgreSQLClient

        return PostgreSQLClient(
            database_url=config.DATABASE_URL,
            workspace_id=config.WORKSPACE_ID,
        )

    # Otherwise, use SQLite (local mode)
    from kurt.db.sqlite import SQLiteClient

    return SQLiteClient()
