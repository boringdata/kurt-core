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

    Currently returns SQLiteClient (local mode) by default.

    Future enhancement: Could check environment variables to select
    different database backends (PostgreSQL, MySQL, etc.).

    Returns:
        DatabaseClient: SQLiteClient instance (local .kurt/kurt.sqlite)
    """
    from kurt.db.sqlite import SQLiteClient

    return SQLiteClient()
