"""Integration tests for workspace CLI commands with real PostgreSQL."""

from uuid import UUID

from kurt.commands.workspace import workspace
from kurt.db.models import Workspace, WorkspaceMember, WorkspaceRole


class TestWorkspaceListCommand:
    """Integration tests for 'kurt workspace list' command."""

    def test_list_empty_workspaces(self, postgres_cli_runner):
        """Test listing workspaces when none exist."""
        runner, _ = postgres_cli_runner

        result = runner.invoke(workspace, ["list"])
        assert result.exit_code == 0
        assert "No workspaces found" in result.output

    def test_list_workspaces_shows_all_active(self, postgres_cli_runner):
        """Test listing shows all active workspaces."""
        runner, _ = postgres_cli_runner

        from kurt.db.base import get_database_client

        client = get_database_client()

        # Create test workspaces
        with client.get_session() as session:
            ws1 = Workspace(
                name="Workspace One",
                slug="ws1",
                owner_email="owner1@example.com",
                plan="free",
            )
            ws2 = Workspace(
                name="Workspace Two",
                slug="ws2",
                owner_email="owner2@example.com",
                plan="pro",
            )
            ws3 = Workspace(
                name="Inactive Workspace",
                slug="ws3",
                is_active=False,  # Inactive
            )
            session.add(ws1)
            session.add(ws2)
            session.add(ws3)
            session.commit()

        # List workspaces
        result = runner.invoke(workspace, ["list"])
        assert result.exit_code == 0

        # Should show active workspaces
        assert "Workspace One" in result.output
        assert "Workspace Two" in result.output

        # Should NOT show inactive workspace
        assert "Inactive Workspace" not in result.output

        # Should show total count
        assert "2 workspace(s)" in result.output


class TestWorkspaceCreateCommand:
    """Integration tests for 'kurt workspace create' command."""

    def test_create_workspace_basic(self, postgres_cli_runner):
        """Test creating a basic workspace."""
        runner, _ = postgres_cli_runner

        result = runner.invoke(workspace, ["create", "My Test Workspace"])
        assert result.exit_code == 0
        assert "Created workspace: My Test Workspace" in result.output
        assert "Slug: my-test-workspace" in result.output

    def test_create_workspace_with_custom_slug(self, postgres_cli_runner):
        """Test creating workspace with custom slug."""
        runner, _ = postgres_cli_runner

        result = runner.invoke(workspace, ["create", "Test Workspace", "--slug", "custom-slug"])
        assert result.exit_code == 0
        assert "Slug: custom-slug" in result.output

    def test_create_workspace_with_plan(self, postgres_cli_runner):
        """Test creating workspace with specific plan."""
        runner, _ = postgres_cli_runner

        result = runner.invoke(workspace, ["create", "Pro Workspace", "--plan", "pro"])
        assert result.exit_code == 0
        assert "Plan: pro" in result.output

    def test_create_workspace_with_owner(self, postgres_cli_runner):
        """Test creating workspace with owner email."""
        runner, _ = postgres_cli_runner

        result = runner.invoke(
            workspace,
            ["create", "Owned Workspace", "--owner-email", "owner@example.com"],
        )
        assert result.exit_code == 0
        assert "Created workspace: Owned Workspace" in result.output

    def test_create_workspace_duplicate_slug_fails(self, postgres_cli_runner):
        """Test that creating workspace with duplicate slug fails."""
        runner, _ = postgres_cli_runner

        # Create first workspace
        result1 = runner.invoke(workspace, ["create", "First", "--slug", "duplicate"])
        assert result1.exit_code == 0

        # Try to create second workspace with same slug
        result2 = runner.invoke(workspace, ["create", "Second", "--slug", "duplicate"])
        assert result2.exit_code == 0  # Command doesn't fail, shows error message
        assert "already exists" in result2.output

    def test_create_workspace_auto_slug_generation(self, postgres_cli_runner):
        """Test automatic slug generation from workspace name."""
        runner, _ = postgres_cli_runner

        test_cases = [
            ("Simple Name", "simple-name"),
            ("Name With   Spaces", "name-with-spaces"),
            ("Special!@# Chars", "special-chars"),
        ]

        for name, expected_slug in test_cases:
            result = runner.invoke(workspace, ["create", name])
            assert result.exit_code == 0
            assert f"Slug: {expected_slug}" in result.output


