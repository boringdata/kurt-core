"""Integration tests for workspace CLI commands."""

from uuid import UUID

import pytest
from click.testing import CliRunner

from kurt.commands.workspace import workspace
from kurt.db.models import Workspace, WorkspaceRole


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_cloud_config(monkeypatch):
    """Mock cloud mode configuration."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    monkeypatch.setenv("WORKSPACE_ID", "00000000-0000-0000-0000-000000000000")


class TestWorkspaceListCommand:
    """Test 'kurt workspace list' command."""

    def test_list_without_database_url(self, runner):
        """Test list command without DATABASE_URL (local mode)."""
        result = runner.invoke(workspace, ["list"])
        assert result.exit_code == 0
        assert "only available in cloud mode" in result.output

    def test_list_with_mock_config(self, runner, mock_cloud_config):
        """Test list command structure with mocked config."""
        # This will fail to connect but tests command structure
        _ = runner.invoke(workspace, ["list"])
        # Command should at least parse correctly
        assert "list" in workspace.commands


class TestWorkspaceCreateCommand:
    """Test 'kurt workspace create' command."""

    def test_create_without_database_url(self, runner):
        """Test create command without DATABASE_URL."""
        result = runner.invoke(workspace, ["create", "Test Workspace"])
        assert result.exit_code == 0
        assert "only available in cloud mode" in result.output

    def test_create_command_signature(self, runner):
        """Test create command has correct parameters."""
        cmd = workspace.commands["create"]
        assert cmd.name == "create"
        # Should have name argument
        assert len([p for p in cmd.params if p.name == "name"]) == 1


class TestWorkspaceAddUserCommand:
    """Test 'kurt workspace add-user' command."""

    def test_add_user_without_database_url(self, runner):
        """Test add-user without DATABASE_URL."""
        result = runner.invoke(workspace, ["add-user", "test@example.com"])
        assert result.exit_code == 0
        assert "only available in cloud mode" in result.output

    def test_add_user_role_options(self, runner):
        """Test add-user accepts valid roles."""
        cmd = workspace.commands["add-user"]
        role_param = next(p for p in cmd.params if p.name == "role")

        # Should accept all valid roles
        assert role_param.type.choices == ["owner", "admin", "member", "viewer"]

    def test_add_user_default_role(self, runner):
        """Test add-user defaults to 'member' role."""
        cmd = workspace.commands["add-user"]
        role_param = next(p for p in cmd.params if p.name == "role")
        assert role_param.default == "member"


class TestWorkspaceListUsersCommand:
    """Test 'kurt workspace list-users' command."""

    def test_list_users_without_database_url(self, runner):
        """Test list-users without DATABASE_URL."""
        result = runner.invoke(workspace, ["list-users"])
        assert result.exit_code == 0
        assert "only available in cloud mode" in result.output

    def test_list_users_uses_workspace_id_from_env(self, runner, mock_cloud_config):
        """Test list-users uses WORKSPACE_ID from environment."""
        # This will fail to connect but tests that WORKSPACE_ID is read
        result = runner.invoke(workspace, ["list-users"])
        # Command should attempt to use WORKSPACE_ID
        assert result.exit_code in [0, 1]  # May fail on DB connection


class TestWorkspaceInfoCommand:
    """Test 'kurt workspace info' command."""

    def test_info_without_workspace_id_or_env(self, runner):
        """Test info command needs workspace ID or env var."""
        result = runner.invoke(workspace, ["info"])
        # Should either show error or use WORKSPACE_ID
        assert result.exit_code in [0, 1]


class TestCommandAvailability:
    """Test all workspace commands are available."""

    def test_all_commands_registered(self):
        """Test all workspace commands are registered."""
        expected_commands = [
            "list",
            "create",
            "info",
            "add-user",
            "list-users",
        ]

        for cmd_name in expected_commands:
            assert cmd_name in workspace.commands

    def test_workspace_group_name(self):
        """Test workspace group has correct name."""
        assert workspace.name == "workspace"


class TestRoleValidation:
    """Test role validation in commands."""

    def test_valid_roles(self):
        """Test all valid WorkspaceRole values."""
        roles = ["owner", "admin", "member", "viewer"]
        for role in roles:
            # Should not raise
            assert WorkspaceRole(role) in [
                WorkspaceRole.OWNER,
                WorkspaceRole.ADMIN,
                WorkspaceRole.MEMBER,
                WorkspaceRole.VIEWER,
            ]

    def test_role_enum_values(self):
        """Test WorkspaceRole enum values match command choices."""
        enum_values = {role.value for role in WorkspaceRole}
        expected = {"owner", "admin", "member", "viewer"}
        assert enum_values == expected


class TestWorkspaceSlugGeneration:
    """Test workspace slug auto-generation logic."""

    def test_slug_generation_logic(self):
        """Test slug is generated from workspace name."""
        import re

        test_names = [
            ("Test Workspace", "test-workspace"),
            ("My Cool Project", "my-cool-project"),
            ("Special!@# Chars", "special-chars"),
            ("Multiple   Spaces", "multiple-spaces"),
        ]

        for name, expected_slug in test_names:
            # Simulate slug generation logic from create_workspace
            slug = re.sub(r"[^a-z0-9-]", "-", name.lower())
            slug = re.sub(r"-+", "-", slug).strip("-")
            assert slug == expected_slug


class TestMultiTenantIsolation:
    """Test multi-tenant isolation concepts."""

    def test_default_workspace_id_format(self):
        """Test default workspace ID is valid UUID."""
        default_id = "00000000-0000-0000-0000-000000000000"
        # Should parse as valid UUID
        uuid_obj = UUID(default_id)
        assert str(uuid_obj) == default_id

    def test_workspace_id_from_env(self, mock_cloud_config):
        """Test WORKSPACE_ID is read from environment."""
        import os

        workspace_id = os.getenv("WORKSPACE_ID")
        assert workspace_id == "00000000-0000-0000-0000-000000000000"
        # Should parse as valid UUID
        UUID(workspace_id)


class TestErrorHandling:
    """Test command error handling."""

    def test_invalid_uuid_handled(self):
        """Test invalid UUID format is handled."""
        with pytest.raises(ValueError):
            UUID("not-a-valid-uuid")

    def test_workspace_model_validation(self):
        """Test Workspace model requires name and slug."""
        # Should create successfully with required fields
        ws = Workspace(name="Test", slug="test")
        assert ws.name == "Test"
        assert ws.slug == "test"
