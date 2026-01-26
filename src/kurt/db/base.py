"""
Database client factory.

Returns DoltDB instance for all database operations.
Dolt provides local database with git-like versioning via MySQL protocol.
"""

from pathlib import Path

from kurt.db.dolt import DoltDB


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
