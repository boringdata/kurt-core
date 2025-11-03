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

from sqlmodel import func, select

from kurt.db.database import get_session
from kurt.db.models import Document, DocumentAnalytics, IngestionStatus


def list_documents(
    status: Optional[IngestionStatus] = None,
    url_prefix: Optional[str] = None,
    url_contains: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    # Analytics filters
    with_analytics: bool = False,
    pageviews_30d_min: Optional[int] = None,
    pageviews_30d_max: Optional[int] = None,
    pageviews_trend: Optional[str] = None,
    order_by: Optional[str] = None,
) -> list[Document]:
    """
    List all documents with optional filtering.

    Args:
        status: Filter by ingestion status (NOT_FETCHED, FETCHED, ERROR)
        url_prefix: Filter by URL prefix (e.g., "https://example.com")
        url_contains: Filter by URL substring (e.g., "blog")
        limit: Maximum number of documents to return
        offset: Number of documents to skip (for pagination)
        with_analytics: Include analytics data in results (LEFT JOIN)
        pageviews_30d_min: Filter by minimum pageviews (last 30 days)
        pageviews_30d_max: Filter by maximum pageviews (last 30 days)
        pageviews_trend: Filter by trend ("increasing", "stable", "decreasing")
        order_by: Sort results by field (created_at, pageviews_30d, pageviews_60d, trend_percentage)

    Returns:
        List of Document objects (with analytics data attached if with_analytics=True)

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

        # Filter by analytics (high-traffic pages)
        docs = list_documents(with_analytics=True, pageviews_30d_min=500, order_by="pageviews_30d")

        # Filter by traffic trend
        docs = list_documents(with_analytics=True, pageviews_trend="decreasing")
    """
    session = get_session()

    # Determine if we need analytics JOIN
    needs_analytics = (
        with_analytics
        or pageviews_30d_min is not None
        or pageviews_30d_max is not None
        or pageviews_trend is not None
        or (order_by and order_by in ["pageviews_30d", "pageviews_60d", "trend_percentage"])
    )

    # Build query
    if needs_analytics:
        # LEFT JOIN to include documents without analytics
        stmt = select(Document).outerjoin(
            DocumentAnalytics, Document.id == DocumentAnalytics.document_id
        )
    else:
        stmt = select(Document)

    # Apply basic filters
    if status:
        stmt = stmt.where(Document.ingestion_status == status)
    if url_prefix:
        stmt = stmt.where(Document.source_url.startswith(url_prefix))
    if url_contains:
        stmt = stmt.where(Document.source_url.contains(url_contains))

    # Apply analytics filters
    if pageviews_30d_min is not None:
        stmt = stmt.where(DocumentAnalytics.pageviews_30d >= pageviews_30d_min)
    if pageviews_30d_max is not None:
        stmt = stmt.where(DocumentAnalytics.pageviews_30d <= pageviews_30d_max)
    if pageviews_trend:
        stmt = stmt.where(DocumentAnalytics.pageviews_trend == pageviews_trend)

    # Apply ordering
    if order_by:
        if order_by == "pageviews_30d":
            stmt = stmt.order_by(DocumentAnalytics.pageviews_30d.desc())
        elif order_by == "pageviews_60d":
            stmt = stmt.order_by(DocumentAnalytics.pageviews_60d.desc())
        elif order_by == "trend_percentage":
            stmt = stmt.order_by(DocumentAnalytics.trend_percentage.desc())
        elif order_by == "created_at":
            stmt = stmt.order_by(Document.created_at.desc())
    else:
        # Default ordering (most recent first)
        stmt = stmt.order_by(Document.created_at.desc())

    # Apply pagination
    if offset:
        stmt = stmt.offset(offset)
    if limit:
        stmt = stmt.limit(limit)

    # Execute query
    documents = session.exec(stmt).all()

    # Return Document objects directly
    # Note: Analytics data is accessible via document.analytics relationship if loaded
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


