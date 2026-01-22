"""Tests for agent workflow CLI commands."""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from kurt.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)


class TestAgentsGroupHelp:
    """Tests for agents group help and options."""

    def test_agents_group_help(self, cli_runner: CliRunner):
        """Test agents group shows help."""
        from kurt.workflows.agents.cli import agents_group

        result = invoke_cli(cli_runner, agents_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Manage agent-based workflow definitions")

    def test_list_help(self, cli_runner: CliRunner):
        """Test list command shows help."""
        from kurt.workflows.agents.cli import agents_group

        result = invoke_cli(cli_runner, agents_group, ["list", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "List all workflow definitions")

    def test_show_help(self, cli_runner: CliRunner):
        """Test show command shows help."""
        from kurt.workflows.agents.cli import agents_group

        result = invoke_cli(cli_runner, agents_group, ["show", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Show workflow definition details")

    def test_run_help(self, cli_runner: CliRunner):
        """Test run command shows help."""
        from kurt.workflows.agents.cli import agents_group

        result = invoke_cli(cli_runner, agents_group, ["run", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Run a workflow definition")
        assert_output_contains(result, "--input")
        assert_output_contains(result, "--foreground")

    def test_validate_help(self, cli_runner: CliRunner):
        """Test validate command shows help."""
        from kurt.workflows.agents.cli import agents_group

        result = invoke_cli(cli_runner, agents_group, ["validate", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Validate workflow file")

    def test_history_help(self, cli_runner: CliRunner):
        """Test history command shows help."""
        from kurt.workflows.agents.cli import agents_group

        result = invoke_cli(cli_runner, agents_group, ["history", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Show run history")

    def test_init_help(self, cli_runner: CliRunner):
        """Test init command shows help."""
        from kurt.workflows.agents.cli import agents_group

        result = invoke_cli(cli_runner, agents_group, ["init", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Initialize the workflows directory")


class TestListCommand:
    """Tests for list command."""

    @patch("kurt.workflows.agents.registry.list_definitions")
    def test_list_empty(self, mock_list, cli_runner: CliRunner):
        """Test list command with no definitions."""
        from kurt.workflows.agents.cli import agents_group

        mock_list.return_value = []

        result = cli_runner.invoke(agents_group, ["list"])
        assert result.exit_code == 0
        assert "No workflow definitions found" in result.output

    @patch("kurt.workflows.agents.registry.list_definitions")
    def test_list_with_definitions(self, mock_list, cli_runner: CliRunner):
        """Test list command with definitions."""
        from kurt.workflows.agents.cli import agents_group
        from kurt.workflows.agents.parser import AgentConfig, GuardrailsConfig, ParsedWorkflow

        mock_list.return_value = [
            ParsedWorkflow(
                name="test-workflow",
                title="Test Workflow",
                body="Test body",
                agent=AgentConfig(model="claude-sonnet-4-20250514"),
                guardrails=GuardrailsConfig(),
                tags=["test", "demo"],
            ),
        ]

        result = cli_runner.invoke(agents_group, ["list"])
        assert result.exit_code == 0
        assert "test-workflow" in result.output
        assert "Test Workflow" in result.output

    @patch("kurt.workflows.agents.registry.list_definitions")
    def test_list_with_tag_filter(self, mock_list, cli_runner: CliRunner):
        """Test list command with tag filter."""
        from kurt.workflows.agents.cli import agents_group
        from kurt.workflows.agents.parser import AgentConfig, GuardrailsConfig, ParsedWorkflow

        mock_list.return_value = [
            ParsedWorkflow(
                name="workflow-1",
                title="Workflow 1",
                body="Body 1",
                agent=AgentConfig(model="claude-sonnet-4-20250514"),
                guardrails=GuardrailsConfig(),
                tags=["automation"],
            ),
            ParsedWorkflow(
                name="workflow-2",
                title="Workflow 2",
                body="Body 2",
                agent=AgentConfig(model="claude-sonnet-4-20250514"),
                guardrails=GuardrailsConfig(),
                tags=["manual"],
            ),
        ]

        result = cli_runner.invoke(agents_group, ["list", "--tag", "automation"])
        assert result.exit_code == 0
        assert "workflow-1" in result.output
        assert "workflow-2" not in result.output


class TestShowCommand:
    """Tests for show command."""

    @patch("kurt.workflows.agents.registry.get_definition")
    def test_show_not_found(self, mock_get, cli_runner: CliRunner):
        """Test show command when workflow not found."""
        from kurt.workflows.agents.cli import agents_group

        mock_get.return_value = None

        result = cli_runner.invoke(agents_group, ["show", "nonexistent"])
        assert result.exit_code != 0
        assert "Workflow not found" in result.output

    @patch("kurt.workflows.agents.registry.get_definition")
    def test_show_found(self, mock_get, cli_runner: CliRunner):
        """Test show command with existing workflow."""
        from kurt.workflows.agents.cli import agents_group
        from kurt.workflows.agents.parser import AgentConfig, GuardrailsConfig, ParsedWorkflow

        mock_get.return_value = ParsedWorkflow(
            name="my-workflow",
            title="My Workflow",
            description="A test workflow",
            body="Test body",
            agent=AgentConfig(
                model="claude-sonnet-4-20250514",
                max_turns=10,
                allowed_tools=["Bash", "Read"],
            ),
            guardrails=GuardrailsConfig(
                max_tokens=100000,
                max_tool_calls=50,
                max_time=300,
            ),
            tags=["test"],
        )

        result = cli_runner.invoke(agents_group, ["show", "my-workflow"])
        assert result.exit_code == 0
        assert "My Workflow" in result.output
        assert "claude-sonnet-4-20250514" in result.output
        assert "Bash" in result.output
        assert "100,000" in result.output


class TestRunCommand:
    """Tests for run command."""

    @patch("kurt.workflows.agents.executor.run_definition")
    def test_run_background(self, mock_run, cli_runner: CliRunner):
        """Test run command in background mode."""
        from kurt.workflows.agents.cli import agents_group

        mock_run.return_value = {"workflow_id": "wf-123", "status": "started"}

        result = cli_runner.invoke(agents_group, ["run", "my-workflow"])
        assert result.exit_code == 0
        assert "Workflow started" in result.output
        assert "wf-123" in result.output
        mock_run.assert_called_once_with(
            "my-workflow",
            inputs=None,
            background=True,
            trigger="manual",
        )

    @patch("kurt.workflows.agents.executor.run_definition")
    def test_run_foreground(self, mock_run, cli_runner: CliRunner):
        """Test run command in foreground mode."""
        from kurt.workflows.agents.cli import agents_group

        mock_run.return_value = {
            "workflow_id": "wf-123",
            "status": "completed",
            "turns": 3,
            "tool_calls": 5,
            "tokens_in": 1000,
            "tokens_out": 500,
            "duration_seconds": 10.5,
        }

        result = cli_runner.invoke(agents_group, ["run", "my-workflow", "--foreground"])
        assert result.exit_code == 0
        assert "Workflow completed" in result.output
        assert "Turns: 3" in result.output
        assert "Tool Calls: 5" in result.output
        mock_run.assert_called_once_with(
            "my-workflow",
            inputs=None,
            background=False,
            trigger="manual",
        )

    @patch("kurt.workflows.agents.executor.run_definition")
    def test_run_with_inputs(self, mock_run, cli_runner: CliRunner):
        """Test run command with input parameters."""
        from kurt.workflows.agents.cli import agents_group

        mock_run.return_value = {"workflow_id": "wf-123", "status": "started"}

        result = cli_runner.invoke(
            agents_group,
            ["run", "my-workflow", "--input", "topic=AI", "--input", 'tags=["a","b"]'],
        )
        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            "my-workflow",
            inputs={"topic": "AI", "tags": ["a", "b"]},
            background=True,
            trigger="manual",
        )

    @patch("kurt.workflows.agents.executor.run_from_path")
    def test_run_from_file_path(self, mock_run, cli_runner: CliRunner, tmp_path):
        """Test run command with a file path."""
        from kurt.workflows.agents.cli import agents_group

        # Create a workflow file
        workflow_file = tmp_path / "my-workflow.md"
        workflow_file.write_text(
            "---\nname: test\ntitle: Test\nagent:\n  model: claude-sonnet-4-20250514\n---\nBody"
        )

        mock_run.return_value = {"workflow_id": "wf-123", "status": "started"}

        result = cli_runner.invoke(agents_group, ["run", str(workflow_file)])
        assert result.exit_code == 0
        assert "Workflow started" in result.output
        mock_run.assert_called_once()
        # Verify the path was passed
        call_args = mock_run.call_args
        assert str(workflow_file) in str(call_args)

    @patch("kurt.workflows.agents.executor.run_from_path")
    def test_run_from_directory_path(self, mock_run, cli_runner: CliRunner, tmp_path):
        """Test run command with a directory path."""
        from kurt.workflows.agents.cli import agents_group

        # Create a workflow directory
        workflow_dir = tmp_path / "my_workflow"
        workflow_dir.mkdir()
        (workflow_dir / "workflow.md").write_text(
            "---\nname: test\ntitle: Test\nagent:\n  model: claude-sonnet-4-20250514\n---\nBody"
        )

        mock_run.return_value = {"workflow_id": "wf-123", "status": "started"}

        result = cli_runner.invoke(agents_group, ["run", str(workflow_dir)])
        assert result.exit_code == 0
        assert "Workflow started" in result.output
        mock_run.assert_called_once()

    def test_run_from_directory_no_workflow_file(self, cli_runner: CliRunner, tmp_path):
        """Test run command with a directory that has no workflow file."""
        from kurt.workflows.agents.cli import agents_group

        # Create empty directory
        workflow_dir = tmp_path / "empty_workflow"
        workflow_dir.mkdir()

        result = cli_runner.invoke(agents_group, ["run", str(workflow_dir)])
        assert result.exit_code != 0
        assert "No workflow.toml or workflow.md found" in result.output

    def test_run_from_nonexistent_path(self, cli_runner: CliRunner):
        """Test run command with a path that doesn't exist."""
        from kurt.workflows.agents.cli import agents_group

        result = cli_runner.invoke(agents_group, ["run", "./nonexistent/workflow.md"])
        assert result.exit_code != 0
        assert "Path not found" in result.output


class TestTrackToolCommand:
    """Tests for track-tool hidden command."""

    def test_track_tool_no_env_var(self, cli_runner: CliRunner):
        """Test track-tool exits silently when KURT_TOOL_LOG_FILE not set."""
        from kurt.workflows.agents.cli import agents_group

        # Without KURT_TOOL_LOG_FILE, command should exit 0
        result = cli_runner.invoke(
            agents_group,
            ["track-tool"],
            input='{"tool_name": "Bash", "tool_use_id": "123"}',
        )
        assert result.exit_code == 0

    def test_track_tool_with_env_var(self, cli_runner: CliRunner, tmp_path):
        """Test track-tool logs tool calls to file."""
        from kurt.workflows.agents.cli import agents_group

        log_file = tmp_path / "tools.jsonl"

        result = cli_runner.invoke(
            agents_group,
            ["track-tool"],
            input='{"tool_name": "Bash", "tool_use_id": "tool-123"}',
            env={"KURT_TOOL_LOG_FILE": str(log_file)},
        )
        assert result.exit_code == 0

        # Verify file was written
        assert log_file.exists()
        content = log_file.read_text()
        assert "Bash" in content
        assert "tool-123" in content

    def test_track_tool_appends(self, cli_runner: CliRunner, tmp_path):
        """Test track-tool appends to existing file."""
        from kurt.workflows.agents.cli import agents_group

        log_file = tmp_path / "tools.jsonl"
        log_file.write_text('{"tool_name": "Read", "tool_use_id": "1"}\n')

        result = cli_runner.invoke(
            agents_group,
            ["track-tool"],
            input='{"tool_name": "Write", "tool_use_id": "2"}',
            env={"KURT_TOOL_LOG_FILE": str(log_file)},
        )
        assert result.exit_code == 0

        # Verify both entries exist
        content = log_file.read_text()
        assert "Read" in content
        assert "Write" in content
        assert content.count("\n") == 2

    def test_track_tool_hidden(self, cli_runner: CliRunner):
        """Test track-tool command is hidden from help."""
        from kurt.workflows.agents.cli import agents_group

        result = cli_runner.invoke(agents_group, ["--help"])
        assert "track-tool" not in result.output


class TestInitCommand:
    """Tests for init command."""

    def test_init_creates_example(self, cli_runner: CliRunner):
        """Test init creates example workflow files (TOML and Markdown)."""
        from kurt.workflows.agents.cli import agents_group

        with cli_runner.isolated_filesystem():
            with patch("kurt.workflows.agents.registry.ensure_workflows_dir") as mock_ensure:
                from pathlib import Path

                # Create temp workflows dir
                workflows_dir = Path("workflows")
                workflows_dir.mkdir(parents=True, exist_ok=True)
                mock_ensure.return_value = workflows_dir

                result = cli_runner.invoke(agents_group, ["init"])
                assert result.exit_code == 0
                assert "Created TOML example" in result.output
                assert "Created Markdown example" in result.output

                # Verify TOML file was created (new preferred format)
                toml_file = workflows_dir / "example-workflow.toml"
                assert toml_file.exists()
                toml_content = toml_file.read_text()
                assert 'name = "example-workflow"' in toml_content
                assert "{{task}}" in toml_content

                # Verify Markdown file was created (legacy format)
                md_file = workflows_dir / "example-workflow-md.md"
                assert md_file.exists()
                md_content = md_file.read_text()
                assert "name: example-workflow-md" in md_content
                assert "{{task}}" in md_content
