"""Tests for branch CLI commands (create, list, switch, delete).

Tests use Click's CliRunner for isolated CLI testing.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kurt.db.isolation.cli import (
    branch_group,
    branch_create_cmd as create_cmd,
    branch_delete_cmd as delete_cmd,
    branch_list_cmd as list_cmd,
    branch_switch_cmd as switch_cmd,
)
from kurt.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)
from kurt.db.dolt import BranchInfo
from kurt.db.isolation.branch import (
    BranchStatus,
    BranchSyncError,
    BranchSyncErrorCode,
    BranchSyncResult,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_dolt_db():
    """Create a mock DoltDB instance."""
    db = MagicMock()
    db.path = Path("/fake/dolt/repo")
    db.exists.return_value = True
    db.branch_current.return_value = "main"
    db.branch_list.return_value = [
        BranchInfo(name="main", hash="abc1234", is_current=True),
    ]
    return db


# =============================================================================
# Tests - Help and Group
# =============================================================================


class TestBranchGroupHelp:
    """Tests for branch command group help."""

    def test_branch_group_help(self, cli_runner: CliRunner):
        """Test branch group shows help."""
        result = invoke_cli(cli_runner, branch_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Manage synchronized Git+Dolt branches")

    def test_branch_list_commands(self, cli_runner: CliRunner):
        """Test branch group lists all commands."""
        result = invoke_cli(cli_runner, branch_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "create")
        assert_output_contains(result, "list")
        assert_output_contains(result, "switch")
        assert_output_contains(result, "delete")


# =============================================================================
# Tests - Create Command
# =============================================================================


class TestCreateCommand:
    """Tests for `branch create` command."""

    def test_create_help(self, cli_runner: CliRunner):
        """Test create command shows help."""
        result = invoke_cli(cli_runner, create_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Create a new branch in both Git and Dolt")

    def test_create_shows_options(self, cli_runner: CliRunner):
        """Test create command lists options in help."""
        result = invoke_cli(cli_runner, create_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--no-switch")

    def test_create_success(self, cli_runner: CliRunner, mock_dolt_db):
        """Test successful branch creation."""
        mock_result = BranchSyncResult(
            git_branch="feature/test",
            dolt_branch="feature/test",
            created=True,
        )

        with patch("kurt.db.isolation.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake/repo")):
                with patch("kurt.db.isolation.cli.create_both", return_value=mock_result) as mock_create:
                    result = invoke_cli(cli_runner, branch_group, ["create", "feature/test"])

        assert_cli_success(result)
        assert_output_contains(result, "Created branch 'feature/test'")
        mock_create.assert_called_once()

    def test_create_already_exists(self, cli_runner: CliRunner, mock_dolt_db):
        """Test create when branch already exists."""
        mock_result = BranchSyncResult(
            git_branch="existing",
            dolt_branch="existing",
            created=False,
        )

        with patch("kurt.db.isolation.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake/repo")):
                with patch("kurt.db.isolation.cli.create_both", return_value=mock_result):
                    result = invoke_cli(cli_runner, branch_group, ["create", "existing"])

        assert_cli_success(result)
        assert_output_contains(result, "already exists")

    def test_create_no_switch(self, cli_runner: CliRunner, mock_dolt_db):
        """Test create with --no-switch flag."""
        mock_result = BranchSyncResult(
            git_branch="feature/no-switch",
            dolt_branch="feature/no-switch",
            created=True,
        )

        with patch("kurt.db.isolation.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake/repo")):
                with patch("kurt.db.isolation.cli.create_both", return_value=mock_result) as mock_create:
                    result = invoke_cli(
                        cli_runner, branch_group, ["create", "feature/no-switch", "--no-switch"]
                    )

        assert_cli_success(result)
        # Verify switch=False was passed
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["switch"] is False

    def test_create_error_handling(self, cli_runner: CliRunner, mock_dolt_db):
        """Test create handles errors gracefully."""
        error = BranchSyncError(
            code=BranchSyncErrorCode.INVALID_BRANCH_NAME,
            message="Invalid branch name",
            details="Use alphanumeric characters only",
        )

        with patch("kurt.db.isolation.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake/repo")):
                with patch("kurt.db.isolation.cli.create_both", side_effect=error):
                    result = invoke_cli(cli_runner, branch_group, ["create", "bad//name"])

        assert result.exit_code != 0
        assert_output_contains(result, "Invalid branch name")


# =============================================================================
# Tests - List Command
# =============================================================================


class TestListCommand:
    """Tests for `branch list` command."""

    def test_list_help(self, cli_runner: CliRunner):
        """Test list command shows help."""
        result = invoke_cli(cli_runner, list_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "List branches with sync status")

    def test_list_shows_options(self, cli_runner: CliRunner):
        """Test list command lists options in help."""
        result = invoke_cli(cli_runner, list_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--json")

    def test_list_table_output(self, cli_runner: CliRunner, mock_dolt_db):
        """Test list shows table output."""
        statuses = [
            BranchStatus(
                branch="main",
                git_commit="abc1234",
                dolt_commit="def5678",
                in_sync=True,
                is_current=True,
                status="clean",
            ),
            BranchStatus(
                branch="feature/test",
                git_commit="xyz9999",
                dolt_commit=None,
                in_sync=False,
                is_current=False,
                status="dolt missing",
            ),
        ]

        with patch("kurt.db.isolation.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake/repo")):
                with patch("kurt.db.isolation.cli.list_branches", return_value=statuses):
                    result = invoke_cli(cli_runner, branch_group, ["list"])

        assert_cli_success(result)
        assert_output_contains(result, "main")
        assert_output_contains(result, "feature/test")
        assert_output_contains(result, "dolt missing")

    def test_list_json_output(self, cli_runner: CliRunner, mock_dolt_db):
        """Test list with --json flag."""
        statuses = [
            BranchStatus(
                branch="main",
                git_commit="abc1234",
                dolt_commit="def5678",
                in_sync=True,
                is_current=True,
                status="clean",
            ),
        ]

        with patch("kurt.db.isolation.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake/repo")):
                with patch("kurt.db.isolation.cli.list_branches", return_value=statuses):
                    result = invoke_cli(cli_runner, branch_group, ["list", "--json"])

        assert_cli_success(result)
        # Should contain JSON structure
        assert '"branch": "main"' in result.output
        assert '"in_sync": true' in result.output

    def test_list_empty(self, cli_runner: CliRunner, mock_dolt_db):
        """Test list with no branches."""
        with patch("kurt.db.isolation.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake/repo")):
                with patch("kurt.db.isolation.cli.list_branches", return_value=[]):
                    result = invoke_cli(cli_runner, branch_group, ["list"])

        assert_cli_success(result)
        assert_output_contains(result, "No branches found")


# =============================================================================
# Tests - Switch Command
# =============================================================================


class TestSwitchCommand:
    """Tests for `branch switch` command."""

    def test_switch_help(self, cli_runner: CliRunner):
        """Test switch command shows help."""
        result = invoke_cli(cli_runner, switch_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Switch to a branch in both Git and Dolt")

    def test_switch_shows_options(self, cli_runner: CliRunner):
        """Test switch command lists options in help."""
        result = invoke_cli(cli_runner, switch_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--force")

    def test_switch_success(self, cli_runner: CliRunner, mock_dolt_db):
        """Test successful branch switch."""
        mock_result = BranchSyncResult(
            git_branch="feature/test",
            dolt_branch="feature/test",
            created=False,
        )

        with patch("kurt.db.isolation.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake/repo")):
                with patch("kurt.db.isolation.cli.switch_both", return_value=mock_result):
                    result = invoke_cli(cli_runner, branch_group, ["switch", "feature/test"])

        assert_cli_success(result)
        assert_output_contains(result, "Switched to branch 'feature/test'")

    def test_switch_creates_missing(self, cli_runner: CliRunner, mock_dolt_db):
        """Test switch creates missing branch in one system."""
        mock_result = BranchSyncResult(
            git_branch="feature/test",
            dolt_branch="feature/test",
            created=True,
        )

        with patch("kurt.db.isolation.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake/repo")):
                with patch("kurt.db.isolation.cli.switch_both", return_value=mock_result):
                    result = invoke_cli(cli_runner, branch_group, ["switch", "feature/test"])

        assert_cli_success(result)
        assert_output_contains(result, "Created missing branch")

    def test_switch_force(self, cli_runner: CliRunner, mock_dolt_db):
        """Test switch with --force flag."""
        mock_result = BranchSyncResult(
            git_branch="main",
            dolt_branch="main",
            created=False,
        )

        with patch("kurt.db.isolation.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake/repo")):
                with patch("kurt.db.isolation.cli.switch_both", return_value=mock_result) as mock_switch:
                    result = invoke_cli(cli_runner, branch_group, ["switch", "main", "--force"])

        assert_cli_success(result)
        mock_switch.assert_called_once()
        call_kwargs = mock_switch.call_args[1]
        assert call_kwargs["force"] is True

    def test_switch_error_handling(self, cli_runner: CliRunner, mock_dolt_db):
        """Test switch handles errors gracefully."""
        error = BranchSyncError(
            code=BranchSyncErrorCode.BRANCH_CHECKOUT_FAILED,
            message="Branch does not exist",
            details="Use 'kurt branch create' to create a new branch.",
        )

        with patch("kurt.db.isolation.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake/repo")):
                with patch("kurt.db.isolation.cli.switch_both", side_effect=error):
                    result = invoke_cli(cli_runner, branch_group, ["switch", "nonexistent"])

        assert result.exit_code != 0
        assert_output_contains(result, "Branch does not exist")


# =============================================================================
# Tests - Delete Command
# =============================================================================


class TestDeleteCommand:
    """Tests for `branch delete` command."""

    def test_delete_help(self, cli_runner: CliRunner):
        """Test delete command shows help."""
        result = invoke_cli(cli_runner, delete_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Delete a branch from both Git and Dolt")

    def test_delete_shows_options(self, cli_runner: CliRunner):
        """Test delete command lists options in help."""
        result = invoke_cli(cli_runner, delete_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--force")
        assert_output_contains(result, "--yes")

    def test_delete_requires_confirmation(self, cli_runner: CliRunner, mock_dolt_db):
        """Test delete asks for confirmation."""
        with patch("kurt.db.isolation.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake/repo")):
                # Simulate user saying "n" to confirmation
                result = cli_runner.invoke(
                    branch_group, ["delete", "feature/test"], input="n\n"
                )

        # Should abort without error
        assert_output_contains(result, "Aborted")

    def test_delete_with_yes_flag(self, cli_runner: CliRunner, mock_dolt_db):
        """Test delete with --yes flag skips confirmation."""
        mock_result = BranchSyncResult(
            git_branch="feature/test",
            dolt_branch="feature/test",
            created=False,
        )

        with patch("kurt.db.isolation.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake/repo")):
                with patch("kurt.db.isolation.cli.delete_both", return_value=mock_result):
                    result = invoke_cli(
                        cli_runner, branch_group, ["delete", "feature/test", "--yes"]
                    )

        assert_cli_success(result)
        assert_output_contains(result, "Deleted branch 'feature/test'")

    def test_delete_main_requires_force(self, cli_runner: CliRunner, mock_dolt_db):
        """Test deleting main branch requires --force --yes."""
        with patch("kurt.db.isolation.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake/repo")):
                result = invoke_cli(cli_runner, branch_group, ["delete", "main"])

        assert result.exit_code != 0
        assert_output_contains(result, "Cannot delete 'main' branch")

    def test_delete_error_handling(self, cli_runner: CliRunner, mock_dolt_db):
        """Test delete handles errors gracefully."""
        error = BranchSyncError(
            code=BranchSyncErrorCode.BRANCH_CHECKOUT_FAILED,
            message="Cannot delete current branch",
            details="Switch to a different branch first.",
        )

        with patch("kurt.db.isolation.cli._get_dolt_db", return_value=mock_dolt_db):
            with patch("kurt.db.isolation.cli._get_git_path", return_value=Path("/fake/repo")):
                with patch("kurt.db.isolation.cli.delete_both", side_effect=error):
                    result = invoke_cli(
                        cli_runner, branch_group, ["delete", "current-branch", "--yes"]
                    )

        assert result.exit_code != 0
        assert_output_contains(result, "Cannot delete current branch")
