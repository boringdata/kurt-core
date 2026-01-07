"""Test helpers for document status manipulation.

These helpers provide a clean API for tests to set document status by
inserting rows into the appropriate pipeline tables. This supports the
model-based architecture where status is derived from pipeline state.

Phase 0: These helpers insert data into pipeline tables to set status.
Phase 1+: The ingestion_status column will be removed from documents table.

Usage:
    def test_fetched_document(tmp_project):
        # Create document
        doc_id = add_document("https://example.com/page")

        # Mark as fetched (inserts landing_fetch row)
        mark_document_as_fetched(doc_id)

        # Now get_document_status(doc_id) returns 'FETCHED'

    def test_indexed_document(tmp_project):
        doc_id = add_document("https://example.com/page")
        mark_document_as_fetched(doc_id)
        mark_document_as_indexed(doc_id)

        # Now get_document_status(doc_id) returns 'INDEXED'
"""

from uuid import UUID

from kurt.db.database import get_session
from kurt.db.tables import TableNames


def _ensure_pipeline_tables_exist(session) -> None:
    """Ensure landing_fetch and staging_section_extractions tables exist.

    This is needed for tests that use status helpers before the pipeline
    has been run (which would normally create these tables).

    Args:
        session: Database session (required - must be provided by caller)
    """
    from sqlalchemy import text

    # Import models to register them with SQLModel (needed for table definitions)

    # Use raw SQL to create tables to avoid connection pool issues
    # Check if tables exist first using SQLite-specific query
    result = session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": TableNames.LANDING_FETCH},
    )
    if result.fetchone() is None:
        # Create landing_fetch table matching FetchRow model schema
        # Includes PipelineModelBase fields: workflow_id, created_at, updated_at, model_name, error
        session.execute(
            text(f"""
            CREATE TABLE IF NOT EXISTS {TableNames.LANDING_FETCH} (
                document_id TEXT PRIMARY KEY,
                workflow_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                model_name TEXT,
                error TEXT,
                status TEXT,
                content_length INTEGER DEFAULT 0,
                content_hash TEXT,
                content_path TEXT,
                embedding_dims INTEGER DEFAULT 0,
                links_extracted INTEGER DEFAULT 0,
                fetch_engine TEXT,
                public_url TEXT,
                metadata_json TEXT
            )
        """)
        )

    result = session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": TableNames.STAGING_SECTION_EXTRACTIONS},
    )
    if result.fetchone() is None:
        # Create staging_section_extractions table matching SectionExtractionRow schema
        # Includes: PipelineModelBase + LLMTelemetryMixin + model-specific fields
        session.execute(
            text(f"""
            CREATE TABLE IF NOT EXISTS {TableNames.STAGING_SECTION_EXTRACTIONS} (
                document_id TEXT NOT NULL,
                section_id TEXT NOT NULL,
                section_number INTEGER DEFAULT 1,
                section_heading TEXT,
                workflow_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                model_name TEXT,
                error TEXT,
                tokens_prompt INTEGER DEFAULT 0,
                tokens_completion INTEGER DEFAULT 0,
                extraction_time_ms INTEGER DEFAULT 0,
                llm_model_name TEXT,
                metadata_json TEXT,
                entities_json TEXT,
                relationships_json TEXT,
                claims_json TEXT,
                existing_entities_context_json TEXT,
                PRIMARY KEY (document_id, section_id)
            )
        """)
        )

    session.commit()


def mark_document_as_fetched(
    document_id: UUID,
    content_path: str = None,
    content_hash: str = None,
    session=None,
) -> None:
    """Mark a document as FETCHED by inserting a landing_fetch row.

    This helper inserts a row into the landing_fetch table with status='FETCHED',
    which causes get_document_status() to return 'FETCHED' for this document.

    Args:
        document_id: Document UUID
        content_path: Optional path to content file
        content_hash: Optional content hash/fingerprint
        session: Optional database session

    Example:
        doc_id = add_document("https://example.com/page")
        mark_document_as_fetched(doc_id)
        assert get_document_status(doc_id) == 'FETCHED'
    """
    from kurt.models.landing.fetch import FetchRow

    if session is None:
        session = get_session()

    # Ensure table exists
    _ensure_pipeline_tables_exist(session)

    # Check if row already exists (upsert behavior)
    doc_id_str = str(document_id)
    existing = session.query(FetchRow).filter(FetchRow.document_id == doc_id_str).first()

    if existing:
        existing.status = "FETCHED"
        if content_path:
            existing.content_path = content_path
        if content_hash:
            existing.content_hash = content_hash
    else:
        row = FetchRow(
            document_id=doc_id_str,
            status="FETCHED",
            content_path=content_path,
            content_hash=content_hash,
            content_length=0,
            embedding_dims=0,
            links_extracted=0,
        )
        session.add(row)

    session.commit()


