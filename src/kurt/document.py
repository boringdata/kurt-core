"""
Document utility functions for Kurt.

These functions provide CRUD operations for documents:
- list_documents: List all documents with filtering
- get_document: Get document by ID
- delete_document: Delete document by ID
- get_document_stats: Get statistics about documents

These can be used directly by agents or wrapped by CLI commands.
"""

from typing import Optional
from uuid import UUID

from sqlmodel import select

from kurt.db.database import get_session
from kurt.db.models import Document, IngestionStatus


def list_documents(
    status: Optional[IngestionStatus] = None,
    url_prefix: Optional[str] = None,
    url_contains: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> list[Document]:
    """
    List all documents with optional filtering.

    Args:
        status: Filter by ingestion status (NOT_FETCHED, FETCHED, ERROR)
        url_prefix: Filter by URL prefix (e.g., "https://example.com")
        url_contains: Filter by URL substring (e.g., "blog")
        limit: Maximum number of documents to return
        offset: Number of documents to skip (for pagination)

    Returns:
        List of Document objects

    Example:
        # List all documents
        docs = list_documents()

        # List only fetched documents
        docs = list_documents(status=IngestionStatus.FETCHED)

        # List documents from specific domain
        docs = list_documents(url_prefix="https://example.com")

        # List documents with "blog" in URL
        docs = list_documents(url_contains="blog")

        # Combine filters
        docs = list_documents(status=IngestionStatus.FETCHED, url_prefix="https://example.com")

        # List first 10 documents
        docs = list_documents(limit=10)

        # Pagination: skip first 10, get next 10
        docs = list_documents(limit=10, offset=10)
    """
    session = get_session()

    # Build query
    stmt = select(Document)

    # Apply filters
    if status:
        stmt = stmt.where(Document.ingestion_status == status)
    if url_prefix:
        stmt = stmt.where(Document.source_url.startswith(url_prefix))
    if url_contains:
        stmt = stmt.where(Document.source_url.contains(url_contains))

    # Apply ordering (most recent first)
    stmt = stmt.order_by(Document.created_at.desc())

    # Apply pagination
    if offset:
        stmt = stmt.offset(offset)
    if limit:
        stmt = stmt.limit(limit)

    # Execute query
    documents = session.exec(stmt).all()

    # Return Document objects directly
    return list(documents)


def get_document(document_id: str) -> Document:
    """
    Get document by ID (supports partial UUIDs).

    Args:
        document_id: Document UUID as string (full or partial, minimum 8 chars)

    Returns:
        Document object

    Raises:
        ValueError: If document not found or ID is ambiguous

    Example:
        doc = get_document("550e8400-e29b-41d4-a716-446655440000")
        doc = get_document("550e8400")  # Partial UUID also works
        print(doc.title)
        print(doc.description)
    """
    session = get_session()

    # Try full UUID first
    try:
        doc_uuid = UUID(document_id)
        doc = session.get(Document, doc_uuid)

        if not doc:
            raise ValueError(f"Document not found: {document_id}")
    except ValueError:
        # Try partial UUID match
        if len(document_id) < 8:
            raise ValueError(f"Document ID too short (minimum 8 characters): {document_id}")

        # Search for documents where ID starts with the partial UUID
        # Convert UUID to string format without hyphens for matching
        stmt = select(Document)
        docs = session.exec(stmt).all()

        # Filter by partial match (comparing without hyphens)
        partial_lower = document_id.lower().replace("-", "")
        matches = [d for d in docs if str(d.id).replace("-", "").startswith(partial_lower)]

        if len(matches) == 0:
            raise ValueError(f"Document not found: {document_id}")
        elif len(matches) > 1:
            raise ValueError(
                f"Ambiguous document ID '{document_id}' matches {len(matches)} documents. "
                f"Please provide more characters."
            )

        doc = matches[0]

    # Return Document object
    return doc


def delete_document(document_id: str, delete_content: bool = False) -> dict:
    """
    Delete document by ID (supports partial UUIDs).

    Args:
        document_id: Document UUID as string (full or partial, minimum 8 chars)
        delete_content: If True, also delete content file from filesystem

    Returns:
        Dictionary with deletion result:
            - deleted_id: str
            - title: str
            - content_deleted: bool

    Raises:
        ValueError: If document not found or ID is ambiguous

    Example:
        # Delete document (keep content file)
        result = delete_document("550e8400-e29b-41d4-a716-446655440000")
        result = delete_document("550e8400")  # Partial UUID also works

        # Delete document and content file
        result = delete_document("550e8400", delete_content=True)
    """

    from kurt.config import load_config

    session = get_session()

    # Try full UUID first
    try:
        doc_uuid = UUID(document_id)
        doc = session.get(Document, doc_uuid)

        if not doc:
            raise ValueError(f"Document not found: {document_id}")
    except ValueError:
        # Try partial UUID match
        if len(document_id) < 8:
            raise ValueError(f"Document ID too short (minimum 8 characters): {document_id}")

        # Search for documents where ID starts with the partial UUID
        stmt = select(Document)
        docs = session.exec(stmt).all()

        # Filter by partial match (comparing without hyphens)
        partial_lower = document_id.lower().replace("-", "")
        matches = [d for d in docs if str(d.id).replace("-", "").startswith(partial_lower)]

        if len(matches) == 0:
            raise ValueError(f"Document not found: {document_id}")
        elif len(matches) > 1:
            raise ValueError(
                f"Ambiguous document ID '{document_id}' matches {len(matches)} documents. "
                f"Please provide more characters."
            )

        doc = matches[0]

    # Store info for result
    title = doc.title
    content_path = doc.content_path
    content_deleted = False

    # Delete content file if requested
    if delete_content and content_path:
        try:
            config = load_config()
            source_base = config.get_absolute_sources_path()
            full_path = source_base / content_path

            if full_path.exists():
                full_path.unlink()
                content_deleted = True
        except Exception:
            # Ignore content deletion errors
            pass

    # Delete document from database
    session.delete(doc)
    session.commit()

    return {
        "deleted_id": str(doc_uuid),
        "title": title,
        "content_deleted": content_deleted,
    }


def get_document_stats() -> dict:
    """
    Get statistics about documents in the database.

    Returns:
        Dictionary with statistics:
            - total: int (total number of documents)
            - not_fetched: int
            - fetched: int
            - error: int

    Example:
        stats = get_document_stats()
        print(f"Total: {stats['total']}")
        print(f"Fetched: {stats['fetched']}")
    """
    from sqlmodel import func

    session = get_session()

    # Count total documents
    total_stmt = select(func.count(Document.id))
    total = session.exec(total_stmt).one()

    # Count by status
    not_fetched_stmt = select(func.count(Document.id)).where(
        Document.ingestion_status == IngestionStatus.NOT_FETCHED
    )
    not_fetched = session.exec(not_fetched_stmt).one()

    fetched_stmt = select(func.count(Document.id)).where(
        Document.ingestion_status == IngestionStatus.FETCHED
    )
    fetched = session.exec(fetched_stmt).one()

    error_stmt = select(func.count(Document.id)).where(
        Document.ingestion_status == IngestionStatus.ERROR
    )
    error = session.exec(error_stmt).one()

    return {
        "total": total,
        "not_fetched": not_fetched,
        "fetched": fetched,
        "error": error,
    }
