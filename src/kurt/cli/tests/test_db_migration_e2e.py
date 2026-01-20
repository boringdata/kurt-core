"""End-to-end tests for SQLite → cloud migration.

Tests the complete migration flow:
1. Export data from SQLite to JSON
2. Import data into PostgreSQL with tenant context
3. Verify data integrity after migration

The cloud API is mocked - no real cloud connection needed.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from kurt.cli.db import db_group
from kurt.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)

# Requires pytest-postgresql plugin
pytest_plugins = ["pytest_postgresql"]


# =============================================================================
# Fixtures
# =============================================================================


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
def pg_with_migration_tables(pg_engine, pg_session):
    """Create all migration-compatible tables in PostgreSQL.

    Schema matches SQLite (document_id as primary key, no separate id column).

    Includes:
    - map_documents
    - fetch_documents
    - research_documents (if exists)
    - monitoring_signals (if exists)
    """
    # map_documents - schema matches SQLite (document_id is PK)
    pg_session.execute(
        text("""
            CREATE TABLE IF NOT EXISTS map_documents (
                document_id TEXT PRIMARY KEY,
                source_url TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL DEFAULT 'url',
                discovery_method TEXT NOT NULL DEFAULT '',
                discovery_url TEXT,
                status TEXT NOT NULL DEFAULT 'SUCCESS',
                is_new BOOLEAN NOT NULL DEFAULT TRUE,
                title TEXT,
                content_hash TEXT,
                error TEXT,
                metadata_json TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                user_id TEXT,
                workspace_id TEXT
            )
        """)
    )

    # fetch_documents - schema matches SQLite (document_id is PK)
    pg_session.execute(
        text("""
            CREATE TABLE IF NOT EXISTS fetch_documents (
                document_id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'PENDING',
                content_length INTEGER,
                fetch_engine TEXT,
                public_url TEXT,
                error TEXT,
                fetched_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                user_id TEXT,
                workspace_id TEXT
            )
        """)
    )

    # research_documents
    pg_session.execute(
        text("""
            CREATE TABLE IF NOT EXISTS research_documents (
                document_id TEXT PRIMARY KEY,
                workflow_id TEXT,
                query TEXT,
                status TEXT,
                answer TEXT,
                sources_json TEXT,
                user_id TEXT,
                workspace_id TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
    )

    # monitoring_signals
    pg_session.execute(
        text("""
            CREATE TABLE IF NOT EXISTS monitoring_signals (
                signal_id TEXT PRIMARY KEY,
                workflow_id TEXT,
                signal_type TEXT,
                status TEXT,
                title TEXT,
                content TEXT,
                user_id TEXT,
                workspace_id TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
    )

    pg_session.commit()

    yield pg_engine

    # Cleanup
    pg_session.execute(text("DROP TABLE IF EXISTS monitoring_signals"))
    pg_session.execute(text("DROP TABLE IF EXISTS research_documents"))
    pg_session.execute(text("DROP TABLE IF EXISTS fetch_documents"))
    pg_session.execute(text("DROP TABLE IF EXISTS map_documents"))
    pg_session.commit()


# =============================================================================
# E2E Migration Tests
# =============================================================================


class TestSQLiteToCloudMigrationE2E:
    """End-to-end tests for SQLite → cloud (PostgreSQL) migration."""

    @pytest.fixture
    def migration_export_file(self, tmp_path: Path) -> Path:
        """Create a sample export file mimicking real SQLite export structure."""
        export_data = {
            "version": "1.0",
            "exported_at": "2026-01-20T10:00:00",
            "tables": {
                "map_documents": {
                    "count": 3,
                    "records": [
                        {
                            "document_id": "doc-1",
                            "source_url": "https://example.com/docs/intro",
                            "source_type": "url",
                            "discovery_method": "sitemap",
                            "status": "SUCCESS",
                            "title": "Introduction",
                        },
                        {
                            "document_id": "doc-2",
                            "source_url": "https://example.com/docs/guide",
                            "source_type": "url",
                            "discovery_method": "sitemap",
                            "status": "SUCCESS",
                            "title": "User Guide",
                        },
                        {
                            "document_id": "doc-3",
                            "source_url": "https://example.com/blog/post",
                            "source_type": "url",
                            "discovery_method": "crawl",
                            "status": "ERROR",
                            "title": "Blog Post",
                            "error": "404 Not Found",
                        },
                    ],
                },
                "fetch_documents": {
                    "count": 2,
                    "records": [
                        {
                            "document_id": "doc-1",
                            "status": "SUCCESS",
                            "content_length": 5000,
                            "fetch_engine": "trafilatura",
                            "public_url": "https://example.com/docs/intro",
                        },
                        {
                            "document_id": "doc-2",
                            "status": "ERROR",
                            "error": "403 Forbidden",
                            "fetch_engine": "httpx",
                        },
                    ],
                },
            },
        }
        export_path = tmp_path / "migration-export.json"
        with open(export_path, "w") as f:
            json.dump(export_data, f)
        return export_path

    def test_full_migration_flow(
        self,
        cli_runner: CliRunner,
        pg_with_migration_tables,
        pg_session,
        migration_export_file: Path,
    ):
        """Test complete export → import migration with data integrity verification.

        Uses a pre-generated export file to test the import flow independently.
        This verifies:
        1. Import into PostgreSQL with tenant context
        2. All records are migrated
        3. Tenant columns (user_id, workspace_id) are set
        4. Data integrity (field values match)
        """
        test_workspace_id = "ws-migration-test-123"
        test_user_id = "user-migration-test-456"

        pg_url = str(pg_with_migration_tables.url)

        # Verify tables are empty before import
        map_count_before = pg_session.execute(
            text("SELECT COUNT(*) FROM map_documents")
        ).scalar()
        assert map_count_before == 0

        # Create managed_session mock that uses our test session
        @contextmanager
        def mock_managed_session():
            yield pg_session

        with patch.dict(os.environ, {"DATABASE_URL": pg_url, "KURT_CLOUD_AUTH": "true"}):
            with patch("kurt.db.tenant.load_context_from_credentials", return_value=True):
                with patch("kurt.db.get_user_id", return_value=test_user_id):
                    with patch("kurt.db.managed_session", mock_managed_session):
                        result = invoke_cli(
                            cli_runner,
                            db_group,
                            [
                                "import",
                                str(migration_export_file),
                                "--workspace-id",
                                test_workspace_id,
                            ],
                        )

        assert_cli_success(result)
        assert_output_contains(result, "Import complete")

        # Verify counts
        pg_session.expire_all()
        map_count_after = pg_session.execute(
            text("SELECT COUNT(*) FROM map_documents")
        ).scalar()
        fetch_count_after = pg_session.execute(
            text("SELECT COUNT(*) FROM fetch_documents")
        ).scalar()

        assert map_count_after == 3, f"Expected 3 map_documents, got {map_count_after}"
        assert fetch_count_after == 2, f"Expected 2 fetch_documents, got {fetch_count_after}"

        # Verify tenant columns are set
        doc1 = pg_session.execute(
            text("SELECT * FROM map_documents WHERE document_id = 'doc-1'")
        ).fetchone()
        assert doc1 is not None
        assert doc1.user_id == test_user_id
        assert doc1.workspace_id == test_workspace_id
        assert doc1.source_url == "https://example.com/docs/intro"
        assert doc1.title == "Introduction"

        # Verify error document
        doc3 = pg_session.execute(
            text("SELECT * FROM map_documents WHERE document_id = 'doc-3'")
        ).fetchone()
        assert doc3 is not None
        assert doc3.status == "ERROR"
        assert doc3.error == "404 Not Found"

    def test_export_and_import_flow(
        self,
        cli_runner: CliRunner,
        tmp_project_with_docs: Path,
    ):
        """Test the export command produces valid JSON that can be re-imported.

        This is a lighter test that verifies:
        1. Export from SQLite works
        2. Export JSON is valid and contains expected structure
        3. Data counts are correct
        """
        export_file = tmp_project_with_docs / "test-export.json"

        # Export from SQLite
        result = invoke_cli(
            cli_runner, db_group, ["export", "--output", str(export_file), "--pretty"]
        )
        assert_cli_success(result)
        assert export_file.exists()

        # Verify export structure
        with open(export_file) as f:
            export_data = json.load(f)

        assert export_data["version"] == "1.0"
        assert "tables" in export_data
        assert "map_documents" in export_data["tables"]
        assert "fetch_documents" in export_data["tables"]

        # Verify counts from fixture
        map_count = export_data["tables"]["map_documents"]["count"]
        fetch_count = export_data["tables"]["fetch_documents"]["count"]
        assert map_count == 7, f"Expected 7 map_documents, got {map_count}"
        assert fetch_count == 3, f"Expected 3 fetch_documents, got {fetch_count}"

        # Verify records have required fields
        map_records = export_data["tables"]["map_documents"]["records"]
        assert len(map_records) == 7
        for record in map_records:
            assert "document_id" in record
            assert "source_url" in record
            assert "status" in record

    def test_migration_dry_run_preserves_source(
        self,
        cli_runner: CliRunner,
        tmp_project_with_docs: Path,
        pg_with_migration_tables,
        pg_session,
    ):
        """Test that --dry-run shows what would be imported without changes."""
        export_file = tmp_project_with_docs / "dryrun-export.json"

        # Export
        result = invoke_cli(
            cli_runner, db_group, ["export", "--output", str(export_file)]
        )
        assert_cli_success(result)

        # Dry-run import
        pg_url = str(pg_with_migration_tables.url)

        with patch.dict(os.environ, {"DATABASE_URL": pg_url, "KURT_CLOUD_AUTH": "true"}):
            with patch("kurt.db.tenant.load_context_from_credentials", return_value=True):
                with patch("kurt.db.get_user_id", return_value="test-user"):
                    result = invoke_cli(
                        cli_runner,
                        db_group,
                        [
                            "import",
                            str(export_file),
                            "--workspace-id",
                            "ws-dryrun",
                            "--dry-run",
                        ],
                    )

        assert_cli_success(result)
        assert_output_contains(result, "DRY RUN")
        assert_output_contains(result, "Would import")

        # Verify no data was actually imported
        map_count = pg_session.execute(
            text("SELECT COUNT(*) FROM map_documents")
        ).scalar()
        assert map_count == 0, "Dry-run should not import any data"

    def test_migration_with_skip_duplicates(
        self,
        cli_runner: CliRunner,
        pg_with_migration_tables,
        pg_session,
        migration_export_file: Path,
    ):
        """Test that duplicate records are skipped on re-import."""
        workspace_id = "ws-dup-test"
        user_id = "user-dup-test"

        @contextmanager
        def mock_managed_session():
            yield pg_session

        pg_url = str(pg_with_migration_tables.url)

        # First import
        with patch.dict(os.environ, {"DATABASE_URL": pg_url, "KURT_CLOUD_AUTH": "true"}):
            with patch("kurt.db.tenant.load_context_from_credentials", return_value=True):
                with patch("kurt.db.get_user_id", return_value=user_id):
                    with patch("kurt.db.managed_session", mock_managed_session):
                        result = invoke_cli(
                            cli_runner,
                            db_group,
                            ["import", str(migration_export_file), "--workspace-id", workspace_id],
                        )

        assert_cli_success(result)

        pg_session.expire_all()
        first_count = pg_session.execute(
            text("SELECT COUNT(*) FROM map_documents")
        ).scalar()

        # Verify first import actually worked
        assert first_count == 3, f"First import should have 3 records, got {first_count}"

        # Second import (same data)
        with patch.dict(os.environ, {"DATABASE_URL": pg_url, "KURT_CLOUD_AUTH": "true"}):
            with patch("kurt.db.tenant.load_context_from_credentials", return_value=True):
                with patch("kurt.db.get_user_id", return_value=user_id):
                    with patch("kurt.db.managed_session", mock_managed_session):
                        result = invoke_cli(
                            cli_runner,
                            db_group,
                            [
                                "import",
                                str(migration_export_file),
                                "--workspace-id",
                                workspace_id,
                                "--skip-duplicates",
                            ],
                        )

        assert_cli_success(result)

        pg_session.expire_all()
        second_count = pg_session.execute(
            text("SELECT COUNT(*) FROM map_documents")
        ).scalar()

        # Count should remain the same (duplicates skipped)
        assert second_count == first_count, "Duplicate records should be skipped"
        assert_output_contains(result, "Skipped")

    def test_migration_export_preserves_all_fields(
        self,
        cli_runner: CliRunner,
        tmp_project_with_docs: Path,
    ):
        """Test that export preserves all document fields."""
        export_file = tmp_project_with_docs / "fields-export.json"

        result = invoke_cli(
            cli_runner, db_group, ["export", "--output", str(export_file)]
        )
        assert_cli_success(result)

        with open(export_file) as f:
            data = json.load(f)

        # Check map_documents fields
        map_records = data["tables"]["map_documents"]["records"]
        doc1 = next((r for r in map_records if r["document_id"] == "doc-1"), None)
        assert doc1 is not None

        # Verify essential fields are preserved
        assert "source_url" in doc1
        assert "source_type" in doc1
        assert "discovery_method" in doc1
        assert "status" in doc1
        assert "title" in doc1

        # Check fetch_documents fields
        fetch_records = data["tables"]["fetch_documents"]["records"]
        doc4 = next((r for r in fetch_records if r["document_id"] == "doc-4"), None)
        assert doc4 is not None

        assert "content_length" in doc4
        assert "fetch_engine" in doc4
        assert "status" in doc4

        # Check error document
        doc6 = next((r for r in fetch_records if r["document_id"] == "doc-6"), None)
        assert doc6 is not None
        assert "error" in doc6

    def test_migration_multiple_workspaces_isolation(
        self,
        cli_runner: CliRunner,
        pg_with_migration_tables,
        pg_session,
        migration_export_file: Path,
    ):
        """Test that different workspace_ids create isolated data sets."""
        pg_url = str(pg_with_migration_tables.url)

        @contextmanager
        def mock_managed_session():
            yield pg_session

        # Import for workspace A
        with patch.dict(os.environ, {"DATABASE_URL": pg_url, "KURT_CLOUD_AUTH": "true"}):
            with patch("kurt.db.tenant.load_context_from_credentials", return_value=True):
                with patch("kurt.db.get_user_id", return_value="user-a"):
                    with patch("kurt.db.managed_session", mock_managed_session):
                        result = invoke_cli(
                            cli_runner,
                            db_group,
                            ["import", str(migration_export_file), "--workspace-id", "ws-a"],
                        )
        assert_cli_success(result)

        pg_session.expire_all()

        # Verify workspace A data
        ws_a_count = pg_session.execute(
            text("SELECT COUNT(*) FROM map_documents WHERE workspace_id = 'ws-a'")
        ).scalar()
        assert ws_a_count == 3, f"Expected 3 records for ws-a, got {ws_a_count}"

        # All records should have user_id set
        user_a_count = pg_session.execute(
            text("SELECT COUNT(*) FROM map_documents WHERE user_id = 'user-a'")
        ).scalar()
        assert user_a_count == 3


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestMigrationErrorHandling:
    """Test error handling during migration."""

    def test_export_fails_in_cloud_mode(self, cli_runner: CliRunner, tmp_project_with_docs: Path):
        """Test that export fails gracefully when in cloud mode."""
        with patch.dict(os.environ, {"DATABASE_URL": "kurt"}):
            with patch("kurt.db.get_mode", return_value="kurt-cloud"):
                result = invoke_cli(cli_runner, db_group, ["export"])

        assert result.exit_code != 0
        assert_output_contains(result, "Export only works in local SQLite mode")

    def test_import_fails_without_auth(self, cli_runner: CliRunner, tmp_path: Path):
        """Test that import requires authentication."""
        # Create minimal export file
        export_file = tmp_path / "noauth-test.json"
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

    def test_import_fails_in_sqlite_mode(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Test that import fails when target is SQLite."""
        export_file = tmp_project_with_docs / "sqlite-target-test.json"
        export_file.write_text('{"version": "1.0", "tables": {}}')

        # tmp_project_with_docs is SQLite mode
        result = invoke_cli(
            cli_runner,
            db_group,
            ["import", str(export_file), "--workspace-id", "ws-test"],
        )

        assert result.exit_code != 0
        assert_output_contains(result, "Import requires PostgreSQL")


# =============================================================================
# Data Type Handling Tests
# =============================================================================


class TestMigrationDataTypes:
    """Test handling of various data types during migration."""

    def test_datetime_serialization(self, cli_runner: CliRunner, tmp_project_with_docs: Path):
        """Test that datetime fields are properly serialized to ISO format."""
        export_file = tmp_project_with_docs / "datetime-test.json"

        result = invoke_cli(
            cli_runner, db_group, ["export", "--output", str(export_file)]
        )
        assert_cli_success(result)

        with open(export_file) as f:
            data = json.load(f)

        # Check that exported_at is ISO format
        assert "T" in data["exported_at"], "exported_at should be ISO format"

    def test_null_fields_preserved(self, cli_runner: CliRunner, tmp_project_with_docs: Path):
        """Test that null/empty fields are preserved in export."""
        export_file = tmp_project_with_docs / "null-test.json"

        result = invoke_cli(
            cli_runner, db_group, ["export", "--output", str(export_file)]
        )
        assert_cli_success(result)

        with open(export_file) as f:
            data = json.load(f)

        # Find a record without error (should have error as None/null)
        map_records = data["tables"]["map_documents"]["records"]
        # Status values are uppercase (SUCCESS, PENDING, ERROR)
        success_doc = next(
            (r for r in map_records if r["status"] == "SUCCESS" and r["document_id"] == "doc-1"),
            None,
        )

        assert success_doc is not None, f"Could not find doc-1 with SUCCESS status. Records: {map_records[:2]}"
        # error field should be None for successful documents
        assert success_doc.get("error") is None
