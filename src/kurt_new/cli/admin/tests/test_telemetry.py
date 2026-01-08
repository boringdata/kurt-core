"""Tests for telemetry CLI command."""

from __future__ import annotations

from click.testing import CliRunner

from kurt_new.cli.admin import admin
from kurt_new.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)


class TestTelemetryGroup:
    """Tests for `admin telemetry` command group."""

    def test_telemetry_help(self, cli_runner: CliRunner):
        """Test telemetry group shows help."""
        result = invoke_cli(cli_runner, admin, ["telemetry", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Manage telemetry and anonymous usage analytics")

    def test_telemetry_list_commands(self, cli_runner: CliRunner):
        """Test telemetry group lists all commands."""
        result = invoke_cli(cli_runner, admin, ["telemetry", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "enable")
        assert_output_contains(result, "disable")
        assert_output_contains(result, "status")


class TestEnableCommand:
    """Tests for `admin telemetry enable` command."""

    def test_enable_help(self, cli_runner: CliRunner):
        """Test enable command shows help."""
        result = invoke_cli(cli_runner, admin, ["telemetry", "enable", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Enable anonymous telemetry collection")


class TestDisableCommand:
    """Tests for `admin telemetry disable` command."""

    def test_disable_help(self, cli_runner: CliRunner):
        """Test disable command shows help."""
        result = invoke_cli(cli_runner, admin, ["telemetry", "disable", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Disable telemetry collection")


class TestStatusCommand:
    """Tests for `admin telemetry status` command."""

    def test_status_help(self, cli_runner: CliRunner):
        """Test status command shows help."""
        result = invoke_cli(cli_runner, admin, ["telemetry", "status", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Show current telemetry status")


class TestE2EWithProject:
    """E2E tests using tmp_project fixture."""

    def test_telemetry_status_shows_info(self, cli_runner: CliRunner, tmp_project):
        """Test telemetry status shows telemetry info."""
        result = invoke_cli(cli_runner, admin, ["telemetry", "status"])
        assert_cli_success(result)
        # Should show enabled/disabled status
        assert "Telemetry" in result.output or "telemetry" in result.output.lower()
