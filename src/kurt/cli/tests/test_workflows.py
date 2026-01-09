"""Tests for workflows CLI commands."""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner
from sqlalchemy import text

from kurt.cli.workflows import workflows_group
from kurt.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)
from kurt.db import managed_session

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def insert_workflow(dbos_launched):
    """Factory fixture to insert workflows into the database.

    Usage:
        def test_example(insert_workflow):
            insert_workflow("wf-123", "my_workflow", "SUCCESS")
    """

    def _insert(workflow_uuid: str, name: str, status: str) -> None:
        with managed_session() as session:
            session.execute(
                text(
                    """
                    INSERT INTO workflow_status (workflow_uuid, name, status, created_at, updated_at)
                    VALUES (:uuid, :name, :status, datetime('now'), datetime('now'))
                    """
                ),
                {"uuid": workflow_uuid, "name": name, "status": status},
            )
            session.commit()

    return _insert


@pytest.fixture
def sample_workflow(insert_workflow):
    """Create a single sample workflow and return its ID.

    Returns:
        str: The workflow UUID ("sample-wf-001")
    """
    workflow_id = "sample-wf-001"
    insert_workflow(workflow_id, "sample_workflow", "SUCCESS")
    return workflow_id


@pytest.fixture
def sample_workflows(insert_workflow):
    """Create multiple sample workflows with different statuses.

    Returns:
        dict: Mapping of status to workflow_id
    """
    workflows = {
        "SUCCESS": "sample-success-wf",
        "PENDING": "sample-pending-wf",
        "ERROR": "sample-error-wf",
    }
    for status, wf_id in workflows.items():
        insert_workflow(wf_id, f"{status.lower()}_workflow", status)
    return workflows


# ============================================================================
# Unit Tests
# ============================================================================


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

    def test_status_with_workflow_id(self, cli_runner: CliRunner, dbos_launched):
        """Test status command with workflow_id argument.

        This test catches bugs where workflow_id is passed incorrectly
        to get_live_status().
        """
        result = invoke_cli(cli_runner, workflows_group, ["status", "test-workflow-123"])
        assert_cli_success(result)
        # Should show the workflow ID in output (even if empty status)
        assert_output_contains(result, "test-workflow-123")

    def test_status_json_format_not_found(self, cli_runner: CliRunner, dbos_launched):
        """Test status command with JSON output for non-existent workflow."""
        result = invoke_cli(cli_runner, workflows_group, ["status", "nonexistent-wf", "--json"])
        assert_cli_success(result)
        # Should still output something (either null or error message)
        assert "nonexistent-wf" in result.output or "not found" in result.output


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

    def test_logs_with_workflow_id(self, cli_runner: CliRunner, dbos_launched):
        """Test logs command with workflow_id argument.

        This test catches bugs where workflow_id is passed incorrectly
        to get_step_logs().
        """
        result = invoke_cli(cli_runner, workflows_group, ["logs", "test-workflow-123"])
        assert_cli_success(result)
        # No logs found is expected since workflow doesn't exist
        assert_output_contains(result, "No logs found")

    def test_logs_with_step_filter(self, cli_runner: CliRunner, dbos_launched):
        """Test logs command with --step filter."""
        result = invoke_cli(cli_runner, workflows_group, ["logs", "test-wf", "--step", "extract"])
        assert_cli_success(result)
        assert_output_contains(result, "No logs found")

    def test_logs_with_limit(self, cli_runner: CliRunner, dbos_launched):
        """Test logs command with --limit option."""
        result = invoke_cli(cli_runner, workflows_group, ["logs", "test-wf", "--limit", "10"])
        assert_cli_success(result)
        assert_output_contains(result, "No logs found")

    def test_logs_json_format(self, cli_runner: CliRunner, dbos_launched):
        """Test logs command with JSON output."""
        result = invoke_cli(cli_runner, workflows_group, ["logs", "test-wf", "--json"])
        assert_cli_success(result)
        # When no logs, the command outputs empty string or "No logs found"
        # Check that it doesn't crash when called with --json
        assert result.exit_code == 0


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

    def test_cancel_with_workflow_id(self, cli_runner: CliRunner, dbos_launched):
        """Test cancel command with workflow_id argument.

        This test catches bugs where workflow_id is passed incorrectly
        to DBOS.cancel_workflow().
        """
        # Cancel a non-existent workflow - should handle gracefully
        result = invoke_cli(cli_runner, workflows_group, ["cancel", "test-workflow-123"])
        # May succeed or show error, but should not crash
        # The important thing is that the function is called with workflow_id correctly
        assert result.exit_code == 0 or "Error" in result.output

    def test_cancel_requires_workflow_id(self, cli_runner: CliRunner):
        """Test cancel command requires workflow_id argument."""
        result = cli_runner.invoke(workflows_group, ["cancel"])
        assert result.exit_code != 0


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

    def test_stats_with_workflow_id(self, cli_runner: CliRunner, tmp_database):
        """Test stats command with workflow_id argument.

        This test catches the bug where workflow_id was passed as positional
        instead of keyword argument to tracer.stats().
        """
        result = invoke_cli(cli_runner, workflows_group, ["stats", "test-workflow-123"])
        assert_cli_success(result)
        assert_output_contains(result, "LLM Usage Statistics")
        assert_output_contains(result, "test-workflow-123")

    def test_stats_without_workflow_id(self, cli_runner: CliRunner, tmp_database):
        """Test stats command without workflow_id shows global stats."""
        result = invoke_cli(cli_runner, workflows_group, ["stats"])
        assert_cli_success(result)
        assert_output_contains(result, "LLM Usage Statistics")

    def test_stats_json_format(self, cli_runner: CliRunner, tmp_database):
        """Test stats command with JSON output."""
        result = invoke_cli(cli_runner, workflows_group, ["stats", "--json"])
        assert_cli_success(result)
        data = json.loads(result.output)
        assert "total_calls" in data
        assert "total_cost" in data


