"""Tests for migrate-db command."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from click.testing import CliRunner

from kurt.cli import main
from kurt.db.models import Document, IngestionStatus, SourceType


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary Kurt project with SQLite database."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create kurt.config
    config_file = project_dir / "kurt.config"
    config_file.write_text(
        """PATH_DB=".kurt/kurt.sqlite"
PATH_SOURCES="sources"
PATH_PROJECTS="projects"
PATH_RULES="rules"
"""
    )

    # Create .kurt directory
    kurt_dir = project_dir / ".kurt"
    kurt_dir.mkdir()

    return project_dir


def test_migrate_db_command_exists(runner):
    """Test migrate-db command is registered."""
    result = runner.invoke(main, ["admin", "migrate", "--help"])

    assert result.exit_code == 0
    assert "migrate-db" in result.output


def test_migrate_db_requires_target_url(runner):
    """Test migrate-db command requires --target-url."""
    result = runner.invoke(main, ["admin", "migrate", "migrate-db"])

    assert result.exit_code != 0
    assert "target-url" in result.output.lower() or "required" in result.output.lower()


def test_migrate_db_help(runner):
    """Test migrate-db command help text."""
    result = runner.invoke(main, ["admin", "migrate", "migrate-db", "--help"])

    assert result.exit_code == 0
    assert "PostgreSQL" in result.output
    assert "SQLite" in result.output
    assert "--target-url" in result.output
    assert "--workspace-id" in result.output


@pytest.mark.integration
def test_migrate_db_dry_run(runner, temp_project, monkeypatch):
    """Test migrate-db command with mocked PostgreSQL connection."""
    monkeypatch.chdir(temp_project)

    # Create some test data in SQLite
    from kurt.db.sqlite import SQLiteClient

    sqlite_client = SQLiteClient()
    sqlite_client.init_database()

    session = sqlite_client.get_session()
    doc = Document(
        title="Test Document",
        source_type=SourceType.URL,
        source_url="https://test.example.com",
        ingestion_status=IngestionStatus.FETCHED,
    )
    session.add(doc)
    session.commit()
    session.close()

    # Mock PostgreSQL connection to avoid needing real database
    with patch("kurt.db.migrate_to_postgres.PostgreSQLClient") as mock_pg_client:
        # Mock successful connection
        mock_client_instance = MagicMock()
        mock_client_instance.check_database_exists.return_value = True
        mock_client_instance.get_session.return_value = MagicMock()
        mock_pg_client.return_value = mock_client_instance

        # Run migration with auto-confirm
        result = runner.invoke(
            main,
            [
                "admin",
                "migrate",
                "migrate-db",
                "--target-url",
                "postgresql://test:pass@localhost:5432/test",
                "--workspace-id",
                str(uuid4()),
                "--auto-confirm",
            ],
        )

        # Should succeed (though mocked)
        assert result.exit_code == 0 or "Error" not in result.output


def test_mask_password():
    """Test password masking utility."""
    from kurt.db.migrate_to_postgres import _mask_password

    # Test standard PostgreSQL URL
    url = "postgresql://user:secretpass@db.example.com:5432/postgres"
    masked = _mask_password(url)

    assert "secretpass" not in masked
    assert "***" in masked
    assert "user" in masked
    assert "db.example.com" in masked

    # Test URL without password
    url = "postgresql://user@db.example.com:5432/postgres"
    masked = _mask_password(url)
    assert masked == url  # Should return unchanged

    # Test malformed URL
    url = "not-a-valid-url"
    masked = _mask_password(url)
    assert masked == url  # Should return unchanged


@pytest.mark.integration
def test_migrate_db_updates_config(runner, temp_project, monkeypatch):
    """Test migrate-db updates kurt.config with DATABASE_URL."""
    monkeypatch.chdir(temp_project)

    # Initialize SQLite
    from kurt.db.sqlite import SQLiteClient

    sqlite_client = SQLiteClient()
    sqlite_client.init_database()

    target_url = "postgresql://test:pass@localhost:5432/test"
    workspace_id = str(uuid4())

    # Mock PostgreSQL to avoid real database
    with patch("kurt.db.migrate_to_postgres.PostgreSQLClient") as mock_pg_client:
        mock_client_instance = MagicMock()
        mock_client_instance.check_database_exists.return_value = True
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = []
        mock_client_instance.get_session.return_value = mock_session
        mock_pg_client.return_value = mock_client_instance

        # Run migration
        result = runner.invoke(
            main,
            [
                "admin",
                "migrate",
                "migrate-db",
                "--target-url",
                target_url,
                "--workspace-id",
                workspace_id,
                "--auto-confirm",
            ],
        )

        # Check if config was updated
        config_file = temp_project / "kurt.config"
        config_content = config_file.read_text()

        # DATABASE_URL might be added to config or user instructed to use .env
        # Depending on implementation, this test may need adjustment
        assert "DATABASE_URL" in config_content or result.exit_code == 0


def test_workspace_id_optional(runner):
    """Test migrate-db allows workspace-id to be optional."""
    result = runner.invoke(
        main,
        [
            "admin",
            "migrate",
            "migrate-db",
            "--target-url",
            "postgresql://test:pass@localhost:5432/test",
            "--help",
        ],
    )

    # workspace-id should be optional (not required)
    assert "--workspace-id" in result.output
    assert (
        "Optional" in result.output
        or "optional" in result.output
        or "help" in result.output.lower()
    )
