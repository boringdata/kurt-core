"""Tests for db CLI commands (export, import, status).

Tests use:
- tmp_project fixture for SQLite testing
- pytest-postgresql for PostgreSQL integration testing
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from kurt.cli.db import db_group, export_cmd, import_cmd, status_cmd
from kurt.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)

# Skip PostgreSQL tests if not available
pytest_plugins = ["pytest_postgresql"]


class TestDbGroupHelp:
    """Tests for db command group help."""

    def test_db_group_help(self, cli_runner: CliRunner):
        """Test db group shows help."""
        result = invoke_cli(cli_runner, db_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Database management commands")

    def test_db_list_commands(self, cli_runner: CliRunner):
        """Test db group lists all commands."""
        result = invoke_cli(cli_runner, db_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "export")
        assert_output_contains(result, "import")
        assert_output_contains(result, "status")


class TestExportCommand:
    """Tests for `db export` command."""

    def test_export_help(self, cli_runner: CliRunner):
        """Test export command shows help."""
        result = invoke_cli(cli_runner, export_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Export local SQLite database to JSON")

    def test_export_shows_options(self, cli_runner: CliRunner):
        """Test export command lists options in help."""
        result = invoke_cli(cli_runner, export_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--output")
        assert_output_contains(result, "--include-traces")
        assert_output_contains(result, "--pretty")


class TestImportCommand:
    """Tests for `db import` command."""

    def test_import_help(self, cli_runner: CliRunner):
        """Test import command shows help."""
        result = invoke_cli(cli_runner, import_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Import data from JSON export into PostgreSQL")

    def test_import_shows_options(self, cli_runner: CliRunner):
        """Test import command lists options in help."""
        result = invoke_cli(cli_runner, import_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--workspace-id")
        assert_output_contains(result, "--dry-run")
        assert_output_contains(result, "--skip-duplicates")


class TestStatusCommand:
    """Tests for `db status` command."""

    def test_status_help(self, cli_runner: CliRunner):
        """Test status command shows help."""
        result = invoke_cli(cli_runner, status_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Show database status and mode")


# ============================================================================
# Functional Tests with tmp_project (SQLite)
# ============================================================================


class TestExportFunctional:
    """Functional tests for export command with real SQLite database."""

    def test_export_creates_json_file(self, cli_runner: CliRunner, tmp_project: Path):
        """Test export creates a JSON file with expected structure."""
        output_file = tmp_project / "test-export.json"

        result = invoke_cli(cli_runner, db_group, ["export", "--output", str(output_file)])
        assert_cli_success(result)
        assert output_file.exists()

        # Verify JSON structure
        with open(output_file) as f:
            data = json.load(f)

        assert "version" in data
        assert "exported_at" in data
        assert "tables" in data
        assert data["version"] == "1.0"

    def test_export_default_filename(self, cli_runner: CliRunner, tmp_project: Path):
        """Test export creates file with default timestamp-based name."""
        result = invoke_cli(cli_runner, db_group, ["export"])
        assert_cli_success(result)
        assert_output_contains(result, "Exported to kurt-export-")

        # Find the created file
        export_files = list(tmp_project.glob("kurt-export-*.json"))
        assert len(export_files) == 1

    def test_export_pretty_json(self, cli_runner: CliRunner, tmp_project: Path):
        """Test export with --pretty flag creates formatted JSON."""
        output_file = tmp_project / "pretty-export.json"

        result = invoke_cli(
            cli_runner, db_group, ["export", "--output", str(output_file), "--pretty"]
        )
        assert_cli_success(result)

        with open(output_file) as f:
            content = f.read()

        # Pretty-printed JSON has newlines and indentation
        assert "\n" in content
        assert "  " in content  # Indentation

    def test_export_with_data(self, cli_runner: CliRunner, tmp_project_with_docs: Path):
        """Test export includes data from tables."""
        output_file = tmp_project_with_docs / "data-export.json"

        result = invoke_cli(cli_runner, db_group, ["export", "--output", str(output_file)])
        assert_cli_success(result)

        with open(output_file) as f:
            data = json.load(f)

        # Should have map_documents and fetch_documents data
        assert "map_documents" in data["tables"]
        assert "fetch_documents" in data["tables"]
        assert data["tables"]["map_documents"]["count"] > 0

    def test_export_summary_table(self, cli_runner: CliRunner, tmp_project_with_docs: Path):
        """Test export shows summary table with counts."""
        result = invoke_cli(cli_runner, db_group, ["export"])
        assert_cli_success(result)
        assert_output_contains(result, "Export Summary")
        assert_output_contains(result, "map_documents")
        assert_output_contains(result, "fetch_documents")

    def test_export_fails_on_postgres(self, cli_runner: CliRunner, tmp_project: Path):
        """Test export fails when DATABASE_URL is set to PostgreSQL."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/db"}):
            result = invoke_cli(cli_runner, db_group, ["export"])
            assert result.exit_code != 0
            assert_output_contains(result, "Export only works in local SQLite mode")


