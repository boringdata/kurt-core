"""Tests for agent workflow executor."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest


class TestToolTrackingHelpers:
    """Tests for tool tracking helper functions."""

    def test_create_tool_tracking_settings(self, tmp_path):
        """Test _create_tool_tracking_settings creates temp files."""
        from kurt.workflows.agents.executor import _create_tool_tracking_settings

        settings_path, tool_log_path = _create_tool_tracking_settings()

        try:
            # Verify settings file exists and has correct structure
            assert os.path.exists(settings_path)
            with open(settings_path) as f:
                settings = json.load(f)
            assert "hooks" in settings
            assert "PostToolUse" in settings["hooks"]
            assert settings["hooks"]["PostToolUse"][0]["matcher"] == "*"
            assert (
                "kurt agents track-tool"
                in settings["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
            )

            # Verify tool log file exists
            assert os.path.exists(tool_log_path)
        finally:
            # Cleanup
            try:
                os.unlink(settings_path)
            except Exception:
                pass
            try:
                os.unlink(tool_log_path)
            except Exception:
                pass

    def test_cleanup_tool_tracking_counts_lines(self, tmp_path):
        """Test _cleanup_tool_tracking counts tool calls correctly."""
        from kurt.workflows.agents.executor import _cleanup_tool_tracking

        # Create temp files
        settings_path = tmp_path / "settings.json"
        tool_log_path = tmp_path / "tools.jsonl"

        settings_path.write_text("{}")
        tool_log_path.write_text(
            '{"tool_name": "Bash", "tool_use_id": "1"}\n'
            '{"tool_name": "Read", "tool_use_id": "2"}\n'
            '{"tool_name": "Write", "tool_use_id": "3"}\n'
        )

        count = _cleanup_tool_tracking(str(settings_path), str(tool_log_path))

        assert count == 3
        # Verify files were deleted
        assert not settings_path.exists()
        assert not tool_log_path.exists()

    def test_cleanup_tool_tracking_empty_file(self, tmp_path):
        """Test _cleanup_tool_tracking handles empty log file."""
        from kurt.workflows.agents.executor import _cleanup_tool_tracking

        settings_path = tmp_path / "settings.json"
        tool_log_path = tmp_path / "tools.jsonl"

        settings_path.write_text("{}")
        tool_log_path.write_text("")

        count = _cleanup_tool_tracking(str(settings_path), str(tool_log_path))

        assert count == 0

    def test_cleanup_tool_tracking_missing_file(self, tmp_path):
        """Test _cleanup_tool_tracking handles missing files gracefully."""
        from kurt.workflows.agents.executor import _cleanup_tool_tracking

        settings_path = tmp_path / "nonexistent_settings.json"
        tool_log_path = tmp_path / "nonexistent_tools.jsonl"

        # Should not raise, should return 0
        count = _cleanup_tool_tracking(str(settings_path), str(tool_log_path))
        assert count == 0


class TestResolveTemplate:
    """Tests for template resolution."""

    def test_resolve_template_basic(self):
        """Test basic template variable resolution."""
        from kurt.workflows.agents.executor import resolve_template

        body = "Hello {{name}}, today is {{date}}"
        inputs = {"name": "World"}

        result = resolve_template(body, inputs)

        assert "World" in result
        # date should be resolved to current date
        import datetime

        assert datetime.datetime.now().strftime("%Y-%m-%d") in result

    def test_resolve_template_list_input(self):
        """Test template resolution with list input."""
        from kurt.workflows.agents.executor import resolve_template

        body = "Topics: {{topics}}"
        inputs = {"topics": ["AI", "ML", "NLP"]}

        result = resolve_template(body, inputs)

        assert "AI, ML, NLP" in result

    def test_resolve_template_unset_variable(self):
        """Test template resolution with unset variables."""
        from kurt.workflows.agents.executor import resolve_template

        body = "Hello {{name}}, your id is {{id}}"
        inputs = {"name": "Test"}

        result = resolve_template(body, inputs)

        assert "Test" in result
        assert "{{id}}" in result  # Unset variables remain unchanged

    def test_resolve_template_builtin_vars(self):
        """Test builtin template variables."""
        from kurt.workflows.agents.executor import resolve_template

        body = "Date: {{date}}, Time: {{time}}, Weekday: {{weekday}}"
        inputs = {}

        result = resolve_template(body, inputs)

        # Builtins should be resolved
        assert "{{date}}" not in result
        assert "{{time}}" not in result
        assert "{{weekday}}" not in result


class TestAgentExecutionStep:
    """Tests for agent_execution_step function."""

    @patch("shutil.which")
    def test_claude_not_found(self, mock_which):
        """Test error when claude CLI not installed."""
        from kurt.workflows.agents.executor import agent_execution_step

        mock_which.return_value = None

        with pytest.raises(RuntimeError, match="Claude Code CLI not found"):
            agent_execution_step(
                prompt="Test",
                model="claude-sonnet-4-20250514",
                max_turns=5,
                allowed_tools=["Bash"],
            )

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_successful_execution(self, mock_run, mock_which, tmp_path):
        """Test successful agent execution."""
        from kurt.workflows.agents.executor import agent_execution_step

        mock_which.return_value = "/usr/bin/claude"

        # Mock subprocess result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {
                "num_turns": 3,
                "total_cost_usd": 0.05,
                "usage": {
                    "input_tokens": 1000,
                    "output_tokens": 500,
                    "cache_read_input_tokens": 100,
                },
                "result": "Task completed successfully",
            }
        )
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Mock tool tracking
        with patch(
            "kurt.workflows.agents.executor._create_tool_tracking_settings"
        ) as mock_create:
            settings_file = tmp_path / "settings.json"
            tool_log_file = tmp_path / "tools.jsonl"
            settings_file.write_text("{}")
            tool_log_file.write_text('{"tool_name": "Bash"}\n' '{"tool_name": "Read"}\n')
            mock_create.return_value = (str(settings_file), str(tool_log_file))

            with patch("kurt.workflows.agents.executor._get_project_root") as mock_root:
                mock_root.return_value = str(tmp_path)

                result = agent_execution_step(
                    prompt="Test prompt",
                    model="claude-sonnet-4-20250514",
                    max_turns=5,
                    allowed_tools=["Bash", "Read"],
                    max_time=300,
                    run_id="test-123",  # Pass run_id for parent workflow tracking
                )

        assert result["turns"] == 3
        assert result["tool_calls"] == 2  # From our mock tool log
        assert result["tokens_in"] == 1100  # 1000 + 100 cache_read
        assert result["tokens_out"] == 500
        assert result["cost_usd"] == 0.05
        assert result["stop_reason"] == "completed"

        # Verify subprocess was called with correct args
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "--settings" in cmd
        assert "--print" in cmd
        assert "--output-format" in cmd or "json" in cmd

        # Verify env vars were set
        env = call_args[1]["env"]
        assert "KURT_TOOL_LOG_FILE" in env
        assert "KURT_PARENT_WORKFLOW_ID" in env
        assert env["KURT_PARENT_WORKFLOW_ID"] == "test-123"

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_timeout_handling(self, mock_run, mock_which, tmp_path):
        """Test timeout handling during execution."""
        import subprocess

        from kurt.workflows.agents.executor import agent_execution_step

        mock_which.return_value = "/usr/bin/claude"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=10)

        with patch(
            "kurt.workflows.agents.executor._create_tool_tracking_settings"
        ) as mock_create:
            settings_file = tmp_path / "settings.json"
            tool_log_file = tmp_path / "tools.jsonl"
            settings_file.write_text("{}")
            tool_log_file.write_text("")
            mock_create.return_value = (str(settings_file), str(tool_log_file))

            with patch("kurt.workflows.agents.executor._get_project_root") as mock_root:
                mock_root.return_value = str(tmp_path)

                result = agent_execution_step(
                    prompt="Test",
                    model="claude-sonnet-4-20250514",
                    max_turns=5,
                    allowed_tools=["Bash"],
                    max_time=10,
                )

        assert "max_time" in result["stop_reason"]
        assert result["turns"] == 0
        assert result["tokens_in"] == 0

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_error_cleanup(self, mock_run, mock_which, tmp_path):
        """Test that cleanup happens even on error."""
        from kurt.workflows.agents.executor import agent_execution_step

        mock_which.return_value = "/usr/bin/claude"
        mock_run.side_effect = Exception("Test error")

        with patch(
            "kurt.workflows.agents.executor._create_tool_tracking_settings"
        ) as mock_create:
            settings_file = tmp_path / "settings.json"
            tool_log_file = tmp_path / "tools.jsonl"
            settings_file.write_text("{}")
            tool_log_file.write_text("")
            mock_create.return_value = (str(settings_file), str(tool_log_file))

            with patch("kurt.workflows.agents.executor._cleanup_tool_tracking") as mock_cleanup:
                mock_cleanup.return_value = 0

                with patch("kurt.workflows.agents.executor._get_project_root") as mock_root:
                    mock_root.return_value = str(tmp_path)

                    with pytest.raises(Exception, match="Test error"):
                        agent_execution_step(
                            prompt="Test",
                            model="claude-sonnet-4-20250514",
                            max_turns=5,
                            allowed_tools=["Bash"],
                        )

                # Verify cleanup was called
                mock_cleanup.assert_called_once()


class TestRunDefinition:
    """Tests for run_definition function."""

    @patch("kurt.workflows.agents.registry.get_definition")
    def test_definition_not_found(self, mock_get):
        """Test error when workflow definition not found."""
        from kurt.workflows.agents.executor import run_definition

        mock_get.return_value = None

        with pytest.raises(ValueError, match="Workflow definition not found"):
            run_definition("nonexistent")

    @patch("kurt.workflows.agents.registry.get_definition")
    @patch("kurt.workflows.agents.executor._spawn_background_agent_run")
    def test_run_background(self, mock_spawn, mock_get_def):
        """Test running definition in background."""
        from kurt.workflows.agents.executor import run_definition
        from kurt.workflows.agents.parser import AgentConfig, GuardrailsConfig, ParsedWorkflow

        mock_get_def.return_value = ParsedWorkflow(
            name="test-workflow",
            title="Test",
            body="Test body",
            agent=AgentConfig(model="claude-sonnet-4-20250514"),
            guardrails=GuardrailsConfig(),
            inputs={"default_key": "default_value"},
        )
        mock_spawn.return_value = {"workflow_id": "wf-123", "status": "started"}

        result = run_definition("test-workflow", inputs={"custom_key": "custom_value"})

        assert result["workflow_id"] == "wf-123"
        assert result["status"] == "started"

        # Verify inputs were merged
        mock_spawn.assert_called_once()
        call_kwargs = mock_spawn.call_args[1]
        inputs_arg = call_kwargs["inputs"]
        assert inputs_arg["default_key"] == "default_value"
        assert inputs_arg["custom_key"] == "custom_value"

    @patch("kurt.workflows.agents.registry.get_definition")
    @patch("kurt.workflows.agents.executor.execute_agent_workflow")
    def test_run_foreground(self, mock_execute, mock_get_def):
        """Test running definition in foreground."""
        from kurt.workflows.agents.executor import run_definition
        from kurt.workflows.agents.parser import AgentConfig, GuardrailsConfig, ParsedWorkflow

        mock_get_def.return_value = ParsedWorkflow(
            name="test-workflow",
            title="Test",
            body="Test body",
            agent=AgentConfig(model="claude-sonnet-4-20250514"),
            guardrails=GuardrailsConfig(),
        )
        mock_execute.return_value = {
            "workflow_id": "wf-123",
            "status": "completed",
            "turns": 2,
        }

        result = run_definition("test-workflow", background=False)

        assert result["status"] == "completed"
        mock_execute.assert_called_once()


class TestToolExtraction:
    """Tests for tool extraction from tools.py."""

    def test_extract_tools_documentation(self, tmp_path):
        """Test extracting tool documentation from tools.py."""
        from kurt.workflows.agents.executor import _extract_tools_documentation

        workflows_dir = tmp_path / "workflows"
        workflow_dir = workflows_dir / "my_workflow"
        workflow_dir.mkdir(parents=True)

        # Create workflow.md
        (workflow_dir / "workflow.md").write_text(
            "---\nname: my-workflow\ntitle: My\nagent:\n  model: claude-sonnet-4-20250514\n---\nBody"
        )

        # Create tools.py with DBOS decorators
        tools_content = '''
"""Tools for my workflow."""

from dbos import DBOS

@DBOS.workflow()
def analyze_data(url: str) -> dict:
    """Analyze data from URL and return insights."""
    return {"result": "analyzed"}

@DBOS.step()
def process_item(item: str, count: int = 1) -> list:
    """Process a single item."""
    return [item] * count

def helper_function():
    """This is not a tool."""
    pass
'''
        (workflow_dir / "tools.py").write_text(tools_content)

        with patch("kurt.workflows.agents.executor.get_workflow_dir") as mock_dir:
            mock_dir.return_value = workflow_dir

            result = _extract_tools_documentation("my-workflow")

        assert "## Available Tools" in result
        assert "`analyze_data(url: str)`" in result
        assert "Analyze data from URL" in result
        # Note: default values are not extracted by AST, just type annotations
        assert "`process_item(item: str, count: int)`" in result
        assert "Process a single item" in result
        # helper_function should not be included
        assert "helper_function" not in result

    def test_extract_tools_no_tools_file(self, tmp_path):
        """Test extraction when no tools.py exists."""
        from kurt.workflows.agents.executor import _extract_tools_documentation

        with patch("kurt.workflows.agents.executor.get_workflow_dir") as mock_dir:
            mock_dir.return_value = tmp_path  # No tools.py here

            result = _extract_tools_documentation("my-workflow")

        assert result == ""

    def test_extract_tools_no_workflow_dir(self):
        """Test extraction when workflow dir doesn't exist."""
        from kurt.workflows.agents.executor import _extract_tools_documentation

        with patch("kurt.workflows.agents.executor.get_workflow_dir") as mock_dir:
            mock_dir.return_value = None

            result = _extract_tools_documentation("nonexistent")

        assert result == ""

    def test_get_tools_import_path(self, tmp_path):
        """Test getting import path for tools."""
        from kurt.workflows.agents.executor import _get_tools_import_path

        workflows_dir = tmp_path / "workflows"
        workflow_dir = workflows_dir / "competitor_tracker"
        workflow_dir.mkdir(parents=True)
        (workflow_dir / "tools.py").write_text("# tools")

        with patch("kurt.workflows.agents.executor.get_workflow_dir") as mock_dir:
            mock_dir.return_value = workflow_dir

            result = _get_tools_import_path("competitor-tracker")

        assert result == "workflows.competitor_tracker.tools"

    def test_get_tools_import_path_no_tools(self):
        """Test import path when no tools exist."""
        from kurt.workflows.agents.executor import _get_tools_import_path

        with patch("kurt.workflows.agents.executor.get_workflow_dir") as mock_dir:
            mock_dir.return_value = None

            result = _get_tools_import_path("nonexistent")

        assert result is None


