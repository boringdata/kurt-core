"""
Unit tests for AgentTool.
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from kurt.tools.agent import (
    AgentArtifact,
    AgentConfig,
    AgentInput,
    AgentOutput,
    AgentParams,
    AgentTool,
    AgentToolCall,
    _cleanup_temp_files,
    _create_tool_log_file,
    _read_tool_calls,
)
from kurt.tools.core import TOOLS, SubstepEvent, ToolContext, ToolTimeoutError, clear_registry

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear the registry before and after each test."""
    saved_tools = dict(TOOLS)
    clear_registry()
    # Re-register AgentTool
    TOOLS["agent"] = AgentTool
    yield
    clear_registry()
    TOOLS.update(saved_tools)


@pytest.fixture
def temp_tool_log(tmp_path):
    """Create a temporary tool log file."""
    log_file = tmp_path / "tool_calls.jsonl"
    log_file.write_text("")
    return str(log_file)


# ============================================================================
# AgentConfig Validation Tests
# ============================================================================


class TestAgentConfigValidation:
    """Test AgentConfig Pydantic validation."""

    def test_valid_config(self):
        """Valid config without agent in tools."""
        config = AgentConfig(
            prompt="Test prompt",
            tools=["Bash", "Read", "Write"],
            max_turns=10,
        )
        assert config.prompt == "Test prompt"
        assert config.tools == ["Bash", "Read", "Write"]
        assert config.max_turns == 10

    def test_default_values(self):
        """Check default values."""
        config = AgentConfig(prompt="Test")
        assert config.tools is None
        assert config.max_turns == 10
        assert config.model == "claude-sonnet-4-20250514"
        assert config.permission_mode == "bypassPermissions"
        assert config.max_tokens == 200000
        assert config.timeout_seconds == 300

    def test_agent_recursion_blocked(self):
        """Agent tool cannot be in tools list."""
        with pytest.raises(ValidationError, match="Agent recursion not allowed"):
            AgentConfig(prompt="Test", tools=["Bash", "agent", "Read"])

    def test_agent_recursion_blocked_case_insensitive(self):
        """Agent tool blocking is case-insensitive."""
        with pytest.raises(ValidationError, match="Agent recursion not allowed"):
            AgentConfig(prompt="Test", tools=["Bash", "Agent", "Read"])
        with pytest.raises(ValidationError, match="Agent recursion not allowed"):
            AgentConfig(prompt="Test", tools=["AGENT"])

    def test_null_tools_allowed(self):
        """Null tools list is allowed (means all except agent)."""
        config = AgentConfig(prompt="Test", tools=None)
        assert config.tools is None

    def test_empty_tools_allowed(self):
        """Empty tools list is allowed."""
        config = AgentConfig(prompt="Test", tools=[])
        assert config.tools == []

    def test_max_turns_range(self):
        """Max turns must be between 1 and 100."""
        with pytest.raises(ValidationError):
            AgentConfig(prompt="Test", max_turns=0)
        with pytest.raises(ValidationError):
            AgentConfig(prompt="Test", max_turns=101)

    def test_timeout_range(self):
        """Timeout must be between 10 and 3600."""
        with pytest.raises(ValidationError):
            AgentConfig(prompt="Test", timeout_seconds=5)
        with pytest.raises(ValidationError):
            AgentConfig(prompt="Test", timeout_seconds=3601)


class TestAgentInput:
    """Test AgentInput model."""

    def test_default_row_none(self):
        """Row defaults to None."""
        inp = AgentInput()
        assert inp.row is None

    def test_row_with_data(self):
        """Row can contain arbitrary data."""
        inp = AgentInput(row={"key": "value", "num": 42})
        assert inp.row["key"] == "value"
        assert inp.row["num"] == 42


class TestAgentOutput:
    """Test AgentOutput model."""

    def test_default_values(self):
        """Check default values."""
        output = AgentOutput(result="Done")
        assert output.result == "Done"
        assert output.artifacts == []
        assert output.tool_calls == []
        assert output.turns_used == 0
        assert output.tokens_in == 0
        assert output.tokens_out == 0
        assert output.cost_usd == 0.0

    def test_full_output(self):
        """Full output with all fields."""
        output = AgentOutput(
            result="Task completed",
            artifacts=[AgentArtifact(path="/tmp/output.txt", type="file")],
            tool_calls=[AgentToolCall(tool="Bash", input={"command": "ls"}, output={"stdout": "files"})],
            turns_used=5,
            tokens_in=1000,
            tokens_out=500,
            cost_usd=0.05,
        )
        assert output.result == "Task completed"
        assert len(output.artifacts) == 1
        assert output.artifacts[0].path == "/tmp/output.txt"
        assert len(output.tool_calls) == 1
        assert output.tool_calls[0].tool == "Bash"


