"""Tests for fetch document filtering behavior.

These tests verify the derived status filtering behavior, where status is
determined from pipeline tables (landing_fetch, staging_section_extractions)
rather than the ingestion_status column on the Document model.
"""

from uuid import uuid4

from kurt.db.models import Document, SourceType
from kurt.tests.status_helpers import (
    mark_document_as_error,
    mark_document_as_fetched,
    mark_document_as_indexed,
)
from kurt.utils.filtering import build_document_query, filter_documents_by_derived_status


def test_fetch_excludes_fetched_by_default(session):
    """Test that fetch excludes FETCHED documents by default."""
    # Create test documents (all start as NOT_FETCHED in derived status)
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

    # Mark doc2 as FETCHED and doc3 as ERROR using pipeline tables
    mark_document_as_fetched(doc2.id, session=session)
    mark_document_as_error(doc3.id, session=session)

    # Query all documents
    stmt = build_document_query(
        id_uuids=None,
        with_status=None,
        refetch=True,  # Get all first
        in_cluster=None,
        with_content_type=None,
        limit=None,
    )

    all_docs = list(session.exec(stmt).all())

    # Apply derived status filtering (excludes FETCHED by default)
    results = filter_documents_by_derived_status(
        all_docs,
        with_status=None,
        refetch=False,
        session=session,
    )
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
    )
    doc2 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/fetched",
    )

    session.add(doc1)
    session.add(doc2)
    session.commit()

    # Mark doc2 as FETCHED using pipeline tables
    mark_document_as_fetched(doc2.id, session=session)

    # Query all documents
    stmt = build_document_query(
        id_uuids=None,
        with_status=None,
        refetch=True,  # Get all first
        in_cluster=None,
        with_content_type=None,
        limit=None,
    )

    all_docs = list(session.exec(stmt).all())

    # Apply derived status filtering with refetch=True
    results = filter_documents_by_derived_status(
        all_docs,
        with_status=None,
        refetch=True,
        session=session,
    )
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
    )
    doc2 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/fetched-2",
    )

    session.add(doc1)
    session.add(doc2)
    session.commit()

    # Mark both as FETCHED using pipeline tables
    mark_document_as_fetched(doc1.id, session=session)
    mark_document_as_fetched(doc2.id, session=session)

    # Query with specific IDs
    stmt = build_document_query(
        id_uuids=[doc1.id, doc2.id],
        with_status=None,
        refetch=True,  # Get all first
        in_cluster=None,
        with_content_type=None,
        limit=None,
    )

    all_docs = list(session.exec(stmt).all())

    # Apply derived status filtering without refetch
    results = filter_documents_by_derived_status(
        all_docs,
        with_status=None,
        refetch=False,
        session=session,
    )
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
    )
    doc2 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/not-fetched",
    )

    session.add(doc1)
    session.add(doc2)
    session.commit()

    # Mark doc1 as FETCHED using pipeline tables
    mark_document_as_fetched(doc1.id, session=session)

    # Query with specific IDs
    stmt = build_document_query(
        id_uuids=[doc1.id, doc2.id],
        with_status=None,
        refetch=True,  # Get all first
        in_cluster=None,
        with_content_type=None,
        limit=None,
    )

    all_docs = list(session.exec(stmt).all())

    # Apply derived status filtering with refetch=True
    results = filter_documents_by_derived_status(
        all_docs,
        with_status=None,
        refetch=True,
        session=session,
    )
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
    )
    doc2 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/fetched",
    )

    session.add(doc1)
    session.add(doc2)
    session.commit()

    # Mark doc2 as FETCHED using pipeline tables
    mark_document_as_fetched(doc2.id, session=session)

    # Query all documents
    stmt = build_document_query(
        id_uuids=None,
        with_status=None,
        refetch=True,  # Get all first
        in_cluster=None,
        with_content_type=None,
        limit=None,
    )

    all_docs = list(session.exec(stmt).all())

    # Apply derived status filtering for explicit FETCHED status
    results = filter_documents_by_derived_status(
        all_docs,
        with_status="FETCHED",
        refetch=False,
        session=session,
    )
    result_ids = [doc.id for doc in results]

    # Should only include FETCHED documents
    assert doc1.id not in result_ids, "Should exclude NOT_FETCHED when filtering for FETCHED"
    assert doc2.id in result_ids, "Should include FETCHED document with explicit filter"


def test_fetch_excludes_indexed_by_default(session):
    """Test that fetch excludes INDEXED documents by default."""
    # Create test documents
    doc1 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/not-fetched",
    )
    doc2 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/indexed",
    )

    session.add(doc1)
    session.add(doc2)
    session.commit()

    # Mark doc2 as INDEXED using pipeline tables
    mark_document_as_fetched(doc2.id, session=session)
    mark_document_as_indexed(doc2.id, session=session)

    # Query all documents
    stmt = build_document_query(
        id_uuids=None,
        with_status=None,
        refetch=True,  # Get all first
        in_cluster=None,
        with_content_type=None,
        limit=None,
    )

    all_docs = list(session.exec(stmt).all())

    # Apply derived status filtering (excludes INDEXED by default, same as FETCHED)
    results = filter_documents_by_derived_status(
        all_docs,
        with_status=None,
        refetch=False,
        session=session,
    )
    result_ids = [doc.id for doc in results]

    # Should include NOT_FETCHED but NOT INDEXED
    assert doc1.id in result_ids, "Should include NOT_FETCHED document"
    assert doc2.id not in result_ids, "Should exclude INDEXED document"


def test_filter_for_indexed_status(session):
    """Test filtering explicitly for INDEXED status."""
    # Create test documents
    doc1 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/fetched",
    )
    doc2 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/indexed",
    )
    doc3 = Document(
        id=uuid4(),
        source_type=SourceType.URL,
        source_url="https://example.com/not-fetched",
    )

    session.add(doc1)
    session.add(doc2)
    session.add(doc3)
    session.commit()

    # Mark doc1 as FETCHED only, doc2 as INDEXED
    mark_document_as_fetched(doc1.id, session=session)
    mark_document_as_fetched(doc2.id, session=session)
    mark_document_as_indexed(doc2.id, session=session)

    # Query all documents
    stmt = build_document_query(
        id_uuids=None,
        with_status=None,
        refetch=True,  # Get all first
        in_cluster=None,
        with_content_type=None,
        limit=None,
    )

    all_docs = list(session.exec(stmt).all())

    # Apply derived status filtering for explicit INDEXED status
    results = filter_documents_by_derived_status(
        all_docs,
        with_status="INDEXED",
        refetch=False,
        session=session,
    )
    result_ids = [doc.id for doc in results]

    # Should only include INDEXED document
    assert doc1.id not in result_ids, "Should exclude FETCHED when filtering for INDEXED"
    assert doc2.id in result_ids, "Should include INDEXED document with explicit filter"
    assert doc3.id not in result_ids, "Should exclude NOT_FETCHED when filtering for INDEXED"
