"""
Pure filtering logic for document fetch operations.

This module provides business logic for building document filter specifications.
NO DATABASE OPERATIONS - returns filter specs that workflows use for DB queries.

Pattern:
- Business logic (pure): Build filter specifications
- Workflow (DB ops): Apply filters to database
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DocumentFetchFilters:
    """Filter specification for selecting documents to fetch.

    This is a pure data structure - no DB queries, just the specification.
    Workflows use this to build and execute DB queries.
    """

    # Raw filter inputs (from CLI)
    include_pattern: Optional[str] = None
    exclude_pattern: Optional[str] = None
    ids: Optional[str] = None  # Comma-separated
    urls: Optional[str] = None  # Comma-separated
    files: Optional[str] = None  # Comma-separated
    in_cluster: Optional[str] = None
    with_status: Optional[str] = None
    with_content_type: Optional[str] = None
    limit: Optional[int] = None
    refetch: bool = False

    # Parsed filter values (computed from raw inputs)
    url_list: list[str] = None
    file_list: list[str] = None
    id_list: list[str] = None

    def __post_init__(self):
        """Parse comma-separated strings into lists."""
        # Parse URLs
        if self.urls:
            self.url_list = [url.strip() for url in self.urls.split(",") if url.strip()]
        else:
            self.url_list = []

        # Parse files
        if self.files:
            self.file_list = [f.strip() for f in self.files.split(",") if f.strip()]
        else:
            self.file_list = []

        # Parse IDs
        if self.ids:
            self.id_list = [id_str.strip() for id_str in self.ids.split(",") if id_str.strip()]
        else:
            self.id_list = []


def build_document_filters(
    include_pattern: str = None,
    urls: str = None,
    files: str = None,
    ids: str = None,
    in_cluster: str = None,
    with_status: str = None,
    with_content_type: str = None,
    exclude: str = None,
    limit: int = None,
    refetch: bool = False,
) -> DocumentFetchFilters:
    """
    Build filter specification for document selection.

    This is PURE BUSINESS LOGIC - no database queries!
    Returns a data structure that workflows use to query the database.

    Args:
        include_pattern: Glob pattern matching source_url or content_path
        urls: Comma-separated list of source URLs
        files: Comma-separated list of local file paths
        ids: Comma-separated list of document IDs
        in_cluster: Cluster name filter
        with_status: Status filter (NOT_FETCHED | FETCHED | ERROR)
        with_content_type: Content type filter
        exclude: Glob pattern to exclude
        limit: Maximum documents to return
        refetch: If True, include FETCHED documents

    Returns:
        DocumentFetchFilters object with parsed filter specification

    Raises:
        ValueError: If no filter provided

    Example:
        >>> filters = build_document_filters(
        ...     urls="https://example.com/page1,https://example.com/page2",
        ...     with_status="NOT_FETCHED"
        ... )
        >>> # Returns: DocumentFetchFilters(url_list=['https://...'], ...)
        >>> # Workflow then uses this to query database
    """
    # Validate: at least one filter required
    if not (
        include_pattern or urls or files or ids or in_cluster or with_status or with_content_type
    ):
        raise ValueError(
            "Requires at least ONE filter: --include, --url, --urls, --file, --files, "
            "--ids, --in-cluster, --with-status, or --with-content-type"
        )

    return DocumentFetchFilters(
        include_pattern=include_pattern,
        exclude_pattern=exclude,
        ids=ids,
        urls=urls,
        files=files,
        in_cluster=in_cluster,
        with_status=with_status,
        with_content_type=with_content_type,
        limit=limit,
        refetch=refetch,
    )


def estimate_fetch_cost(document_count: int, skip_index: bool = False) -> float:
    """
    Estimate LLM cost for fetching documents.

    Pure calculation - no external dependencies.

    Args:
        document_count: Number of documents to fetch
        skip_index: If True, skip indexing cost

    Returns:
        Estimated cost in USD

    Example:
        >>> estimate_fetch_cost(10, skip_index=False)
        0.05  # $0.005 per document
        >>> estimate_fetch_cost(10, skip_index=True)
        0.0  # No LLM calls if skipping index
    """
    if skip_index:
        return 0.0

    # Cost breakdown:
    # - Embedding generation: ~$0.0001 per document
    # - Metadata extraction: ~$0.005 per document
    return document_count * 0.005


def select_documents_for_fetch(
    include_pattern: str = None,
    urls: str = None,
    files: str = None,
    ids: str = None,
    in_cluster: str = None,
    with_status: str = None,
    with_content_type: str = None,
    exclude: str = None,
    limit: int = None,
    skip_index: bool = False,
    refetch: bool = False,
) -> dict:
    """
    Select documents to fetch based on filters.
    Leverages filtering.py helpers for query building and document.py for CRUD.
    """
    from uuid import UUID

    from kurt.content.document import add_documents_for_files, add_documents_for_urls
    from kurt.content.filtering import (
        apply_glob_filters,
        build_document_query,
        resolve_ids_to_uuids,
    )
    from kurt.db.database import get_session
    from kurt.db.models import IngestionStatus

    # Validate: at least one filter required
    if not (
        include_pattern or urls or files or ids or in_cluster or with_status or with_content_type
    ):
        raise ValueError(
            "Requires at least ONE filter: --include, --url, --urls, --file, --files, --ids, --in-cluster, --with-status, or --with-content-type"
        )

    warnings = []
    errors = []
    session = get_session()

    # Step 1: Create documents for URLs (calls document.py helper)
    url_list = []
    if urls:
        url_list = [url.strip() for url in urls.split(",")]
        _, new_count = add_documents_for_urls(url_list)
        if new_count > 0:
            warnings.append(f"Auto-created {new_count} document(s) for new URLs")

    # Step 2: Create documents for files (calls document.py helper)
    file_doc_ids = []
    if files:
        file_list = [f.strip() for f in files.split(",")]
        file_docs, new_count, file_errors, copied_files = add_documents_for_files(file_list)
        errors.extend(file_errors)
        # Add copied file messages to warnings
        warnings.extend(copied_files)
        if new_count > 0:
            warnings.append(f"Created {new_count} document(s) for local files")
        file_doc_ids = [doc.id for doc in file_docs if doc.id]

    # Step 3: Resolve IDs to UUIDs (calls filtering.py helper)
    id_uuids = []
    if ids:
        try:
            uuid_strs = resolve_ids_to_uuids(ids)
            id_uuids = [UUID(uuid_str) for uuid_str in uuid_strs]
        except ValueError as e:
            errors.append(str(e))

    # Merge file doc IDs with resolved IDs
    if file_doc_ids:
        id_uuids.extend(file_doc_ids)

    # Merge URL filtering (if URLs provided, filter to those URLs)
    if url_list and not id_uuids:
        # Query for documents matching these URLs
        from sqlmodel import select

        from kurt.db.models import Document

        stmt = select(Document).where(Document.source_url.in_(url_list))
        url_docs = list(session.exec(stmt).all())
        id_uuids = [doc.id for doc in url_docs]

    # Step 4: Build query (calls filtering.py helper - NO logic here!)
    stmt = build_document_query(
        id_uuids=id_uuids if id_uuids else None,
        with_status=with_status,
        refetch=refetch,
        in_cluster=in_cluster,
        with_content_type=with_content_type,
        limit=limit,
    )

    # Execute query without status filter to check for FETCHED documents
    if not with_status and not refetch and id_uuids:
        # For ID-based queries, query without status filter to find FETCHED docs
        stmt_no_filter = build_document_query(
            id_uuids=id_uuids,
            with_status=None,
            refetch=True,  # Include all statuses
            in_cluster=in_cluster,
            with_content_type=with_content_type,
            limit=None,
        )
        docs_before_status_filter = list(session.exec(stmt_no_filter).all())
    elif not with_status and not refetch:
        # For pattern-based queries
        docs_before_status_filter = list(session.exec(stmt).all())
    else:
        docs_before_status_filter = []

    # Re-build query with status filter for final results
    stmt = build_document_query(
        id_uuids=id_uuids if id_uuids else None,
        with_status=with_status,
        refetch=refetch,
        in_cluster=in_cluster,
        with_content_type=with_content_type,
        limit=None,  # Don't apply limit yet - apply after glob filtering
    )
    docs = list(session.exec(stmt).all())

    # Step 5: Apply glob filters (calls filtering.py helper)
    filtered_docs = apply_glob_filters(docs, include_pattern, exclude)

    # Apply limit after filtering
    if limit:
        filtered_docs = filtered_docs[:limit]

    # Warn if >100 docs
    if len(filtered_docs) > 100:
        warnings.append(f"About to fetch {len(filtered_docs)} documents")

    # Calculate estimated cost
    estimated_cost = estimate_fetch_cost(len(filtered_docs), skip_index)

    # Count excluded FETCHED documents
    excluded_fetched_count = 0
    if not with_status and not refetch and docs_before_status_filter:
        fetched_docs = [
            d for d in docs_before_status_filter if d.ingestion_status == IngestionStatus.FETCHED
        ]
        excluded_fetched_count = len(fetched_docs)

    return {
        "docs": filtered_docs,
        "doc_ids": [str(doc.id) for doc in filtered_docs],
        "total": len(filtered_docs),
        "warnings": warnings,
        "errors": errors,
        "estimated_cost": estimated_cost,
        "excluded_fetched_count": excluded_fetched_count,
    }


def select_documents_to_fetch(filters: DocumentFetchFilters) -> list[dict]:
    """
    Select documents to fetch based on filters (for workflow steps).

    Returns lightweight dicts suitable for checkpointing.
    """
    from kurt.content.document import add_documents_for_files, add_documents_for_urls
    from kurt.content.filtering import (
        apply_glob_filters,
        build_document_query,
        resolve_ids_to_uuids,
    )
    from kurt.db.database import get_session

    session = get_session()

    # Step 1: Create documents for URLs
    if filters.url_list:
        add_documents_for_urls(filters.url_list)

    # Step 2: Create documents for files
    if filters.file_list:
        add_documents_for_files(filters.file_list)

    # Step 3: Resolve IDs to UUIDs
    id_uuids = []
    if filters.id_list:
        id_uuids = resolve_ids_to_uuids(filters.id_list)

    # Step 4: Build and execute query
    stmt = build_document_query(
        id_uuids=id_uuids,
        with_status=filters.with_status,
        refetch=filters.refetch,
        in_cluster=filters.in_cluster,
        with_content_type=filters.with_content_type,
        limit=filters.limit,
    )
    docs = list(session.exec(stmt).all())

    # Step 5: Apply glob filters
    filtered_docs = apply_glob_filters(
        docs,
        include_pattern=filters.include_pattern,
        exclude_pattern=filters.exclude_pattern,
    )

    # Convert to lightweight dicts for checkpoint
    return [
        {
            "id": str(doc.id),
            "source_url": doc.source_url,
            "cms_platform": doc.cms_platform,
            "cms_instance": doc.cms_instance,
            "cms_document_id": doc.cms_document_id,
            "discovery_url": doc.discovery_url,
        }
        for doc in filtered_docs
    ]


__all__ = [
    "DocumentFetchFilters",
    "build_document_filters",
    "estimate_fetch_cost",
    "select_documents_for_fetch",
    "select_documents_to_fetch",
]