# ============================================================================
# Helper Function Tests
# ============================================================================


class TestHelperFunctions:
    """Test helper functions."""

    def test_create_tool_log_file(self, tmp_path):
        """Test creating tool log file."""
        log_path = _create_tool_log_file()
        try:
            assert os.path.exists(log_path)
            assert log_path.endswith(".jsonl")
        finally:
            _cleanup_temp_files(log_path)

    def test_cleanup_temp_files(self, tmp_path):
        """Test cleanup removes files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content")
        file2.write_text("content")

        _cleanup_temp_files(str(file1), str(file2))

        assert not file1.exists()
        assert not file2.exists()

    def test_cleanup_handles_missing_files(self, tmp_path):
        """Cleanup doesn't fail on missing files."""
        nonexistent = tmp_path / "nonexistent.txt"
        # Should not raise
        _cleanup_temp_files(str(nonexistent))

    def test_read_tool_calls_empty(self, temp_tool_log):
        """Read empty tool log."""
        tool_calls = _read_tool_calls(temp_tool_log)
        assert tool_calls == []

    def test_read_tool_calls_with_data(self, tmp_path):
        """Read tool calls from log."""
        log_file = tmp_path / "tools.jsonl"
        log_file.write_text(
            '{"tool_name": "Bash", "input": {"command": "ls"}, "output": {"stdout": "files"}}\n'
            '{"tool_name": "Read", "input": {"file": "test.py"}, "output": {}}\n'
        )

        tool_calls = _read_tool_calls(str(log_file))

        assert len(tool_calls) == 2
        assert tool_calls[0].tool == "Bash"
        assert tool_calls[0].input == {"command": "ls"}
        assert tool_calls[1].tool == "Read"

    def test_read_tool_calls_handles_invalid_json(self, tmp_path):
        """Invalid JSON lines are skipped."""
        log_file = tmp_path / "tools.jsonl"
        log_file.write_text(
            '{"tool_name": "Bash"}\n'
            "not json\n"
            '{"tool_name": "Read"}\n'
        )

        tool_calls = _read_tool_calls(str(log_file))

        assert len(tool_calls) == 2

    def test_read_tool_calls_missing_file(self, tmp_path):
        """Missing file returns empty list."""
        tool_calls = _read_tool_calls(str(tmp_path / "nonexistent.jsonl"))
        assert tool_calls == []


# ============================================================================
# AgentTool Registration Tests
# ============================================================================


class TestAgentToolRegistration:
    """Test AgentTool registration."""

    def test_tool_registered(self):
        """AgentTool is registered in TOOLS."""
        assert "agent" in TOOLS
        assert TOOLS["agent"] is AgentTool

    def test_tool_attributes(self):
        """AgentTool has correct attributes."""
        assert AgentTool.name == "agent"
        assert AgentTool.description is not None
        assert AgentTool.InputModel is AgentParams
        assert AgentTool.OutputModel is AgentOutput


# ============================================================================
# AgentTool Execution Tests
# ============================================================================


