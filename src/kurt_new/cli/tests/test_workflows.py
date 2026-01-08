"""Tests for workflows CLI commands."""

from __future__ import annotations

from click.testing import CliRunner

from kurt_new.cli.workflows import workflows_group
from kurt_new.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)


class TestWorkflowsGroup:
    """Tests for the workflows command group."""

    def test_workflows_group_help(self, cli_runner: CliRunner):
        """Test workflows group shows help."""
        result = invoke_cli(cli_runner, workflows_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Manage background workflows")

    def test_workflows_list_commands(self, cli_runner: CliRunner):
        """Test workflows group lists all commands."""
        result = invoke_cli(cli_runner, workflows_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "list")
        assert_output_contains(result, "status")
        assert_output_contains(result, "logs")
        assert_output_contains(result, "follow")
        assert_output_contains(result, "cancel")
        assert_output_contains(result, "stats")


class TestListCommand:
    """Tests for `workflows list` command."""

    def test_list_help(self, cli_runner: CliRunner):
        """Test list command shows help."""
        result = invoke_cli(cli_runner, workflows_group, ["list", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "List background workflows")

    def test_list_shows_options(self, cli_runner: CliRunner):
        """Test list command lists options in help."""
        result = invoke_cli(cli_runner, workflows_group, ["list", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--status")
        assert_output_contains(result, "--limit")
        assert_output_contains(result, "--id")
        assert_output_contains(result, "--format")


class TestStatusCommand:
    """Tests for `workflows status` command."""

    def test_status_help(self, cli_runner: CliRunner):
        """Test status command shows help."""
        result = invoke_cli(cli_runner, workflows_group, ["status", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Show detailed workflow status")

    def test_status_requires_workflow_id(self, cli_runner: CliRunner):
        """Test status command requires workflow_id argument."""
        result = cli_runner.invoke(workflows_group, ["status"])
        assert result.exit_code != 0


class TestLogsCommand:
    """Tests for `workflows logs` command."""

    def test_logs_help(self, cli_runner: CliRunner):
        """Test logs command shows help."""
        result = invoke_cli(cli_runner, workflows_group, ["logs", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Show workflow logs")

    def test_logs_shows_options(self, cli_runner: CliRunner):
        """Test logs command lists options in help."""
        result = invoke_cli(cli_runner, workflows_group, ["logs", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--step")
        assert_output_contains(result, "--limit")
        assert_output_contains(result, "--json")


class TestFollowCommand:
    """Tests for `workflows follow` command."""

    def test_follow_help(self, cli_runner: CliRunner):
        """Test follow command shows help."""
        result = invoke_cli(cli_runner, workflows_group, ["follow", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Attach to a running workflow")

    def test_follow_shows_wait_option(self, cli_runner: CliRunner):
        """Test follow command has --wait option."""
        result = invoke_cli(cli_runner, workflows_group, ["follow", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--wait")


class TestCancelCommand:
    """Tests for `workflows cancel` command."""

    def test_cancel_help(self, cli_runner: CliRunner):
        """Test cancel command shows help."""
        result = invoke_cli(cli_runner, workflows_group, ["cancel", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Cancel a workflow")


class TestStatsCommand:
    """Tests for `workflows stats` command."""

    def test_stats_help(self, cli_runner: CliRunner):
        """Test stats command shows help."""
        result = invoke_cli(cli_runner, workflows_group, ["stats", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Show LLM usage statistics")

    def test_stats_shows_options(self, cli_runner: CliRunner):
        """Test stats command lists options in help."""
        result = invoke_cli(cli_runner, workflows_group, ["stats", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--json")