def get_analytics_stats(url_prefix: Optional[str] = None) -> dict:
    """
    Get analytics statistics with percentile-based traffic thresholds.

    Calculates traffic distribution for the given domain and returns
    percentile thresholds for categorizing pages as HIGH/MEDIUM/LOW/ZERO traffic.

    Args:
        url_prefix: Optional URL prefix to scope stats (e.g., "https://docs.company.com")

    Returns:
        Dictionary with analytics statistics:
            - total_with_analytics: int
            - total_zero_traffic: int
            - avg_pageviews_30d: float
            - median_pageviews_30d: int
            - p75_pageviews_30d: int (75th percentile - HIGH traffic threshold)
            - p25_pageviews_30d: int (25th percentile - LOW traffic threshold)
            - traffic_categories: dict with counts per category

    Example:
        stats = get_analytics_stats(url_prefix="https://docs.company.com")
        print(f"HIGH traffic threshold (p75): {stats['p75_pageviews_30d']} views/month")
        print(f"Pages with ZERO traffic: {stats['total_zero_traffic']}")
    """
    session = get_session()

    # Build query for documents with analytics
    stmt = (
        select(DocumentAnalytics)
        .join(Document, Document.id == DocumentAnalytics.document_id)
    )

    if url_prefix:
        stmt = stmt.where(Document.source_url.startswith(url_prefix))

    analytics = session.exec(stmt).all()

    if not analytics:
        return {
            "total_with_analytics": 0,
            "total_zero_traffic": 0,
            "avg_pageviews_30d": 0,
            "median_pageviews_30d": 0,
            "p75_pageviews_30d": 0,
            "p25_pageviews_30d": 0,
            "traffic_categories": {
                "zero": 0,
                "low": 0,
                "medium": 0,
                "high": 0,
            },
        }

    # Extract pageviews and sort
    pageviews = [a.pageviews_30d for a in analytics]
    pageviews_sorted = sorted(pageviews)
    total = len(pageviews_sorted)

    # Count zero traffic pages
    zero_traffic = sum(1 for pv in pageviews if pv == 0)

    # Remove zeros for percentile calculation
    pageviews_nonzero = [pv for pv in pageviews_sorted if pv > 0]

    if not pageviews_nonzero:
        # All pages have zero traffic
        return {
            "total_with_analytics": total,
            "total_zero_traffic": zero_traffic,
            "avg_pageviews_30d": 0,
            "median_pageviews_30d": 0,
            "p75_pageviews_30d": 0,
            "p25_pageviews_30d": 0,
            "traffic_categories": {
                "zero": zero_traffic,
                "low": 0,
                "medium": 0,
                "high": 0,
            },
        }

    # Calculate statistics
    avg = sum(pageviews_nonzero) / len(pageviews_nonzero)

    # Percentiles (using non-zero traffic only)
    def percentile(data, p):
        """Calculate percentile (0-100)"""
        if not data:
            return 0
        n = len(data)
        idx = int(n * p / 100)
        return data[min(idx, n - 1)]

    median = percentile(pageviews_nonzero, 50)
    p25 = percentile(pageviews_nonzero, 25)
    p75 = percentile(pageviews_nonzero, 75)

    # Categorize pages using percentiles
    # ZERO: 0 views
    # LOW: >0 and <= p25
    # MEDIUM: >p25 and <= p75
    # HIGH: >p75
    categories = {
        "zero": zero_traffic,
        "low": sum(1 for pv in pageviews_nonzero if pv <= p25),
        "medium": sum(1 for pv in pageviews_nonzero if p25 < pv <= p75),
        "high": sum(1 for pv in pageviews_nonzero if pv > p75),
    }

    return {
        "total_with_analytics": total,
        "total_zero_traffic": zero_traffic,
        "avg_pageviews_30d": round(avg, 1),
        "median_pageviews_30d": median,
        "p75_pageviews_30d": p75,
        "p25_pageviews_30d": p25,
        "traffic_categories": categories,
    }