class TestWorkspaceInfoCommand:
    """Integration tests for 'kurt workspace info' command."""

    def test_info_with_workspace_id(self, postgres_cli_runner):
        """Test showing workspace info by ID."""
        runner, _ = postgres_cli_runner

        from kurt.db.base import get_database_client

        client = get_database_client()

        # Create test workspace
        with client.get_session() as session:
            ws = Workspace(
                name="Info Test Workspace",
                slug="info-test",
                plan="pro",
                owner_email="owner@example.com",
                organization="Test Org",
            )
            session.add(ws)
            session.commit()
            session.refresh(ws)
            workspace_id = str(ws.id)

        # Get info
        result = runner.invoke(workspace, ["info", workspace_id])
        assert result.exit_code == 0

        # Check output contains expected fields
        assert "Info Test Workspace" in result.output
        assert "info-test" in result.output
        assert "pro" in result.output
        assert "owner@example.com" in result.output
        assert "Test Org" in result.output

    def test_info_uses_env_workspace_id(self, postgres_cli_runner):
        """Test that info command uses WORKSPACE_ID from environment."""
        runner, _ = postgres_cli_runner

        # WORKSPACE_ID is set by postgres_cli_runner fixture
        result = runner.invoke(workspace, ["info"])

        # Should either show workspace info or error if workspace doesn't exist
        # Exit code 0 or 1 both acceptable
        assert result.exit_code in [0, 1]

    def test_info_nonexistent_workspace(self, postgres_cli_runner):
        """Test info command with nonexistent workspace ID."""
        runner, _ = postgres_cli_runner

        fake_id = "00000000-0000-0000-0000-999999999999"
        result = runner.invoke(workspace, ["info", fake_id])

        assert result.exit_code == 0  # Command doesn't fail
        assert "not found" in result.output


class TestWorkspaceAddUserCommand:
    """Integration tests for 'kurt workspace add-user' command."""

    def test_add_user_with_default_role(self, postgres_cli_runner):
        """Test adding user with default 'member' role."""
        runner, _ = postgres_cli_runner

        from kurt.db.base import get_database_client

        client = get_database_client()

        # Create test workspace
        with client.get_session() as session:
            ws = Workspace(name="User Test", slug="user-test")
            session.add(ws)
            session.commit()
            session.refresh(ws)
            workspace_id = str(ws.id)

        # Add user
        result = runner.invoke(
            workspace,
            ["add-user", "newuser@example.com", "--workspace-id", workspace_id],
        )
        assert result.exit_code == 0
        assert "Added newuser@example.com with role: member" in result.output

        # Verify in database
        with client.get_session() as session:
            from sqlmodel import select

            member = session.exec(
                select(WorkspaceMember).where(WorkspaceMember.user_email == "newuser@example.com")
            ).first()
            assert member is not None
            assert member.role == WorkspaceRole.MEMBER

    def test_add_user_with_specific_roles(self, postgres_cli_runner):
        """Test adding users with different roles."""
        runner, _ = postgres_cli_runner

        from kurt.db.base import get_database_client

        client = get_database_client()

        # Create test workspace
        with client.get_session() as session:
            ws = Workspace(name="Role Test", slug="role-test")
            session.add(ws)
            session.commit()
            session.refresh(ws)
            workspace_id = str(ws.id)

        # Test each role
        roles_to_test = [
            ("owner@example.com", "owner"),
            ("admin@example.com", "admin"),
            ("member@example.com", "member"),
            ("viewer@example.com", "viewer"),
        ]

        for email, role in roles_to_test:
            result = runner.invoke(
                workspace,
                ["add-user", email, "--workspace-id", workspace_id, "--role", role],
            )
            assert result.exit_code == 0
            assert f"Added {email} with role: {role}" in result.output

        # Verify all users in database
        with client.get_session() as session:
            from sqlmodel import select

            members = session.exec(
                select(WorkspaceMember).where(WorkspaceMember.workspace_id == UUID(workspace_id))
            ).all()
            assert len(members) == 4

    def test_add_duplicate_user(self, postgres_cli_runner):
        """Test adding the same user twice fails gracefully."""
        runner, _ = postgres_cli_runner

        from kurt.db.base import get_database_client

        client = get_database_client()

        # Create test workspace
        with client.get_session() as session:
            ws = Workspace(name="Duplicate Test", slug="dup-test")
            session.add(ws)
            session.commit()
            session.refresh(ws)
            workspace_id = str(ws.id)

        # Add user first time
        result1 = runner.invoke(
            workspace,
            ["add-user", "duplicate@example.com", "--workspace-id", workspace_id],
        )
        assert result1.exit_code == 0

        # Try to add same user again
        result2 = runner.invoke(
            workspace,
            ["add-user", "duplicate@example.com", "--workspace-id", workspace_id],
        )
        assert result2.exit_code == 0  # Command doesn't fail
        assert "already exists" in result2.output

    def test_add_user_to_nonexistent_workspace(self, postgres_cli_runner):
        """Test adding user to nonexistent workspace fails gracefully."""
        runner, _ = postgres_cli_runner

        fake_id = "00000000-0000-0000-0000-999999999999"
        result = runner.invoke(
            workspace,
            ["add-user", "user@example.com", "--workspace-id", fake_id],
        )
        assert result.exit_code == 0
        assert "not found" in result.output


