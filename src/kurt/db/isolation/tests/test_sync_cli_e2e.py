"""
E2E tests for `kurt sync` command (pull, push, merge).

These tests verify the sync CLI commands work correctly.
Tests mock external Git/Dolt operations while testing the full CLI integration.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from kurt.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)
from kurt.db.isolation.cli import (
    merge_cmd,
    pull_cmd,
    push_cmd,
    sync_group,
)


class TestSyncHelp:
    """Tests for sync command help and options."""

    def test_sync_group_help(self, cli_runner: CliRunner):
        """Verify sync group shows help."""
        result = invoke_cli(cli_runner, sync_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Git+Dolt version control")

    def test_sync_lists_commands(self, cli_runner: CliRunner):
        """Verify sync group lists all commands."""
        result = invoke_cli(cli_runner, sync_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "pull")
        assert_output_contains(result, "push")
        assert_output_contains(result, "branch")
        assert_output_contains(result, "merge")


class TestSyncPullHelp:
    """E2E tests for sync pull command help."""

    def test_pull_help(self, cli_runner: CliRunner):
        """Verify pull command shows help."""
        result = invoke_cli(cli_runner, pull_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Pull changes from Git and Dolt")

    def test_pull_shows_options(self, cli_runner: CliRunner):
        """Verify pull command lists all options."""
        result = invoke_cli(cli_runner, pull_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--remote")
        assert_output_contains(result, "--git-only")
        assert_output_contains(result, "--dolt-only")
        assert_output_contains(result, "--json")


class TestSyncPull:
    """E2E tests for sync pull command execution."""

    def test_pull_git_only_dolt_only_mutually_exclusive(self, cli_runner: CliRunner):
        """Verify --git-only and --dolt-only are mutually exclusive."""
        with patch("kurt.db.isolation.cli._get_dolt_db"):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake")):
                result = invoke_cli(
                    cli_runner, pull_cmd, ["--git-only", "--dolt-only"]
                )

        assert result.exit_code != 0
        assert "Cannot use both" in result.output

    def test_pull_success(self, cli_runner: CliRunner):
        """Verify pull executes successfully with mocked operations."""
        mock_result = MagicMock()
        mock_result.git.status = "success"
        mock_result.git.commits_pulled = 2
        mock_result.dolt.status = "success"
        mock_result.dolt.commits_pulled = 1
        mock_result.to_dict.return_value = {
            "git": {"status": "success", "commits_pulled": 2},
            "dolt": {"status": "success", "commits_pulled": 1},
        }

        with patch("kurt.db.isolation.cli._get_dolt_db"):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake")):
                with patch("kurt.db.isolation.cli.pull", return_value=mock_result):
                    result = invoke_cli(cli_runner, pull_cmd, [])

        assert result.exit_code == 0
        assert "Git" in result.output
        assert "Dolt" in result.output

    def test_pull_git_only(self, cli_runner: CliRunner):
        """Verify pull with --git-only skips Dolt."""
        mock_result = MagicMock()
        mock_result.git.status = "success"
        mock_result.git.commits_pulled = 0
        mock_result.to_dict.return_value = {
            "git": {"status": "success", "commits_pulled": 0},
        }

        with patch("kurt.db.isolation.cli._get_dolt_db"):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake")):
                with patch("kurt.db.isolation.cli.pull", return_value=mock_result) as mock_pull:
                    result = invoke_cli(cli_runner, pull_cmd, ["--git-only"])

        assert result.exit_code == 0
        mock_pull.assert_called_once()
        call_kwargs = mock_pull.call_args[1]
        assert call_kwargs["git_only"] is True

    def test_pull_json_output(self, cli_runner: CliRunner):
        """Verify pull with --json outputs JSON."""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "git": {"status": "success", "commits_pulled": 0},
            "dolt": {"status": "success", "commits_pulled": 0},
        }

        with patch("kurt.db.isolation.cli._get_dolt_db"):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake")):
                with patch("kurt.db.isolation.cli.pull", return_value=mock_result):
                    result = invoke_cli(cli_runner, pull_cmd, ["--json"])

        assert result.exit_code == 0
        assert "{" in result.output


class TestSyncPushHelp:
    """E2E tests for sync push command help."""

    def test_push_help(self, cli_runner: CliRunner):
        """Verify push command shows help."""
        result = invoke_cli(cli_runner, push_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Push changes to Git and Dolt")

    def test_push_shows_options(self, cli_runner: CliRunner):
        """Verify push command lists all options."""
        result = invoke_cli(cli_runner, push_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--remote")
        assert_output_contains(result, "--git-only")
        assert_output_contains(result, "--dolt-only")
        assert_output_contains(result, "--json")


class TestSyncPush:
    """E2E tests for sync push command execution."""

    def test_push_git_only_dolt_only_mutually_exclusive(self, cli_runner: CliRunner):
        """Verify --git-only and --dolt-only are mutually exclusive."""
        with patch("kurt.db.isolation.cli._get_dolt_db"):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake")):
                result = invoke_cli(
                    cli_runner, push_cmd, ["--git-only", "--dolt-only"]
                )

        assert result.exit_code != 0
        assert "Cannot use both" in result.output

    def test_push_success(self, cli_runner: CliRunner):
        """Verify push executes successfully with mocked operations."""
        mock_result = MagicMock()
        mock_result.git.status = "success"
        mock_result.git.commits_pushed = 1
        mock_result.dolt.status = "success"
        mock_result.dolt.commits_pushed = 1
        mock_result.to_dict.return_value = {
            "git": {"status": "success", "commits_pushed": 1},
            "dolt": {"status": "success", "commits_pushed": 1},
        }

        with patch("kurt.db.isolation.cli._get_dolt_db"):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake")):
                with patch("kurt.db.isolation.cli.push", return_value=mock_result):
                    result = invoke_cli(cli_runner, push_cmd, [])

        assert result.exit_code == 0
        assert "Dolt" in result.output
        assert "Git" in result.output

    def test_push_dolt_only(self, cli_runner: CliRunner):
        """Verify push with --dolt-only skips Git."""
        mock_result = MagicMock()
        mock_result.dolt.status = "success"
        mock_result.dolt.commits_pushed = 0
        mock_result.to_dict.return_value = {
            "dolt": {"status": "success", "commits_pushed": 0},
        }

        with patch("kurt.db.isolation.cli._get_dolt_db"):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake")):
                with patch("kurt.db.isolation.cli.push", return_value=mock_result) as mock_push:
                    result = invoke_cli(cli_runner, push_cmd, ["--dolt-only"])

        assert result.exit_code == 0
        mock_push.assert_called_once()
        call_kwargs = mock_push.call_args[1]
        assert call_kwargs["dolt_only"] is True


class TestSyncMergeHelp:
    """E2E tests for sync merge command help."""

    def test_merge_help(self, cli_runner: CliRunner):
        """Verify merge command shows help."""
        result = invoke_cli(cli_runner, merge_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Merge a branch")

    def test_merge_shows_options(self, cli_runner: CliRunner):
        """Verify merge command lists all options."""
        result = invoke_cli(cli_runner, merge_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--abort")
        assert_output_contains(result, "--no-commit")
        assert_output_contains(result, "--squash")
        assert_output_contains(result, "--message")
        assert_output_contains(result, "--json")
        assert_output_contains(result, "--dry-run")


class TestSyncMerge:
    """E2E tests for sync merge command execution."""

    def test_merge_requires_branch(self, cli_runner: CliRunner):
        """Verify merge requires branch argument."""
        with patch("kurt.db.isolation.cli._get_dolt_db"):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake")):
                result = invoke_cli(cli_runner, merge_cmd, [])

        # Should fail or exit with error
        assert result.exit_code != 0 or "Branch name required" in result.output

    def test_merge_success(self, cli_runner: CliRunner):
        """Verify merge executes successfully with mocked operations."""
        mock_result = MagicMock()
        mock_result.source_branch = "feature/test"
        mock_result.target_branch = "main"
        mock_result.dolt_commit_hash = "abc123"
        mock_result.git_commit_hash = "def456789"
        mock_result.message = "Merged feature/test into main"

        with patch("kurt.db.isolation.cli._get_dolt_db"):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake")):
                with patch("kurt.db.isolation.cli.merge_branch", return_value=mock_result):
                    result = invoke_cli(cli_runner, merge_cmd, ["feature/test"])

        # Exit code 0 means success (MergeExitCode.SUCCESS)
        assert result.exit_code == 0
        assert "Merged" in result.output or "feature/test" in result.output

    def test_merge_dry_run(self, cli_runner: CliRunner):
        """Verify merge --dry-run checks for conflicts."""
        mock_conflicts = MagicMock()
        mock_conflicts.dolt_conflicts = []
        mock_conflicts.git_conflicts = []

        with patch("kurt.db.isolation.cli._get_dolt_db"):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake")):
                with patch("kurt.db.isolation.cli.check_conflicts", return_value=mock_conflicts):
                    with patch("kurt.db.isolation.branch._git_current_branch", return_value="main"):
                        result = invoke_cli(
                            cli_runner, merge_cmd, ["feature/test", "--dry-run"]
                        )

        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "no conflicts" in output_lower or "can be merged" in output_lower

    def test_merge_abort(self, cli_runner: CliRunner):
        """Verify merge --abort aborts in-progress merge."""
        with patch("kurt.db.isolation.cli._get_dolt_db"):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake")):
                with patch("kurt.db.isolation.cli.abort_merge", return_value=True):
                    result = invoke_cli(cli_runner, merge_cmd, ["--abort"])

        assert result.exit_code == 0
        assert "aborted" in result.output.lower()

    def test_merge_json_output(self, cli_runner: CliRunner):
        """Verify merge with --json outputs JSON."""
        mock_result = MagicMock()
        mock_result.source_branch = "feature/test"
        mock_result.target_branch = "main"
        mock_result.dolt_commit_hash = "abc123"
        mock_result.git_commit_hash = "def456789"
        mock_result.message = "Merged"

        with patch("kurt.db.isolation.cli._get_dolt_db"):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake")):
                with patch("kurt.db.isolation.cli.merge_branch", return_value=mock_result):
                    result = invoke_cli(
                        cli_runner, merge_cmd, ["feature/test", "--json"]
                    )

        assert result.exit_code == 0
        assert "{" in result.output
        assert '"success": true' in result.output


class TestSyncRemoteOptions:
    """E2E tests for remote-related options."""

    def test_pull_custom_remote(self, cli_runner: CliRunner):
        """Verify pull with custom --remote works."""
        mock_result = MagicMock()
        mock_result.git.status = "success"
        mock_result.git.commits_pulled = 0
        mock_result.dolt.status = "success"
        mock_result.dolt.commits_pulled = 0
        mock_result.to_dict.return_value = {}

        with patch("kurt.db.isolation.cli._get_dolt_db"):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake")):
                with patch("kurt.db.isolation.cli.pull", return_value=mock_result) as mock_pull:
                    result = invoke_cli(
                        cli_runner, pull_cmd, ["--remote", "upstream"]
                    )

        assert result.exit_code == 0
        mock_pull.assert_called_once()
        call_kwargs = mock_pull.call_args[1]
        assert call_kwargs["remote"] == "upstream"

    def test_push_custom_remote(self, cli_runner: CliRunner):
        """Verify push with custom --remote works."""
        mock_result = MagicMock()
        mock_result.git.status = "success"
        mock_result.git.commits_pushed = 0
        mock_result.dolt.status = "success"
        mock_result.dolt.commits_pushed = 0
        mock_result.to_dict.return_value = {}

        with patch("kurt.db.isolation.cli._get_dolt_db"):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake")):
                with patch("kurt.db.isolation.cli.push", return_value=mock_result) as mock_push:
                    result = invoke_cli(
                        cli_runner, push_cmd, ["--remote", "upstream"]
                    )

        assert result.exit_code == 0
        mock_push.assert_called_once()
        call_kwargs = mock_push.call_args[1]
        assert call_kwargs["remote"] == "upstream"
