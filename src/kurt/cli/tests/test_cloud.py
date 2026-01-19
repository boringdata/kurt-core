"""Tests for kurt cloud CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kurt.cli.cloud import cloud_group


@pytest.fixture
def cli_runner():
    """Create CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_credentials():
    """Create mock credentials."""
    from kurt.cli.auth.credentials import Credentials

    return Credentials(
        access_token="test-token-123",
        refresh_token="test-refresh-456",
        user_id="user-789",
        email="test@example.com",
        workspace_id="ws-abc",
        expires_at=9999999999,  # Far future
    )


@pytest.fixture
def tmp_config(tmp_path: Path):
    """Create temporary kurt.config file."""
    config_file = tmp_path / "kurt.config"
    config_file.write_text('WORKSPACE_ID="ws-test-123"\nOPENAI_API_KEY="sk-test"\n')
    return config_file


# =============================================================================
# Cloud Group Help
# =============================================================================


class TestCloudGroupHelp:
    """Tests for cloud command group."""

    def test_cloud_group_help(self, cli_runner: CliRunner):
        """Test cloud --help shows available commands."""
        result = cli_runner.invoke(cloud_group, ["--help"])
        assert result.exit_code == 0
        assert "Kurt Cloud operations" in result.output
        assert "login" in result.output
        assert "logout" in result.output
        assert "status" in result.output

    def test_cloud_list_commands(self, cli_runner: CliRunner):
        """Test all expected commands are registered."""
        result = cli_runner.invoke(cloud_group, ["--help"])
        assert result.exit_code == 0
        # Check visible commands are listed (workspaces and members are hidden)
        expected_commands = [
            "login",
            "logout",
            "status",
            "whoami",
            "invite",
            "use",
            "workspace-create",
        ]
        for cmd in expected_commands:
            assert cmd in result.output, f"Command '{cmd}' not found in help"


# =============================================================================
# Login Command
# =============================================================================


class TestLoginCommand:
    """Tests for kurt cloud login command."""

    def test_login_help(self, cli_runner: CliRunner):
        """Test login --help."""
        result = cli_runner.invoke(cloud_group, ["login", "--help"])
        assert result.exit_code == 0
        assert "Login to Kurt Cloud" in result.output


# =============================================================================
# Logout Command
# =============================================================================


class TestLogoutCommand:
    """Tests for kurt cloud logout command."""

    def test_logout_help(self, cli_runner: CliRunner):
        """Test logout --help."""
        result = cli_runner.invoke(cloud_group, ["logout", "--help"])
        assert result.exit_code == 0
        assert "Logout from Kurt Cloud" in result.output

    def test_logout_when_not_logged_in(self, cli_runner: CliRunner):
        """Test logout when no credentials exist."""
        with patch("kurt.cli.auth.credentials.load_credentials", return_value=None):
            result = cli_runner.invoke(cloud_group, ["logout"])
        assert result.exit_code == 0
        assert "Not logged in" in result.output

    def test_logout_clears_credentials(self, cli_runner: CliRunner, mock_credentials):
        """Test logout clears stored credentials."""
        with (
            patch("kurt.cli.auth.credentials.load_credentials", return_value=mock_credentials),
            patch("kurt.cli.auth.credentials.clear_credentials") as mock_clear,
        ):
            result = cli_runner.invoke(cloud_group, ["logout"])
        assert result.exit_code == 0
        assert "Logged out" in result.output
        mock_clear.assert_called_once()


# =============================================================================
# Status Command
# =============================================================================


