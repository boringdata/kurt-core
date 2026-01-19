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


def get_database_client() -> DatabaseClient:
    """
    Factory function to get the appropriate database client.

    Priority order for DATABASE_URL:
    1. Environment variable DATABASE_URL
    2. kurt.config DATABASE_URL field

    Values:
    - "postgresql://...": Returns PostgreSQLClient (direct connection)
    - None, empty, or "kurt": Returns SQLiteClient (local .kurt/kurt.sqlite)

    Note: In cloud mode (DATABASE_URL="kurt"), CLI commands check is_cloud_mode()
    and route to API before calling this function, so SQLiteClient is never used.

    Returns:
        DatabaseClient: Appropriate client for the environment
    """
    import os

    # Priority 1: Environment variable
    database_url = os.environ.get("DATABASE_URL")

    # Priority 2: Config file
    if not database_url:
        database_url = _get_database_url_from_config()

    # PostgreSQL direct connection
    if database_url and database_url.startswith("postgres"):
        try:
            from kurt.db.postgresql import PostgreSQLClient

            return PostgreSQLClient(database_url)
        except ImportError as e:
            missing_module = str(e).split("'")[1] if "'" in str(e) else "unknown"
            raise ImportError(
                f"PostgreSQL mode requires additional dependencies.\n"
                f"Missing module: {missing_module}\n\n"
                f"Install with: uv pip install 'kurt[postgres]'\n"
                f"Or install all extras: uv pip install 'kurt[all]'"
            ) from e

    # Default: SQLite (also used as fallback for DATABASE_URL="kurt")
    from kurt.db.sqlite import SQLiteClient

    return SQLiteClient()
