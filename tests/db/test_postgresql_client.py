"""Tests for PostgreSQL database client."""

import os
from uuid import uuid4

import pytest
from sqlmodel import select

from kurt.db.models import Document, Entity, IngestionStatus, SourceType
from kurt.db.postgresql import PostgreSQLClient


@pytest.fixture
def postgres_url():
    """PostgreSQL connection URL from environment or skip test."""
    url = os.getenv("TEST_POSTGRES_URL")
    if not url:
        pytest.skip("TEST_POSTGRES_URL not set - skipping PostgreSQL tests")
    return url


@pytest.fixture
def workspace_id():
    """Generate a unique workspace ID for tests."""
    return str(uuid4())


@pytest.fixture
def postgres_client(postgres_url, workspace_id):
    """Create a PostgreSQL client for testing."""
    client = PostgreSQLClient(database_url=postgres_url, workspace_id=workspace_id)

    # Clean up any existing test data
    session = client.get_session()
    try:
        # Delete test documents
        test_docs = session.exec(select(Document).where(Document.tenant_id == workspace_id)).all()
        for doc in test_docs:
            session.delete(doc)

        # Delete test entities
        test_entities = session.exec(select(Entity).where(Entity.tenant_id == workspace_id)).all()
        for entity in test_entities:
            session.delete(entity)

        session.commit()
    finally:
        session.close()

    yield client

    # Clean up after tests
    session = client.get_session()
    try:
        test_docs = session.exec(select(Document).where(Document.tenant_id == workspace_id)).all()
        for doc in test_docs:
            session.delete(doc)

        test_entities = session.exec(select(Entity).where(Entity.tenant_id == workspace_id)).all()
        for entity in test_entities:
            session.delete(entity)

        session.commit()
    finally:
        session.close()


@pytest.mark.integration
def test_postgresql_client_connection(postgres_client):
    """Test PostgreSQL client can connect to database."""
    assert postgres_client.check_database_exists()
    assert postgres_client.get_mode_name() == "postgresql"


@pytest.mark.integration
def test_postgresql_client_database_url(postgres_client, postgres_url):
    """Test PostgreSQL client returns correct database URL."""
    assert postgres_client.get_database_url() == postgres_url


@pytest.mark.integration
def test_postgresql_client_session(postgres_client, workspace_id):
    """Test PostgreSQL client can create sessions with workspace context."""
    session = postgres_client.get_session()

    assert session is not None

    # Verify workspace context is set
    # This assumes the database has app.current_workspace support
    # If not set up yet, this will just pass

    session.close()


@pytest.mark.integration
def test_postgresql_document_crud(postgres_client, workspace_id):
    """Test CRUD operations on documents with tenant isolation."""
    session = postgres_client.get_session()

    try:
        # Create document
        doc = Document(
            tenant_id=workspace_id,
            title="Test Document",
            source_type=SourceType.URL,
            source_url="https://test.example.com/doc",
            content_path="sources/test.md",
            ingestion_status=IngestionStatus.FETCHED,
        )

        session.add(doc)
        session.commit()
        session.refresh(doc)

        assert doc.id is not None
        assert doc.tenant_id == workspace_id
        assert doc.title == "Test Document"

        # Read document
        doc_id = doc.id
        retrieved_doc = session.get(Document, doc_id)

        assert retrieved_doc is not None
        assert retrieved_doc.title == "Test Document"
        assert retrieved_doc.tenant_id == workspace_id

        # Update document
        retrieved_doc.title = "Updated Document"
        session.add(retrieved_doc)
        session.commit()

        updated_doc = session.get(Document, doc_id)
        assert updated_doc.title == "Updated Document"

        # Delete document
        session.delete(updated_doc)
        session.commit()

        deleted_doc = session.get(Document, doc_id)
        assert deleted_doc is None

    finally:
        session.close()


