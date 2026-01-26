"""Tests for workflow CLI commands (run, status, cancel).

Tests use Click's CliRunner for isolated CLI testing.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kurt.workflows.toml.cli import (
    _parse_input,
    cancel_cmd,
    logs_cmd,
    run_cmd,
    status_cmd,
    workflow_group,
)
from kurt.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_workflow_toml(tmp_path: Path) -> Path:
    """Create a sample workflow TOML file."""
    workflow_content = '''
[workflow]
name = "test_workflow"
description = "A test workflow"

[inputs.url]
type = "string"
required = true

[inputs.max_pages]
type = "int"
default = 100

[steps.map]
type = "map"
config = { url = "{{url}}", max_pages = "{{max_pages}}" }

[steps.fetch]
type = "fetch"
depends_on = ["map"]
config = { concurrency = 5 }
'''
    workflow_path = tmp_path / "test_workflow.toml"
    workflow_path.write_text(workflow_content)
    return workflow_path


@pytest.fixture
def mock_dolt_db():
    """Create a mock DoltDB instance."""
    db = MagicMock()
    db.path = Path("/fake/dolt/repo")
    db.exists.return_value = True
    return db


@pytest.fixture
def mock_lifecycle():
    """Create a mock WorkflowLifecycle."""
    lifecycle = MagicMock()
    lifecycle.create_run.return_value = "test-run-123"
    lifecycle.get_run.return_value = {
        "id": "test-run-123",
        "workflow": "test_workflow",
        "status": "running",
        "started_at": "2024-01-15 10:00:00",
        "completed_at": None,
        "error": None,
    }
    lifecycle.get_step_logs.return_value = [
        {"step_id": "map", "status": "completed", "output_count": 10},
        {"step_id": "fetch", "status": "running", "output_count": None},
    ]
    return lifecycle


# =============================================================================
# Tests - Input Parsing
# =============================================================================


class TestInputParsing:
    """Tests for _parse_input helper function."""

    def test_parse_string_value(self):
        """Test parsing a string value."""
        key, value = _parse_input("url=https://example.com")
        assert key == "url"
        assert value == "https://example.com"

    def test_parse_integer_value(self):
        """Test parsing an integer value."""
        key, value = _parse_input("max_pages=100")
        assert key == "max_pages"
        assert value == 100
        assert isinstance(value, int)

    def test_parse_negative_integer(self):
        """Test parsing a negative integer."""
        key, value = _parse_input("offset=-10")
        assert key == "offset"
        assert value == -10
        assert isinstance(value, int)

    def test_parse_float_value(self):
        """Test parsing a float value."""
        key, value = _parse_input("threshold=0.75")
        assert key == "threshold"
        assert value == 0.75
        assert isinstance(value, float)

    def test_parse_boolean_true(self):
        """Test parsing a boolean true value."""
        key, value = _parse_input("enabled=true")
        assert key == "enabled"
        assert value is True
        assert isinstance(value, bool)

    def test_parse_boolean_false(self):
        """Test parsing a boolean false value."""
        key, value = _parse_input("enabled=false")
        assert key == "enabled"
        assert value is False
        assert isinstance(value, bool)

    def test_parse_boolean_uppercase(self):
        """Test parsing boolean with different case."""
        key, value = _parse_input("enabled=TRUE")
        assert value is True

        key, value = _parse_input("enabled=False")
        assert value is False

    def test_parse_value_with_equals(self):
        """Test parsing value containing equals sign."""
        key, value = _parse_input("query=name=john&age=30")
        assert key == "query"
        assert value == "name=john&age=30"

    def test_parse_empty_value(self):
        """Test parsing empty value."""
        key, value = _parse_input("empty=")
        assert key == "empty"
        assert value == ""

    def test_parse_invalid_format(self, cli_runner: CliRunner):
        """Test that invalid format raises error."""
        import click

        with pytest.raises(click.BadParameter):
            _parse_input("invalid_no_equals")


# =============================================================================
# Tests - Run Command
# =============================================================================


class TestRunCommand:
    """Tests for `run` command."""

    def test_run_help(self, cli_runner: CliRunner):
        """Test run command shows help."""
        result = invoke_cli(cli_runner, run_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Run a workflow from a TOML file")

    def test_run_shows_options(self, cli_runner: CliRunner):
        """Test run command lists options in help."""
        result = invoke_cli(cli_runner, run_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--input")
        assert_output_contains(result, "--background")
        assert_output_contains(result, "--dry-run")

    def test_run_requires_workflow_path(self, cli_runner: CliRunner):
        """Test run command requires workflow path argument."""
        result = cli_runner.invoke(run_cmd, [])
        assert result.exit_code != 0

    def test_run_dry_run(self, cli_runner: CliRunner, sample_workflow_toml: Path):
        """Test dry-run mode parses workflow without executing."""
        with patch("kurt.workflows.toml.cli._get_dolt_db"):
            result = invoke_cli(
                cli_runner,
                run_cmd,
                [str(sample_workflow_toml), "--dry-run", "--input", "url=https://example.com"],
            )

        assert_cli_success(result)
        data = json.loads(result.output)
        assert data["workflow"] == "test_workflow"
        assert data["dry_run"] is True
        assert "map" in data["steps"]
        assert "fetch" in data["steps"]

    def test_run_dry_run_shows_inputs(self, cli_runner: CliRunner, sample_workflow_toml: Path):
        """Test dry-run shows input configuration."""
        with patch("kurt.workflows.toml.cli._get_dolt_db"):
            result = invoke_cli(
                cli_runner,
                run_cmd,
                [str(sample_workflow_toml), "--dry-run", "--input", "url=https://example.com"],
            )

        assert_cli_success(result)
        data = json.loads(result.output)
        assert "inputs" in data
        assert data["inputs"]["url"]["provided"] is True
        assert data["inputs"]["url"]["value"] == "https://example.com"
        assert data["inputs"]["max_pages"]["provided"] is False
        assert data["inputs"]["max_pages"]["value"] == 100  # default

    def test_run_missing_required_input(
        self, cli_runner: CliRunner, sample_workflow_toml: Path, mock_dolt_db
    ):
        """Test run fails when required input is missing."""
        with patch("kurt.workflows.toml.cli._get_dolt_db", return_value=mock_dolt_db):
            result = cli_runner.invoke(run_cmd, [str(sample_workflow_toml)])

        assert result.exit_code != 0
        assert_output_contains(result, "Required input 'url' not provided")

    def test_run_multiple_inputs(self, cli_runner: CliRunner, sample_workflow_toml: Path):
        """Test run with multiple input values."""
        with patch("kurt.workflows.toml.cli._get_dolt_db"):
            result = invoke_cli(
                cli_runner,
                run_cmd,
                [
                    str(sample_workflow_toml),
                    "--dry-run",
                    "--input",
                    "url=https://example.com",
                    "--input",
                    "max_pages=50",
                ],
            )

        assert_cli_success(result)
        data = json.loads(result.output)
        assert data["inputs"]["url"]["value"] == "https://example.com"
        assert data["inputs"]["max_pages"]["value"] == 50

    def test_run_file_not_found(self, cli_runner: CliRunner):
        """Test run with non-existent workflow file."""
        result = cli_runner.invoke(run_cmd, ["/nonexistent/workflow.toml"])
        assert result.exit_code != 0


# =============================================================================
# Tests - Status Command
# =============================================================================


class TestStatusCommand:
    """Tests for `status` command."""

    def test_status_help(self, cli_runner: CliRunner):
        """Test status command shows help."""
        result = invoke_cli(cli_runner, status_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Show workflow status")

    def test_status_shows_options(self, cli_runner: CliRunner):
        """Test status command lists options in help."""
        result = invoke_cli(cli_runner, status_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--json")
        assert_output_contains(result, "--follow")

    def test_status_requires_run_id(self, cli_runner: CliRunner):
        """Test status command requires run_id argument."""
        result = cli_runner.invoke(status_cmd, [])
        assert result.exit_code != 0

    def test_status_json_output(
        self, cli_runner: CliRunner, mock_dolt_db, mock_lifecycle
    ):
        """Test status command with JSON output."""
        with patch("kurt.workflows.toml.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch(
                "kurt.observability.WorkflowLifecycle", return_value=mock_lifecycle
            ):
                result = invoke_cli(
                    cli_runner, status_cmd, ["test-run-123", "--json"]
                )

        assert_cli_success(result)
        data = json.loads(result.output)
        assert data["run_id"] == "test-run-123"
        assert data["status"] == "running"
        assert data["workflow"] == "test_workflow"
        assert len(data["steps"]) == 2

    def test_status_text_output(
        self, cli_runner: CliRunner, mock_dolt_db, mock_lifecycle
    ):
        """Test status command with text output."""
        with patch("kurt.workflows.toml.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch(
                "kurt.observability.WorkflowLifecycle", return_value=mock_lifecycle
            ):
                result = invoke_cli(cli_runner, status_cmd, ["test-run-123"])

        assert_cli_success(result)
        assert_output_contains(result, "test-run-123")
        assert_output_contains(result, "test_workflow")
        assert_output_contains(result, "running")
        assert_output_contains(result, "map")
        assert_output_contains(result, "fetch")

    def test_status_not_found(self, cli_runner: CliRunner, mock_dolt_db):
        """Test status command when workflow not found."""
        mock_lifecycle = MagicMock()
        mock_lifecycle.get_run.return_value = None

        with patch("kurt.workflows.toml.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch(
                "kurt.observability.WorkflowLifecycle", return_value=mock_lifecycle
            ):
                result = invoke_cli(cli_runner, status_cmd, ["nonexistent-id"])

        assert_cli_success(result)  # Returns 0 but shows error message
        assert_output_contains(result, "not found")

    def test_status_completed_workflow(self, cli_runner: CliRunner, mock_dolt_db):
        """Test status for completed workflow."""
        mock_lifecycle = MagicMock()
        mock_lifecycle.get_run.return_value = {
            "id": "completed-run",
            "workflow": "test_workflow",
            "status": "completed",
            "started_at": "2024-01-15 10:00:00",
            "completed_at": "2024-01-15 10:05:00",
            "error": None,
        }
        mock_lifecycle.get_step_logs.return_value = [
            {"step_id": "map", "status": "completed", "output_count": 100},
        ]

        with patch("kurt.workflows.toml.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch(
                "kurt.observability.WorkflowLifecycle", return_value=mock_lifecycle
            ):
                result = invoke_cli(cli_runner, status_cmd, ["completed-run"])

        assert_cli_success(result)
        assert_output_contains(result, "completed")


# =============================================================================
# Tests - Cancel Command
# =============================================================================


class TestCancelCommand:
    """Tests for `cancel` command."""

    def test_cancel_help(self, cli_runner: CliRunner):
        """Test cancel command shows help."""
        result = invoke_cli(cli_runner, cancel_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Cancel a running workflow")

    def test_cancel_shows_options(self, cli_runner: CliRunner):
        """Test cancel command lists options in help."""
        result = invoke_cli(cli_runner, cancel_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--timeout")

    def test_cancel_requires_run_id(self, cli_runner: CliRunner):
        """Test cancel command requires run_id argument."""
        result = cli_runner.invoke(cancel_cmd, [])
        assert result.exit_code != 0

    def test_cancel_not_found(self, cli_runner: CliRunner, mock_dolt_db):
        """Test cancel when workflow not found."""
        mock_lifecycle = MagicMock()
        mock_lifecycle.get_run.return_value = None

        with patch("kurt.workflows.toml.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch(
                "kurt.observability.WorkflowLifecycle", return_value=mock_lifecycle
            ):
                result = cli_runner.invoke(cancel_cmd, ["nonexistent-id"])

        assert result.exit_code != 0
        assert_output_contains(result, "not found")

    def test_cancel_already_completed(self, cli_runner: CliRunner, mock_dolt_db):
        """Test cancel when workflow already completed."""
        mock_lifecycle = MagicMock()
        mock_lifecycle.get_run.return_value = {
            "id": "completed-run",
            "workflow": "test_workflow",
            "status": "completed",
        }

        with patch("kurt.workflows.toml.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch(
                "kurt.observability.WorkflowLifecycle", return_value=mock_lifecycle
            ):
                result = invoke_cli(cli_runner, cancel_cmd, ["completed-run"])

        assert_cli_success(result)
        data = json.loads(result.output)
        assert data["success"] is False
        assert "already in terminal state" in data["error"]

    def test_cancel_running_workflow(self, cli_runner: CliRunner, mock_dolt_db):
        """Test cancel on running workflow."""
        mock_lifecycle = MagicMock()
        # First call returns running, then canceled (after the sleep loop)
        mock_lifecycle.get_run.side_effect = [
            {"id": "running-run", "workflow": "test_workflow", "status": "running"},
            {"id": "running-run", "workflow": "test_workflow", "status": "canceled"},
            {"id": "running-run", "workflow": "test_workflow", "status": "canceled"},
        ]
        # update_status should not raise
        mock_lifecycle.update_status.return_value = None

        with patch("kurt.workflows.toml.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch(
                "kurt.observability.WorkflowLifecycle", return_value=mock_lifecycle
            ):
                with patch("kurt.workflows.toml.cli.time.sleep"):  # Skip the sleep
                    result = invoke_cli(cli_runner, cancel_cmd, ["running-run"])

        assert_cli_success(result)
        # Output includes JSON followed by console message, extract JSON part
        json_output = result.output.split("\n\n")[0]  # Get first part (JSON)
        data = json.loads(json_output)
        assert data["success"] is True
        assert data["status"] == "canceled"


# =============================================================================
# Tests - Workflow Group
# =============================================================================


class TestWorkflowGroup:
    """Tests for the workflow command group."""

    def test_workflow_group_help(self, cli_runner: CliRunner):
        """Test workflow group shows help."""
        result = invoke_cli(cli_runner, workflow_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Manage workflows (both TOML and Markdown formats)")

    def test_workflow_group_lists_commands(self, cli_runner: CliRunner):
        """Test workflow group lists all commands."""
        result = invoke_cli(cli_runner, workflow_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "run")
        assert_output_contains(result, "status")
        assert_output_contains(result, "logs")
        assert_output_contains(result, "cancel")


# =============================================================================
# Tests - Logs Command
# =============================================================================


class TestLogsCommand:
    """Tests for `logs` command."""

    def test_logs_help(self, cli_runner: CliRunner):
        """Test logs command shows help."""
        result = invoke_cli(cli_runner, logs_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "View step logs for a workflow run")

    def test_logs_shows_options(self, cli_runner: CliRunner):
        """Test logs command lists options in help."""
        result = invoke_cli(cli_runner, logs_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--step")
        assert_output_contains(result, "--substep")
        assert_output_contains(result, "--status")
        assert_output_contains(result, "--json")
        assert_output_contains(result, "--tail")
        assert_output_contains(result, "--limit")

    def test_logs_requires_run_id(self, cli_runner: CliRunner):
        """Test logs command requires run_id argument."""
        result = cli_runner.invoke(logs_cmd, [])
        assert result.exit_code != 0

    def test_logs_not_found(self, cli_runner: CliRunner, mock_dolt_db):
        """Test logs command when workflow not found."""
        mock_lifecycle = MagicMock()
        mock_lifecycle.get_run.return_value = None

        with patch("kurt.workflows.toml.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch(
                "kurt.observability.WorkflowLifecycle", return_value=mock_lifecycle
            ):
                result = cli_runner.invoke(logs_cmd, ["nonexistent-id"])

        assert result.exit_code == 1
        assert_output_contains(result, "not found")

    def test_logs_not_found_json(self, cli_runner: CliRunner, mock_dolt_db):
        """Test logs command when workflow not found with JSON output."""
        mock_lifecycle = MagicMock()
        mock_lifecycle.get_run.return_value = None

        with patch("kurt.workflows.toml.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch(
                "kurt.observability.WorkflowLifecycle", return_value=mock_lifecycle
            ):
                result = cli_runner.invoke(logs_cmd, ["nonexistent-id", "--json"])

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error"] == "Workflow run not found"

    def test_logs_text_output(self, cli_runner: CliRunner, mock_dolt_db):
        """Test logs command with text output."""
        mock_lifecycle = MagicMock()
        mock_lifecycle.get_run.return_value = {
            "id": "test-run-123",
            "workflow": "test_workflow",
            "status": "running",
            "started_at": "2024-01-15 10:00:00",
        }

        mock_dolt_db.query.return_value = MagicMock(
            rows=[
                {
                    "step_id": "map",
                    "tool": "MapTool",
                    "status": "completed",
                    "started_at": "2024-01-15 10:00:00",
                    "completed_at": "2024-01-15 10:00:05",
                    "input_count": 10,
                    "output_count": 10,
                    "error_count": 0,
                },
            ]
        )

        with patch("kurt.workflows.toml.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch(
                "kurt.observability.WorkflowLifecycle", return_value=mock_lifecycle
            ):
                result = invoke_cli(cli_runner, logs_cmd, ["test-run-123"])

        assert_cli_success(result)
        assert_output_contains(result, "test_workflow")
        assert_output_contains(result, "running")
        assert_output_contains(result, "map")

    def test_logs_json_output(self, cli_runner: CliRunner, mock_dolt_db):
        """Test logs command with JSON output."""
        mock_lifecycle = MagicMock()
        mock_lifecycle.get_run.return_value = {
            "id": "test-run-123",
            "workflow": "test_workflow",
            "status": "completed",
        }

        # Mock step logs query
        step_logs_result = MagicMock(rows=[])

        # Mock step events query
        step_events_result = MagicMock(
            rows=[
                {
                    "id": 1,
                    "run_id": "test-run-123",
                    "step_id": "fetch",
                    "substep": "fetch_urls",
                    "status": "progress",
                    "created_at": "2024-01-15 10:00:02",
                    "current": 50,
                    "total": 100,
                    "message": "Fetching batch 2",
                },
            ]
        )

        mock_dolt_db.query.side_effect = [step_logs_result, step_events_result]

        with patch("kurt.workflows.toml.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch(
                "kurt.observability.WorkflowLifecycle", return_value=mock_lifecycle
            ):
                result = invoke_cli(cli_runner, logs_cmd, ["test-run-123", "--json"])

        assert_cli_success(result)
        data = json.loads(result.output)
        assert data["step"] == "fetch"
        assert data["substep"] == "fetch_urls"
        assert data["status"] == "progress"
        assert data["current"] == 50
        assert data["total"] == 100
        assert data["message"] == "Fetching batch 2"

    def test_logs_with_step_filter(self, cli_runner: CliRunner, mock_dolt_db):
        """Test logs command with step filter."""
        mock_lifecycle = MagicMock()
        mock_lifecycle.get_run.return_value = {
            "id": "test-run-123",
            "workflow": "test_workflow",
            "status": "running",
        }

        mock_dolt_db.query.return_value = MagicMock(rows=[])

        with patch("kurt.workflows.toml.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch(
                "kurt.observability.WorkflowLifecycle", return_value=mock_lifecycle
            ):
                result = invoke_cli(
                    cli_runner, logs_cmd, ["test-run-123", "--step=fetch"]
                )

        assert_cli_success(result)
        # Verify the step filter was passed in queries
        calls = mock_dolt_db.query.call_args_list
        # The step_logs query should include step_id filter
        assert any("step_id = ?" in str(call) for call in calls)

    def test_logs_with_status_filter(self, cli_runner: CliRunner, mock_dolt_db):
        """Test logs command with status filter."""
        mock_lifecycle = MagicMock()
        mock_lifecycle.get_run.return_value = {
            "id": "test-run-123",
            "workflow": "test_workflow",
            "status": "running",
        }

        mock_dolt_db.query.return_value = MagicMock(rows=[])

        with patch("kurt.workflows.toml.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch(
                "kurt.observability.WorkflowLifecycle", return_value=mock_lifecycle
            ):
                result = invoke_cli(
                    cli_runner, logs_cmd, ["test-run-123", "--status=failed"]
                )

        assert_cli_success(result)
        # Verify status filter in step_events query
        calls = mock_dolt_db.query.call_args_list
        # At least one query should include status filter
        assert any("status = ?" in str(call) for call in calls)

    def test_logs_with_limit(self, cli_runner: CliRunner, mock_dolt_db):
        """Test logs command with custom limit."""
        mock_lifecycle = MagicMock()
        mock_lifecycle.get_run.return_value = {
            "id": "test-run-123",
            "workflow": "test_workflow",
            "status": "running",
        }

        mock_dolt_db.query.return_value = MagicMock(rows=[])

        with patch("kurt.workflows.toml.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch(
                "kurt.observability.WorkflowLifecycle", return_value=mock_lifecycle
            ):
                result = invoke_cli(
                    cli_runner, logs_cmd, ["test-run-123", "--limit=50"]
                )

        assert_cli_success(result)
        # Verify limit parameter was used
        calls = mock_dolt_db.query.call_args_list
        # The step_events query should use the limit
        assert any("LIMIT" in str(call) for call in calls)

    def test_logs_tail_terminates_on_completion(
        self, cli_runner: CliRunner, mock_dolt_db
    ):
        """Test logs --tail terminates when workflow completes."""
        mock_lifecycle = MagicMock()
        mock_lifecycle.get_run.return_value = {
            "id": "test-run-123",
            "workflow": "test_workflow",
            "status": "running",
        }

        # First call returns empty, second returns terminal status
        mock_dolt_db.query.return_value = MagicMock(rows=[])
        mock_dolt_db.query_one.side_effect = [
            {"status": "completed"},  # First check - terminal
        ]

        with patch("kurt.workflows.toml.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch(
                "kurt.observability.WorkflowLifecycle", return_value=mock_lifecycle
            ):
                with patch("kurt.workflows.toml.cli.time.sleep"):  # Skip sleep
                    result = invoke_cli(
                        cli_runner, logs_cmd, ["test-run-123", "--tail"]
                    )

        assert_cli_success(result)
        assert_output_contains(result, "completed")


# =============================================================================
# Integration Tests (require DoltDB setup)
# =============================================================================


class TestWorkflowIntegration:
    """Integration tests for workflow CLI commands.

    These tests require actual DoltDB setup and may be slower.
    """

    @pytest.mark.skip(reason="Requires Dolt installation and initialized database")
    def test_full_workflow_execution(
        self, cli_runner: CliRunner, sample_workflow_toml: Path, tmp_path: Path
    ):
        """Test full workflow execution cycle."""
        # This would test:
        # 1. kurt run workflow.toml --input url=... --background
        # 2. kurt status <run_id> --follow
        # 3. Verify completion
        pass
