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


def get_document_stats(include_pattern: Optional[str] = None) -> dict:
    """
    Get statistics about documents in the database.

    Args:
        include_pattern: Optional glob pattern to filter documents (e.g., "*docs.dagster.io*")

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

        # With filter
        stats = get_document_stats(include_pattern="*docs.dagster.io*")
    """
    from fnmatch import fnmatch

    from sqlmodel import func

    session = get_session()

    # Build base query with optional filtering
    if include_pattern:
        # Get all documents matching pattern
        all_docs_stmt = select(Document)
        all_docs = session.exec(all_docs_stmt).all()

        # Filter by glob pattern
        filtered_docs = []
        for doc in all_docs:
            if doc.source_url and fnmatch(doc.source_url, include_pattern):
                filtered_docs.append(doc)
            elif doc.content_path and fnmatch(str(doc.content_path), include_pattern):
                filtered_docs.append(doc)

        # Count by status
        total = len(filtered_docs)
        not_fetched = sum(
            1 for d in filtered_docs if d.ingestion_status == IngestionStatus.NOT_FETCHED
        )
        fetched = sum(1 for d in filtered_docs if d.ingestion_status == IngestionStatus.FETCHED)
        error = sum(1 for d in filtered_docs if d.ingestion_status == IngestionStatus.ERROR)
    else:
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


def list_clusters() -> list[dict]:
    """
    List all topic clusters with document counts.

    Returns:
        List of dictionaries with cluster information:
            - id: UUID
            - name: str
            - description: str
            - created_at: datetime
            - doc_count: int

    Example:
        clusters = list_clusters()
        for cluster in clusters:
            print(f"{cluster['name']}: {cluster['doc_count']} docs")
    """
    from sqlalchemy import func, select

    from kurt.db.models import DocumentClusterEdge, TopicCluster

    session = get_session()

    # Get all clusters with document counts
    stmt = (
        select(
            TopicCluster.id,
            TopicCluster.name,
            TopicCluster.description,
            TopicCluster.created_at,
            func.count(DocumentClusterEdge.document_id).label("doc_count"),
        )
        .outerjoin(DocumentClusterEdge, TopicCluster.id == DocumentClusterEdge.cluster_id)
        .group_by(TopicCluster.id)
        .order_by(func.count(DocumentClusterEdge.document_id).desc())
    )

    results = session.exec(stmt).all()

    # Convert to list of dicts
    clusters = []
    for row in results:
        clusters.append(
            {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "created_at": row.created_at,
                "doc_count": row.doc_count,
            }
        )

    return clusters