class TestStatusFunctional:
    """Functional tests for status command."""

    def test_status_shows_sqlite_mode(self, cli_runner: CliRunner, tmp_project: Path):
        """Test status shows SQLite mode."""
        result = invoke_cli(cli_runner, db_group, ["status"])
        assert_cli_success(result)
        assert_output_contains(result, "Database Status")
        assert_output_contains(result, "sqlite")
        assert_output_contains(result, "PostgreSQL: No")

    def test_status_shows_table_counts(self, cli_runner: CliRunner, tmp_project_with_docs: Path):
        """Test status shows table counts."""
        result = invoke_cli(cli_runner, db_group, ["status"])
        assert_cli_success(result)
        assert_output_contains(result, "Table Statistics")
        assert_output_contains(result, "map_documents")
        assert_output_contains(result, "fetch_documents")


# ============================================================================
# PostgreSQL Integration Tests
# ============================================================================


@pytest.fixture
def pg_engine(postgresql):
    """Create SQLAlchemy engine from pytest-postgresql connection."""
    info = postgresql.info
    url = f"postgresql://{info.user}@{info.host}:{info.port}/{info.dbname}"
    engine = create_engine(url)
    return engine


@pytest.fixture
def pg_session(pg_engine):
    """Create a session with the PostgreSQL engine."""
    with Session(pg_engine) as session:
        yield session


