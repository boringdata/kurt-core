"""Test helpers for working with document status.

Status is now derived from staging tables (landing_fetch, staging_section_extractions).
These helpers provide convenient functions to:
1. Mark documents as FETCHED (create landing_fetch records)
2. Mark documents as INDEXED (create staging_section_extractions records)
3. Get document status from staging tables
"""

from uuid import UUID

from sqlalchemy import text


def mark_document_as_fetched(doc_id: str | UUID, session=None) -> None:
    """Mark a document as FETCHED by creating landing_fetch record.

    Status is now derived from staging tables, so we create a record
    in landing_fetch to simulate a successful fetch.
    """
    if session is None:
        from kurt.db.database import get_session

        session = get_session()

    # Ensure landing_fetch table exists
    session.execute(
        text(
            """
        CREATE TABLE IF NOT EXISTS landing_fetch (
            document_id TEXT PRIMARY KEY,
            status TEXT DEFAULT 'pending',
            content_length INTEGER DEFAULT 0,
            content_hash TEXT,
            content_path TEXT,
            embedding_dims INTEGER DEFAULT 0,
            links_extracted INTEGER DEFAULT 0,
            fetch_engine TEXT,
            public_url TEXT,
            metadata_json TEXT,
            workflow_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            model_name TEXT,
            error TEXT
        )
    """
        )
    )

    # Convert UUID to string format matching SQLModel storage (no hyphens)
    doc_id_str = str(doc_id).replace("-", "")

    # Insert or replace the fetch record
    session.execute(
        text(
            """
        INSERT OR REPLACE INTO landing_fetch (document_id, status, content_length, workflow_id)
        VALUES (:doc_id, 'FETCHED', 100, 'test-workflow')
    """
        ),
        {"doc_id": doc_id_str},
    )
    session.commit()


def mark_document_as_indexed(doc_id: str | UUID, session=None) -> None:
    """Mark a document as INDEXED by creating staging_section_extractions record.

    Status is derived from staging tables - INDEXED means there are records
    in staging_section_extractions.
    """
    if session is None:
        from kurt.db.database import get_session

        session = get_session()

    # Ensure staging_section_extractions table exists
    session.execute(
        text(
            """
        CREATE TABLE IF NOT EXISTS staging_section_extractions (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            section_index INTEGER DEFAULT 0,
            section_header TEXT,
            section_content TEXT,
            section_type TEXT,
            embedding BLOB,
            metadata_json TEXT,
            workflow_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            model_name TEXT,
            error TEXT
        )
    """
        )
    )

    # Insert a section extraction record
    from uuid import uuid4

    # Convert UUID to string format matching SQLModel storage (no hyphens)
    doc_id_str = str(doc_id).replace("-", "")

    session.execute(
        text(
            """
        INSERT OR REPLACE INTO staging_section_extractions
        (id, document_id, section_index, section_header, section_content, workflow_id)
        VALUES (:id, :doc_id, 0, 'Test Section', 'Test content', 'test-workflow')
    """
        ),
        {"id": str(uuid4()).replace("-", ""), "doc_id": doc_id_str},
    )
    session.commit()


def get_doc_status(doc_id: str | UUID) -> str:
    """Get document status from staging tables.

    Returns: 'INDEXED', 'FETCHED', 'DISCOVERED', 'NOT_FETCHED', or 'ERROR'
    """
    from kurt.db.documents import get_document_status

    return get_document_status(str(doc_id))["status"]


def create_staging_tables(session=None) -> None:
    """Create all staging tables used for status derivation.

    Call this in test setup if you need to work with staging tables
    before running any pipeline models.
    """
    if session is None:
        from kurt.db.database import get_session

        session = get_session()

    # Create landing_fetch
    session.execute(
        text(
            """
        CREATE TABLE IF NOT EXISTS landing_fetch (
            document_id TEXT PRIMARY KEY,
            status TEXT DEFAULT 'pending',
            content_length INTEGER DEFAULT 0,
            content_hash TEXT,
            content_path TEXT,
            embedding_dims INTEGER DEFAULT 0,
            links_extracted INTEGER DEFAULT 0,
            fetch_engine TEXT,
            public_url TEXT,
            metadata_json TEXT,
            workflow_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            model_name TEXT,
            error TEXT
        )
    """
        )
    )

    # Create landing_discovery
    session.execute(
        text(
            """
        CREATE TABLE IF NOT EXISTS landing_discovery (
            document_id TEXT PRIMARY KEY,
            status TEXT DEFAULT 'pending',
            discovery_method TEXT,
            discovery_url TEXT,
            metadata_json TEXT,
            workflow_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            model_name TEXT,
            error TEXT
        )
    """
        )
    )

    # Create staging_section_extractions
    session.execute(
        text(
            """
        CREATE TABLE IF NOT EXISTS staging_section_extractions (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            section_index INTEGER DEFAULT 0,
            section_header TEXT,
            section_content TEXT,
            section_type TEXT,
            embedding BLOB,
            metadata_json TEXT,
            workflow_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            model_name TEXT,
            error TEXT
        )
    """
        )
    )

    # Create staging_topic_clustering
    session.execute(
        text(
            """
        CREATE TABLE IF NOT EXISTS staging_topic_clustering (
            document_id TEXT PRIMARY KEY,
            cluster_name TEXT,
            content_type TEXT,
            metadata_json TEXT,
            workflow_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            model_name TEXT,
            error TEXT
        )
    """
        )
    )

    session.commit()
