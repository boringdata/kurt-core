"""Integration tests for PostgreSQL database functionality."""

from uuid import UUID, uuid4

import pytest
from sqlmodel import select

from kurt.db.models import (
    Document,
    Entity,
    SourceType,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)


class TestPostgreSQLConnection:
    """Test basic PostgreSQL connection and setup."""

    def test_postgres_connection(self, postgres_db):
        """Test that PostgreSQL connection works."""
        cursor = postgres_db.cursor()
        cursor.execute("SELECT version();")
        result = cursor.fetchone()
        assert result is not None
        assert "PostgreSQL" in result[0]

    def test_pgvector_extension_installed(self, postgres_db):
        """Test that pgvector extension is installed."""
        cursor = postgres_db.cursor()
        cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        result = cursor.fetchone()
        assert result is not None

    def test_migrations_applied(self, postgres_db):
        """Test that Kurt migrations have been applied."""
        cursor = postgres_db.cursor()

        # Check that main tables exist
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('documents', 'entities', 'workspaces', 'workspace_members')
        """)
        tables = [row[0] for row in cursor.fetchall()]

        assert "documents" in tables
        assert "entities" in tables
        assert "workspaces" in tables
        assert "workspace_members" in tables

    def test_tenant_id_columns_exist(self, postgres_db):
        """Test that tenant_id columns were added by migration."""
        cursor = postgres_db.cursor()

        # Check documents table has tenant_id
        cursor.execute("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'documents' AND column_name = 'tenant_id'
        """)
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == "tenant_id"
        assert "uuid" in result[1].lower()

        # Check entities table has tenant_id
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'entities' AND column_name = 'tenant_id'
        """)
        result = cursor.fetchone()
        assert result is not None


class TestMultiTenantIsolation:
    """Test multi-tenant data isolation with real PostgreSQL."""

    def test_documents_isolated_by_workspace(self, postgres_db):
        """Test that documents are isolated by workspace tenant_id."""
        from kurt.db.base import get_database_client

        client = get_database_client()

        workspace1_id = uuid4()
        workspace2_id = uuid4()

        with client.get_session() as session:
            # Create workspaces
            ws1 = Workspace(id=workspace1_id, name="Workspace 1", slug="ws1")
            ws2 = Workspace(id=workspace2_id, name="Workspace 2", slug="ws2")
            session.add(ws1)
            session.add(ws2)
            session.commit()

            # Create documents in different workspaces
            doc1 = Document(
                tenant_id=workspace1_id,
                title="Doc in WS1",
                source_type=SourceType.URL,
                source_url="https://ws1.example.com",
            )
            doc2 = Document(
                tenant_id=workspace2_id,
                title="Doc in WS2",
                source_type=SourceType.URL,
                source_url="https://ws2.example.com",
            )
            session.add(doc1)
            session.add(doc2)
            session.commit()

            # Query documents for workspace 1
            ws1_docs = session.exec(
                select(Document).where(Document.tenant_id == workspace1_id)
            ).all()

            # Query documents for workspace 2
            ws2_docs = session.exec(
                select(Document).where(Document.tenant_id == workspace2_id)
            ).all()

            # Each workspace should only see its own documents
            assert len(ws1_docs) == 1
            assert len(ws2_docs) == 1
            assert ws1_docs[0].title == "Doc in WS1"
            assert ws2_docs[0].title == "Doc in WS2"

    def test_entities_isolated_by_workspace(self, postgres_db):
        """Test that entities are isolated by workspace tenant_id."""
        from kurt.db.base import get_database_client

        client = get_database_client()

        workspace1_id = uuid4()
        workspace2_id = uuid4()

        with client.get_session() as session:
            # Create workspaces
            ws1 = Workspace(id=workspace1_id, name="Workspace 1", slug="ws1")
            ws2 = Workspace(id=workspace2_id, name="Workspace 2", slug="ws2")
            session.add(ws1)
            session.add(ws2)
            session.commit()

            # Create entities in different workspaces
            entity1 = Entity(tenant_id=workspace1_id, name="Entity in WS1", entity_type="PRODUCT")
            entity2 = Entity(tenant_id=workspace2_id, name="Entity in WS2", entity_type="PRODUCT")
            session.add(entity1)
            session.add(entity2)
            session.commit()

            # Query entities for each workspace
            ws1_entities = session.exec(
                select(Entity).where(Entity.tenant_id == workspace1_id)
            ).all()
            ws2_entities = session.exec(
                select(Entity).where(Entity.tenant_id == workspace2_id)
            ).all()

            # Each workspace should only see its own entities
            assert len(ws1_entities) == 1
            assert len(ws2_entities) == 1
            assert ws1_entities[0].name == "Entity in WS1"
            assert ws2_entities[0].name == "Entity in WS2"

    def test_workspace_member_access_control(self, postgres_db):
        """Test workspace member access control."""
        from kurt.db.base import get_database_client

        client = get_database_client()

        workspace_id = uuid4()

        with client.get_session() as session:
            # Create workspace
            ws = Workspace(id=workspace_id, name="Test Workspace", slug="test")
            session.add(ws)
            session.commit()

            # Add members with different roles
            owner = WorkspaceMember(
                workspace_id=workspace_id,
                user_email="owner@example.com",
                role=WorkspaceRole.OWNER,
            )
            admin = WorkspaceMember(
                workspace_id=workspace_id,
                user_email="admin@example.com",
                role=WorkspaceRole.ADMIN,
            )
            member = WorkspaceMember(
                workspace_id=workspace_id,
                user_email="member@example.com",
                role=WorkspaceRole.MEMBER,
            )
            viewer = WorkspaceMember(
                workspace_id=workspace_id,
                user_email="viewer@example.com",
                role=WorkspaceRole.VIEWER,
            )

            session.add(owner)
            session.add(admin)
            session.add(member)
            session.add(viewer)
            session.commit()

            # Query all members
            members = session.exec(
                select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)
            ).all()

            assert len(members) == 4

            # Verify roles
            roles = {m.user_email: m.role for m in members}
            assert roles["owner@example.com"] == WorkspaceRole.OWNER
            assert roles["admin@example.com"] == WorkspaceRole.ADMIN
            assert roles["member@example.com"] == WorkspaceRole.MEMBER
            assert roles["viewer@example.com"] == WorkspaceRole.VIEWER


class TestLocalModeCompatibility:
    """Test that local mode (SQLite-style) still works with PostgreSQL."""

    def test_default_local_workspace_id(self, postgres_db):
        """Test that default local workspace ID works in PostgreSQL."""
        from kurt.db.base import get_database_client

        client = get_database_client()
        local_workspace_id = UUID("00000000-0000-0000-0000-000000000000")

        with client.get_session() as session:
            # Create document with default local workspace ID
            doc = Document(
                tenant_id=local_workspace_id,
                title="Local Document",
                source_type=SourceType.FILE_UPLOAD,
            )
            session.add(doc)
            session.commit()

            # Query by local workspace ID
            local_docs = session.exec(
                select(Document).where(Document.tenant_id == local_workspace_id)
            ).all()

            assert len(local_docs) == 1
            assert local_docs[0].title == "Local Document"
            assert local_docs[0].tenant_id == local_workspace_id


class TestWorkspaceOperations:
    """Test workspace CRUD operations with real PostgreSQL."""

    def test_create_workspace(self, postgres_db):
        """Test creating a workspace."""
        from kurt.db.base import get_database_client

        client = get_database_client()

        with client.get_session() as session:
            workspace = Workspace(
                name="Test Workspace",
                slug="test-workspace",
                plan="free",
                owner_email="owner@example.com",
            )
            session.add(workspace)
            session.commit()
            session.refresh(workspace)

            assert workspace.id is not None
            assert workspace.name == "Test Workspace"
            assert workspace.slug == "test-workspace"
            assert workspace.is_active is True

    def test_list_workspaces(self, postgres_db):
        """Test listing all workspaces."""
        from kurt.db.base import get_database_client

        client = get_database_client()

        with client.get_session() as session:
            # Create multiple workspaces
            ws1 = Workspace(name="Workspace 1", slug="ws1")
            ws2 = Workspace(name="Workspace 2", slug="ws2")
            ws3 = Workspace(name="Workspace 3", slug="ws3", is_active=False)

            session.add(ws1)
            session.add(ws2)
            session.add(ws3)
            session.commit()

            # Query active workspaces
            active_workspaces = session.exec(select(Workspace).where(Workspace.is_active)).all()

            assert len(active_workspaces) >= 2
            active_names = {ws.name for ws in active_workspaces}
            assert "Workspace 1" in active_names
            assert "Workspace 2" in active_names
            assert "Workspace 3" not in active_names

    def test_workspace_slug_uniqueness(self, postgres_db):
        """Test that workspace slugs must be unique."""
        from sqlalchemy.exc import IntegrityError

        from kurt.db.base import get_database_client

        client = get_database_client()

        with client.get_session() as session:
            ws1 = Workspace(name="First", slug="duplicate-slug")
            session.add(ws1)
            session.commit()

            # Try to create another workspace with same slug
            ws2 = Workspace(name="Second", slug="duplicate-slug")
            session.add(ws2)

            with pytest.raises(IntegrityError):
                session.commit()