class TestAgentToolExecution:
    """Test AgentTool execution."""

    @pytest.mark.asyncio
    async def test_claude_not_found(self):
        """Error when claude CLI not installed."""
        tool = AgentTool()
        params = AgentParams(
            config=AgentConfig(prompt="Test", tools=["Bash"]),
        )
        context = ToolContext()

        with patch("shutil.which", return_value=None):
            result = await tool.run(params, context)

        assert result.success is False
        assert len(result.errors) == 1
        assert "not found" in result.errors[0].message.lower()

    @pytest.mark.asyncio
    async def test_runtime_recursion_block(self):
        """Agent tool is blocked at runtime (defense in depth)."""
        # This bypasses Pydantic validation by using model_construct
        tool = AgentTool()
        config = AgentConfig.model_construct(
            prompt="Test",
            tools=["Bash", "agent"],  # Would normally fail validation
            max_turns=10,
            model="claude-sonnet-4-20250514",
            permission_mode="bypassPermissions",
            max_tokens=200000,
            timeout_seconds=300,
        )
        params = AgentParams(config=config)
        context = ToolContext()

        with patch("shutil.which", return_value="/usr/bin/claude"):
            result = await tool.run(params, context)

        assert result.success is False
        assert len(result.errors) == 1
        assert "recursion" in result.errors[0].message.lower()

    @pytest.mark.asyncio
    async def test_successful_execution(self, tmp_path):
        """Successful agent execution."""
        tool = AgentTool()
        params = AgentParams(
            config=AgentConfig(
                prompt="Test task",
                tools=["Bash", "Read"],
                max_turns=5,
            ),
        )
        context = ToolContext()

        # Mock subprocess result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "num_turns": 3,
            "total_cost_usd": 0.05,
            "usage": {
                "input_tokens": 1000,
                "output_tokens": 500,
                "cache_read_input_tokens": 100,
            },
            "result": "Task completed successfully",
        })
        mock_result.stderr = ""

        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("subprocess.run", return_value=mock_result):
                with patch("kurt.tools.agent._get_project_root", return_value=str(tmp_path)):
                    result = await tool.run(params, context)

        assert result.success is True
        assert len(result.data) == 1

        output = result.data[0]
        assert output["result"] == "Task completed successfully"
        assert output["turns_used"] == 3
        assert output["tokens_in"] == 1100  # 1000 + 100 cache
        assert output["tokens_out"] == 500
        assert output["cost_usd"] == 0.05

    @pytest.mark.asyncio
    async def test_execution_with_input_context(self, tmp_path):
        """Agent receives input context."""
        tool = AgentTool()
        params = AgentParams(
            input=AgentInput(row={"url": "https://example.com", "status": "pending"}),
            config=AgentConfig(prompt="Process this URL", tools=["Bash"]),
        )
        context = ToolContext()

        captured_cmd = None

        def capture_run(cmd, **kwargs):
            nonlocal captured_cmd
            captured_cmd = cmd
            result = MagicMock()
            result.returncode = 0
            result.stdout = json.dumps({"result": "Done", "num_turns": 1})
            result.stderr = ""
            return result

        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("subprocess.run", side_effect=capture_run):
                with patch("kurt.tools.agent._get_project_root", return_value=str(tmp_path)):
                    await tool.run(params, context)

        # The prompt should include the context
        prompt = captured_cmd[-1]
        assert "example.com" in prompt
        assert "pending" in prompt

    @pytest.mark.asyncio
    async def test_timeout_handling(self, tmp_path):
        """Handle subprocess timeout."""
        import subprocess

        tool = AgentTool()
        params = AgentParams(
            config=AgentConfig(
                prompt="Long task",
                tools=["Bash"],
                timeout_seconds=10,
            ),
        )
        context = ToolContext()

        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="claude", timeout=10)):
                with patch("kurt.tools.agent._get_project_root", return_value=str(tmp_path)):
                    with pytest.raises(ToolTimeoutError) as exc_info:
                        await tool.run(params, context)

        assert exc_info.value.tool_name == "agent"
        assert exc_info.value.timeout_seconds == 10

    @pytest.mark.asyncio
    async def test_subprocess_error(self, tmp_path):
        """Handle subprocess error."""
        tool = AgentTool()
        params = AgentParams(
            config=AgentConfig(prompt="Task", tools=["Bash"]),
        )
        context = ToolContext()

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = json.dumps({"is_error": True, "subtype": "permission_denied"})
        mock_result.stderr = "Permission denied"

        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("subprocess.run", return_value=mock_result):
                with patch("kurt.tools.agent._get_project_root", return_value=str(tmp_path)):
                    result = await tool.run(params, context)

        # Should have error but still return result
        assert len(result.errors) == 1
        assert "permission_denied" in result.errors[0].message

    @pytest.mark.asyncio
    async def test_progress_callback(self, tmp_path):
        """Progress callback is called."""
        tool = AgentTool()
        params = AgentParams(
            config=AgentConfig(prompt="Task", tools=["Bash"], max_turns=5),
        )
        context = ToolContext()

        events: list[SubstepEvent] = []

        def on_progress(event: SubstepEvent):
            events.append(event)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"result": "Done", "num_turns": 2})
        mock_result.stderr = ""

        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("subprocess.run", return_value=mock_result):
                with patch("kurt.tools.agent._get_project_root", return_value=str(tmp_path)):
                    await tool.run(params, context, on_progress)

        assert len(events) >= 2
        assert any(e.substep == "run_claude_agent" and e.status == "running" for e in events)
        assert any(e.substep == "run_claude_agent" and e.status == "completed" for e in events)

    @pytest.mark.asyncio
    async def test_tool_calls_tracked(self, tmp_path):
        """Tool calls from log are included in output."""
        tool = AgentTool()
        params = AgentParams(
            config=AgentConfig(prompt="Task", tools=["Bash", "Read"]),
        )
        context = ToolContext()

        # Create tool log with calls
        tool_log = tmp_path / "tools.jsonl"
        tool_log.write_text(
            '{"tool_name": "Bash", "input": {"command": "ls"}}\n'
            '{"tool_name": "Read", "input": {"file": "test.py"}}\n'
        )

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"result": "Done", "num_turns": 2})
        mock_result.stderr = ""

        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("subprocess.run", return_value=mock_result):
                with patch("kurt.tools.agent._get_project_root", return_value=str(tmp_path)):
                    with patch("kurt.tools.agent._create_tool_log_file", return_value=str(tool_log)):
                        result = await tool.run(params, context)

        assert result.success is True
        assert len(result.data) == 1
        tool_calls = result.data[0]["tool_calls"]
        assert len(tool_calls) == 2
        assert tool_calls[0]["tool"] == "Bash"
        assert tool_calls[1]["tool"] == "Read"


