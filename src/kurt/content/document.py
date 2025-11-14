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


def get_document_stats(
    include_pattern: Optional[str] = None,
    in_cluster: Optional[str] = None,
    with_status: Optional[str] = None,
    with_content_type: Optional[str] = None,
    limit: Optional[int] = None,
) -> dict:
    """
    Get statistics about documents in the database.

    Args:
        include_pattern: Optional glob pattern to filter documents (e.g., "*docs.dagster.io*")
        in_cluster: Optional cluster name to filter documents
        with_status: Optional ingestion status filter (NOT_FETCHED, FETCHED, ERROR)
        with_content_type: Optional content type filter (tutorial, guide, blog, etc.)
        limit: Optional limit on number of documents to include in stats

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
        stats = get_document_stats(in_cluster="Tutorials", with_status="FETCHED")
    """
    from fnmatch import fnmatch

    session = get_session()

    # Build base query
    stmt = select(Document)

    # Apply filters (SQL-based when possible)
    if with_status:
        status_enum = IngestionStatus[with_status.upper()]
        stmt = stmt.where(Document.ingestion_status == status_enum)

    if in_cluster:
        # Join with clusters to filter
        from kurt.db.models import ClusterMembership

        stmt = stmt.join(ClusterMembership, Document.id == ClusterMembership.document_id).where(
            ClusterMembership.cluster_name == in_cluster
        )

    if with_content_type:
        # Need to join with document_classifications
        from kurt.db.models import DocumentClassification

        stmt = stmt.join(
            DocumentClassification, Document.id == DocumentClassification.document_id
        ).where(DocumentClassification.document_type == with_content_type)

    # Fetch documents (need glob filtering)
    all_docs = session.exec(stmt).all()

    # Apply glob pattern filtering (post-fetch)
    if include_pattern:
        filtered_docs = []
        for doc in all_docs:
            if doc.source_url and fnmatch(doc.source_url, include_pattern):
                filtered_docs.append(doc)
            elif doc.content_path and fnmatch(str(doc.content_path), include_pattern):
                filtered_docs.append(doc)
        all_docs = filtered_docs

    # Apply limit
    if limit and len(all_docs) > limit:
        all_docs = all_docs[:limit]

    # Count by status
    total = len(all_docs)
    not_fetched = sum(1 for d in all_docs if d.ingestion_status == IngestionStatus.NOT_FETCHED)
    fetched = sum(1 for d in all_docs if d.ingestion_status == IngestionStatus.FETCHED)
    error = sum(1 for d in all_docs if d.ingestion_status == IngestionStatus.ERROR)

    return {
        "total": total,
        "not_fetched": not_fetched,
        "fetched": fetched,
        "error": error,
    }


