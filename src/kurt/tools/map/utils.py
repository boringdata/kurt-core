from __future__ import annotations

import hashlib
import logging
from fnmatch import fnmatch
from typing import Any, Callable, Optional

from .models import MapStatus

logger = logging.getLogger(__name__)


def parse_patterns(patterns_str: Optional[str]) -> tuple[str, ...]:
    if not patterns_str:
        return ()
    return tuple(p.strip() for p in patterns_str.split(",") if p.strip())


def compute_status(row: dict[str, Any]) -> MapStatus:
    if row.get("error"):
        return MapStatus.ERROR
    return MapStatus.SUCCESS


def get_source_type(discovery_method: str) -> str:
    return {"folder": "file", "cms": "cms"}.get(discovery_method, "url")


def make_document_id(source: str) -> str:
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()
    return f"map_{digest}"


def get_source_identifier(item: dict[str, Any]) -> str:
    return (
        item.get("document_id")
        or item.get("doc_id")
        or item.get("url")
        or item.get("path")
        or item.get("source_url")
        or item.get("cms_id")
        or ""
    )


def resolve_existing(doc_ids: list[str]) -> set[str]:
    """Check which document IDs already exist in Dolt."""
    if not doc_ids:
        return set()
    try:
        from kurt.db.documents import get_dolt_db, get_existing_ids

        db = get_dolt_db()
        return get_existing_ids(db, doc_ids)
    except Exception as e:
        logger.warning(f"Failed to check existing documents in Dolt: {e}")
        return set()


def build_rows(
    discovered_docs: list[dict[str, Any]],
    *,
    discovery_method: str,
    discovery_url: str,
    source_type: str,
) -> list[dict[str, Any]]:
    doc_ids = []
    for item in discovered_docs:
        source = get_source_identifier(item)
        doc_id = str(item.get("document_id") or item.get("doc_id") or make_document_id(source))
        doc_ids.append(doc_id)

    existing_ids = resolve_existing(doc_ids)
    rows: list[dict[str, Any]] = []

    for item, doc_id in zip(discovered_docs, doc_ids):
        row = {
            "document_id": doc_id,
            "source_url": item.get("url") or item.get("path") or "",
            "source_type": source_type,
            "discovery_method": discovery_method,
            "discovery_url": discovery_url,
            "is_new": doc_id not in existing_ids,
            "title": item.get("title"),
            "content_hash": item.get("content_hash"),
            "error": item.get("error"),
            "metadata_json": item.get("metadata"),
        }
        row["status"] = compute_status(row)
        rows.append(row)

    return rows


def serialize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    serialized = []
    for row in rows:
        row_copy = dict(row)
        status = row_copy.get("status")
        if isinstance(status, MapStatus):
            row_copy["status"] = status.value
        serialized.append(row_copy)
    return serialized


def persist_map_documents(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Persist map results to Dolt documents table.

    Converts map-specific fields to the unified documents schema:
    - document_id -> id
    - source_url -> url
    - status (MapStatus) -> metadata.map_status
    - discovery_method, discovery_url, title, is_new -> metadata
    - fetch_status defaults to 'pending' for new documents
    """
    from kurt.db.documents import get_dolt_db, upsert_documents

    # Convert to Dolt documents format
    dolt_docs = []
    for row in rows:
        # Map status to string for metadata
        status = row.get("status")
        if isinstance(status, MapStatus):
            status = status.value

        doc = {
            "id": row.get("document_id"),
            "url": row.get("source_url"),
            "source_type": row.get("source_type", "url"),
            "content_hash": row.get("content_hash"),
            "error": row.get("error"),
            "fetch_status": "pending",  # New documents start as pending
            "metadata": {
                "discovery_method": row.get("discovery_method"),
                "discovery_url": row.get("discovery_url"),
                "title": row.get("title"),
                "is_new": row.get("is_new"),
                "map_status": status,
                **(row.get("metadata_json") or {}),
            },
        }
        dolt_docs.append(doc)

    db = get_dolt_db()
    result = upsert_documents(db, dolt_docs)
    return {"rows_written": result["inserted"], "rows_updated": result["updated"]}


def filter_items(
    items: list[Any],
    *,
    include_patterns: tuple[str, ...] = (),
    exclude_patterns: tuple[str, ...] = (),
    max_items: int | None = None,
    to_string: Callable[[Any], str] | None = None,
) -> list[Any]:
    """
    Filter items by glob patterns and optional max limit.
    """

    def default_to_string(item: Any) -> str:
        return str(item)

    if to_string is None:
        to_string = default_to_string

    if include_patterns:
        items = [
            item for item in items if any(fnmatch(to_string(item), p) for p in include_patterns)
        ]
    if exclude_patterns:
        items = [
            item for item in items if not any(fnmatch(to_string(item), p) for p in exclude_patterns)
        ]
    if max_items is not None and len(items) > max_items:
        items = items[:max_items]
    return items