class TestAgentToolCommandBuilding:
    """Test command building for subprocess."""

    @pytest.mark.asyncio
    async def test_command_includes_allowed_tools(self, tmp_path):
        """Allowed tools are passed to CLI."""
        tool = AgentTool()
        params = AgentParams(
            config=AgentConfig(
                prompt="Task",
                tools=["Bash", "Read", "Write"],
            ),
        )
        context = ToolContext()

        captured_cmd = None

        def capture_run(cmd, **kwargs):
            nonlocal captured_cmd
            captured_cmd = cmd
            result = MagicMock()
            result.returncode = 0
            result.stdout = json.dumps({"result": "Done"})
            result.stderr = ""
            return result

        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("subprocess.run", side_effect=capture_run):
                with patch("kurt.tools.agent._get_project_root", return_value=str(tmp_path)):
                    await tool.run(params, context)

        assert "--allowedTools" in captured_cmd
        idx = captured_cmd.index("--allowedTools")
        assert captured_cmd[idx + 1] == "Bash,Read,Write"

    @pytest.mark.asyncio
    async def test_command_includes_model(self, tmp_path):
        """Model is passed to CLI."""
        tool = AgentTool()
        params = AgentParams(
            config=AgentConfig(
                prompt="Task",
                model="claude-opus-4-20250514",
            ),
        )
        context = ToolContext()

        captured_cmd = None

        def capture_run(cmd, **kwargs):
            nonlocal captured_cmd
            captured_cmd = cmd
            result = MagicMock()
            result.returncode = 0
            result.stdout = json.dumps({"result": "Done"})
            result.stderr = ""
            return result

        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("subprocess.run", side_effect=capture_run):
                with patch("kurt.tools.agent._get_project_root", return_value=str(tmp_path)):
                    await tool.run(params, context)

        assert "--model" in captured_cmd
        idx = captured_cmd.index("--model")
        assert captured_cmd[idx + 1] == "claude-opus-4-20250514"

    @pytest.mark.asyncio
    async def test_command_includes_permission_mode(self, tmp_path):
        """Permission mode is passed to CLI."""
        tool = AgentTool()
        params = AgentParams(
            config=AgentConfig(
                prompt="Task",
                permission_mode="acceptEdits",
            ),
        )
        context = ToolContext()

        captured_cmd = None

        def capture_run(cmd, **kwargs):
            nonlocal captured_cmd
            captured_cmd = cmd
            result = MagicMock()
            result.returncode = 0
            result.stdout = json.dumps({"result": "Done"})
            result.stderr = ""
            return result

        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("subprocess.run", side_effect=capture_run):
                with patch("kurt.tools.agent._get_project_root", return_value=str(tmp_path)):
                    await tool.run(params, context)

        assert "--permission-mode" in captured_cmd
        idx = captured_cmd.index("--permission-mode")
        assert captured_cmd[idx + 1] == "acceptEdits"

    @pytest.mark.asyncio
    async def test_command_includes_max_turns(self, tmp_path):
        """Max turns is passed to CLI."""
        tool = AgentTool()
        params = AgentParams(
            config=AgentConfig(
                prompt="Task",
                max_turns=15,
            ),
        )
        context = ToolContext()

        captured_cmd = None

        def capture_run(cmd, **kwargs):
            nonlocal captured_cmd
            captured_cmd = cmd
            result = MagicMock()
            result.returncode = 0
            result.stdout = json.dumps({"result": "Done"})
            result.stderr = ""
            return result

        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("subprocess.run", side_effect=capture_run):
                with patch("kurt.tools.agent._get_project_root", return_value=str(tmp_path)):
                    await tool.run(params, context)

        assert "--max-turns" in captured_cmd
        idx = captured_cmd.index("--max-turns")
        assert captured_cmd[idx + 1] == "15"


