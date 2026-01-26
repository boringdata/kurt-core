"""
Dolt-based document registry.

Provides document listing and retrieval from the unified Dolt `documents` table.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from kurt.documents.filtering import DocumentFilters

if TYPE_CHECKING:
    from kurt.db.dolt import DoltDB

logger = logging.getLogger(__name__)


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
    from kurt.db.dolt import get_dolt_db

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
    from kurt.db.dolt import get_dolt_db

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
    from kurt.db.dolt import get_dolt_db

    if not doc_ids:
        return 0

    db = get_dolt_db()
    placeholders = ", ".join("?" for _ in doc_ids)
    count = db.execute(f"DELETE FROM documents WHERE id IN ({placeholders})", doc_ids)
    return count


def upsert_documents(
    db: "DoltDB",
    documents: list[dict[str, Any]],
) -> dict[str, int]:
    """DEPRECATED: Use persist_map_documents from tools.map.utils instead.

    This function writes to a legacy 'documents' table that doesn't exist.
    Use MapDocument entries via persist_map_documents() for document creation.

    Args:
        db: DoltDB client
        documents: List of document dicts with keys matching upsert_document params

    Returns:
        Dict with 'inserted' and 'updated' counts
    """
    import warnings
    warnings.warn(
        "upsert_documents() is deprecated. Use persist_map_documents() from "
        "tools.map.utils to create MapDocument entries instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    inserted = 0
    updated = 0

    with db.transaction() as tx:
        for doc in documents:
            doc_id = doc.get("id") or doc.get("document_id")
            url = doc.get("url") or doc.get("source_url")

            if not doc_id or not url:
                logger.warning(f"Skipping document without id or url: {doc}")
                continue

            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

            # Check if exists
            check_sql = "SELECT id FROM documents WHERE id = ?"
            result = tx.query(check_sql, [doc_id])
            exists = len(result.rows) > 0 if hasattr(result, 'rows') else len(result) > 0

            # Build metadata from extra fields
            metadata = doc.get("metadata") or doc.get("metadata_json") or {}
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    metadata = {}

            # Move map-specific fields to metadata
            for key in ["discovery_method", "discovery_url", "title", "is_new", "map_status"]:
                if key in doc and doc[key] is not None:
                    metadata[key] = doc[key]

            metadata_json = json.dumps(metadata) if metadata else None

            if exists:
                # Update
                update_sql = """
                    UPDATE documents SET
                        url = ?, source_type = ?, content_path = ?, content_hash = ?,
                        fetch_status = ?, error = ?, metadata = ?, updated_at = ?
                    WHERE id = ?
                """
                tx.execute(update_sql, [
                    url,
                    doc.get("source_type", "url"),
                    doc.get("content_path"),
                    doc.get("content_hash"),
                    doc.get("fetch_status") or doc.get("status", "pending"),
                    doc.get("error"),
                    metadata_json,
                    now,
                    doc_id,
                ])
                updated += 1
            else:
                # Insert
                insert_sql = """
                    INSERT INTO documents (id, url, source_type, content_path, content_hash,
                                           fetch_status, error, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                tx.execute(insert_sql, [
                    doc_id,
                    url,
                    doc.get("source_type", "url"),
                    doc.get("content_path"),
                    doc.get("content_hash"),
                    doc.get("fetch_status") or doc.get("status", "pending"),
                    doc.get("error"),
                    metadata_json,
                    now,
                    now,
                ])
                inserted += 1

    return {"inserted": inserted, "updated": updated}


def get_status_counts(db: "DoltDB") -> dict[str, int]:
    """Get document counts by fetch status.

    Args:
        db: DoltDB client

    Returns:
        Dict mapping fetch_status to count (None status mapped to 'pending')
    """
    sql = """
        SELECT fetch_status, COUNT(*) as count
        FROM documents
        GROUP BY fetch_status
    """
    result = db.query(sql)
    # Handle NULL fetch_status (omitted from dict by DoltDB JSON parser)
    # Map NULL to 'pending' for consistency
    counts = {}
    for row in result:
        status = row.get("fetch_status", "pending")  # NULL -> pending
        if status is None:
            status = "pending"
        counts[status] = row["count"]
    return counts


def get_domain_counts(db: "DoltDB", limit: int = 100) -> dict[str, int]:
    """Get document counts by domain.

    Args:
        db: DoltDB client
        limit: Maximum number of domains to return

    Returns:
        Dict mapping domain to count
    """
    # Dolt/MySQL supports SUBSTRING_INDEX for domain extraction
    sql = f"""
        SELECT
            SUBSTRING_INDEX(SUBSTRING_INDEX(url, '://', -1), '/', 1) as domain,
            COUNT(*) as count
        FROM documents
        WHERE url IS NOT NULL AND url != ''
        GROUP BY domain
        ORDER BY count DESC
        LIMIT {limit}
    """
    result = db.query(sql)
    return {row["domain"]: row["count"] for row in result}