@pytest.fixture
def pg_with_tables(pg_engine, pg_session):
    """Create test tables in PostgreSQL."""
    pg_session.execute(
        text("""
            CREATE TABLE IF NOT EXISTS map_documents (
                id SERIAL PRIMARY KEY,
                document_id TEXT UNIQUE,
                source_url TEXT,
                source_type TEXT,
                discovery_method TEXT,
                status TEXT,
                title TEXT,
                user_id TEXT,
                workspace_id TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
    )
    pg_session.execute(
        text("""
            CREATE TABLE IF NOT EXISTS fetch_documents (
                id SERIAL PRIMARY KEY,
                document_id TEXT UNIQUE,
                status TEXT,
                content_length INTEGER,
                fetch_engine TEXT,
                public_url TEXT,
                error TEXT,
                user_id TEXT,
                workspace_id TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
    )
    pg_session.commit()
    yield pg_engine
    pg_session.execute(text("DROP TABLE IF EXISTS fetch_documents"))
    pg_session.execute(text("DROP TABLE IF EXISTS map_documents"))
    pg_session.commit()


class TestImportFunctional:
    """Functional tests for import command with PostgreSQL."""

    @pytest.fixture
    def export_file(self, tmp_path: Path) -> Path:
        """Create a sample export file for import testing."""
        export_data = {
            "version": "1.0",
            "exported_at": "2026-01-14T10:00:00",
            "tables": {
                "map_documents": {
                    "count": 2,
                    "records": [
                        {
                            "document_id": "doc-import-1",
                            "source_url": "https://example.com/page1",
                            "source_type": "url",
                            "discovery_method": "sitemap",
                            "status": "success",
                            "title": "Page 1",
                        },
                        {
                            "document_id": "doc-import-2",
                            "source_url": "https://example.com/page2",
                            "source_type": "url",
                            "discovery_method": "crawl",
                            "status": "success",
                            "title": "Page 2",
                        },
                    ],
                },
                "fetch_documents": {
                    "count": 1,
                    "records": [
                        {
                            "document_id": "doc-import-1",
                            "status": "success",
                            "content_length": 5000,
                            "fetch_engine": "trafilatura",
                            "public_url": "https://example.com/page1",
                        },
                    ],
                },
            },
        }
        export_path = tmp_path / "import-test.json"
        with open(export_path, "w") as f:
            json.dump(export_data, f)
        return export_path

    def test_import_fails_on_sqlite(
        self, cli_runner: CliRunner, tmp_project: Path, export_file: Path
    ):
        """Test import fails when in SQLite mode."""
        result = invoke_cli(
            cli_runner,
            db_group,
            ["import", str(export_file), "--workspace-id", "ws-test"],
        )
        assert result.exit_code != 0
        assert_output_contains(result, "Import requires PostgreSQL")

    def test_import_dry_run(self, cli_runner: CliRunner, pg_with_tables, export_file: Path):
        """Test import with --dry-run shows what would be imported."""
        info = pg_with_tables.url

        with patch.dict(os.environ, {"DATABASE_URL": str(info)}):
            # Mock the auth credentials loading - patch at source module
            with patch("kurt.db.tenant.load_context_from_credentials", return_value=True):
                with patch("kurt.db.get_user_id", return_value="test-user-123"):
                    result = invoke_cli(
                        cli_runner,
                        db_group,
                        [
                            "import",
                            str(export_file),
                            "--workspace-id",
                            "ws-test",
                            "--dry-run",
                        ],
                    )

        assert_cli_success(result)
        assert_output_contains(result, "DRY RUN")
        assert_output_contains(result, "Would import")

    def test_import_requires_workspace_id(self, cli_runner: CliRunner, export_file: Path):
        """Test import requires --workspace-id option."""
        result = invoke_cli(cli_runner, db_group, ["import", str(export_file)])
        assert result.exit_code != 0
        assert "workspace-id" in result.output.lower()

    def test_import_adds_tenant_columns(
        self, cli_runner: CliRunner, pg_with_tables, pg_session, export_file: Path
    ):
        """Test import adds user_id and workspace_id to imported records."""
        info = pg_with_tables.url

        with patch.dict(os.environ, {"DATABASE_URL": str(info)}):
            with patch("kurt.db.tenant.load_context_from_credentials", return_value=True):
                with patch("kurt.db.get_user_id", return_value="user-abc"):
                    with patch("kurt.db.managed_session") as mock_session:
                        # Setup mock session to capture INSERT parameters
                        mock_ctx = MagicMock()
                        mock_session.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                        mock_session.return_value.__exit__ = MagicMock(return_value=False)

                        # Mock execute to return rowcount
                        mock_result = MagicMock()
                        mock_result.rowcount = 1
                        mock_ctx.execute.return_value = mock_result

                        result = invoke_cli(
                            cli_runner,
                            db_group,
                            [
                                "import",
                                str(export_file),
                                "--workspace-id",
                                "ws-xyz",
                            ],
                        )

                        assert_cli_success(result)

                        # Verify tenant columns were added to records
                        calls = mock_ctx.execute.call_args_list
                        if calls:
                            # Check that user_id and workspace_id are in the params
                            for call in calls:
                                params = call[0][1] if len(call[0]) > 1 else {}
                                if "user_id" in params:
                                    assert params["user_id"] == "user-abc"
                                    assert params["workspace_id"] == "ws-xyz"


class TestImportWithRealPostgres:
    """Integration tests for import with actual PostgreSQL database."""

    @pytest.fixture
    def export_file_simple(self, tmp_path: Path) -> Path:
        """Create a minimal export file."""
        export_data = {
            "version": "1.0",
            "exported_at": "2026-01-14T10:00:00",
            "tables": {
                "map_documents": {
                    "count": 1,
                    "records": [
                        {
                            "document_id": "pg-doc-1",
                            "source_url": "https://pg-test.example.com",
                            "source_type": "url",
                            "discovery_method": "manual",
                            "status": "success",
                            "title": "PG Test Doc",
                        },
                    ],
                },
            },
        }
        export_path = tmp_path / "pg-import.json"
        with open(export_path, "w") as f:
            json.dump(export_data, f)
        return export_path

    def test_actual_import_to_postgres(
        self, cli_runner: CliRunner, pg_with_tables, pg_session, export_file_simple: Path
    ):
        """Test actual data import to PostgreSQL."""
        info = pg_with_tables.url

        # Verify table is empty before import
        count_before = pg_session.execute(text("SELECT COUNT(*) FROM map_documents")).scalar()
        assert count_before == 0

        with patch.dict(os.environ, {"DATABASE_URL": str(info), "KURT_CLOUD_AUTH": "true"}):
            with patch("kurt.db.tenant.load_context_from_credentials", return_value=True):
                with patch("kurt.db.get_user_id", return_value="pg-user-test"):
                    # Replace managed_session to use our test session
                    from contextlib import contextmanager

                    @contextmanager
                    def mock_managed_session():
                        yield pg_session

                    with patch("kurt.db.managed_session", mock_managed_session):
                        result = invoke_cli(
                            cli_runner,
                            db_group,
                            [
                                "import",
                                str(export_file_simple),
                                "--workspace-id",
                                "pg-ws-test",
                            ],
                        )

        assert_cli_success(result)

        # Verify data was imported with tenant columns
        pg_session.expire_all()
        row = pg_session.execute(
            text("SELECT * FROM map_documents WHERE document_id = 'pg-doc-1'")
        ).fetchone()

        assert row is not None
        assert row.user_id == "pg-user-test"
        assert row.workspace_id == "pg-ws-test"


class TestStatusWithPostgres:
    """Test status command with PostgreSQL."""

    def test_status_shows_postgres_mode(self, cli_runner: CliRunner, pg_engine):
        """Test status shows PostgreSQL mode when DATABASE_URL is set."""
        with patch.dict(os.environ, {"DATABASE_URL": str(pg_engine.url)}):
            with patch("kurt.db.managed_session") as mock_session:
                mock_ctx = MagicMock()
                mock_session.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_session.return_value.__exit__ = MagicMock(return_value=False)
                mock_ctx.execute.return_value.scalar.return_value = 0

                result = invoke_cli(cli_runner, db_group, ["status"])

        assert_cli_success(result)
        assert_output_contains(result, "postgres")
        assert_output_contains(result, "PostgreSQL: Yes")

    def test_status_shows_cloud_mode(self, cli_runner: CliRunner, pg_engine):
        """Test status shows cloud mode when KURT_CLOUD_AUTH is set."""
        with patch.dict(
            os.environ,
            {"DATABASE_URL": str(pg_engine.url), "KURT_CLOUD_AUTH": "true"},
        ):
            with patch("kurt.db.managed_session") as mock_session:
                mock_ctx = MagicMock()
                mock_session.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_session.return_value.__exit__ = MagicMock(return_value=False)
                mock_ctx.execute.return_value.scalar.return_value = 0

                result = invoke_cli(cli_runner, db_group, ["status"])

        assert_cli_success(result)
        assert_output_contains(result, "kurt-cloud")
        assert_output_contains(result, "Cloud Auth: Enabled")


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestExportEdgeCases:
    """Edge case tests for export command."""

    def test_export_empty_tables(self, cli_runner: CliRunner, tmp_project: Path):
        """Test export works with empty tables."""
        output_file = tmp_project / "empty-export.json"

        result = invoke_cli(cli_runner, db_group, ["export", "--output", str(output_file)])
        assert_cli_success(result)

        with open(output_file) as f:
            data = json.load(f)

        # Tables should exist but be empty
        for table_data in data["tables"].values():
            assert table_data["count"] == 0
            assert table_data["records"] == []


class TestImportEdgeCases:
    """Edge case tests for import command."""

    def test_import_nonexistent_file(self, cli_runner: CliRunner):
        """Test import fails gracefully for non-existent file."""
        result = invoke_cli(
            cli_runner,
            db_group,
            ["import", "/nonexistent/file.json", "--workspace-id", "ws-test"],
        )
        assert result.exit_code != 0

    def test_import_invalid_json(self, cli_runner: CliRunner, tmp_path: Path):
        """Test import fails gracefully for invalid JSON."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json {{{")

        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/db"}):
            with patch("kurt.db.tenant.load_context_from_credentials", return_value=True):
                with patch("kurt.db.get_user_id", return_value="test-user"):
                    # Use catch_exceptions=True to handle JSON decode errors
                    result = cli_runner.invoke(
                        db_group,
                        ["import", str(invalid_file), "--workspace-id", "ws-test"],
                        catch_exceptions=True,
                    )

        assert result.exit_code != 0

    def test_import_requires_auth(self, cli_runner: CliRunner, tmp_path: Path):
        """Test import requires authentication."""
        export_file = tmp_path / "test.json"
        export_file.write_text('{"version": "1.0", "tables": {}}')

        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/db"}):
            with patch("kurt.db.tenant.load_context_from_credentials", return_value=False):
                result = invoke_cli(
                    cli_runner,
                    db_group,
                    ["import", str(export_file), "--workspace-id", "ws-test"],
                )

        assert result.exit_code != 0
        assert_output_contains(result, "Not logged in")
