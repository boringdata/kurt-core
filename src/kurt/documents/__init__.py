"""
Document lifecycle management for kurt.

Provides a unified view of documents across all workflow stages.
DocumentView is a virtual aggregation - not a persisted table.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kurt.documents.filtering import DocumentFilters
from kurt.documents.models import DocumentView
from kurt.documents.registry import DocumentRegistry

# Lazy import to avoid requiring heavy ML dependencies (trafilatura, lxml) in API mode
if TYPE_CHECKING:
    from kurt.workflows.fetch.utils import load_document_content as _load_document_content
else:
    _load_document_content = None

__all__ = [
    "DocumentView",
    "DocumentRegistry",
    "DocumentFilters",
    "resolve_documents",
    "load_document_content",
]


def load_document_content(*args, **kwargs):
    """Lazy wrapper for load_document_content to avoid importing trafilatura in API mode."""
    global _load_document_content
    if _load_document_content is None:
        from kurt.workflows.fetch.utils import load_document_content as _ldc

        _load_document_content = _ldc
    return _load_document_content(*args, **kwargs)


def resolve_documents(
    *,
    identifier: str | None = None,
    include_pattern: str | None = None,
    ids: str | None = None,
    in_cluster: str | None = None,
    with_status: str | None = None,
    with_content_type: str | None = None,
    limit: int | None = None,
    # Advanced filters
    exclude_pattern: str | None = None,
    url_contains: str | None = None,
    file_ext: str | None = None,
    source_type: str | None = None,
    has_content: bool | None = None,
    min_content_length: int | None = None,
    fetch_engine: str | None = None,
    # Direct URL/file input
    urls: str | None = None,
    files: str | None = None,
) -> list[dict[str, Any]]:
    """
    Resolve documents from CLI parameters to list of dicts for workflow input.

    This is the CLI adapter layer that maps CLI option names to internal filter names.

    Args:
        identifier: Single document ID or URL
        include_pattern: Glob pattern to include (e.g., "*/docs/*")
        ids: Comma-separated document IDs
        in_cluster: Filter by cluster name
        with_status: Filter by status (NOT_FETCHED, FETCHED, ERROR)
        with_content_type: Filter by content type
        limit: Maximum number of documents
        exclude_pattern: Glob pattern to exclude
        url_contains: Filter URLs containing this substring
        file_ext: Filter by file extension (e.g., "md", "html")
        source_type: Filter by source type (url, file, cms)
        has_content: Filter documents with/without content
        min_content_length: Minimum content length in characters
        fetch_engine: Filter by fetch engine (trafilatura, firecrawl, httpx)
        urls: Comma-separated URLs (filter to only these URLs)
        files: Comma-separated file paths (filter to only these files)
    """
    import hashlib
    from pathlib import Path

    from kurt.db import managed_session
    from kurt.workflows.fetch.models import FetchStatus
    from kurt.workflows.map.models import MapDocument, MapStatus

    # If identifier looks like a URL, auto-create MapDocument if needed
    if identifier and identifier.startswith(("http://", "https://")):
        from sqlmodel import select

        with managed_session() as session:
            existing = session.exec(
                select(MapDocument).where(MapDocument.source_url == identifier)
            ).first()
            if not existing:
                doc_id = hashlib.sha256(identifier.encode()).hexdigest()[:12]
                doc = MapDocument(
                    document_id=doc_id,
                    source_url=identifier,
                    source_type="url",
                    status=MapStatus.SUCCESS,
                    discovery_method="cli",
                )
                session.add(doc)
                session.commit()

    # Build list of source URLs to filter by (from urls/files options)
    source_urls_filter: list[str] | None = None
    if urls or files:
        source_urls_filter = []
        if urls:
            source_urls_filter.extend([u.strip() for u in urls.split(",") if u.strip()])
        if files:
            # Resolve file paths to absolute paths
            source_urls_filter.extend(
                [str(Path(f.strip()).resolve()) for f in files.split(",") if f.strip()]
            )

    # Build internal filters
    # If identifier is a URL, don't use it as an ID filter (we'll filter by source_url later)
    identifier_is_url = identifier and identifier.startswith(("http://", "https://"))
    filters = DocumentFilters(
        ids=[identifier]
        if identifier and not identifier_is_url
        else (ids.split(",") if ids else None),
        include=include_pattern,
        exclude=exclude_pattern,
        url_contains=url_contains,
        limit=limit,
        source_type=source_type.lower() if source_type else None,
        has_content=has_content,
        min_content_length=min_content_length,
        fetch_engine=fetch_engine.lower() if fetch_engine else None,
    )

    # If identifier is a URL, add it to source_urls_filter
    if identifier_is_url:
        if source_urls_filter is None:
            source_urls_filter = []
        source_urls_filter.append(identifier)

    # Map CLI status to internal
    if with_status:
        status_upper = with_status.upper()
        if status_upper == "NOT_FETCHED":
            filters.not_fetched = True
        elif status_upper == "FETCHED":
            filters.fetch_status = FetchStatus.SUCCESS
        elif status_upper == "ERROR":
            filters.fetch_status = FetchStatus.ERROR

    # Query documents
    registry = DocumentRegistry()
    with managed_session() as session:
        docs = registry.list(session, filters)

    # Apply post-query filters (glob patterns are applied in registry.list via apply_glob_filters)
    # Apply additional substring/extension filters here
    result_docs = list(docs)

    # Filter by specific URLs/files if provided
    if source_urls_filter:
        result_docs = [d for d in result_docs if d.source_url in source_urls_filter]

    # File extension filter
    if file_ext:
        ext = file_ext.lstrip(".")  # Normalize: "md" or ".md" -> "md"
        result_docs = [d for d in result_docs if d.source_url.endswith(f".{ext}")]

    # Deduplicate by source_url (keep first occurrence - older document)
    seen_urls: set[str] = set()
    unique_docs = []
    for d in result_docs:
        if d.source_url not in seen_urls:
            seen_urls.add(d.source_url)
            unique_docs.append(d)
    result_docs = unique_docs

    # Convert to dicts for workflow input
    return [
        {
            "document_id": d.document_id,
            "source_url": d.source_url,
            "source_type": d.source_type,
            "title": d.title,
            "discovery_url": d.discovery_url,
            "metadata_json": d.metadata,
        }
        for d in result_docs
    ]
