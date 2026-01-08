"""Tests for status CLI command."""

from __future__ import annotations

from click.testing import CliRunner

from kurt_new.cli.status import status
from kurt_new.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)


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