class TestStatusCommand:
    """Tests for kurt cloud status command."""

    def test_status_help(self, cli_runner: CliRunner):
        """Test status --help."""
        result = cli_runner.invoke(cloud_group, ["status", "--help"])
        assert result.exit_code == 0
        assert "Show authentication and workspace status" in result.output

    def test_status_not_logged_in(self, cli_runner: CliRunner):
        """Test status when not logged in."""
        with (
            patch("kurt.cli.auth.credentials.load_credentials", return_value=None),
            patch("kurt.config.config_file_exists", return_value=False),
        ):
            result = cli_runner.invoke(cloud_group, ["status"])
        assert result.exit_code == 0
        assert "Not logged in" in result.output

    def test_status_logged_in(self, cli_runner: CliRunner, mock_credentials):
        """Test status when logged in."""
        mock_config = MagicMock()
        mock_config.WORKSPACE_ID = "ws-test-123"
        mock_config.DATABASE_URL = None

        with (
            patch("kurt.cli.auth.credentials.load_credentials", return_value=mock_credentials),
            patch("kurt.config.config_file_exists", return_value=True),
            patch("kurt.config.load_config", return_value=mock_config),
            patch("kurt.db.get_mode", return_value="sqlite"),
        ):
            result = cli_runner.invoke(cloud_group, ["status"])
        assert result.exit_code == 0
        assert "Authenticated" in result.output
        assert mock_credentials.email in result.output

    def test_status_auto_fills_workspace_id(self, cli_runner: CliRunner, mock_credentials, tmp_path: Path):
        """Test status auto-fills WORKSPACE_ID when missing."""
        config_file = tmp_path / "kurt.config"
        config_file.write_text('DATABASE_URL="postgresql://localhost/db"\n')

        with (
            patch("kurt.cli.auth.credentials.load_credentials", return_value=mock_credentials),
            patch("kurt.cli.auth.credentials.ensure_fresh_token", return_value=mock_credentials),
            patch("kurt.config.base.get_config_file_path", return_value=config_file),
            patch("kurt.config.get_config_file_path", return_value=config_file),
            patch("kurt.db.get_mode", return_value="postgres"),
        ):
            result = cli_runner.invoke(cloud_group, ["status"])

        assert result.exit_code == 0
        content = config_file.read_text()
        assert f'WORKSPACE_ID="{mock_credentials.workspace_id}"' in content
        assert f"Workspace ID: {mock_credentials.workspace_id}" in result.output


# =============================================================================
# Whoami Command
# =============================================================================


class TestWhoamiCommand:
    """Tests for kurt cloud whoami command."""

    def test_whoami_help(self, cli_runner: CliRunner):
        """Test whoami --help."""
        result = cli_runner.invoke(cloud_group, ["whoami", "--help"])
        assert result.exit_code == 0
        assert "Show current user info" in result.output

    def test_whoami_not_logged_in(self, cli_runner: CliRunner):
        """Test whoami when not logged in."""
        with patch("kurt.cli.auth.credentials.load_credentials", return_value=None):
            result = cli_runner.invoke(cloud_group, ["whoami"])
        assert result.exit_code == 1
        assert "Not logged in" in result.output


# =============================================================================
# Invite Command
# =============================================================================