# ============================================================================
# Database Integration Tests
# ============================================================================


class TestStatusCommandDatabase:
    """Database integration tests for `workflows status` command."""

    def test_status_with_existing_workflow(self, cli_runner: CliRunner, sample_workflow):
        """Test status command with an existing workflow in database."""
        result = invoke_cli(cli_runner, workflows_group, ["status", sample_workflow])
        assert_cli_success(result)
        assert sample_workflow in result.output

    def test_status_json_with_existing_workflow(self, cli_runner: CliRunner, insert_workflow):
        """Test status command with JSON output for existing workflow."""
        insert_workflow("wf-json-status", "json_test", "PENDING")

        result = invoke_cli(cli_runner, workflows_group, ["status", "wf-json-status", "--json"])
        assert_cli_success(result)
        data = json.loads(result.output)
        assert "workflow_id" in data
        assert data["workflow_id"] == "wf-json-status"


class TestListWorkflowsDatabase:
    """Database integration tests for `workflows list` command.

    These tests use insert_workflow fixture to ensure DBOS tables exist
    and test the actual raw SQL queries against workflow_status table.
    """

    def test_list_empty_workflows(self, cli_runner: CliRunner, dbos_launched):
        """Test listing workflows when none exist."""
        result = invoke_cli(cli_runner, workflows_group, ["list"])
        assert_cli_success(result)
        assert_output_contains(result, "No workflows found")

    def test_list_workflows_with_data(self, cli_runner: CliRunner, insert_workflow):
        """Test listing workflows with data in database."""
        insert_workflow("wf-001-uuid", "test_workflow", "SUCCESS")
        insert_workflow("wf-002-uuid", "another_workflow", "PENDING")

        result = invoke_cli(cli_runner, workflows_group, ["list"])
        assert_cli_success(result)
        assert_output_contains(result, "wf-001-uuid")
        assert_output_contains(result, "wf-002-uuid")

    def test_list_workflows_filter_by_status(self, cli_runner: CliRunner, sample_workflows):
        """Test filtering workflows by status using sample_workflows fixture."""
        result = invoke_cli(cli_runner, workflows_group, ["list", "--status", "SUCCESS"])
        assert_cli_success(result)
        # IDs are truncated in table output, check for prefix
        assert sample_workflows["SUCCESS"][:12] in result.output
        assert sample_workflows["PENDING"][:12] not in result.output
        assert sample_workflows["ERROR"][:12] not in result.output

    def test_list_workflows_filter_by_id(self, cli_runner: CliRunner, insert_workflow):
        """Test filtering workflows by ID substring."""
        insert_workflow("abc-workflow-123", "first_wf", "SUCCESS")
        insert_workflow("xyz-workflow-456", "second_wf", "SUCCESS")

        result = invoke_cli(cli_runner, workflows_group, ["list", "--id", "abc"])
        assert_cli_success(result)
        assert "abc-workflow" in result.output
        assert "xyz-workflow" not in result.output

    def test_list_workflows_limit(self, cli_runner: CliRunner, insert_workflow):
        """Test limiting number of workflows returned."""
        for i in range(5):
            insert_workflow(f"wf-limit-{i}", f"workflow_{i}", "SUCCESS")

        result = invoke_cli(cli_runner, workflows_group, ["list", "--limit", "2"])
        assert_cli_success(result)
        # Should only show 2 workflows
        count = sum(1 for i in range(5) if f"wf-limit-{i}" in result.output)
        assert count == 2

    def test_list_workflows_json_format(self, cli_runner: CliRunner, sample_workflow):
        """Test JSON output format using sample_workflow fixture."""
        result = invoke_cli(cli_runner, workflows_group, ["list", "--format", "json"])
        assert_cli_success(result)

        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["workflow_id"] == sample_workflow
        assert data[0]["status"] == "SUCCESS"

    def test_list_workflows_combined_filters(self, cli_runner: CliRunner, insert_workflow):
        """Test combining status and ID filters."""
        insert_workflow("test-success-001", "wf1", "SUCCESS")
        insert_workflow("test-pending-001", "wf2", "PENDING")
        insert_workflow("other-success-002", "wf3", "SUCCESS")

        result = invoke_cli(
            cli_runner, workflows_group, ["list", "--status", "SUCCESS", "--id", "test"]
        )
        assert_cli_success(result)
        assert "test-success" in result.output
        assert "test-pending" not in result.output
        assert "other-success" not in result.output
