"""Tests for admin CLI commands."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from kurt.cli.admin import admin
from kurt.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)

# Check if migrations module exists
try:
    from kurt.db.migrations import utils as migrations_utils  # noqa: F401

    HAS_MIGRATIONS = True
except ImportError:
    HAS_MIGRATIONS = False


class TestAdminGroup:
    """Tests for the admin command group."""

    def test_admin_group_help(self, cli_runner: CliRunner):
        """Test admin group shows help."""
        result = invoke_cli(cli_runner, admin, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Administrative commands")

    def test_admin_list_commands(self, cli_runner: CliRunner):
        """Test admin group lists all commands."""
        result = invoke_cli(cli_runner, admin, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "migrate")


class TestMigrateGroup:
    """Tests for `admin migrate` command group."""

    def test_migrate_help(self, cli_runner: CliRunner):
        """Test migrate group shows help."""
        result = invoke_cli(cli_runner, admin, ["migrate", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Database schema migration commands")

    def test_migrate_list_commands(self, cli_runner: CliRunner):
        """Test migrate group lists all commands."""
        result = invoke_cli(cli_runner, admin, ["migrate", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "apply")
        assert_output_contains(result, "status")
        assert_output_contains(result, "init")


class TestMigrateApplyCommand:
    """Tests for `admin migrate apply` command."""

    def test_apply_help(self, cli_runner: CliRunner):
        """Test apply command shows help."""
        result = invoke_cli(cli_runner, admin, ["migrate", "apply", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Apply pending database migrations")

    def test_apply_shows_options(self, cli_runner: CliRunner):
        """Test apply command lists options in help."""
        result = invoke_cli(cli_runner, admin, ["migrate", "apply", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--auto-confirm")
        assert_output_contains(result, "-y")


class TestMigrateStatusCommand:
    """Tests for `admin migrate status` command."""

    def test_status_help(self, cli_runner: CliRunner):
        """Test status command shows help."""
        result = invoke_cli(cli_runner, admin, ["migrate", "status", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Show current database migration status")


class TestMigrateInitCommand:
    """Tests for `admin migrate init` command."""

    def test_init_help(self, cli_runner: CliRunner):
        """Test init command shows help."""
        result = invoke_cli(cli_runner, admin, ["migrate", "init", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Initialize Alembic")


# ============================================================================
# Functional Tests with Real Database
# ============================================================================


@pytest.fixture
def tmp_project_no_migrations(tmp_path: Path, monkeypatch):
    """
    Create a temporary project with config but WITHOUT running migrations.

    This simulates a project where migrations are pending.
    """
    # Create .kurt directory structure
    kurt_dir = tmp_path / ".kurt"
    kurt_dir.mkdir(parents=True, exist_ok=True)

    # Force SQLite (no DATABASE_URL)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Change to temp directory
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    # Create config file
    from kurt.config import create_config

    create_config()

    yield tmp_path

    os.chdir(original_cwd)


@pytest.fixture
def tmp_project_with_migrations(tmp_project_no_migrations: Path):
    """Create a temporary project with migrations applied via Alembic."""
    from kurt.db.migrations.utils import apply_migrations

    apply_migrations(auto_confirm=True, silent=True)
    yield tmp_project_no_migrations


@pytest.mark.skipif(not HAS_MIGRATIONS, reason="migrations module not available")
class TestMigrateFunctional:
    """Functional tests for migration commands with real database."""

    def test_migrate_status_shows_pending(
        self, cli_runner: CliRunner, tmp_project_no_migrations: Path
    ):
        """Test migrate status on fresh project shows pending migrations."""
        result = invoke_cli(cli_runner, admin, ["migrate", "status"])
        assert_cli_success(result)
        assert "Migration Status" in result.output

    def test_migrate_apply_creates_database(
        self, cli_runner: CliRunner, tmp_project_no_migrations: Path
    ):
        """Test migrate apply creates database and applies migrations."""
        result = invoke_cli(cli_runner, admin, ["migrate", "apply", "-y"])
        assert_cli_success(result)

        # Database should now exist
        db_path = tmp_project_no_migrations / ".kurt" / "kurt.sqlite"
        assert db_path.exists()

    def test_migrate_apply_idempotent(self, cli_runner: CliRunner, tmp_project_no_migrations: Path):
        """Test that running migrate apply twice is idempotent."""
        result1 = invoke_cli(cli_runner, admin, ["migrate", "apply", "-y"])
        assert_cli_success(result1)

        result2 = invoke_cli(cli_runner, admin, ["migrate", "apply", "-y"])
        assert_cli_success(result2)
        assert "up to date" in result2.output.lower()

    def test_full_migration_workflow(self, cli_runner: CliRunner, tmp_project_no_migrations: Path):
        """Test the full migration workflow: status -> apply -> verify tables."""
        # 1. Check initial status
        status1 = invoke_cli(cli_runner, admin, ["migrate", "status"])
        assert_cli_success(status1)
        assert "Pending" in status1.output

        # 2. Apply migrations
        apply_result = invoke_cli(cli_runner, admin, ["migrate", "apply", "-y"])
        assert_cli_success(apply_result)

        # 3. Verify all workflow tables were created
        from kurt.db import managed_session
        from kurt.workflows.fetch.models import FetchDocument
        from kurt.workflows.map.models import MapDocument

        with managed_session() as session:
            # Tables should exist and be queryable
            assert session.query(MapDocument).count() == 0
            assert session.query(FetchDocument).count() == 0


@pytest.mark.skipif(not HAS_MIGRATIONS, reason="migrations module not available")
class TestMigrationUtils:
    """Tests for migration utility functions."""

    def test_get_pending_migrations_fresh(self, tmp_project_no_migrations: Path):
        """Test get_pending_migrations returns migrations for fresh project."""
        from kurt.db.migrations.utils import get_pending_migrations

        pending = get_pending_migrations()
        assert len(pending) >= 2  # At least initial + workflow tables

    def test_apply_migrations_creates_all_tables(self, tmp_project_no_migrations: Path):
        """Test apply_migrations creates all workflow tables."""
        from kurt.db.migrations.utils import apply_migrations

        result = apply_migrations(auto_confirm=True, silent=True)

        assert result["success"] is True
        assert result["count"] >= 2  # At least 2 migrations

    def test_check_migrations_needed_after_apply(self, tmp_project_with_migrations: Path):
        """Test check_migrations_needed returns False after migrations applied."""
        from kurt.db.migrations.utils import check_migrations_needed

        assert check_migrations_needed() is False
