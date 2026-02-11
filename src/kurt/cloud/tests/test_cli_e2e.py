"""
E2E tests for `kurt cloud` command.

These tests verify the cloud CLI commands work correctly.
Tests mock external API calls while testing the full CLI integration.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from kurt.cloud.cli import (
    cloud_group,
    cloud_help_cmd,
    login_cmd,
    logout_cmd,
    status_cmd,
    whoami_cmd,
)
from kurt.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)


class TestCloudHelp:
    """Tests for cloud command help and options."""

    def test_cloud_group_help(self, cli_runner: CliRunner):
        """Verify cloud group shows help."""
        result = invoke_cli(cli_runner, cloud_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Kurt Cloud operations")

    def test_cloud_login_help(self, cli_runner: CliRunner):
        """Verify cloud login shows help."""
        result = invoke_cli(cli_runner, login_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Login")

    def test_cloud_logout_help(self, cli_runner: CliRunner):
        """Verify cloud logout shows help."""
        result = invoke_cli(cli_runner, logout_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Logout")

    def test_cloud_status_help(self, cli_runner: CliRunner):
        """Verify cloud status shows help."""
        result = invoke_cli(cli_runner, status_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "status")

    def test_cloud_whoami_help(self, cli_runner: CliRunner):
        """Verify cloud whoami shows help."""
        result = invoke_cli(cli_runner, whoami_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "user info")

    def test_cloud_help_command(self, cli_runner: CliRunner):
        """Verify cloud help shows setup instructions."""
        result = invoke_cli(cli_runner, cloud_help_cmd, [])
        assert_cli_success(result)
        # Should contain cloud setup info
        assert "CLOUD" in result.output.upper() or "SETUP" in result.output.upper()


class TestCloudStatus:
    """E2E tests for cloud status command."""

    def test_status_not_logged_in(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify status shows not logged in when no credentials."""
        with patch("kurt.cloud.auth.load_credentials", return_value=None):
            with patch("kurt.cloud.auth.ensure_fresh_token", return_value=None):
                result = invoke_cli(cli_runner, status_cmd, [])

        assert result.exit_code == 0
        assert "Not logged in" in result.output or "not logged" in result.output.lower()

    def test_status_shows_workspace_info(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify status shows workspace when configured."""
        mock_creds = MagicMock()
        mock_creds.email = "test@example.com"
        mock_creds.user_id = "user-123"
        mock_creds.is_expired.return_value = False

        with patch("kurt.cloud.auth.load_credentials", return_value=mock_creds):
            with patch("kurt.cloud.auth.ensure_fresh_token", return_value=mock_creds):
                with patch("kurt.config.config_file_exists", return_value=True):
                    mock_config = MagicMock()
                    mock_config.WORKSPACE_ID = "ws-123"
                    mock_config.DATABASE_URL = None
                    with patch("kurt.config.load_config", return_value=mock_config):
                        with patch("kurt.db.get_mode", return_value="sqlite"):
                            result = invoke_cli(cli_runner, status_cmd, [])

        assert result.exit_code == 0
        # Should show authenticated status
        assert "Authenticated" in result.output or "test@example.com" in result.output


class TestCloudLogout:
    """E2E tests for cloud logout command."""

    def test_logout_not_logged_in(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify logout handles not logged in state."""
        with patch("kurt.cloud.auth.load_credentials", return_value=None):
            result = invoke_cli(cli_runner, logout_cmd, [])

        assert result.exit_code == 0
        assert "Not logged in" in result.output

    def test_logout_success(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify logout clears credentials."""
        mock_creds = MagicMock()
        mock_creds.email = "test@example.com"

        with patch("kurt.cloud.auth.load_credentials", return_value=mock_creds):
            with patch("kurt.cloud.auth.clear_credentials") as mock_clear:
                result = invoke_cli(cli_runner, logout_cmd, [])

        assert result.exit_code == 0
        mock_clear.assert_called_once()
        assert "Logged out" in result.output


class TestCloudWhoami:
    """E2E tests for cloud whoami command."""

    def test_whoami_not_logged_in(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify whoami handles not logged in state."""
        with patch("kurt.cloud.auth.load_credentials", return_value=None):
            result = invoke_cli(cli_runner, whoami_cmd, [])

        assert result.exit_code != 0
        assert "Not logged in" in result.output

    def test_whoami_shows_user_info(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify whoami shows user information."""
        mock_creds = MagicMock()
        mock_creds.access_token = "test-token"
        mock_creds.email = "test@example.com"
        mock_creds.user_id = "user-123"

        mock_user_info = {
            "user_id": "user-123",
            "email": "test@example.com",
        }

        with patch("kurt.cloud.auth.load_credentials", return_value=mock_creds):
            with patch("kurt.cloud.auth.ensure_fresh_token", return_value=mock_creds):
                with patch("kurt.cloud.auth.get_user_info", return_value=mock_user_info):
                    result = invoke_cli(cli_runner, whoami_cmd, [])

        assert result.exit_code == 0
        assert "user-123" in result.output
        assert "test@example.com" in result.output


class TestCloudLogin:
    """E2E tests for cloud login command."""

    def test_login_help_shows_browser_info(self, cli_runner: CliRunner):
        """Verify login help mentions browser authentication."""
        result = invoke_cli(cli_runner, login_cmd, ["--help"])
        assert_cli_success(result)
        assert "browser" in result.output.lower()


class TestCloudWorkspaceCommands:
    """E2E tests for cloud workspace commands (hidden)."""

    def test_cloud_group_has_workspace_create(self, cli_runner: CliRunner):
        """Verify workspace-create command exists."""
        from kurt.cloud.cli import workspace_create_cmd

        result = invoke_cli(cli_runner, workspace_create_cmd, ["--help"])
        assert_cli_success(result)
        assert "Create a new workspace" in result.output

    def test_workspace_create_requires_github_repo(self, cli_runner: CliRunner):
        """Verify workspace-create requires --github-repo."""
        from kurt.cloud.cli import workspace_create_cmd

        result = cli_runner.invoke(workspace_create_cmd, ["My Project"])
        # Should fail because --github-repo is required
        assert result.exit_code != 0


class TestCloudMemberCommands:
    """E2E tests for cloud member commands (hidden)."""

    def test_invite_help(self, cli_runner: CliRunner):
        """Verify invite command help."""
        from kurt.cloud.cli import invite_cmd

        result = invoke_cli(cli_runner, invite_cmd, ["--help"])
        assert_cli_success(result)
        assert "Invite" in result.output

    def test_invite_shows_options(self, cli_runner: CliRunner):
        """Verify invite command lists options."""
        from kurt.cloud.cli import invite_cmd

        result = invoke_cli(cli_runner, invite_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--role")


class TestCloudIntegration:
    """Integration tests for cloud commands."""

    def test_cloud_status_without_config(self, cli_runner: CliRunner):
        """Verify status handles missing config file."""
        with patch("kurt.cloud.auth.load_credentials", return_value=None):
            with patch("kurt.cloud.auth.ensure_fresh_token", return_value=None):
                with patch("kurt.config.config_file_exists", return_value=False):
                    result = invoke_cli(cli_runner, status_cmd, [])

        assert result.exit_code == 0
        # Should mention no config or not logged in
        output_lower = result.output.lower()
        assert "no kurt.config" in output_lower or "not logged in" in output_lower

    def test_cloud_status_with_expired_token(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify status handles expired token."""
        mock_creds = MagicMock()
        mock_creds.email = "test@example.com"
        mock_creds.user_id = "user-123"
        mock_creds.is_expired.return_value = True

        with patch("kurt.cloud.auth.load_credentials", return_value=mock_creds):
            with patch("kurt.cloud.auth.ensure_fresh_token", return_value=mock_creds):
                with patch("kurt.config.config_file_exists", return_value=True):
                    mock_config = MagicMock()
                    mock_config.WORKSPACE_ID = "ws-123"
                    mock_config.DATABASE_URL = None
                    with patch("kurt.config.load_config", return_value=mock_config):
                        with patch("kurt.db.get_mode", return_value="sqlite"):
                            result = invoke_cli(cli_runner, status_cmd, [])

        assert result.exit_code == 0
        # Should still show status
