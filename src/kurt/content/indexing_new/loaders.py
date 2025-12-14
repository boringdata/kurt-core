"""
Generic document loading utilities for the framework.

These utilities provide generic document loading capabilities from the Kurt database,
including filtering, content loading, and change detection. They can be used by any
workflow that needs to process documents.
"""

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from kurt.config import get_config_or_default
from kurt.content.document import load_document_content
from kurt.content.filtering import DocumentFilters
from kurt.db.database import get_session
from kurt.db.models import Document, IngestionStatus

logger = logging.getLogger(__name__)


def load_documents(
    filters: DocumentFilters,
    incremental_mode: str = "full",
    workflow_id: Optional[str] = None,
    force: bool = False,
) -> List[Dict[str, Any]]:
    """
    Load documents from the database with content and metadata.

    This is a generic document loader that can be used by any workflow. It:
    1. Queries documents from the database based on filters
    2. Loads their content from the filesystem
    3. Computes content hashes for change detection
    4. Determines skip logic based on incremental mode

    Args:
        filters: Document filtering criteria
        incremental_mode: Processing mode ("full" or "delta")
        workflow_id: Optional workflow ID for tracking
        force: If True, ignore incremental mode and process all documents

    Returns:
        List of document payloads with:
            - document_id: Document UUID
            - content: Document content text
            - content_hash: SHA256 hash of content
            - skip: Whether to skip processing
            - skip_reason: Reason for skipping
            - metadata: Additional document metadata
    """
    session: Session = get_session()

    # Build query from filters
    query = select(Document)

    # Apply status filter
    if filters.with_status:
        try:
            status = IngestionStatus[filters.with_status]
            query = query.where(Document.ingestion_status == status)
        except KeyError:
            logger.warning(f"Invalid status filter: {filters.with_status}")
            return []

    # Apply ID filters
    if filters.ids:
        from uuid import UUID

        doc_ids = []
        for id_str in filters.ids.split(","):
            id_str = id_str.strip()
            if id_str:
                try:
                    # Try to parse as UUID
                    doc_ids.append(UUID(id_str))
                except ValueError:
                    # Invalid UUID, skip it
                    logger.debug(f"Skipping invalid UUID: {id_str}")
                    continue
        if doc_ids:
            query = query.where(Document.id.in_(doc_ids))

    # Apply pattern filters
    if filters.include_pattern:
        query = query.where(Document.source_url.like(filters.include_pattern.replace("*", "%")))
    if filters.exclude_pattern:
        query = query.where(~Document.source_url.like(filters.exclude_pattern.replace("*", "%")))

    # Apply content type filter
    if filters.with_content_type:
        query = query.where(Document.content_type == filters.with_content_type)

    # Apply limit
    if filters.limit and filters.limit > 0:
        query = query.limit(filters.limit)

    # Execute query
    documents = session.exec(query).all()

    # Load content and prepare payloads
    payloads = []
    for doc in documents:
        try:
            # Load content from filesystem
            content = ""
            if doc.content_path:
                try:
                    content = load_document_content(doc, strip_frontmatter=True)
                except Exception as e:
                    logger.warning(f"Failed to load content for document {doc.id}: {e}")
                    content = ""

            # Compute content hash
            content_hash = hashlib.sha256(content.encode()).hexdigest()

            # Determine skip logic
            skip = False
            skip_reason = None

            if not force and incremental_mode == "delta":
                # Check if content has changed since last indexing
                if doc.indexed_with_hash and doc.indexed_with_hash == content_hash:
                    skip = True
                    skip_reason = "content_unchanged"

            # Build payload
            payload = {
                "document_id": str(doc.id),
                "title": doc.title or "",
                "source_url": doc.source_url,
                "source_type": doc.source_type,
                "content": content,
                "content_hash": content_hash,
                "content_path": doc.content_path,
                "content_type": doc.content_type,
                "ingestion_status": doc.ingestion_status.value if doc.ingestion_status else None,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                "workflow_id": workflow_id,
                "skip": skip,
                "skip_reason": skip_reason,
                "previous_hash": doc.indexed_with_hash,
            }

            payloads.append(payload)

        except Exception as e:
            logger.error(f"Error processing document {doc.id}: {e}", exc_info=True)
            continue

    logger.info(
        f"Loaded {len(payloads)} documents (mode: {incremental_mode}, "
        f"skipped: {sum(1 for p in payloads if p['skip'])})"
    )

    return payloads


def load_previous_state(document_id: str, table_name: str) -> Dict[str, Any]:
    """
    Load previous state for a document from a specific table.

    This is a generic utility for loading any previous state data.

    Args:
        document_id: Document UUID
        table_name: Table name to query

    Returns:
        Dict of previous state data or empty dict if not found
    """
    import sqlite3

    import pandas as pd

    from kurt.db.database import get_session

    get_session()

    # Get the database path from config
    config = get_config_or_default()
    db_path = Path(config.PATH_DB)

    if not db_path.exists():
        return {}

    try:
        conn = sqlite3.connect(db_path)

        # Check if table exists
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
        )
        if not cursor.fetchone():
            conn.close()
            return {}

        # Load data for this document
        query = f"SELECT * FROM {table_name} WHERE document_id = ?"
        df = pd.read_sql_query(query, conn, params=[document_id])
        conn.close()

        if df.empty:
            return {}

        # Convert to dict
        return df.to_dict("records")

    except Exception as e:
        logger.warning(f"Error loading previous state from {table_name}: {e}")
        return {}


def load_document_with_state(
    document_id: str,
    filters: Optional[DocumentFilters] = None,
    incremental_mode: str = "full",
    workflow_id: Optional[str] = None,
    force: bool = False,
    include_previous_state: bool = False,
    state_tables: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Load a single document with optional previous state.

    This combines document loading with state retrieval for workflows
    that need both current content and historical data.

    Args:
        document_id: Document UUID to load
        filters: Optional additional filters
        incremental_mode: Processing mode
        workflow_id: Optional workflow ID
        force: Force processing even if unchanged
        include_previous_state: Whether to load previous state
        state_tables: List of tables to load previous state from

    Returns:
        Document payload with optional previous_state field
    """
    # Use filters to load specific document
    if filters is None:
        filters = DocumentFilters(ids=document_id)
    else:
        # Add document ID to existing filters
        filters.ids = document_id

    # Load document
    docs = load_documents(filters, incremental_mode, workflow_id, force)

    if not docs:
        raise ValueError(f"Document {document_id} not found")

    doc = docs[0]

    # Load previous state if requested
    if include_previous_state:
        doc["previous_state"] = {}

        if state_tables is None:
            # Default tables to check - these are common in Kurt
            state_tables = [
                "entities",
                "claims",
                "section_extractions",
                "document_summaries",
            ]

        for table in state_tables:
            state = load_previous_state(document_id, table)
            if state:
                doc["previous_state"][table] = state

    return doc
