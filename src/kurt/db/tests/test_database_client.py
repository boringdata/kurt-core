"""Tests for database client factory defaults.

Tests verify server-only mode behavior (embedded mode has been removed).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from kurt.db.database import get_database_client


def test_get_database_client_defaults_to_server_mode(monkeypatch, tmp_path: Path):
    """Without DATABASE_URL, local Dolt should default to server mode."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DOLT_PATH", raising=False)

    with patch("kurt.db.database.DoltDB") as mock_dolt:
        mock_instance = MagicMock()
        mock_dolt.return_value = mock_instance

        result = get_database_client()

        assert result == mock_instance
        mock_dolt.assert_called_once_with(
            path=tmp_path.resolve(),
            mode="server",
            host="localhost",
            port=3306,
            user="root",
            password="",
            database=tmp_path.name,
        )


def test_get_database_client_mysql_url_uses_server_params(monkeypatch, tmp_path: Path):
    """MySQL DATABASE_URL should configure explicit server connection."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://alice:secret@db.internal:3311/kurtdb")

    with patch("kurt.db.database.DoltDB") as mock_dolt:
        mock_instance = MagicMock()
        mock_dolt.return_value = mock_instance

        result = get_database_client()

        assert result == mock_instance
        mock_dolt.assert_called_once_with(
            path=tmp_path.resolve(),
            mode="server",
            host="db.internal",
            port=3311,
            user="alice",
            password="secret",
            database="kurtdb",
        )


def test_get_database_client_custom_server_url(monkeypatch, tmp_path: Path):
    """KURT_DOLT_SERVER_URL should configure custom host:port."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("KURT_DOLT_SERVER_URL", "dbhost:3307")

    with patch("kurt.db.database.DoltDB") as mock_dolt:
        mock_instance = MagicMock()
        mock_dolt.return_value = mock_instance

        result = get_database_client()

        assert result == mock_instance
        mock_dolt.assert_called_once_with(
            path=tmp_path.resolve(),
            mode="server",
            host="dbhost",
            port=3307,
            user="root",
            password="",
            database=tmp_path.name,
        )


def test_get_database_client_custom_port_override(monkeypatch, tmp_path: Path):
    """KURT_DOLT_PORT should override port from KURT_DOLT_SERVER_URL."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("KURT_DOLT_SERVER_URL", "localhost:3306")
    monkeypatch.setenv("KURT_DOLT_PORT", "3308")

    with patch("kurt.db.database.DoltDB") as mock_dolt:
        mock_instance = MagicMock()
        mock_dolt.return_value = mock_instance

        result = get_database_client()

        assert result == mock_instance
        mock_dolt.assert_called_once_with(
            path=tmp_path.resolve(),
            mode="server",
            host="localhost",
            port=3308,
            user="root",
            password="",
            database=tmp_path.name,
        )