# Analytics stats moved to telemetry module
# For backwards compatibility, re-export it here
def get_analytics_stats(include_pattern: Optional[str] = None) -> dict:
    """Get analytics statistics (deprecated: use kurt.telemetry.analytics.get_analytics_stats)."""
    from kurt.admin.telemetry.analytics import get_analytics_stats as _get_analytics_stats

    return _get_analytics_stats(include_pattern=include_pattern)


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
    with_analytics: bool = False,
    order_by: str = None,
    min_pageviews: int = None,
    max_pageviews: int = None,
    trend: str = None,
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
        with_analytics: Include analytics data (pageviews, trends)
        order_by: Sort by analytics metric (pageviews_30d | pageviews_60d | trend_percentage)
        min_pageviews: Minimum pageviews_30d filter
        max_pageviews: Maximum pageviews_30d filter
        trend: Filter by trend (increasing | decreasing | stable)

    Returns:
        List of Document objects (with analytics dict attribute if with_analytics=True)

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

        # With analytics
        docs = list_content(with_analytics=True, order_by="pageviews_30d", limit=10)
        docs = list_content(with_analytics=True, trend="decreasing", min_pageviews=1000)

        # Combine filters
        docs = list_content(with_status="FETCHED", include_pattern="*/blog/*", max_depth=2)
    """
    from fnmatch import fnmatch

    from kurt.db.models import DocumentAnalytics, DocumentClusterEdge, TopicCluster

    session = get_session()

    # Build query with optional analytics join
    if with_analytics:
        # Select both Document and DocumentAnalytics
        stmt = select(Document, DocumentAnalytics).outerjoin(
            DocumentAnalytics, Document.id == DocumentAnalytics.document_id
        )
    else:
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

    # Apply analytics filters
    if with_analytics:
        if min_pageviews is not None:
            stmt = stmt.where(
                (DocumentAnalytics.pageviews_30d >= min_pageviews)
                | (DocumentAnalytics.pageviews_30d.is_(None))
            )
        if max_pageviews is not None:
            stmt = stmt.where(
                (DocumentAnalytics.pageviews_30d <= max_pageviews)
                | (DocumentAnalytics.pageviews_30d.is_(None))
            )
        if trend:
            from kurt.db.models import TrendType

            trend_enum = TrendType(trend.lower())
            stmt = stmt.where(DocumentAnalytics.pageviews_trend == trend_enum)

    # Apply ordering
    if with_analytics and order_by:
        # Order by analytics field
        order_field_map = {
            "pageviews_30d": DocumentAnalytics.pageviews_30d,
            "pageviews_60d": DocumentAnalytics.pageviews_60d,
            "trend_percentage": DocumentAnalytics.trend_percentage,
        }
        order_field = order_field_map.get(order_by)
        if order_field is not None:
            # NULL values last, then descending
            stmt = stmt.order_by(order_field.desc().nullslast())
    else:
        # Default ordering (most recent first)
        stmt = stmt.order_by(Document.created_at.desc())

    # Apply pagination
    if offset:
        stmt = stmt.offset(offset)
    if limit:
        stmt = stmt.limit(limit)

    # Execute query
    results = session.exec(stmt).all()

    # Process results
    if with_analytics:
        # results is a list of tuples (Document, DocumentAnalytics or None)
        documents = []
        for doc, analytics in results:
            # Attach analytics data as dict attribute
            if analytics:
                doc.analytics = {
                    "pageviews_30d": analytics.pageviews_30d,
                    "pageviews_60d": analytics.pageviews_60d,
                    "pageviews_previous_30d": analytics.pageviews_previous_30d,
                    "unique_visitors_30d": analytics.unique_visitors_30d,
                    "pageviews_trend": analytics.pageviews_trend.value
                    if analytics.pageviews_trend
                    else None,
                    "trend_percentage": analytics.trend_percentage,
                }
            else:
                doc.analytics = None
            documents.append(doc)
    else:
        documents = list(results)

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
    ids: Optional[str] = None,
    include_pattern: Optional[str] = None,
    in_cluster: Optional[str] = None,
    with_status: Optional[str] = None,
    with_content_type: Optional[str] = None,
    all_flag: bool = False,
) -> list[Document]:
    """
    Get documents that need to be indexed based on filtering criteria.

    This function encapsulates the business logic for selecting documents
    for the indexing process. It handles multiple modes:
    1. Single or multiple documents by IDs (comma-separated)
    2. All FETCHED documents in a cluster
    3. All FETCHED documents matching a glob pattern
    4. All FETCHED documents with specific status
    5. All FETCHED documents with specific content type
    6. All FETCHED documents (when all_flag is True)

    Args:
        ids: Comma-separated list of document IDs (full/partial UUIDs, URLs, or file paths)
        include_pattern: Glob pattern to filter documents (e.g., "*/docs/*")
        in_cluster: Cluster name to filter documents
        with_status: Filter by ingestion status (NOT_FETCHED, FETCHED, ERROR)
        with_content_type: Filter by content type (tutorial, guide, blog, etc.)
        all_flag: If True, return all FETCHED documents

    Returns:
        List of Document objects ready for indexing

    Raises:
        ValueError: If identifier cannot be resolved or is ambiguous
        ValueError: If no filtering criteria provided

    Example:
        # Get single or multiple documents by IDs
        docs = list_documents_for_indexing(ids="44ea066e")
        docs = list_documents_for_indexing(ids="44ea066e,550e8400,a73af781")

        # Get documents in a cluster
        docs = list_documents_for_indexing(in_cluster="Tutorials")

        # Get all documents matching pattern
        docs = list_documents_for_indexing(include_pattern="*/docs/*")

        # Get all FETCHED documents
        docs = list_documents_for_indexing(all_flag=True)

        # Get documents by status
        docs = list_documents_for_indexing(with_status="FETCHED")

        # Get documents by content type
        docs = list_documents_for_indexing(with_content_type="tutorial")
    """
    from fnmatch import fnmatch

    # Validate input - need at least one filtering criterion
    if (
        not ids
        and not include_pattern
        and not in_cluster
        and not with_status
        and not with_content_type
        and not all_flag
    ):
        raise ValueError(
            "Must provide either ids, include_pattern, in_cluster, with_status, with_content_type, or all_flag=True"
        )

    # Mode 1: Documents by IDs (single or multiple, supports partial UUIDs/URLs/file paths)
    if ids:
        from kurt.content.filtering import resolve_ids_to_uuids

        try:
            # Resolve all identifiers to full UUIDs
            uuid_strs = resolve_ids_to_uuids(ids)
            docs = []
            for uuid_str in uuid_strs:
                try:
                    doc = get_document(uuid_str)
                    docs.append(doc)
                except ValueError:
                    # Skip invalid IDs but continue with others
                    pass
            return docs
        except ValueError as e:
            raise ValueError(f"Failed to resolve identifiers: {e}")

    # Mode 2+: Batch mode - get documents by filters
    if include_pattern or in_cluster or with_status or with_content_type or all_flag:
        # Determine status filter (default to FETCHED if not specified)
        if with_status:
            try:
                status_filter = IngestionStatus[with_status]
            except KeyError:
                raise ValueError(
                    f"Invalid status: {with_status}. Must be one of: NOT_FETCHED, FETCHED, ERROR"
                )
        else:
            # Default to FETCHED for backwards compatibility
            status_filter = IngestionStatus.FETCHED

        # Get documents with status filter
        docs = list_documents(
            status=status_filter,
            url_prefix=None,
            url_contains=None,
            limit=None,
        )

        # Apply cluster filter if provided
        if in_cluster:
            docs = [d for d in docs if d.cluster and d.cluster == in_cluster]

        # Apply content type filter if provided
        if with_content_type:
            from kurt.db.database import get_session
            from kurt.db.models import DocumentClassification

            session = get_session()
            # Get document IDs with matching content type
            classified_ids = set()
            for doc in docs:
                classification = (
                    session.query(DocumentClassification)
                    .filter(DocumentClassification.document_id == doc.id)
                    .first()
                )
                if classification and classification.document_type == with_content_type:
                    classified_ids.add(doc.id)

            docs = [d for d in docs if d.id in classified_ids]

        # Apply glob pattern filter if provided
        if include_pattern:
            # First, check if pattern matches any documents (regardless of status)
            all_docs_any_status = list_documents(limit=None)
            matching_any_status = [
                d
                for d in all_docs_any_status
                if (d.source_url and fnmatch(d.source_url, include_pattern))
                or (d.content_path and fnmatch(d.content_path, include_pattern))
            ]

            # Filter documents by pattern
            docs = [
                d
                for d in docs
                if (d.source_url and fnmatch(d.source_url, include_pattern))
                or (d.content_path and fnmatch(d.content_path, include_pattern))
            ]

            # If no docs with requested status but pattern matched other statuses, provide helpful error
            if not docs and matching_any_status:
                status_counts = {}
                for d in matching_any_status:
                    status = d.ingestion_status.value
                    status_counts[status] = status_counts.get(status, 0) + 1

                status_summary = ", ".join(
                    [f"{count} {status}" for status, count in status_counts.items()]
                )
                raise ValueError(
                    f"Found {len(matching_any_status)} document(s) matching pattern '{include_pattern}' "
                    f"({status_summary}), but none are {status_filter.value}.\n"
                    f"Tip: Use 'kurt fetch --include \"{include_pattern}\"' to fetch these documents first."
                )

        return docs

    # Should never reach here due to initial validation
    raise ValueError(
        "Must provide either ids, include_pattern, in_cluster, with_status, with_content_type, or all_flag=True"
    )
