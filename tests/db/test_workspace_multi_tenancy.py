"""Unit tests for workspace multi-tenancy functionality."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from kurt.db.models import (
    Document,
    Entity,
    SourceType,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)


@pytest.fixture
def workspace():
    """Create a test workspace."""
    return Workspace(
        id=uuid4(),
        name="Test Workspace",
        slug="test-workspace",
        plan="free",
        owner_email="owner@example.com",
        is_active=True,
    )


@pytest.fixture
def workspace_member(workspace):
    """Create a test workspace member."""
    return WorkspaceMember(
        id=uuid4(),
        workspace_id=workspace.id,
        user_email="user@example.com",
        role=WorkspaceRole.MEMBER,
        is_active=True,
    )


class TestWorkspaceModel:
    """Test Workspace model."""

    def test_workspace_creation(self, workspace):
        """Test creating a workspace."""
        assert workspace.name == "Test Workspace"
        assert workspace.slug == "test-workspace"
        assert workspace.plan == "free"
        assert workspace.is_active is True

    def test_workspace_default_values(self):
        """Test workspace default values."""
        ws = Workspace(name="Test", slug="test")
        assert ws.plan == "free"
        assert ws.is_active is True
        assert isinstance(ws.created_at, datetime)
        assert isinstance(ws.updated_at, datetime)

    def test_workspace_optional_fields(self, workspace):
        """Test workspace optional fields."""
        assert workspace.owner_email == "owner@example.com"
        assert workspace.organization is None
        assert workspace.max_documents is None
        assert workspace.max_users is None


class TestWorkspaceMemberModel:
    """Test WorkspaceMember model."""

    def test_member_creation(self, workspace_member):
        """Test creating a workspace member."""
        assert workspace_member.user_email == "user@example.com"
        assert workspace_member.role == WorkspaceRole.MEMBER
        assert workspace_member.is_active is True

    def test_member_roles(self, workspace):
        """Test all workspace roles."""
        roles = [
            WorkspaceRole.OWNER,
            WorkspaceRole.ADMIN,
            WorkspaceRole.MEMBER,
            WorkspaceRole.VIEWER,
        ]

        for role in roles:
            member = WorkspaceMember(
                workspace_id=workspace.id,
                user_email=f"{role.value}@example.com",
                role=role,
            )
            assert member.role == role
            assert member.role.value in ["owner", "admin", "member", "viewer"]

    def test_member_default_values(self, workspace):
        """Test member default values."""
        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_email="test@example.com",
        )
        assert member.role == WorkspaceRole.MEMBER
        assert member.is_active is True
        assert isinstance(member.invited_at, datetime)
        assert member.joined_at is None


class TestMultiTenantIsolation:
    """Test multi-tenant data isolation."""

    def test_document_tenant_id(self, workspace):
        """Test document has tenant_id."""
        doc = Document(
            tenant_id=workspace.id,
            title="Test Doc",
            source_type=SourceType.URL,
            source_url="https://example.com",
        )
        assert doc.tenant_id == workspace.id

    def test_document_default_tenant_id(self):
        """Test document default tenant_id (local mode)."""
        doc = Document(
            title="Test Doc",
            source_type=SourceType.URL,
            source_url="https://example.com",
        )
        # Default is local workspace
        assert doc.tenant_id == UUID("00000000-0000-0000-0000-000000000000")

    def test_entity_tenant_id(self, workspace):
        """Test entity has tenant_id."""
        entity = Entity(
            tenant_id=workspace.id,
            name="Test Entity",
            entity_type="PRODUCT",
        )
        assert entity.tenant_id == workspace.id

    def test_multiple_workspaces_isolation(self):
        """Test that different workspaces have different tenant_ids."""
        ws1 = Workspace(name="Workspace 1", slug="ws1")
        ws2 = Workspace(name="Workspace 2", slug="ws2")

        doc1 = Document(
            tenant_id=ws1.id,
            title="Doc 1",
            source_type=SourceType.URL,
            source_url="https://ws1.example.com",
        )
        doc2 = Document(
            tenant_id=ws2.id,
            title="Doc 2",
            source_type=SourceType.URL,
            source_url="https://ws2.example.com",
        )

        # Different workspaces should have different tenant_ids
        assert doc1.tenant_id != doc2.tenant_id
        assert doc1.tenant_id == ws1.id
        assert doc2.tenant_id == ws2.id


class TestWorkspaceRoles:
    """Test workspace role permissions."""

    def test_role_hierarchy(self):
        """Test role value hierarchy."""
        roles = {
            "owner": WorkspaceRole.OWNER,
            "admin": WorkspaceRole.ADMIN,
            "member": WorkspaceRole.MEMBER,
            "viewer": WorkspaceRole.VIEWER,
        }

        for role_str, role_enum in roles.items():
            assert role_enum.value == role_str

    def test_role_from_string(self):
        """Test creating role from string."""
        assert WorkspaceRole("owner") == WorkspaceRole.OWNER
        assert WorkspaceRole("admin") == WorkspaceRole.ADMIN
        assert WorkspaceRole("member") == WorkspaceRole.MEMBER
        assert WorkspaceRole("viewer") == WorkspaceRole.VIEWER

    def test_invalid_role_raises_error(self):
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError):
            WorkspaceRole("invalid_role")


class TestWorkspaceMembership:
    """Test workspace membership logic."""

    def test_member_belongs_to_workspace(self, workspace, workspace_member):
        """Test member belongs to correct workspace."""
        assert workspace_member.workspace_id == workspace.id

    def test_multiple_members_same_workspace(self, workspace):
        """Test multiple members in same workspace."""
        member1 = WorkspaceMember(
            workspace_id=workspace.id,
            user_email="user1@example.com",
            role=WorkspaceRole.ADMIN,
        )
        member2 = WorkspaceMember(
            workspace_id=workspace.id,
            user_email="user2@example.com",
            role=WorkspaceRole.MEMBER,
        )

        assert member1.workspace_id == member2.workspace_id
        assert member1.user_email != member2.user_email
        assert member1.role != member2.role

    def test_member_invitation_flow(self, workspace):
        """Test member invitation workflow."""
        # Create invited member
        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_email="invited@example.com",
            invited_by="admin@example.com",
        )

        assert member.joined_at is None  # Not yet joined
        assert member.invited_at is not None
        assert member.invited_by == "admin@example.com"

        # Simulate joining
        member.joined_at = datetime.utcnow()
        assert member.joined_at is not None

    def test_inactive_member(self, workspace_member):
        """Test deactivating a member."""
        workspace_member.is_active = False
        assert workspace_member.is_active is False


class TestLocalVsCloudMode:
    """Test local vs cloud mode differences."""

    def test_local_mode_default_workspace(self):
        """Test local mode uses default workspace ID."""
        local_workspace_id = UUID("00000000-0000-0000-0000-000000000000")

        doc = Document(
            tenant_id=local_workspace_id,
            title="Local Doc",
            source_type=SourceType.FILE_UPLOAD,
        )

        assert doc.tenant_id == local_workspace_id

    def test_cloud_mode_custom_workspace(self):
        """Test cloud mode uses custom workspace ID."""
        cloud_workspace = Workspace(
            name="Cloud Workspace",
            slug="cloud",
            owner_email="cloud@example.com",
        )

        doc = Document(
            tenant_id=cloud_workspace.id,
            title="Cloud Doc",
            source_type=SourceType.URL,
            source_url="https://cloud.example.com",
        )

        assert doc.tenant_id == cloud_workspace.id
        assert doc.tenant_id != UUID("00000000-0000-0000-0000-000000000000")