def mark_document_as_error(
    document_id: UUID,
    error_message: str = "Test error",
    session=None,
) -> None:
    """Mark a document as ERROR by inserting a landing_fetch row.

    This helper inserts a row into the landing_fetch table with status='ERROR',
    which causes get_document_status() to return 'ERROR' for this document.

    Args:
        document_id: Document UUID
        error_message: Error message to store
        session: Optional database session

    Example:
        doc_id = add_document("https://example.com/page")
        mark_document_as_error(doc_id, "Connection timeout")
        assert get_document_status(doc_id) == 'ERROR'
    """
    from kurt.models.landing.fetch import FetchRow

    if session is None:
        session = get_session()

    # Ensure table exists
    _ensure_pipeline_tables_exist(session)

    doc_id_str = str(document_id)
    existing = session.query(FetchRow).filter(FetchRow.document_id == doc_id_str).first()

    if existing:
        existing.status = "ERROR"
        existing.error = error_message
    else:
        row = FetchRow(
            document_id=doc_id_str,
            status="ERROR",
            error=error_message,
            content_length=0,
            embedding_dims=0,
            links_extracted=0,
        )
        session.add(row)

    session.commit()


def mark_document_as_indexed(
    document_id: UUID,
    section_id: str = "main",
    section_number: int = 1,
    session=None,
) -> None:
    """Mark a document as INDEXED by inserting a staging_section_extractions row.

    This helper inserts a row into the staging_section_extractions table,
    which causes get_document_status() to return 'INDEXED' for this document.

    Note: A document should typically be marked as FETCHED first, but this
    is not enforced. The INDEXED status takes precedence over FETCHED.

    Args:
        document_id: Document UUID
        section_id: Section identifier (default: 'main')
        section_number: Section number (default: 1)
        session: Optional database session

    Example:
        doc_id = add_document("https://example.com/page")
        mark_document_as_fetched(doc_id)
        mark_document_as_indexed(doc_id)
        assert get_document_status(doc_id) == 'INDEXED'
    """
    from kurt.models.staging.indexing.step_extract_sections import SectionExtractionRow

    if session is None:
        session = get_session()

    # Ensure table exists
    _ensure_pipeline_tables_exist(session)

    doc_id_str = str(document_id)

    # Check if row already exists
    existing = (
        session.query(SectionExtractionRow)
        .filter(
            SectionExtractionRow.document_id == doc_id_str,
            SectionExtractionRow.section_id == section_id,
        )
        .first()
    )

    if not existing:
        row = SectionExtractionRow(
            document_id=doc_id_str,
            section_id=section_id,
            section_number=section_number,
        )
        session.add(row)
        session.commit()


def clear_document_pipeline_state(document_id: UUID, session=None) -> None:
    """Clear all pipeline state for a document.

    This removes all rows from landing_fetch and staging_section_extractions
    for the given document, resetting its derived status to 'NOT_FETCHED'.

    Args:
        document_id: Document UUID
        session: Optional database session

    Example:
        clear_document_pipeline_state(doc_id)
        assert get_document_status(doc_id) == 'NOT_FETCHED'
    """
    from sqlalchemy import text

    if session is None:
        session = get_session()

    doc_id_str = str(document_id)
    doc_id_no_hyphens = doc_id_str.replace("-", "")

    # Clear landing_fetch
    session.execute(
        text(
            f"""
            DELETE FROM {TableNames.LANDING_FETCH}
            WHERE document_id = :doc_id OR document_id = :doc_id_no_hyphens
            """
        ),
        {"doc_id": doc_id_str, "doc_id_no_hyphens": doc_id_no_hyphens},
    )

    # Clear staging_section_extractions
    session.execute(
        text(
            f"""
            DELETE FROM {TableNames.STAGING_SECTION_EXTRACTIONS}
            WHERE document_id = :doc_id OR document_id = :doc_id_no_hyphens
            """
        ),
        {"doc_id": doc_id_str, "doc_id_no_hyphens": doc_id_no_hyphens},
    )

    session.commit()


# Convenience exports for use in conftest.py or test files
__all__ = [
    "mark_document_as_fetched",
    "mark_document_as_error",
    "mark_document_as_indexed",
    "clear_document_pipeline_state",
]
