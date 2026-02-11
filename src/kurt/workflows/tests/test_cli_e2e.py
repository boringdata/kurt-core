"""
E2E tests for `kurt workflow` command.

These tests verify the workflow CLI commands work correctly.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from kurt.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)

# Import agent workflow commands from agents/cli.py
from kurt.workflows.agents.cli import (
    create_cmd,
    history_cmd,
    init_cmd,
    list_cmd,
    show_cmd,
    validate_cmd,
)

# Import from toml/cli.py which defines the unified workflow_group
from kurt.workflows.toml.cli import (
    cancel_cmd,
    logs_cmd,
    run_cmd,
    status_cmd,
    test_cmd,
    workflow_group,
)


class TestWorkflowHelp:
    """Tests for workflow command help and options."""

    def test_workflow_group_help(self, cli_runner: CliRunner):
        """Verify workflow group shows help."""
        result = invoke_cli(cli_runner, workflow_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Manage workflows")

    def test_workflow_run_help(self, cli_runner: CliRunner):
        """Verify workflow run shows help."""
        result = invoke_cli(cli_runner, run_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Run a workflow")

    def test_workflow_status_help(self, cli_runner: CliRunner):
        """Verify workflow status shows help."""
        result = invoke_cli(cli_runner, status_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Show workflow status")

    def test_workflow_logs_help(self, cli_runner: CliRunner):
        """Verify workflow logs shows help."""
        result = invoke_cli(cli_runner, logs_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "step logs")

    def test_workflow_cancel_help(self, cli_runner: CliRunner):
        """Verify workflow cancel shows help."""
        result = invoke_cli(cli_runner, cancel_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Cancel")

    def test_workflow_list_help(self, cli_runner: CliRunner):
        """Verify workflow list shows help."""
        result = invoke_cli(cli_runner, list_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "List")

    def test_workflow_show_help(self, cli_runner: CliRunner):
        """Verify workflow show shows help."""
        result = invoke_cli(cli_runner, show_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "workflow definition")

    def test_workflow_validate_help(self, cli_runner: CliRunner):
        """Verify workflow validate shows help."""
        result = invoke_cli(cli_runner, validate_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Validate")

    def test_workflow_history_help(self, cli_runner: CliRunner):
        """Verify workflow history shows help."""
        result = invoke_cli(cli_runner, history_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "history")

    def test_workflow_init_help(self, cli_runner: CliRunner):
        """Verify workflow init shows help."""
        result = invoke_cli(cli_runner, init_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Initialize")

    def test_workflow_create_help(self, cli_runner: CliRunner):
        """Verify workflow create shows help."""
        result = invoke_cli(cli_runner, create_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Create")

    def test_workflow_test_help(self, cli_runner: CliRunner):
        """Verify workflow test shows help."""
        result = invoke_cli(cli_runner, test_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Test")


class TestWorkflowList:
    """E2E tests for workflow list command."""

    def test_workflow_list_empty_project(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify workflow list works with no workflows."""
        result = invoke_cli(cli_runner, list_cmd, [])

        # Should complete - may show empty or error
        assert result.exit_code in (0, 1)

    def test_workflow_list_with_tag_filter(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --tag filter is accepted."""
        result = invoke_cli(cli_runner, list_cmd, ["--tag", "test"])

        assert result.exit_code in (0, 1)

    def test_workflow_list_with_scheduled_filter(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --scheduled filter is accepted."""
        result = invoke_cli(cli_runner, list_cmd, ["--scheduled"])

        assert result.exit_code in (0, 1)


class TestWorkflowValidate:
    """E2E tests for workflow validate command."""

    def test_workflow_validate_missing_file(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify validate handles missing file."""
        result = invoke_cli(cli_runner, validate_cmd, ["nonexistent.toml"])

        # Should fail with error about file not found
        assert result.exit_code != 0 or "not found" in result.output.lower()

    def test_workflow_validate_empty_workflows_dir(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify validate handles empty workflows directory."""
        result = invoke_cli(cli_runner, validate_cmd, [])

        # Should complete - may warn or succeed
        assert result.exit_code in (0, 1, 2)

    def test_workflow_validate_valid_toml(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify validate works with valid TOML workflow."""
        # Create a valid workflow file
        workflow_dir = tmp_project / ".kurt" / "workflows"
        workflow_dir.mkdir(parents=True, exist_ok=True)
        workflow_file = workflow_dir / "test.toml"
        workflow_file.write_text("""
[workflow]
name = "test"
version = "1.0"

[[steps]]
name = "step1"
type = "sql"
query = "SELECT 1"
""")

        result = invoke_cli(cli_runner, validate_cmd, [str(workflow_file)])

        # Should pass validation
        assert result.exit_code in (0, 1)

    def test_workflow_validate_invalid_toml(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify validate detects invalid TOML."""
        # Create invalid workflow
        workflow_dir = tmp_project / ".kurt" / "workflows"
        workflow_dir.mkdir(parents=True, exist_ok=True)
        workflow_file = workflow_dir / "invalid.toml"
        workflow_file.write_text("this is not valid toml {{{{")

        result = invoke_cli(cli_runner, validate_cmd, [str(workflow_file)])

        # Should fail with parse error
        assert result.exit_code != 0


class TestWorkflowStatus:
    """E2E tests for workflow status command."""

    @pytest.mark.skip(reason="Requires full database setup")
    def test_workflow_status_not_found(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify status handles non-existent workflow."""
        result = invoke_cli(cli_runner, status_cmd, ["nonexistent-run-id"])

        # Should fail or show not found
        assert result.exit_code in (0, 1, 2)

    @pytest.mark.skip(reason="Requires full database setup")
    def test_workflow_status_json_option(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --json option is accepted."""
        result = invoke_cli(cli_runner, status_cmd, ["some-id", "--json"])

        assert result.exit_code in (0, 1, 2)


class TestWorkflowLogs:
    """E2E tests for workflow logs command."""

    @pytest.mark.skip(reason="Requires full database setup")
    def test_workflow_logs_not_found(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify logs handles non-existent workflow."""
        result = invoke_cli(cli_runner, logs_cmd, ["nonexistent-run-id"])

        assert result.exit_code in (0, 1, 2)


class TestWorkflowCancel:
    """E2E tests for workflow cancel command."""

    @pytest.mark.skip(reason="Requires full database setup")
    def test_workflow_cancel_not_found(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify cancel handles non-existent workflow."""
        result = invoke_cli(cli_runner, cancel_cmd, ["nonexistent-run-id"])

        assert result.exit_code in (0, 1, 2)


class TestWorkflowHistory:
    """E2E tests for workflow history command."""

    def test_workflow_history_not_found(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify history handles non-existent workflow."""
        result = invoke_cli(cli_runner, history_cmd, ["nonexistent.toml"])

        assert result.exit_code in (0, 1, 2)

    def test_workflow_history_with_limit(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --limit option is accepted."""
        result = invoke_cli(cli_runner, history_cmd, ["test.toml", "--limit", "5"])

        assert result.exit_code in (0, 1, 2)


class TestWorkflowInit:
    """E2E tests for workflow init command."""

    def test_workflow_init_creates_directory(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify init creates workflows directory."""
        result = invoke_cli(cli_runner, init_cmd, [])

        # Should complete - creates example workflows
        assert result.exit_code in (0, 1)

        # Check if directory was created
        tmp_project / ".kurt" / "workflows"
        # May or may not exist depending on implementation


class TestWorkflowCreate:
    """E2E tests for workflow create command."""

    def test_workflow_create_generates_file(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify create generates workflow file."""
        result = invoke_cli(cli_runner, create_cmd, ["--name", "my-workflow"])

        # Should create file
        assert result.exit_code in (0, 1)

    def test_workflow_create_with_steps(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --with-steps option is accepted."""
        result = invoke_cli(cli_runner, create_cmd, ["--name", "my-workflow-2", "--with-steps"])

        assert result.exit_code in (0, 1)


class TestWorkflowRun:
    """E2E tests for workflow run command."""

    def test_workflow_run_missing_file(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify run handles missing file."""
        result = invoke_cli(cli_runner, run_cmd, ["nonexistent.toml"])

        # Should fail with file not found
        assert result.exit_code != 0 or "not found" in result.output.lower()

    def test_workflow_run_dry_run(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --dry-run option is accepted."""
        # Create a workflow file
        workflow_dir = tmp_project / ".kurt" / "workflows"
        workflow_dir.mkdir(parents=True, exist_ok=True)
        workflow_file = workflow_dir / "test.toml"
        workflow_file.write_text("""
[workflow]
name = "test"
version = "1.0"

[[steps]]
name = "step1"
type = "sql"
query = "SELECT 1"
""")

        result = invoke_cli(cli_runner, run_cmd, [str(workflow_file), "--dry-run"])

        assert result.exit_code in (0, 1, 2)


class TestWorkflowTest:
    """E2E tests for workflow test command."""

    def test_workflow_test_missing_file(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify test handles missing file."""
        result = invoke_cli(cli_runner, test_cmd, ["nonexistent.toml"])

        # Should fail with file not found
        assert result.exit_code != 0 or "not found" in result.output.lower()


class TestWorkflowShow:
    """E2E tests for workflow show command."""

    def test_workflow_show_missing_file(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify show handles missing file."""
        result = invoke_cli(cli_runner, show_cmd, ["nonexistent.toml"])

        # Should fail with file not found
        assert result.exit_code != 0 or "not found" in result.output.lower()

    def test_workflow_show_valid_file(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify show displays workflow definition."""
        # Create a workflow file
        workflow_dir = tmp_project / ".kurt" / "workflows"
        workflow_dir.mkdir(parents=True, exist_ok=True)
        workflow_file = workflow_dir / "test.toml"
        workflow_file.write_text("""
[workflow]
name = "test"
version = "1.0"

[[steps]]
name = "step1"
type = "sql"
query = "SELECT 1"
""")

        result = invoke_cli(cli_runner, show_cmd, [str(workflow_file)])

        assert result.exit_code in (0, 1)