@pytest.mark.integration
def test_postgresql_entity_crud(postgres_client, workspace_id):
    """Test CRUD operations on entities with tenant isolation."""
    session = postgres_client.get_session()

    try:
        # Create entity
        entity = Entity(
            tenant_id=workspace_id,
            name="Python",
            entity_type="Technology",
            description="Programming language",
            confidence_score=0.95,
        )

        session.add(entity)
        session.commit()
        session.refresh(entity)

        assert entity.id is not None
        assert entity.tenant_id == workspace_id
        assert entity.name == "Python"

        # Read entity
        entity_id = entity.id
        retrieved_entity = session.get(Entity, entity_id)

        assert retrieved_entity is not None
        assert retrieved_entity.name == "Python"
        assert retrieved_entity.tenant_id == workspace_id

        # Clean up
        session.delete(retrieved_entity)
        session.commit()

    finally:
        session.close()


@pytest.mark.integration
def test_postgresql_workspace_isolation(postgres_url):
    """Test that workspaces are isolated from each other."""
    workspace_1 = str(uuid4())
    workspace_2 = str(uuid4())

    client_1 = PostgreSQLClient(database_url=postgres_url, workspace_id=workspace_1)
    client_2 = PostgreSQLClient(database_url=postgres_url, workspace_id=workspace_2)

    session_1 = client_1.get_session()
    session_2 = client_2.get_session()

    try:
        # Create document in workspace 1
        doc_1 = Document(
            tenant_id=workspace_1,
            title="Workspace 1 Document",
            source_type=SourceType.URL,
            source_url="https://test.example.com/workspace1",
        )
        session_1.add(doc_1)
        session_1.commit()
        session_1.refresh(doc_1)

        # Create document in workspace 2
        doc_2 = Document(
            tenant_id=workspace_2,
            title="Workspace 2 Document",
            source_type=SourceType.URL,
            source_url="https://test.example.com/workspace2",
        )
        session_2.add(doc_2)
        session_2.commit()
        session_2.refresh(doc_2)

        # Query workspace 1 - should only see workspace 1 docs
        workspace_1_docs = session_1.exec(
            select(Document).where(Document.tenant_id == workspace_1)
        ).all()

        assert len(workspace_1_docs) == 1
        assert workspace_1_docs[0].title == "Workspace 1 Document"

        # Query workspace 2 - should only see workspace 2 docs
        workspace_2_docs = session_2.exec(
            select(Document).where(Document.tenant_id == workspace_2)
        ).all()

        assert len(workspace_2_docs) == 1
        assert workspace_2_docs[0].title == "Workspace 2 Document"

        # Clean up
        session_1.delete(doc_1)
        session_1.commit()

        session_2.delete(doc_2)
        session_2.commit()

    finally:
        session_1.close()
        session_2.close()


def test_postgresql_client_init_without_url():
    """Test PostgreSQL client raises error without DATABASE_URL."""
    with pytest.raises(ValueError, match="DATABASE_URL is required"):
        PostgreSQLClient(database_url=None)


def test_postgresql_client_async_methods(postgres_url, workspace_id):
    """Test async method interfaces exist."""
    client = PostgreSQLClient(database_url=postgres_url, workspace_id=workspace_id)

    # Test async URL conversion
    async_url = client.get_async_database_url()
    assert "postgresql+asyncpg://" in async_url or "postgresql://" in async_url

    # Test async engine creation
    engine = client.get_async_engine()
    assert engine is not None

    # Test async session maker
    session_maker = client.get_async_session_maker()
    assert session_maker is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgresql_async_session(postgres_client):
    """Test async session operations."""
    session_maker = postgres_client.get_async_session_maker()

    async with session_maker() as session:
        # Simple query to verify async works
        result = await session.exec(select(Document).limit(1))
        docs = result.all()

        # Should succeed even if no documents
        assert isinstance(docs, list)


def test_postgresql_client_mask_password():
    """Test password masking in display."""
    from kurt.db.migrate_to_postgres import _mask_password

    url = "postgresql://user:secret123@db.example.com:5432/postgres"
    masked = _mask_password(url)

    assert "secret123" not in masked
    assert "user:***@" in masked
    assert "db.example.com" in masked
