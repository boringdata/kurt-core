"""Tests for database client factory pattern."""

from unittest.mock import patch

import pytest

from kurt.config.base import KurtConfig
from kurt.db.base import get_database_client
from kurt.db.postgresql import PostgreSQLClient
from kurt.db.sqlite import SQLiteClient


def test_get_database_client_returns_sqlite_by_default():
    """Test factory returns SQLiteClient when no DATABASE_URL is set."""
    with patch("kurt.db.base.get_config_or_default") as mock_config:
        mock_config.return_value = KurtConfig()

        client = get_database_client()

        assert isinstance(client, SQLiteClient)
        assert client.get_mode_name() == "local"


def test_get_database_client_returns_postgres_with_url():
    """Test factory returns PostgreSQLClient when DATABASE_URL is set."""
    with patch("kurt.db.base.get_config_or_default") as mock_config:
        mock_config.return_value = KurtConfig(
            DATABASE_URL="postgresql://user:pass@host:5432/db",
            WORKSPACE_ID="workspace-123",
        )

        client = get_database_client()

        assert isinstance(client, PostgreSQLClient)
        assert client.get_mode_name() == "postgresql"
        assert client.database_url == "postgresql://user:pass@host:5432/db"
        assert client.workspace_id == "workspace-123"


def test_get_database_client_postgres_without_workspace():
    """Test PostgreSQLClient can be created without workspace_id."""
    with patch("kurt.db.base.get_config_or_default") as mock_config:
        mock_config.return_value = KurtConfig(
            DATABASE_URL="postgresql://user:pass@host:5432/db",
            WORKSPACE_ID=None,
        )

        client = get_database_client()

        assert isinstance(client, PostgreSQLClient)
        assert client.workspace_id is None


def test_get_database_client_caching():
    """Test that factory creates new client instances each time."""
    with patch("kurt.db.base.get_config_or_default") as mock_config:
        mock_config.return_value = KurtConfig()

        client1 = get_database_client()
        client2 = get_database_client()

        # Should be different instances (no caching)
        assert client1 is not client2


def test_database_client_mode_switching():
    """Test switching between SQLite and PostgreSQL based on config."""
    # Start with SQLite
    with patch("kurt.db.base.get_config_or_default") as mock_config:
        mock_config.return_value = KurtConfig()

        client = get_database_client()
        assert isinstance(client, SQLiteClient)

    # Switch to PostgreSQL
    with patch("kurt.db.base.get_config_or_default") as mock_config:
        mock_config.return_value = KurtConfig(DATABASE_URL="postgresql://user:pass@host:5432/db")

        client = get_database_client()
        assert isinstance(client, PostgreSQLClient)


def test_database_client_interface():
    """Test that both clients implement DatabaseClient interface."""
    from kurt.db.base import DatabaseClient

    with patch("kurt.db.base.get_config_or_default") as mock_config:
        # Test SQLiteClient
        mock_config.return_value = KurtConfig()
        sqlite_client = get_database_client()
        assert isinstance(sqlite_client, DatabaseClient)
        assert hasattr(sqlite_client, "get_database_url")
        assert hasattr(sqlite_client, "get_session")
        assert hasattr(sqlite_client, "check_database_exists")
        assert hasattr(sqlite_client, "get_mode_name")

        # Test PostgreSQLClient
        mock_config.return_value = KurtConfig(DATABASE_URL="postgresql://user:pass@host:5432/db")
        postgres_client = get_database_client()
        assert isinstance(postgres_client, DatabaseClient)
        assert hasattr(postgres_client, "get_database_url")
        assert hasattr(postgres_client, "get_session")
        assert hasattr(postgres_client, "check_database_exists")
        assert hasattr(postgres_client, "get_mode_name")


def test_database_url_validation():
    """Test PostgreSQLClient validates DATABASE_URL."""
    with pytest.raises(ValueError, match="DATABASE_URL is required"):
        PostgreSQLClient(database_url=None)

    with pytest.raises(ValueError, match="DATABASE_URL is required"):
        PostgreSQLClient(database_url="")


def test_postgres_connection_string_formats():
    """Test PostgreSQLClient accepts various connection string formats."""
    # Standard format
    client = PostgreSQLClient(database_url="postgresql://user:pass@host:5432/db")
    assert client.database_url == "postgresql://user:pass@host:5432/db"

    # With postgres:// scheme
    client = PostgreSQLClient(database_url="postgres://user:pass@host:5432/db")
    assert client.database_url == "postgres://user:pass@host:5432/db"

    # With special characters in password
    client = PostgreSQLClient(database_url="postgresql://user:p@ss%21@host:5432/db")
    assert "p@ss%21" in client.database_url
