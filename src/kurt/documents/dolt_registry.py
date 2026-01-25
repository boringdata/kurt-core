"""
Dolt-based document registry.

Provides document listing and retrieval from the unified Dolt `documents` table.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from kurt.documents.filtering import DocumentFilters


@dataclass
class DoltDocumentView:
    """Unified view of a document from Dolt."""

    document_id: str
    source_url: str
    source_type: str | None = None
    title: str | None = None
    fetch_status: str | None = None
    content_path: str | None = None
    content_hash: str | None = None
    content_length: int | None = None
    error: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Computed from metadata
    discovery_method: str | None = None
    discovery_url: str | None = None
    is_new: bool | None = None
    map_status: str | None = None
    fetch_engine: str | None = None
    public_url: str | None = None
    discovered_at: datetime | None = None
    fetched_at: datetime | None = None

    # For backward compatibility
    user_id: str | None = None
    workspace_id: str | None = None


def _row_to_view(row: dict[str, Any]) -> DoltDocumentView:
    """Convert a Dolt row to DoltDocumentView."""
    # Parse metadata JSON
    metadata = row.get("metadata")
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}
    metadata = metadata or {}

    return DoltDocumentView(
        document_id=row.get("id"),
        source_url=row.get("url"),
        source_type=row.get("source_type"),
        title=metadata.get("title"),
        fetch_status=row.get("fetch_status"),
        content_path=row.get("content_path"),
        content_hash=row.get("content_hash"),
        content_length=metadata.get("content_length") or metadata.get("bytes_fetched"),
        error=row.get("error"),
        metadata=metadata,
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        # From metadata
        discovery_method=metadata.get("discovery_method"),
        discovery_url=metadata.get("discovery_url"),
        is_new=metadata.get("is_new"),
        map_status=metadata.get("map_status"),
        fetch_engine=metadata.get("fetch_engine"),
        public_url=metadata.get("public_url"),
        discovered_at=row.get("created_at"),  # created_at is discovery time
        fetched_at=row.get("updated_at") if row.get("fetch_status") == "success" else None,
    )


def list_documents_dolt(filters: DocumentFilters | None = None) -> list[DoltDocumentView]:
    """
    List documents from Dolt.

    Args:
        filters: Optional filters to apply

    Returns:
        List of DoltDocumentView
    """
    from kurt.db.documents import get_dolt_db

    db = get_dolt_db()
    filters = filters or DocumentFilters()

    # Build query
    sql = "SELECT * FROM documents"
    conditions = []
    params = []

    if filters.ids:
        placeholders = ", ".join("?" for _ in filters.ids)
        conditions.append(f"id IN ({placeholders})")
        params.extend(filters.ids)

    if filters.url_contains:
        conditions.append("url LIKE ?")
        params.append(f"%{filters.url_contains}%")

    if filters.fetch_status:
        conditions.append("fetch_status = ?")
        params.append(str(filters.fetch_status.value) if hasattr(filters.fetch_status, 'value') else str(filters.fetch_status))

    if filters.not_fetched:
        conditions.append("(fetch_status = 'pending' OR fetch_status IS NULL)")

    if filters.has_error:
        conditions.append("(error IS NOT NULL AND error != '')")

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY created_at DESC"

    if filters.limit:
        sql += f" LIMIT {filters.limit}"
    if filters.offset:
        sql += f" OFFSET {filters.offset}"

    rows = db.query(sql, params)
    views = [_row_to_view(row) for row in rows]

    # Apply glob filters post-query
    if filters.include or filters.exclude:
        from fnmatch import fnmatch

        if filters.include:
            views = [v for v in views if fnmatch(v.source_url or "", filters.include)]
        if filters.exclude:
            views = [v for v in views if not fnmatch(v.source_url or "", filters.exclude)]

    return views


def get_document_dolt(identifier: str) -> DoltDocumentView | None:
    """
    Get a single document by ID or URL.

    Args:
        identifier: Document ID or URL

    Returns:
        DoltDocumentView or None if not found
    """
    from kurt.db.documents import get_dolt_db

    db = get_dolt_db()

    # Try exact ID match first
    rows = db.query("SELECT * FROM documents WHERE id = ?", [identifier])
    if rows:
        return _row_to_view(rows[0])

    # Try URL match
    if identifier.startswith(("http://", "https://", "file://")):
        rows = db.query("SELECT * FROM documents WHERE url = ?", [identifier])
        if rows:
            return _row_to_view(rows[0])

    # Try partial ID match
    rows = db.query("SELECT * FROM documents WHERE id LIKE ? LIMIT 1", [f"%{identifier}%"])
    if rows:
        return _row_to_view(rows[0])

    return None


def delete_documents_dolt(doc_ids: list[str]) -> int:
    """
    Delete documents from Dolt.

    Args:
        doc_ids: List of document IDs to delete

    Returns:
        Number of deleted documents
    """
    from kurt.db.documents import get_dolt_db

    if not doc_ids:
        return 0

    db = get_dolt_db()
    placeholders = ", ".join("?" for _ in doc_ids)
    count = db.execute(f"DELETE FROM documents WHERE id IN ({placeholders})", doc_ids)
    return count
