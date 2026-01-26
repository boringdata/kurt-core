"""Tests for update CLI command."""

from __future__ import annotations

from click.testing import CliRunner

from kurt.cli.update import update
from kurt.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)


class TestUpdateCommand:
    """Tests for `kurt update` command."""

    def test_update_help(self, cli_runner: CliRunner):
        """Test update command shows help."""
        result = invoke_cli(cli_runner, update, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Update agent instructions")

    def test_update_shows_options(self, cli_runner: CliRunner):
        """Test update command lists options in help."""
        result = invoke_cli(cli_runner, update, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--backup")
        assert_output_contains(result, "--no-backup")

    def test_update_no_agents_file(self, cli_runner: CliRunner, cli_runner_isolated):
        """Test update shows message when package or workspace agents not found."""
        result = invoke_cli(cli_runner, update, [])
        # Should succeed but show warning about missing files
        assert_cli_success(result)
        # Either package or workspace agents file not found
        assert (
            "Package AGENTS.md not found" in result.output
            or "No .agents/AGENTS.md found" in result.output
        )
