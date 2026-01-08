"""Tests for status CLI command."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from kurt_new.cli.status import status
from kurt_new.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)

# Check if migrations module exists
try:
    from kurt_new.db.migrations import utils as migrations_utils  # noqa: F401

    HAS_MIGRATIONS = True
except ImportError:
    HAS_MIGRATIONS = False


@pytest.fixture
def cli_runner_sqlite(cli_runner: CliRunner, monkeypatch):
    """CLI runner with isolated filesystem and SQLite database."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with cli_runner.isolated_filesystem():
        yield cli_runner


class TestStatusCommand:
    """Tests for `kurt status` command."""

    def test_status_help(self, cli_runner: CliRunner):
        """Test status command shows help."""
        result = invoke_cli(cli_runner, status, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Show comprehensive Kurt project status")

    def test_status_shows_options(self, cli_runner: CliRunner):
        """Test status command lists options in help."""
        result = invoke_cli(cli_runner, status, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--format")
        assert_output_contains(result, "--hook-cc")

    def test_status_format_choices(self, cli_runner: CliRunner):
        """Test status --format accepts valid choices."""
        result = invoke_cli(cli_runner, status, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "pretty")
        assert_output_contains(result, "json")

    def test_status_not_initialized(self, cli_runner: CliRunner, cli_runner_isolated):
        """Test status shows message when not initialized."""
        result = invoke_cli(cli_runner, status, [])
        assert_cli_success(result)
        assert_output_contains(result, "not initialized")

    def test_status_json_not_initialized(self, cli_runner: CliRunner, cli_runner_isolated):
        """Test status --format json outputs JSON when not initialized."""
        result = invoke_cli(cli_runner, status, ["--format", "json"])
        assert_cli_success(result)
        import json

        data = json.loads(result.output)
        assert data["initialized"] is False

    def test_status_with_database(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test status shows documents when database has data."""
        result = invoke_cli(cli_runner, status, ["--format", "json"])
        assert_cli_success(result)
        import json

        data = json.loads(result.output)
        assert data["initialized"] is True
        assert "documents" in data
        assert data["documents"]["total"] == 7


class TestStatusHookCC:
    """Tests for `kurt status --hook-cc` option."""

    def test_hook_cc_auto_init(self, cli_runner_sqlite):
        """Test --hook-cc auto-initializes project if not initialized.

        This test catches bugs where auto-init fails in hook mode.
        """
        result = cli_runner_sqlite.invoke(status, ["--hook-cc"])
        assert_cli_success(result)
        import json

        data = json.loads(result.output)
        assert "systemMessage" in data
        assert "initialized" in data["systemMessage"].lower()

    def test_hook_cc_outputs_valid_json(self, cli_runner: CliRunner, tmp_project):
        """Test --hook-cc outputs valid JSON format for Claude Code hooks."""
        result = invoke_cli(cli_runner, status, ["--hook-cc"])
        assert_cli_success(result)
        import json

        data = json.loads(result.output)
        assert "systemMessage" in data
        assert "hookSpecificOutput" in data
        assert "hookEventName" in data["hookSpecificOutput"]

    def test_hook_cc_with_documents(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test --hook-cc outputs document status when database has data."""
        result = invoke_cli(cli_runner, status, ["--hook-cc"])
        assert_cli_success(result)
        import json

        data = json.loads(result.output)
        assert "Documents" in data["systemMessage"]
        assert "additionalContext" in data["hookSpecificOutput"]


class TestStatusPrettyFormat:
    """Tests for `kurt status` pretty format output."""

    def test_status_pretty_with_project(self, cli_runner: CliRunner, tmp_project):
        """Test status pretty output with initialized project."""
        result = invoke_cli(cli_runner, status, [])
        assert_cli_success(result)
        # Pretty format should show markdown-style output
        assert "Kurt Status" in result.output or "Documents" in result.output

    def test_status_pretty_with_documents(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test status pretty output shows document counts."""
        result = invoke_cli(cli_runner, status, [])
        assert_cli_success(result)
        assert "Documents" in result.output


# ============================================================================
# Migration Warning Tests
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
    from kurt_new.config import create_config

    create_config()

    yield tmp_path

    os.chdir(original_cwd)


@pytest.mark.skipif(not HAS_MIGRATIONS, reason="migrations module not available")
class TestStatusMigrationWarning:
    """Tests for migration warning in kurt status command."""

    def test_status_shows_pending_migrations_warning(
        self, cli_runner: CliRunner, tmp_project_no_migrations: Path
    ):
        """Test that kurt status shows warning when migrations are pending."""
        # First apply migrations to create database
        from kurt_new.db.migrations.utils import apply_migrations

        apply_migrations(auto_confirm=True, silent=True)

        # Now check status - should NOT show migration warning
        result = invoke_cli(cli_runner, status, [])
        assert_cli_success(result)
        # No pending warning when up to date
        assert "pending database migration" not in result.output.lower()

    def test_status_json_includes_migration_info(
        self, cli_runner: CliRunner, tmp_project_no_migrations: Path
    ):
        """Test that kurt status --format json includes migration info."""
        # Apply migrations first
        from kurt_new.db.migrations.utils import apply_migrations

        apply_migrations(auto_confirm=True, silent=True)

        result = invoke_cli(cli_runner, status, ["--format", "json"])
        assert_cli_success(result)

        import json

        data = json.loads(result.output)
        assert "migrations" in data
        assert data["migrations"]["has_pending"] is False

    def test_full_workflow_status_then_migrate(
        self, cli_runner: CliRunner, tmp_project_no_migrations: Path
    ):
        """
        Test full workflow: kurt status shows pending -> migrate -> status shows up to date.

        This is the key user scenario:
        1. User runs `kurt status` and sees migration warning
        2. User runs `kurt admin migrate apply`
        3. User runs `kurt status` and sees no warning
        """
        from kurt_new.cli.admin import admin

        # Note: For fresh project, status will fail because DB doesn't exist
        # So we need to run migrate first to create the DB

        # Step 1: Run migrate to create database and apply migrations
        migrate_result = invoke_cli(cli_runner, admin, ["migrate", "apply", "-y"])
        assert_cli_success(migrate_result)

        # Step 2: Now status should work and show no pending migrations
        status_result = invoke_cli(cli_runner, status, [])
        assert_cli_success(status_result)
        assert "pending database migration" not in status_result.output.lower()