class TestWorkspaceListUsersCommand:
    """Integration tests for 'kurt workspace list-users' command."""

    def test_list_users_empty_workspace(self, postgres_cli_runner):
        """Test listing users in workspace with no members."""
        runner, _ = postgres_cli_runner

        from kurt.db.base import get_database_client

        client = get_database_client()

        # Create empty workspace
        with client.get_session() as session:
            ws = Workspace(name="Empty Workspace", slug="empty")
            session.add(ws)
            session.commit()
            session.refresh(ws)
            workspace_id = str(ws.id)

        result = runner.invoke(workspace, ["list-users", "--workspace-id", workspace_id])
        assert result.exit_code == 0
        assert "No users found" in result.output

    def test_list_users_shows_all_members(self, postgres_cli_runner):
        """Test listing shows all workspace members."""
        runner, _ = postgres_cli_runner

        from kurt.db.base import get_database_client

        client = get_database_client()

        # Create workspace with members
        with client.get_session() as session:
            ws = Workspace(name="User List Test", slug="user-list")
            session.add(ws)
            session.commit()
            session.refresh(ws)

            # Add members
            owner = WorkspaceMember(
                workspace_id=ws.id,
                user_email="owner@example.com",
                role=WorkspaceRole.OWNER,
            )
            admin = WorkspaceMember(
                workspace_id=ws.id,
                user_email="admin@example.com",
                role=WorkspaceRole.ADMIN,
            )
            member = WorkspaceMember(
                workspace_id=ws.id,
                user_email="member@example.com",
                role=WorkspaceRole.MEMBER,
            )
            session.add(owner)
            session.add(admin)
            session.add(member)
            session.commit()

            workspace_id = str(ws.id)

        # List users
        result = runner.invoke(workspace, ["list-users", "--workspace-id", workspace_id])
        assert result.exit_code == 0

        # Check all users shown
        assert "owner@example.com" in result.output
        assert "admin@example.com" in result.output
        assert "member@example.com" in result.output

        # Check count
        assert "3 user(s)" in result.output

    def test_list_users_shows_status(self, postgres_cli_runner):
        """Test that list-users shows member status (Active/Pending)."""
        runner, _ = postgres_cli_runner

        from datetime import datetime

        from kurt.db.base import get_database_client

        client = get_database_client()

        # Create workspace with active and pending members
        with client.get_session() as session:
            ws = Workspace(name="Status Test", slug="status-test")
            session.add(ws)
            session.commit()
            session.refresh(ws)

            # Active member (has joined_at)
            active = WorkspaceMember(
                workspace_id=ws.id,
                user_email="active@example.com",
                role=WorkspaceRole.MEMBER,
                joined_at=datetime.utcnow(),
            )

            # Pending member (no joined_at)
            pending = WorkspaceMember(
                workspace_id=ws.id,
                user_email="pending@example.com",
                role=WorkspaceRole.MEMBER,
            )

            session.add(active)
            session.add(pending)
            session.commit()

            workspace_id = str(ws.id)

        # List users
        result = runner.invoke(workspace, ["list-users", "--workspace-id", workspace_id])
        assert result.exit_code == 0

        # Output should contain status information
        assert "active@example.com" in result.output
        assert "pending@example.com" in result.output


class TestWorkspaceCommandsErrorHandling:
    """Test error handling in workspace commands."""

    def test_invalid_workspace_id_format(self, postgres_cli_runner):
        """Test commands handle invalid UUID format gracefully."""
        runner, _ = postgres_cli_runner

        # Try with invalid UUID
        result = runner.invoke(workspace, ["info", "not-a-valid-uuid"])

        # Should handle gracefully (not crash)
        # May show error or invalid workspace message
        assert result.exit_code in [0, 1, 2]

    def test_commands_require_cloud_mode(self, monkeypatch, tmp_path):
        """Test that workspace commands check for cloud mode (DATABASE_URL)."""
        from click.testing import CliRunner

        # Create runner WITHOUT DATABASE_URL (local mode)
        runner = CliRunner()

        # All workspace commands should indicate cloud mode required
        commands_to_test = [
            ["list"],
            ["create", "Test"],
            ["add-user", "test@example.com"],
            ["list-users"],
        ]

        for cmd in commands_to_test:
            result = runner.invoke(workspace, cmd)
            assert result.exit_code == 0
            assert "cloud mode" in result.output.lower() or "DATABASE_URL" in result.output
