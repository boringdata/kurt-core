"""Document filtering and resolution utilities.

This module provides document filtering and identifier resolution functionality
that can be used by CLI commands, agents, and other parts of the system.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DocumentFilters:
    """Resolved document filters for querying.

    Attributes:
        ids: Comma-separated document IDs (supports partial UUIDs, URLs, file paths)
        include_pattern: Glob pattern matching source_url or content_path
        in_cluster: Cluster name filter
        with_status: Ingestion status filter (NOT_FETCHED, FETCHED, ERROR)
        with_content_type: Content type filter (tutorial, guide, blog, etc.)
        with_entity: Entity filter in format "EntityType:EntityName" (e.g., "Topic:Python", "Technology:FastAPI")
        with_relationship: Relationship filter in format "Entity1:RelationType:Entity2" (e.g., "Python:USES:FastAPI")
        limit: Maximum number of documents to process/display
        exclude_pattern: Glob pattern for exclusion (used in fetch)
    """

    ids: Optional[str] = None
    include_pattern: Optional[str] = None
    in_cluster: Optional[str] = None
    with_status: Optional[str] = None
    with_content_type: Optional[str] = None
    with_entity: Optional[str] = None
    with_relationship: Optional[str] = None
    limit: Optional[int] = None
    exclude_pattern: Optional[str] = None


def resolve_identifier_to_doc_id(identifier: str) -> str:
    """
    Resolve an identifier (ID, URL, or file path) to a document ID.

    Supports:
    - Full UUIDs: "550e8400-e29b-41d4-a716-446655440000"
    - Partial UUIDs: "550e8400" (minimum 8 characters)
    - URLs: "https://example.com/article"
    - File paths: "./docs/article.md"

    Args:
        identifier: Document ID, URL, or file path

    Returns:
        Document ID as string (full UUID)

    Raises:
        ValueError: If identifier cannot be resolved or is ambiguous

    Example:
        doc_id = resolve_identifier_to_doc_id("550e8400")
        doc_id = resolve_identifier_to_doc_id("https://example.com/article")
        doc_id = resolve_identifier_to_doc_id("./docs/article.md")
    """
    from kurt.db.documents import get_document, list_documents

    # Check if it's a URL
    if identifier.startswith(("http://", "https://")):
        # Look up document by URL
        matching_docs = [d for d in list_documents() if d.source_url == identifier]
        if not matching_docs:
            raise ValueError(f"Document not found: {identifier}")
        return str(matching_docs[0].id)

    # Check if it's a file path
    elif (
        os.path.exists(identifier) or identifier.startswith(("./", "../", "/")) or "/" in identifier
    ):
        # Look up document by content_path
        # Try both absolute and relative path matching
        abs_path = os.path.abspath(identifier)

        # Get all documents
        all_docs = list_documents()

        # Try multiple matching strategies
        matching_docs = []

        # Strategy 1: Exact match on content_path
        for d in all_docs:
            if d.content_path == identifier:
                matching_docs.append(d)

        # Strategy 2: Absolute path match
        if not matching_docs:
            for d in all_docs:
                if d.content_path and os.path.abspath(d.content_path) == abs_path:
                    matching_docs.append(d)

        # Strategy 3: Relative path from sources/ directory (common case)
        if not matching_docs and identifier.startswith("sources/"):
            rel_path = identifier[8:]  # Remove "sources/" prefix
            for d in all_docs:
                if d.content_path and d.content_path == rel_path:
                    matching_docs.append(d)

        # Strategy 4: Suffix match (last resort)
        if not matching_docs:
            for d in all_docs:
                if d.content_path and d.content_path.endswith(identifier):
                    matching_docs.append(d)

        if not matching_docs:
            raise ValueError(
                f"Document not found for file: {identifier}\nTip: Use 'kurt content list' to see available documents"
            )

        if len(matching_docs) > 1:
            raise ValueError(
                f"Ambiguous file path: {identifier} matches {len(matching_docs)} documents. "
                f"Use document ID instead."
            )

        return str(matching_docs[0].id)

    # Assume it's a document ID (full or partial)
    else:
        # get_document already supports partial UUIDs
        doc = get_document(identifier)
        return str(doc.id)


def resolve_ids_to_uuids(ids_str: str) -> list[str]:
    """
    Resolve comma-separated identifiers to full UUIDs.

    Each identifier can be:
    - Full UUID
    - Partial UUID (minimum 8 characters)
    - URL (resolves to document with that URL)
    - File path (resolves to document with that content_path)

    Args:
        ids_str: Comma-separated list of identifiers

    Returns:
        List of full UUIDs as strings

    Raises:
        ValueError: If any identifier cannot be resolved

    Example:
        uuids = resolve_ids_to_uuids("550e8400,https://example.com/article,docs/file.md")
    """
    uuids = []
    errors = []

    for id_str in ids_str.split(","):
        id_str = id_str.strip()
        if not id_str:
            continue

        try:
            doc_id = resolve_identifier_to_doc_id(id_str)
            uuids.append(doc_id)
        except ValueError as e:
            errors.append(f"{id_str}: {e}")

    if errors:
        raise ValueError("Failed to resolve identifiers:\n" + "\n".join(errors))

    return uuids


def resolve_filters(
    identifier: Optional[str] = None,
    ids: Optional[str] = None,
    include_pattern: Optional[str] = None,
    in_cluster: Optional[str] = None,
    with_status: Optional[str] = None,
    with_content_type: Optional[str] = None,
    with_entity: Optional[str] = None,
    with_relationship: Optional[str] = None,
    limit: Optional[int] = None,
    exclude_pattern: Optional[str] = None,
) -> DocumentFilters:
    """
    Resolve and merge filters, especially handling positional IDENTIFIER.

    The positional IDENTIFIER argument (if provided) is resolved to a document ID
    and merged into the ids filter. This provides a clean API where:
    - `kurt index DOC_ID` is shorthand for `kurt index --ids DOC_ID`
    - `kurt index DOC_ID --ids "ID1,ID2"` becomes `--ids "DOC_ID,ID1,ID2"`

    Args:
        identifier: Positional identifier (doc ID, URL, or file path)
        ids: Comma-separated document IDs
        include_pattern: Glob pattern for inclusion
        in_cluster: Cluster name filter
        with_status: Ingestion status filter
        with_content_type: Content type filter
        with_entity: Entity filter in format "EntityType:EntityName"
        with_relationship: Relationship filter in format "Entity1:RelationType:Entity2"
        limit: Maximum number of documents
        exclude_pattern: Glob pattern for exclusion

    Returns:
        DocumentFilters instance with resolved and merged filters

    Example:
        # Simple case
        filters = resolve_filters(identifier="44ea066e")
        # filters.ids == "44ea066e-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

        # Merging case
        filters = resolve_filters(
            identifier="44ea066e",
            ids="550e8400,a73af781",
            include_pattern="*/docs/*"
        )
        # filters.ids == "44ea066e-xxxx-xxxx-xxxx-xxxxxxxxxxxx,550e8400,a73af781"
        # filters.include_pattern == "*/docs/*"

        # Entity filtering
        filters = resolve_filters(with_entity="Topic:Python")
        # filters.with_entity == "Topic:Python"

        # Relationship filtering
        filters = resolve_filters(with_relationship="Python:USES:FastAPI")
        # filters.with_relationship == "Python:USES:FastAPI"
    """
    # If identifier provided, resolve and merge into ids
    resolved_ids = ids
    if identifier:
        try:
            doc_id = resolve_identifier_to_doc_id(identifier)
            if resolved_ids:
                # Merge: identifier comes first
                resolved_ids = f"{doc_id},{resolved_ids}"
            else:
                resolved_ids = doc_id
        except ValueError as e:
            # Let the caller handle the error
            raise ValueError(f"Failed to resolve identifier '{identifier}': {e}")

    return DocumentFilters(
        ids=resolved_ids,
        include_pattern=include_pattern,
        in_cluster=in_cluster,
        with_status=with_status,
        with_content_type=with_content_type,
        with_entity=with_entity,
        with_relationship=with_relationship,
        limit=limit,
        exclude_pattern=exclude_pattern,
    )


# ============================================================================
# Query Building for Document Selection (Helper for workflows)
# ============================================================================


def build_document_query(
    id_uuids: list,
    with_status: str = None,
    refetch: bool = False,
    in_cluster: str = None,
    with_content_type: str = None,
    limit: int = None,
    session=None,
):
    """
    Build SQLModel query for document selection.

    Pure query construction - no execution, just returns the statement.
    Used by workflows to construct DB queries from filter specifications.

    Args:
        id_uuids: List of UUIDs to filter by
        with_status: Status filter (NOT_FETCHED | FETCHED | ERROR)
        refetch: If True, include FETCHED documents
        in_cluster: Cluster name filter
        with_content_type: Content type filter
        limit: Maximum documents to return
        session: Optional SQLModel session (for testing with isolated sessions)

    Returns:
        SQLModel Select statement

    Example:
        >>> stmt = build_document_query(
        ...     id_uuids=[uuid1, uuid2],
        ...     with_status="NOT_FETCHED",
        ...     limit=10
        ... )
        >>> # Then execute: docs = session.exec(stmt).all()
    """
    from sqlalchemy import text
    from sqlmodel import select

    from kurt.db.documents import _get_status_subquery, _table_exists
    from kurt.db.models import Document

    # Get session for table existence checks
    if session is None:
        from kurt.db.database import get_session

        session = get_session()

    stmt = select(Document)

    # Filter by IDs
    if id_uuids:
        stmt = stmt.where(Document.id.in_(id_uuids))

    # Filter by status using helper that handles missing staging tables
    if with_status:
        status_upper = with_status.upper()
        status_subquery = _get_status_subquery(session, status_upper)
        if status_subquery:
            stmt = stmt.where(text(status_subquery))
    elif not refetch:
        # Default: exclude FETCHED documents unless refetch=True
        status_subquery = _get_status_subquery(session, "NOT_FETCHED")
        if status_subquery:
            stmt = stmt.where(text(status_subquery))

    # Filter by cluster (uses staging_topic_clustering table)
    if in_cluster:
        if _table_exists(session, "staging_topic_clustering"):
            # Use REPLACE to strip hyphens from UUID for comparison
            # (staging tables store UUIDs without hyphens)
            stmt = stmt.where(
                text(
                    f"REPLACE(CAST(id AS TEXT), '-', '') IN ("
                    f"SELECT document_id FROM staging_topic_clustering "
                    f"WHERE cluster_name = '{in_cluster}')"
                )
            )
        else:
            # No documents can match if table doesn't exist
            stmt = stmt.where(text("1=0"))

    # Filter by content type (uses staging_topic_clustering table)
    if with_content_type:
        if _table_exists(session, "staging_topic_clustering"):
            # Use REPLACE to strip hyphens from UUID for comparison
            # (staging tables store UUIDs without hyphens)
            stmt = stmt.where(
                text(
                    f"REPLACE(CAST(id AS TEXT), '-', '') IN ("
                    f"SELECT document_id FROM staging_topic_clustering "
                    f"WHERE content_type = '{with_content_type.lower()}')"
                )
            )
        else:
            # No documents can match if table doesn't exist
            stmt = stmt.where(text("1=0"))

    # Apply limit
    if limit:
        stmt = stmt.limit(limit)

    return stmt


def should_include_document(doc_url: str, doc_path: str, include_pattern: str) -> bool:
    """Check if document matches include pattern using glob matching."""
    from fnmatch import fnmatch

    if not include_pattern:
        return True

    return (doc_url and fnmatch(doc_url, include_pattern)) or (
        doc_path and fnmatch(doc_path, include_pattern)
    )


def should_exclude_document(doc_url: str, doc_path: str, exclude_pattern: str) -> bool:
    """Check if document matches exclude pattern using glob matching."""
    from fnmatch import fnmatch

    if not exclude_pattern:
        return False

    return (doc_url and fnmatch(doc_url, exclude_pattern)) or (
        doc_path and fnmatch(doc_path, exclude_pattern)
    )


def apply_glob_filters(
    docs: list, include_pattern: str = None, exclude_pattern: str = None
) -> list:
    """
    Apply glob pattern filters to document list.

    Pure filtering function - no DB operations.
    Uses should_include_document and should_exclude_document helpers.

    Args:
        docs: List of Document objects
        include_pattern: Glob pattern to include (e.g., "*/api/*")
        exclude_pattern: Glob pattern to exclude (e.g., "*/internal/*")

    Returns:
        Filtered list of Document objects

    Example:
        >>> filtered = apply_glob_filters(
        ...     docs,
        ...     include_pattern="*/docs/*",
        ...     exclude_pattern="*/api/*"
        ... )
    """
    filtered_docs = []
    for doc in docs:
        # Include pattern
        if include_pattern:
            if not should_include_document(
                doc.source_url or "", doc.content_path or "", include_pattern
            ):
                continue

        # Exclude pattern
        if exclude_pattern:
            if should_exclude_document(
                doc.source_url or "", doc.content_path or "", exclude_pattern
            ):
                continue

        filtered_docs.append(doc)

    return filtered_docs


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

    from kurt.db.database import get_session
    from kurt.db.documents import add_documents_for_files, add_documents_for_urls
    from kurt.utils.filtering import (
        apply_glob_filters,
        build_document_query,
        resolve_ids_to_uuids,
    )

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

    # Count excluded FETCHED documents (uses staging tables)
    excluded_fetched_count = 0
    if not with_status and not refetch and docs_before_status_filter:
        # Query landing_fetch to find which docs are fetched
        from sqlalchemy import text

        doc_ids_str = ",".join(f"'{str(d.id)}'" for d in docs_before_status_filter)
        try:
            fetched_sql = text(f"""
                SELECT COUNT(DISTINCT document_id) as count
                FROM landing_fetch
                WHERE document_id IN ({doc_ids_str})
                AND status = 'FETCHED'
            """)
            excluded_fetched_count = session.execute(fetched_sql).scalar() or 0
        except Exception:
            excluded_fetched_count = 0

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
    from kurt.db.database import get_session
    from kurt.db.documents import add_documents_for_files, add_documents_for_urls
    from kurt.utils.filtering import (
        apply_glob_filters,
        build_document_query,
        resolve_ids_to_uuids,
    )

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
    # Note: discovery_url removed from Document model - now in landing_discovery table
    return [
        {
            "id": str(doc.id),
            "source_url": doc.source_url,
            "cms_platform": doc.cms_platform,
            "cms_instance": doc.cms_instance,
            "cms_document_id": doc.cms_document_id,
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