class TestAgentToolEdgeCases:
    """Test edge cases for AgentTool."""

    @pytest.mark.asyncio
    async def test_plain_text_output(self, tmp_path):
        """Handle plain text output (not JSON)."""
        tool = AgentTool()
        params = AgentParams(
            config=AgentConfig(prompt="Task"),
        )
        context = ToolContext()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "This is plain text output"
        mock_result.stderr = ""

        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("subprocess.run", return_value=mock_result):
                with patch("kurt.tools.agent._get_project_root", return_value=str(tmp_path)):
                    result = await tool.run(params, context)

        assert result.success is True
        assert result.data[0]["result"] == "This is plain text output"

    @pytest.mark.asyncio
    async def test_empty_tools_list(self, tmp_path):
        """Empty tools list doesn't add --allowedTools."""
        tool = AgentTool()
        params = AgentParams(
            config=AgentConfig(prompt="Task", tools=[]),
        )
        context = ToolContext()

        captured_cmd = None

        def capture_run(cmd, **kwargs):
            nonlocal captured_cmd
            captured_cmd = cmd
            result = MagicMock()
            result.returncode = 0
            result.stdout = json.dumps({"result": "Done"})
            result.stderr = ""
            return result

        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("subprocess.run", side_effect=capture_run):
                with patch("kurt.tools.agent._get_project_root", return_value=str(tmp_path)):
                    await tool.run(params, context)

        assert "--allowedTools" not in captured_cmd

    @pytest.mark.asyncio
    async def test_cleanup_on_success(self, tmp_path):
        """Tool log file is cleaned up on success."""
        tool = AgentTool()
        params = AgentParams(
            config=AgentConfig(prompt="Task"),
        )
        context = ToolContext()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"result": "Done"})
        mock_result.stderr = ""

        created_log_file = None

        def track_creation():
            nonlocal created_log_file
            created_log_file = _create_tool_log_file()
            return created_log_file

        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("subprocess.run", return_value=mock_result):
                with patch("kurt.tools.agent._get_project_root", return_value=str(tmp_path)):
                    with patch("kurt.tools.agent._create_tool_log_file", side_effect=track_creation):
                        await tool.run(params, context)

        if created_log_file:
            assert not os.path.exists(created_log_file)

    @pytest.mark.asyncio
    async def test_substep_recorded(self, tmp_path):
        """Substep is recorded in result."""
        tool = AgentTool()
        params = AgentParams(
            config=AgentConfig(prompt="Task", max_turns=10),
        )
        context = ToolContext()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"result": "Done", "num_turns": 5})
        mock_result.stderr = ""

        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("subprocess.run", return_value=mock_result):
                with patch("kurt.tools.agent._get_project_root", return_value=str(tmp_path)):
                    result = await tool.run(params, context)

        assert len(result.substeps) == 1
        assert result.substeps[0].name == "run_claude_agent"
        assert result.substeps[0].status == "completed"
        assert result.substeps[0].current == 5
        assert result.substeps[0].total == 10
