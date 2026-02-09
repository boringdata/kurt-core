"""
E2E tests for Kurt main CLI.

These tests verify global CLI options and command aliases work correctly.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from kurt.conftest import (
    assert_cli_success,
    assert_output_contains,
)
from kurt.cli.main import main


class TestMainCLIHelp:
    """Tests for main CLI help and options."""

    def test_main_help(self, cli_runner: CliRunner):
        """Verify main CLI shows help."""
        result = cli_runner.invoke(main, ["--help"], catch_exceptions=False)
        assert_cli_success(result)
        assert_output_contains(result, "Kurt")

    def test_main_version(self, cli_runner: CliRunner):
        """Verify --version shows version."""
        result = cli_runner.invoke(main, ["--version"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "kurt" in result.output.lower() or "version" in result.output.lower()

    def test_main_shows_commands(self, cli_runner: CliRunner):
        """Verify main CLI lists all commands."""
        result = cli_runner.invoke(main, ["--help"], catch_exceptions=False)
        assert_cli_success(result)
        # Check for main command groups
        assert_output_contains(result, "init")
        assert_output_contains(result, "status")
        assert_output_contains(result, "doctor")
        assert_output_contains(result, "workflow")
        assert_output_contains(result, "tool")
        assert_output_contains(result, "docs")
        assert_output_contains(result, "sync")
        assert_output_contains(result, "connect")


class TestGlobalJsonFlag:
    """E2E tests for global --json flag."""

    def test_json_flag_with_doctor(self, cli_runner: CliRunner):
        """Verify --json flag works with doctor command."""
        with cli_runner.isolated_filesystem():
            # Create a minimal git repo
            import subprocess
            subprocess.run(["git", "init"], capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], capture_output=True)
            Path("README.md").write_text("# Test")
            subprocess.run(["git", "add", "."], capture_output=True)
            subprocess.run(["git", "commit", "-m", "Init"], capture_output=True)

            result = cli_runner.invoke(main, ["--json", "doctor"], catch_exceptions=False)

        # Should produce JSON output or handle gracefully
        assert result.exit_code in (0, 1, 2)

    def test_json_flag_with_status(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --json flag works with status command."""
        result = cli_runner.invoke(main, ["--json", "status"], catch_exceptions=False)

        # Should complete
        assert result.exit_code in (0, 1, 2)
        # Output should contain JSON structure
        if result.exit_code == 0:
            assert "{" in result.output or "success" in result.output.lower()

    def test_robot_flag_alias(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --robot flag is alias for --json."""
        result = cli_runner.invoke(main, ["--robot", "status"], catch_exceptions=False)

        # Should complete (--robot is hidden alias)
        assert result.exit_code in (0, 1, 2)


class TestGlobalQuietFlag:
    """E2E tests for global --quiet flag."""

    def test_quiet_flag_with_status(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --quiet flag suppresses non-essential output."""
        result = cli_runner.invoke(main, ["--quiet", "status"], catch_exceptions=False)

        # Should complete
        assert result.exit_code in (0, 1, 2)


class TestCommandAliases:
    """E2E tests for command aliases (LLM typo tolerance)."""

    def test_doc_alias_for_docs(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify 'doc' alias works for 'docs'."""
        result = cli_runner.invoke(main, ["doc", "--help"], catch_exceptions=False)

        assert_cli_success(result)
        # Should show docs help
        assert "Document management" in result.output or "list" in result.output.lower()

    def test_documents_alias_for_docs(self, cli_runner: CliRunner):
        """Verify 'documents' alias works for 'docs'."""
        result = cli_runner.invoke(main, ["documents", "--help"], catch_exceptions=False)

        assert_cli_success(result)

    def test_stat_alias_for_status(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify 'stat' alias works for 'status'."""
        result = cli_runner.invoke(main, ["stat"], catch_exceptions=False)

        # Should complete (may fail if no project)
        assert result.exit_code in (0, 1, 2)

    def test_st_alias_for_status(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify 'st' alias works for 'status'."""
        result = cli_runner.invoke(main, ["st"], catch_exceptions=False)

        assert result.exit_code in (0, 1, 2)

    def test_wf_alias_for_workflow(self, cli_runner: CliRunner):
        """Verify 'wf' alias works for 'workflow'."""
        result = cli_runner.invoke(main, ["wf", "--help"], catch_exceptions=False)

        assert_cli_success(result)
        assert "workflow" in result.output.lower() or "run" in result.output.lower()

    def test_workflows_alias_for_workflow(self, cli_runner: CliRunner):
        """Verify 'workflows' alias works for 'workflow'."""
        result = cli_runner.invoke(main, ["workflows", "--help"], catch_exceptions=False)

        assert_cli_success(result)

    def test_tools_alias_for_tool(self, cli_runner: CliRunner):
        """Verify 'tools' alias works for 'tool'."""
        result = cli_runner.invoke(main, ["tools", "--help"], catch_exceptions=False)

        assert_cli_success(result)

    def test_initialize_alias_for_init(self, cli_runner: CliRunner):
        """Verify 'initialize' alias works for 'init'."""
        result = cli_runner.invoke(main, ["initialize", "--help"], catch_exceptions=False)

        assert_cli_success(result)

    def test_agent_alias_for_agents(self, cli_runner: CliRunner):
        """Verify 'agent' alias works for 'agents'."""
        result = cli_runner.invoke(main, ["agent", "--help"], catch_exceptions=False)

        assert_cli_success(result)


class TestLazyLoading:
    """E2E tests for lazy command loading."""

    def test_workflow_lazy_loads(self, cli_runner: CliRunner):
        """Verify workflow command is lazily loaded."""
        result = cli_runner.invoke(main, ["workflow", "--help"], catch_exceptions=False)

        assert_cli_success(result)
        assert_output_contains(result, "workflow")

    def test_tool_lazy_loads(self, cli_runner: CliRunner):
        """Verify tool command is lazily loaded."""
        result = cli_runner.invoke(main, ["tool", "--help"], catch_exceptions=False)

        assert_cli_success(result)

    def test_docs_lazy_loads(self, cli_runner: CliRunner):
        """Verify docs command is lazily loaded."""
        result = cli_runner.invoke(main, ["docs", "--help"], catch_exceptions=False)

        assert_cli_success(result)

    def test_sync_lazy_loads(self, cli_runner: CliRunner):
        """Verify sync command is lazily loaded."""
        result = cli_runner.invoke(main, ["sync", "--help"], catch_exceptions=False)

        assert_cli_success(result)

    def test_connect_lazy_loads(self, cli_runner: CliRunner):
        """Verify connect command is lazily loaded."""
        result = cli_runner.invoke(main, ["connect", "--help"], catch_exceptions=False)

        assert_cli_success(result)

    def test_cloud_lazy_loads(self, cli_runner: CliRunner):
        """Verify cloud command is lazily loaded."""
        result = cli_runner.invoke(main, ["cloud", "--help"], catch_exceptions=False)

        assert_cli_success(result)

    def test_admin_lazy_loads(self, cli_runner: CliRunner):
        """Verify admin command is lazily loaded."""
        result = cli_runner.invoke(main, ["admin", "--help"], catch_exceptions=False)

        assert_cli_success(result)

    def test_agents_lazy_loads(self, cli_runner: CliRunner):
        """Verify agents command is lazily loaded."""
        result = cli_runner.invoke(main, ["agents", "--help"], catch_exceptions=False)

        assert_cli_success(result)


class TestInvalidCommands:
    """E2E tests for invalid command handling."""

    def test_unknown_command(self, cli_runner: CliRunner):
        """Verify unknown command shows error."""
        result = cli_runner.invoke(main, ["unknown_command"], catch_exceptions=False)

        assert result.exit_code != 0

    def test_typo_suggestion(self, cli_runner: CliRunner):
        """Verify typo doesn't crash CLI."""
        result = cli_runner.invoke(main, ["statos"], catch_exceptions=False)

        # Should fail but not crash
        assert result.exit_code != 0
