"""
Document filtering for lifecycle queries.

Internal API uses clean names (status, include, limit).
CLI adapter layer (future) will map to kurt-style names (--with-status, --in-cluster).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from fnmatch import fnmatch
from typing import TYPE_CHECKING, Optional, Sequence

from sqlalchemy import or_
from sqlalchemy.sql import Select
from sqlmodel import select

from kurt_new.workflows.fetch.models import FetchDocument, FetchStatus
from kurt_new.workflows.map.models import MapDocument, MapStatus

if TYPE_CHECKING:
    from kurt_new.documents.models import DocumentView


@dataclass
class DocumentFilters:
    """Filters for querying documents across their lifecycle.

    Internal API - clean names, type-safe.
    """

    # Identity filters
    ids: Optional[list[str]] = None
    include: Optional[str] = None  # glob pattern on source_url
    exclude: Optional[str] = None  # glob pattern to exclude

    # Lifecycle stage filters
    map_status: Optional[MapStatus] = None
    fetch_status: Optional[FetchStatus] = None

    # Cross-stage queries
    not_fetched: bool = False  # mapped but not yet fetched
    has_error: Optional[bool] = None  # error in any stage

    # Source filters
    source_type: Optional[str] = None  # "url" | "file" | "cms"
    discovery_method: Optional[str] = None  # "sitemap" | "crawl" | "folder"
    discovery_url: Optional[str] = None  # parent URL

    # Fetch-specific
    fetch_engine: Optional[str] = None  # "trafilatura" | "firecrawl" | "httpx"
    has_content: Optional[bool] = None  # content_length > 0
    min_content_length: Optional[int] = None

    # Tenant
    user_id: Optional[str] = None
    workspace_id: Optional[str] = None

    # Time filters
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None

    # Pagination
    limit: Optional[int] = None
    offset: Optional[int] = None

    # Ordering
    order_by: Optional[str] = None  # field name
    order_desc: bool = False


def build_map_query(filters: DocumentFilters) -> Select:
    """Build SQLModel query for MapDocument table."""
    query = select(MapDocument)

    if filters.ids:
        query = query.where(MapDocument.document_id.in_(filters.ids))

    if filters.map_status:
        query = query.where(MapDocument.status == filters.map_status)

    if filters.source_type:
        query = query.where(MapDocument.source_type == filters.source_type)

    if filters.discovery_method:
        query = query.where(MapDocument.discovery_method == filters.discovery_method)

    if filters.discovery_url:
        query = query.where(MapDocument.discovery_url == filters.discovery_url)

    if filters.has_error is True:
        query = query.where(MapDocument.error.isnot(None))
    elif filters.has_error is False:
        query = query.where(MapDocument.error.is_(None))

    if filters.user_id:
        query = query.where(MapDocument.user_id == filters.user_id)

    if filters.workspace_id:
        query = query.where(MapDocument.workspace_id == filters.workspace_id)

    if filters.created_after:
        query = query.where(MapDocument.created_at >= filters.created_after)

    if filters.created_before:
        query = query.where(MapDocument.created_at <= filters.created_before)

    if filters.offset:
        query = query.offset(filters.offset)

    if filters.limit:
        query = query.limit(filters.limit)

    return query


def build_fetch_query(filters: DocumentFilters) -> Select:
    """Build SQLModel query for FetchDocument table."""
    query = select(FetchDocument)

    if filters.ids:
        query = query.where(FetchDocument.document_id.in_(filters.ids))

    if filters.fetch_status:
        query = query.where(FetchDocument.status == filters.fetch_status)

    if filters.fetch_engine:
        query = query.where(FetchDocument.fetch_engine == filters.fetch_engine)

    if filters.has_content is True:
        query = query.where(FetchDocument.content_length > 0)
    elif filters.has_content is False:
        query = query.where(FetchDocument.content_length == 0)

    if filters.min_content_length:
        query = query.where(FetchDocument.content_length >= filters.min_content_length)

    if filters.has_error is True:
        query = query.where(FetchDocument.error.isnot(None))
    elif filters.has_error is False:
        query = query.where(FetchDocument.error.is_(None))

    if filters.user_id:
        query = query.where(FetchDocument.user_id == filters.user_id)

    if filters.workspace_id:
        query = query.where(FetchDocument.workspace_id == filters.workspace_id)

    if filters.created_after:
        query = query.where(FetchDocument.created_at >= filters.created_after)

    if filters.created_before:
        query = query.where(FetchDocument.created_at <= filters.created_before)

    if filters.offset:
        query = query.offset(filters.offset)

    if filters.limit:
        query = query.limit(filters.limit)

    return query


def build_joined_query(filters: DocumentFilters) -> Select:
    """Build query joining map and fetch tables for full lifecycle view."""
    query = select(MapDocument, FetchDocument).outerjoin(
        FetchDocument, MapDocument.document_id == FetchDocument.document_id
    )

    # Map filters
    if filters.ids:
        query = query.where(MapDocument.document_id.in_(filters.ids))

    if filters.map_status:
        query = query.where(MapDocument.status == filters.map_status)

    if filters.source_type:
        query = query.where(MapDocument.source_type == filters.source_type)

    if filters.discovery_method:
        query = query.where(MapDocument.discovery_method == filters.discovery_method)

    if filters.discovery_url:
        query = query.where(MapDocument.discovery_url == filters.discovery_url)

    # Fetch filters
    if filters.fetch_status:
        query = query.where(FetchDocument.status == filters.fetch_status)

    if filters.fetch_engine:
        query = query.where(FetchDocument.fetch_engine == filters.fetch_engine)

    if filters.has_content is True:
        query = query.where(FetchDocument.content_length > 0)
    elif filters.has_content is False:
        query = query.where(
            or_(FetchDocument.content_length == 0, FetchDocument.content_length.is_(None))
        )

    if filters.min_content_length:
        query = query.where(FetchDocument.content_length >= filters.min_content_length)

    # Cross-stage filters
    if filters.not_fetched:
        query = query.where(
            or_(FetchDocument.document_id.is_(None), FetchDocument.status == FetchStatus.PENDING)
        )

    # Error in any stage
    if filters.has_error is True:
        query = query.where(or_(MapDocument.error.isnot(None), FetchDocument.error.isnot(None)))
    elif filters.has_error is False:
        query = query.where(MapDocument.error.is_(None)).where(
            or_(FetchDocument.error.is_(None), FetchDocument.document_id.is_(None))
        )

    # Tenant
    if filters.user_id:
        query = query.where(MapDocument.user_id == filters.user_id)

    if filters.workspace_id:
        query = query.where(MapDocument.workspace_id == filters.workspace_id)

    # Time
    if filters.created_after:
        query = query.where(MapDocument.created_at >= filters.created_after)

    if filters.created_before:
        query = query.where(MapDocument.created_at <= filters.created_before)

    # Pagination
    if filters.offset:
        query = query.offset(filters.offset)

    if filters.limit:
        query = query.limit(filters.limit)

    return query


def apply_glob_filters(
    docs: Sequence["DocumentView"],
    include: Optional[str] = None,
    exclude: Optional[str] = None,
) -> list["DocumentView"]:
    """Apply glob pattern filtering on source_url (post-query).

    Args:
        docs: Documents to filter
        include: Glob pattern to include (e.g., "*/docs/*")
        exclude: Glob pattern to exclude (e.g., "*/internal/*")

    Returns:
        Filtered list of documents
    """
    result = list(docs)

    if include:
        result = [d for d in result if fnmatch(d.source_url, include)]

    if exclude:
        result = [d for d in result if not fnmatch(d.source_url, exclude)]

    return result
