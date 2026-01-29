"""Tests for admin CLI commands."""

from __future__ import annotations

from click.testing import CliRunner

from kurt.admin.cli import admin
from kurt.conftest import (
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
        # Should have feedback, telemetry, sync commands
        assert_output_contains(result, "feedback")
        assert_output_contains(result, "telemetry")
        assert_output_contains(result, "sync")


class TestTelemetryGroup:
    """Tests for `admin telemetry` command group."""

    def test_telemetry_help(self, cli_runner: CliRunner):
        """Test telemetry group shows help."""
        result = invoke_cli(cli_runner, admin, ["telemetry", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Manage telemetry")

    def test_telemetry_list_commands(self, cli_runner: CliRunner):
        """Test telemetry group lists all commands."""
        result = invoke_cli(cli_runner, admin, ["telemetry", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "enable")
        assert_output_contains(result, "disable")
        assert_output_contains(result, "status")


class TestFeedbackGroup:
    """Tests for `admin feedback` command group."""

    def test_feedback_help(self, cli_runner: CliRunner):
        """Test feedback group shows help."""
        result = invoke_cli(cli_runner, admin, ["feedback", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Log feedback telemetry events")
