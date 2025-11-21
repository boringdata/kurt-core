"""Tests for content generation context building."""

from uuid import uuid4

import pytest

from kurt.content.generation.context import ContextBuilder
from kurt.content.generation.models import ContentGenerationRequest
from kurt.db.database import get_session
from kurt.db.models import Document, IngestionStatus, SourceType


@pytest.fixture
def sample_documents(tmp_path):
    """Create sample documents with content files."""
    session = get_session()

    # Create content files
    doc1_path = tmp_path / "doc1.md"
    doc1_path.write_text("# Authentication Guide\n\nThis is a guide about OAuth 2.0.")

    doc2_path = tmp_path / "doc2.md"
    doc2_path.write_text("# API Tutorial\n\nLearn how to use our API.")

    # Create documents in database
    doc1 = Document(
        title="Authentication Guide",
        source_type=SourceType.URL,
        source_url="https://example.com/auth",
        content_path=str(doc1_path),
        ingestion_status=IngestionStatus.FETCHED,
    )
    doc2 = Document(
        title="API Tutorial",
        source_type=SourceType.URL,
        source_url="https://example.com/api",
        content_path=str(doc2_path),
        ingestion_status=IngestionStatus.FETCHED,
    )

    session.add(doc1)
    session.add(doc2)
    session.commit()
    session.refresh(doc1)
    session.refresh(doc2)

    yield [doc1, doc2]

    # Cleanup
    session.delete(doc1)
    session.delete(doc2)
    session.commit()


def test_context_builder_with_document_ids(sample_documents):
    """Test building context from specified document IDs."""
    doc1, doc2 = sample_documents

    request = ContentGenerationRequest(
        goal="Write about authentication",
        source_document_ids=[doc1.id],
    )

    builder = ContextBuilder(request)
    context, sources = builder.build_context()

    # Check context includes document content
    assert "Authentication Guide" in context
    assert "OAuth 2.0" in context
    assert "https://example.com/auth" in context

    # Check sources
    assert len(sources) == 1
    assert sources[0].document_id == doc1.id
    assert sources[0].document_title == "Authentication Guide"
    assert sources[0].document_url == "https://example.com/auth"


def test_context_builder_with_multiple_documents(sample_documents):
    """Test building context from multiple documents."""
    doc1, doc2 = sample_documents

    request = ContentGenerationRequest(
        goal="Write comprehensive guide",
        source_document_ids=[doc1.id, doc2.id],
    )

    builder = ContextBuilder(request)
    context, sources = builder.build_context()

    # Check both documents are in context
    assert "Authentication Guide" in context
    assert "API Tutorial" in context
    assert "OAuth 2.0" in context
    assert "use our API" in context

    # Check sources
    assert len(sources) == 2
    assert {s.document_id for s in sources} == {doc1.id, doc2.id}


def test_context_builder_with_missing_document():
    """Test context building handles missing documents gracefully."""
    fake_id = uuid4()

    request = ContentGenerationRequest(
        goal="Test",
        source_document_ids=[fake_id],
    )

    builder = ContextBuilder(request)
    context, sources = builder.build_context()

    # Should still return context, but with no sources
    assert context is not None
    assert len(sources) == 0


def test_context_builder_no_sources():
    """Test context builder with no sources specified."""
    request = ContentGenerationRequest(goal="Write generic content")

    builder = ContextBuilder(request)
    context, sources = builder.build_context()

    # Should return default context
    assert "No Specific Sources" in context
    assert "general knowledge" in context
    assert len(sources) == 0


def test_context_builder_with_search_query(sample_documents):
    """Test building context from search query."""
    request = ContentGenerationRequest(
        goal="Write about authentication",
        source_query="authentication",
    )

    builder = ContextBuilder(request)
    context, sources = builder.build_context()

    # Should find document with "authentication" in title
    assert len(sources) > 0
    assert any("Authentication" in s.document_title for s in sources)