class TestPythonPathSetup:
    """Tests for PYTHONPATH setup in agent execution."""

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_pythonpath_set_for_workflow_with_tools(self, mock_run, mock_which, tmp_path):
        """Test that PYTHONPATH is set when workflow_dir is provided."""
        from kurt.workflows.agents.executor import agent_execution_step

        mock_which.return_value = "/usr/bin/claude"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"num_turns": 1, "result": "done"})
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        workflow_dir = tmp_path / "workflows" / "my_workflow"
        workflow_dir.mkdir(parents=True)

        with patch(
            "kurt.workflows.agents.executor._create_tool_tracking_settings"
        ) as mock_create:
            settings_file = tmp_path / "settings.json"
            tool_log_file = tmp_path / "tools.jsonl"
            settings_file.write_text("{}")
            tool_log_file.write_text("")
            mock_create.return_value = (str(settings_file), str(tool_log_file))

            with patch("kurt.workflows.agents.executor._get_project_root") as mock_root:
                mock_root.return_value = str(tmp_path)

                agent_execution_step(
                    prompt="Test",
                    model="claude-sonnet-4-20250514",
                    max_turns=5,
                    allowed_tools=["Bash"],
                    workflow_dir=str(workflow_dir),
                )

        # Check PYTHONPATH was set
        call_args = mock_run.call_args
        env = call_args[1]["env"]
        assert "PYTHONPATH" in env
        # Should contain parent of workflows (project root)
        assert str(tmp_path) in env["PYTHONPATH"]

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_pythonpath_not_set_without_workflow_dir(self, mock_run, mock_which, tmp_path):
        """Test that PYTHONPATH is not modified when workflow_dir is None."""
        from kurt.workflows.agents.executor import agent_execution_step

        mock_which.return_value = "/usr/bin/claude"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"num_turns": 1, "result": "done"})
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Capture original PYTHONPATH if any
        original_pythonpath = os.environ.get("PYTHONPATH", "")

        with patch(
            "kurt.workflows.agents.executor._create_tool_tracking_settings"
        ) as mock_create:
            settings_file = tmp_path / "settings.json"
            tool_log_file = tmp_path / "tools.jsonl"
            settings_file.write_text("{}")
            tool_log_file.write_text("")
            mock_create.return_value = (str(settings_file), str(tool_log_file))

            with patch("kurt.workflows.agents.executor._get_project_root") as mock_root:
                mock_root.return_value = str(tmp_path)

                agent_execution_step(
                    prompt="Test",
                    model="claude-sonnet-4-20250514",
                    max_turns=5,
                    allowed_tools=["Bash"],
                    workflow_dir=None,  # No workflow dir
                )

        # Check PYTHONPATH wasn't modified beyond original
        call_args = mock_run.call_args
        env = call_args[1]["env"]
        assert env.get("PYTHONPATH", "") == original_pythonpath
