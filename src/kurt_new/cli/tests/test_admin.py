"""Tests for admin CLI commands."""

from __future__ import annotations

from click.testing import CliRunner

from kurt_new.cli.admin import admin
from kurt_new.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)


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