def list_content(
    with_status: str = None,
    include_pattern: str = None,
    in_cluster: str = None,
    with_content_type: str = None,
    max_depth: int = None,
    limit: int = None,
    offset: int = 0,
) -> list[Document]:
    """
    List documents with new explicit naming (for CLI-SPEC.md compliance).

    This is the new API-compliant version of list_documents() with explicit naming.

    Args:
        with_status: Filter by status (NOT_FETCHED | FETCHED | ERROR)
        include_pattern: Glob pattern matching source_url or content_path
        in_cluster: Filter by cluster name (case-insensitive)
        with_content_type: Filter by content type (tutorial | guide | blog | etc)
        max_depth: Filter by maximum URL depth (e.g., 2 for example.com/a/b)
        limit: Maximum number of documents to return
        offset: Number of documents to skip (for pagination)

    Returns:
        List of Document objects

    Example:
        # List all documents
        docs = list_content()

        # List only fetched documents
        docs = list_content(with_status="FETCHED")

        # List documents matching pattern
        docs = list_content(include_pattern="*/docs/*")

        # List documents in cluster
        docs = list_content(in_cluster="Tutorials")

        # Filter by URL depth
        docs = list_content(max_depth=2)

        # Combine filters
        docs = list_content(with_status="FETCHED", include_pattern="*/blog/*", max_depth=2)
    """
    from fnmatch import fnmatch

    from kurt.db.models import DocumentClusterEdge, TopicCluster

    session = get_session()

    # Build query
    stmt = select(Document)

    # Apply cluster filter (JOIN with edges and clusters tables)
    if in_cluster:
        stmt = (
            stmt.join(DocumentClusterEdge, Document.id == DocumentClusterEdge.document_id)
            .join(TopicCluster, DocumentClusterEdge.cluster_id == TopicCluster.id)
            .where(TopicCluster.name.ilike(f"%{in_cluster}%"))
        )

    # Apply status filter
    if with_status:
        status_enum = IngestionStatus(with_status)
        stmt = stmt.where(Document.ingestion_status == status_enum)

    # Apply content_type filter
    if with_content_type:
        from kurt.db.models import ContentType

        content_type_enum = ContentType(with_content_type.lower())
        stmt = stmt.where(Document.content_type == content_type_enum)

    # Apply ordering (most recent first)
    stmt = stmt.order_by(Document.created_at.desc())

    # Apply pagination
    if offset:
        stmt = stmt.offset(offset)
    if limit:
        stmt = stmt.limit(limit)

    # Execute query
    documents = list(session.exec(stmt).all())

    # Apply glob pattern filtering (post-query)
    if include_pattern:
        documents = [
            d
            for d in documents
            if (d.source_url and fnmatch(d.source_url, include_pattern))
            or (d.content_path and fnmatch(d.content_path, include_pattern))
        ]

    # Apply max_depth filtering (post-query)
    if max_depth is not None:
        from kurt.utils.url_utils import get_url_depth

        documents = [d for d in documents if get_url_depth(d.source_url) <= max_depth]

    return documents


def list_documents_for_indexing(
    doc_id: Optional[str] = None,
    include_pattern: Optional[str] = None,
    all_flag: bool = False,
) -> list[Document]:
    """
    Get documents that need to be indexed based on filtering criteria.

    This function encapsulates the business logic for selecting documents
    for the indexing process. It handles three modes:
    1. Single document by ID
    2. All FETCHED documents matching a glob pattern
    3. All FETCHED documents (when all_flag is True)

    Args:
        doc_id: Document ID (full or partial UUID, minimum 8 chars)
        include_pattern: Glob pattern to filter documents (e.g., "*/docs/*")
        all_flag: If True, return all FETCHED documents

    Returns:
        List of Document objects ready for indexing

    Raises:
        ValueError: If doc_id is provided but document not found or is ambiguous
        ValueError: If no filtering criteria provided

    Example:
        # Get single document
        docs = list_documents_for_indexing(doc_id="44ea066e")

        # Get all documents matching pattern
        docs = list_documents_for_indexing(include_pattern="*/docs/*")

        # Get all FETCHED documents
        docs = list_documents_for_indexing(all_flag=True)
    """
    from fnmatch import fnmatch

    # Validate input - need at least one filtering criterion
    if not doc_id and not include_pattern and not all_flag:
        raise ValueError("Must provide either doc_id, include_pattern, or all_flag=True")

    # Mode 1: Single document by ID
    if doc_id:
        doc = get_document(doc_id)
        return [doc]

    # Mode 2 & 3: Batch mode - get FETCHED documents
    if include_pattern or all_flag:
        # Get all FETCHED documents (no limit for indexing)
        docs = list_documents(
            status=IngestionStatus.FETCHED,
            url_prefix=None,
            url_contains=None,
            limit=None,
        )

        # Apply glob pattern filter if provided
        if include_pattern:
            docs = [
                d
                for d in docs
                if (d.source_url and fnmatch(d.source_url, include_pattern))
                or (d.content_path and fnmatch(d.content_path, include_pattern))
            ]

        return docs

    # Should never reach here due to initial validation
    raise ValueError("Must provide either doc_id, include_pattern, or all_flag=True")
