"""Tests for fetch document filtering behavior.

Status is now derived from staging tables (landing_fetch, staging_section_extractions).
These tests use the status_helpers module to set up document status correctly.
"""

from uuid import uuid4

from kurt.db.models import Document, SourceType
from kurt.utils.filtering import build_document_query
from tests.helpers.status_helpers import create_staging_tables, mark_document_as_fetched


def test_fetch_excludes_fetched_by_default(session):
    """Test that fetch excludes FETCHED documents by default."""
    # Create staging tables first
    create_staging_tables(session)

    # Create test documents with different statuses
    doc1 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/not-fetched",
    )
    doc2 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/fetched",
    )
    doc3 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/error",
    )

    session.add(doc1)
    session.add(doc2)
    session.add(doc3)
    session.commit()

    # Mark doc2 as FETCHED in landing_fetch table
    mark_document_as_fetched(doc2.id, session)

    # Query without refetch flag
    stmt = build_document_query(
        id_uuids=None,
        with_status=None,
        refetch=False,
        in_cluster=None,
        with_content_type=None,
        limit=None,
        session=session,
    )

    results = list(session.exec(stmt).all())
    result_ids = [doc.id for doc in results]

    # Should include NOT_FETCHED, but NOT FETCHED
    assert doc1.id in result_ids, "Should include NOT_FETCHED document"
    assert doc2.id not in result_ids, "Should exclude FETCHED document"
    assert doc3.id in result_ids, "Should include document without status (NOT_FETCHED)"


def test_fetch_with_refetch_flag_includes_fetched(session):
    """Test that fetch with --refetch flag includes FETCHED documents."""
    # Create staging tables first
    create_staging_tables(session)

    # Create test documents
    doc1 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/not-fetched",
    )
    doc2 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/fetched",
    )

    session.add(doc1)
    session.add(doc2)
    session.commit()

    # Mark doc2 as FETCHED
    mark_document_as_fetched(doc2.id, session)

    # Query with refetch=True
    stmt = build_document_query(
        id_uuids=None,
        with_status=None,
        refetch=True,
        in_cluster=None,
        with_content_type=None,
        limit=None,
        session=session,
    )

    results = list(session.exec(stmt).all())
    result_ids = [doc.id for doc in results]

    # Should include both documents
    assert doc1.id in result_ids, "Should include NOT_FETCHED document"
    assert doc2.id in result_ids, "Should include FETCHED document with refetch=True"


def test_fetch_with_specific_ids_respects_status_filter(session):
    """Test that fetch with specific IDs still respects the status filter."""
    # Create staging tables first
    create_staging_tables(session)

    # Create test documents
    doc1 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/fetched-1",
    )
    doc2 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/fetched-2",
    )

    session.add(doc1)
    session.add(doc2)
    session.commit()

    # Mark both as FETCHED
    mark_document_as_fetched(doc1.id, session)
    mark_document_as_fetched(doc2.id, session)

    # Query with specific IDs but without refetch
    stmt = build_document_query(
        id_uuids=[doc1.id, doc2.id],
        with_status=None,
        refetch=False,
        in_cluster=None,
        with_content_type=None,
        limit=None,
        session=session,
    )

    results = list(session.exec(stmt).all())
    result_ids = [doc.id for doc in results]

    # Should exclude both because they're FETCHED and refetch=False
    assert doc1.id not in result_ids, "Should exclude FETCHED document even with specific ID"
    assert doc2.id not in result_ids, "Should exclude FETCHED document even with specific ID"


def test_fetch_with_ids_and_refetch_includes_all(session):
    """Test that fetch with specific IDs and --refetch includes them."""
    # Create staging tables first
    create_staging_tables(session)

    # Create test documents
    doc1 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/fetched-1",
    )
    doc2 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/not-fetched",
    )

    session.add(doc1)
    session.add(doc2)
    session.commit()

    # Mark only doc1 as FETCHED
    mark_document_as_fetched(doc1.id, session)

    # Query with specific IDs and refetch=True
    stmt = build_document_query(
        id_uuids=[doc1.id, doc2.id],
        with_status=None,
        refetch=True,
        in_cluster=None,
        with_content_type=None,
        limit=None,
        session=session,
    )

    results = list(session.exec(stmt).all())
    result_ids = [doc.id for doc in results]

    # Should include both documents
    assert doc1.id in result_ids, "Should include FETCHED document with refetch=True"
    assert doc2.id in result_ids, "Should include NOT_FETCHED document"


def test_fetch_with_explicit_status_filter(session):
    """Test that explicit --with-status filter overrides default behavior."""
    # Create staging tables first
    create_staging_tables(session)

    # Create test documents
    doc1 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/not-fetched",
    )
    doc2 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/fetched",
    )

    session.add(doc1)
    session.add(doc2)
    session.commit()

    # Mark doc2 as FETCHED
    mark_document_as_fetched(doc2.id, session)

    # Query with explicit status filter for FETCHED
    stmt = build_document_query(
        id_uuids=None,
        with_status="FETCHED",
        refetch=False,
        in_cluster=None,
        with_content_type=None,
        limit=None,
        session=session,
    )

    results = list(session.exec(stmt).all())
    result_ids = [doc.id for doc in results]

    # Should only include FETCHED documents
    assert doc1.id not in result_ids, "Should exclude NOT_FETCHED when filtering for FETCHED"
    assert doc2.id in result_ids, "Should include FETCHED document with explicit filter"
