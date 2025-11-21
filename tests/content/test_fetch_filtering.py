"""Tests for fetch document filtering behavior."""

from uuid import uuid4

from kurt.content.filtering import build_document_query
from kurt.db.models import Document, IngestionStatus, SourceType


def test_fetch_excludes_fetched_by_default(session):
    """Test that fetch excludes FETCHED documents by default."""
    # Create test documents with different statuses
    doc1 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/not-fetched",
        ingestion_status=IngestionStatus.NOT_FETCHED,
    )
    doc2 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/fetched",
        ingestion_status=IngestionStatus.FETCHED,
    )
    doc3 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/error",
        ingestion_status=IngestionStatus.ERROR,
    )

    session.add(doc1)
    session.add(doc2)
    session.add(doc3)
    session.commit()

    # Query without refetch flag
    stmt = build_document_query(
        id_uuids=None,
        with_status=None,
        refetch=False,
        in_cluster=None,
        with_content_type=None,
        limit=None,
    )

    results = list(session.exec(stmt).all())
    result_ids = [doc.id for doc in results]

    # Should include NOT_FETCHED and ERROR, but NOT FETCHED
    assert doc1.id in result_ids, "Should include NOT_FETCHED document"
    assert doc2.id not in result_ids, "Should exclude FETCHED document"
    assert doc3.id in result_ids, "Should include ERROR document"


def test_fetch_with_refetch_flag_includes_fetched(session):
    """Test that fetch with --refetch flag includes FETCHED documents."""
    # Create test documents
    doc1 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/not-fetched",
        ingestion_status=IngestionStatus.NOT_FETCHED,
    )
    doc2 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/fetched",
        ingestion_status=IngestionStatus.FETCHED,
    )

    session.add(doc1)
    session.add(doc2)
    session.commit()

    # Query with refetch=True
    stmt = build_document_query(
        id_uuids=None,
        with_status=None,
        refetch=True,
        in_cluster=None,
        with_content_type=None,
        limit=None,
    )

    results = list(session.exec(stmt).all())
    result_ids = [doc.id for doc in results]

    # Should include both documents
    assert doc1.id in result_ids, "Should include NOT_FETCHED document"
    assert doc2.id in result_ids, "Should include FETCHED document with refetch=True"


def test_fetch_with_specific_ids_respects_status_filter(session):
    """Test that fetch with specific IDs still respects the status filter."""
    # Create test documents
    doc1 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/fetched-1",
        ingestion_status=IngestionStatus.FETCHED,
    )
    doc2 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/fetched-2",
        ingestion_status=IngestionStatus.FETCHED,
    )

    session.add(doc1)
    session.add(doc2)
    session.commit()

    # Query with specific IDs but without refetch
    stmt = build_document_query(
        id_uuids=[doc1.id, doc2.id],
        with_status=None,
        refetch=False,
        in_cluster=None,
        with_content_type=None,
        limit=None,
    )

    results = list(session.exec(stmt).all())
    result_ids = [doc.id for doc in results]

    # Should exclude both because they're FETCHED and refetch=False
    assert doc1.id not in result_ids, "Should exclude FETCHED document even with specific ID"
    assert doc2.id not in result_ids, "Should exclude FETCHED document even with specific ID"


def test_fetch_with_ids_and_refetch_includes_all(session):
    """Test that fetch with specific IDs and --refetch includes them."""
    # Create test documents
    doc1 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/fetched-1",
        ingestion_status=IngestionStatus.FETCHED,
    )
    doc2 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/not-fetched",
        ingestion_status=IngestionStatus.NOT_FETCHED,
    )

    session.add(doc1)
    session.add(doc2)
    session.commit()

    # Query with specific IDs and refetch=True
    stmt = build_document_query(
        id_uuids=[doc1.id, doc2.id],
        with_status=None,
        refetch=True,
        in_cluster=None,
        with_content_type=None,
        limit=None,
    )

    results = list(session.exec(stmt).all())
    result_ids = [doc.id for doc in results]

    # Should include both documents
    assert doc1.id in result_ids, "Should include FETCHED document with refetch=True"
    assert doc2.id in result_ids, "Should include NOT_FETCHED document"


def test_fetch_with_explicit_status_filter(session):
    """Test that explicit --with-status filter overrides default behavior."""
    # Create test documents
    doc1 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/not-fetched",
        ingestion_status=IngestionStatus.NOT_FETCHED,
    )
    doc2 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/fetched",
        ingestion_status=IngestionStatus.FETCHED,
    )

    session.add(doc1)
    session.add(doc2)
    session.commit()

    # Query with explicit status filter for FETCHED
    stmt = build_document_query(
        id_uuids=None,
        with_status="FETCHED",
        refetch=False,
        in_cluster=None,
        with_content_type=None,
        limit=None,
    )

    results = list(session.exec(stmt).all())
    result_ids = [doc.id for doc in results]

    # Should only include FETCHED documents
    assert doc1.id not in result_ids, "Should exclude NOT_FETCHED when filtering for FETCHED"
    assert doc2.id in result_ids, "Should include FETCHED document with explicit filter"
