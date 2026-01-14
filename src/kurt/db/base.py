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


def _resolve_kurt_cloud_url() -> str | None:
    """Resolve DATABASE_URL='kurt' to actual Kurt Cloud connection string.

    Requires user to be logged in (credentials stored).
    Returns pooled connection URL from Kurt Cloud API.
    """
    try:
        from kurt.cli.auth.credentials import get_cloud_api_url, load_credentials

        creds = load_credentials()
        if creds is None or creds.is_expired():
            return None

        # Get pooled connection URL from Kurt Cloud
        import json
        import urllib.request

        cloud_url = get_cloud_api_url()
        req = urllib.request.Request(f"{cloud_url}/api/v1/database/connection")
        req.add_header("Authorization", f"Bearer {creds.access_token}")

        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("connection_url")

    except Exception:
        return None


def get_database_client() -> DatabaseClient:
    """
    Factory function to get the appropriate database client.

    Priority order for DATABASE_URL:
    1. Environment variable DATABASE_URL
    2. kurt.config DATABASE_URL field
       - If "kurt": fetches connection from Kurt Cloud API (requires login)
       - If postgresql://...: uses direct connection

    Falls back to SQLite if no PostgreSQL URL found.

    Returns:
        DatabaseClient: Appropriate client for the environment
    """
    import os

    # Priority 1: Environment variable
    database_url = os.environ.get("DATABASE_URL")

    # Priority 2: Config file
    if not database_url:
        database_url = _get_database_url_from_config()

    # Handle "kurt" magic value - resolve to actual URL
    if database_url == "kurt":
        database_url = _resolve_kurt_cloud_url()
        if not database_url:
            # Fall back to SQLite if cloud resolution fails
            # User likely not logged in
            from kurt.db.sqlite import SQLiteClient

            return SQLiteClient()

    if database_url and database_url.startswith("postgres"):
        from kurt.db.postgresql import PostgreSQLClient

        return PostgreSQLClient(database_url)
    else:
        from kurt.db.sqlite import SQLiteClient

        return SQLiteClient()