class TestInviteCommand:
    """Tests for kurt cloud invite command."""

    def test_invite_help(self, cli_runner: CliRunner):
        """Test invite --help."""
        result = cli_runner.invoke(cloud_group, ["invite", "--help"])
        assert result.exit_code == 0
        assert "Invite a user to your workspace" in result.output
        assert "--role" in result.output

    def test_invite_requires_email_argument(self, cli_runner: CliRunner):
        """Test invite requires email argument."""
        result = cli_runner.invoke(cloud_group, ["invite"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output

    def test_invite_not_logged_in(self, cli_runner: CliRunner):
        """Test invite when not logged in."""
        with patch("kurt.cli.auth.credentials.load_credentials", return_value=None):
            result = cli_runner.invoke(cloud_group, ["invite", "user@example.com"])
        assert result.exit_code == 1
        assert "Not logged in" in result.output

    def test_invite_no_config(self, cli_runner: CliRunner, mock_credentials):
        """Test invite when no kurt.config exists."""
        with (
            patch("kurt.cli.auth.credentials.load_credentials", return_value=mock_credentials),
            patch("kurt.config.config_file_exists", return_value=False),
        ):
            result = cli_runner.invoke(cloud_group, ["invite", "user@example.com"])
        assert result.exit_code == 1
        assert "No kurt.config found" in result.output

    def test_invite_no_workspace_id(self, cli_runner: CliRunner, mock_credentials):
        """Test invite when WORKSPACE_ID is not set."""
        mock_config = MagicMock()
        mock_config.WORKSPACE_ID = None

        with (
            patch("kurt.cli.auth.credentials.load_credentials", return_value=mock_credentials),
            patch("kurt.config.config_file_exists", return_value=True),
            patch("kurt.config.load_config", return_value=mock_config),
        ):
            result = cli_runner.invoke(cloud_group, ["invite", "user@example.com"])
        assert result.exit_code == 1
        assert "No WORKSPACE_ID" in result.output


# =============================================================================
# Use Command
# =============================================================================


class TestUseCommand:
    """Tests for kurt cloud use command."""

    def test_use_help(self, cli_runner: CliRunner):
        """Test use --help."""
        result = cli_runner.invoke(cloud_group, ["use", "--help"])
        assert result.exit_code == 0
        assert "Switch to a different workspace" in result.output

    def test_use_requires_workspace_id_argument(self, cli_runner: CliRunner):
        """Test use requires workspace_id argument."""
        result = cli_runner.invoke(cloud_group, ["use"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output

    def test_use_not_logged_in(self, cli_runner: CliRunner):
        """Test use when not logged in."""
        with patch("kurt.cli.auth.credentials.load_credentials", return_value=None):
            result = cli_runner.invoke(cloud_group, ["use", "ws-new-123"])
        assert result.exit_code == 1
        assert "Not logged in" in result.output


# =============================================================================
# Workspaces Command
# =============================================================================


class TestWorkspacesCommand:
    """Tests for kurt cloud workspaces command."""

    def test_workspaces_help(self, cli_runner: CliRunner):
        """Test workspaces --help."""
        result = cli_runner.invoke(cloud_group, ["workspaces", "--help"])
        assert result.exit_code == 0
        assert "List your workspaces" in result.output

    def test_workspaces_not_logged_in(self, cli_runner: CliRunner):
        """Test workspaces when not logged in."""
        with patch("kurt.cli.auth.credentials.load_credentials", return_value=None):
            result = cli_runner.invoke(cloud_group, ["workspaces"])
        assert result.exit_code == 1
        assert "Not logged in" in result.output


# =============================================================================
# Members Command
# =============================================================================


class TestMembersCommand:
    """Tests for kurt cloud members command."""

    def test_members_help(self, cli_runner: CliRunner):
        """Test members --help."""
        result = cli_runner.invoke(cloud_group, ["members", "--help"])
        assert result.exit_code == 0
        assert "List members of the current workspace" in result.output

    def test_members_not_logged_in(self, cli_runner: CliRunner):
        """Test members when not logged in."""
        with patch("kurt.cli.auth.credentials.load_credentials", return_value=None):
            result = cli_runner.invoke(cloud_group, ["members"])
        assert result.exit_code == 1
        assert "Not logged in" in result.output

    def test_members_no_config(self, cli_runner: CliRunner, mock_credentials):
        """Test members when no kurt.config exists."""
        with (
            patch("kurt.cli.auth.credentials.load_credentials", return_value=mock_credentials),
            patch("kurt.config.config_file_exists", return_value=False),
        ):
            result = cli_runner.invoke(cloud_group, ["members"])
        assert result.exit_code == 1
        assert "No kurt.config found" in result.output

    def test_members_no_workspace_id(self, cli_runner: CliRunner, mock_credentials):
        """Test members when WORKSPACE_ID is not set."""
        mock_config = MagicMock()
        mock_config.WORKSPACE_ID = None

        with (
            patch("kurt.cli.auth.credentials.load_credentials", return_value=mock_credentials),
            patch("kurt.config.config_file_exists", return_value=True),
            patch("kurt.config.load_config", return_value=mock_config),
        ):
            result = cli_runner.invoke(cloud_group, ["members"])
        assert result.exit_code == 1
        assert "No WORKSPACE_ID" in result.output


# =============================================================================
# E2E with Mocked API
# =============================================================================


class TestCloudE2EWithMockedAPI:
    """End-to-end tests with mocked Kurt Cloud API."""

    def test_workspaces_shows_list(self, cli_runner: CliRunner, mock_credentials):
        """Test workspaces command shows workspace list from API."""
        mock_config = MagicMock()
        mock_config.WORKSPACE_ID = "ws-current"

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            [
                {"id": "ws-1", "name": "My Workspace", "role": "owner"},
                {"id": "ws-2", "name": "Team Workspace", "role": "member"},
            ]
        ).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch("kurt.cli.auth.credentials.load_credentials", return_value=mock_credentials),
            patch("kurt.config.config_file_exists", return_value=True),
            patch("kurt.config.load_config", return_value=mock_config),
            patch("urllib.request.urlopen", return_value=mock_response),
        ):
            result = cli_runner.invoke(cloud_group, ["workspaces"])

        assert result.exit_code == 0
        assert "My Workspace" in result.output
        assert "Team Workspace" in result.output
        assert "owner" in result.output
        assert "member" in result.output

    def test_members_shows_list(self, cli_runner: CliRunner, mock_credentials):
        """Test members command shows member list from API."""
        mock_config = MagicMock()
        mock_config.WORKSPACE_ID = "ws-test"

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            [
                {"email": "owner@example.com", "role": "owner", "status": "active"},
                {"email": "member@example.com", "role": "member", "status": "pending"},
            ]
        ).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch("kurt.cli.auth.credentials.load_credentials", return_value=mock_credentials),
            patch("kurt.config.config_file_exists", return_value=True),
            patch("kurt.config.load_config", return_value=mock_config),
            patch("urllib.request.urlopen", return_value=mock_response),
        ):
            result = cli_runner.invoke(cloud_group, ["members"])

        assert result.exit_code == 0
        assert "owner@example.com" in result.output
        assert "member@example.com" in result.output
        assert "pending" in result.output

    def test_invite_success(self, cli_runner: CliRunner, mock_credentials):
        """Test invite command sends API request."""
        mock_config = MagicMock()
        mock_config.WORKSPACE_ID = "ws-test"

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "email": "newuser@example.com",
                "role": "member",
                "status": "pending",
            }
        ).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch("kurt.cli.auth.credentials.load_credentials", return_value=mock_credentials),
            patch("kurt.config.config_file_exists", return_value=True),
            patch("kurt.config.load_config", return_value=mock_config),
            patch("urllib.request.urlopen", return_value=mock_response),
        ):
            result = cli_runner.invoke(cloud_group, ["invite", "newuser@example.com"])

        assert result.exit_code == 0
        assert "Invited" in result.output
        assert "newuser@example.com" in result.output

    def test_use_switches_workspace(self, cli_runner: CliRunner, mock_credentials, tmp_path: Path):
        """Test use command switches workspace."""
        # Create temp config file
        config_file = tmp_path / "kurt.config"
        config_file.write_text('WORKSPACE_ID="ws-old"\n')

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "id": "ws-new",
                "name": "New Workspace",
                "role": "member",
            }
        ).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch("kurt.cli.auth.credentials.load_credentials", return_value=mock_credentials),
            patch("kurt.cli.auth.credentials.save_credentials"),
            patch("kurt.config.config_file_exists", return_value=True),
            patch("kurt.config.get_config_file_path", return_value=config_file),
            patch("urllib.request.urlopen", return_value=mock_response),
        ):
            result = cli_runner.invoke(cloud_group, ["use", "ws-new"])

        assert result.exit_code == 0
        assert "Switched to workspace" in result.output
        # Verify config file was updated
        content = config_file.read_text()
        assert 'WORKSPACE_ID="ws-new"' in content
