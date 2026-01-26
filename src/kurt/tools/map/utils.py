from __future__ import annotations

import logging
from fnmatch import fnmatch
from typing import Any, Callable, Optional

# Use shared URL canonicalization for consistent document IDs
from kurt.tools.core import make_document_id

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
    """Check which document IDs already exist in document_registry."""
    if not doc_ids:
        return set()
    try:
        from kurt.db.dolt import get_dolt_db

        db = get_dolt_db()
        placeholders = ", ".join("?" for _ in doc_ids)
        sql = f"SELECT document_id FROM document_registry WHERE document_id IN ({placeholders})"
        result = db.query(sql, doc_ids)
        return {row["document_id"] for row in result}
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
    """Serialize rows for workflow output.

    Also adds 'url' field as alias for 'source_url' for compatibility
    with downstream tools (e.g., FetchTool expects 'url').
    """
    serialized = []
    for row in rows:
        row_copy = dict(row)
        status = row_copy.get("status")
        if isinstance(status, MapStatus):
            row_copy["status"] = status.value
        # Add 'url' as alias for compatibility with FetchTool
        if "source_url" in row_copy and "url" not in row_copy:
            row_copy["url"] = row_copy["source_url"]
        serialized.append(row_copy)
    return serialized


def persist_map_documents(
    rows: list[dict[str, Any]],
    run_id: str | None = None,
) -> dict[str, int]:
    """Persist map results to SQLModel map_documents table.

    Args:
        rows: List of map result dicts
        run_id: Run/batch ID (unused, kept for API compatibility)

    Returns:
        Dict with counts: {"registered": N, "inserted": M}
    """
    from kurt.db import managed_session

    from .models import MapDocument

    inserted = 0
    with managed_session() as session:
        for row in rows:
            # Get status - convert string to enum if needed
            status = row.get("status")
            if isinstance(status, str):
                try:
                    status = MapStatus(status.upper())
                except ValueError:
                    status = MapStatus.SUCCESS
            elif not isinstance(status, MapStatus):
                status = MapStatus.SUCCESS

            doc = MapDocument(
                document_id=row.get("document_id", ""),
                source_url=row.get("source_url", ""),
                source_type=row.get("source_type", "url"),
                discovery_method=row.get("discovery_method", ""),
                discovery_url=row.get("discovery_url"),
                status=status,
                is_new=row.get("is_new", True),
                title=row.get("title"),
                content_hash=row.get("content_hash"),
                error=row.get("error"),
                metadata_json=row.get("metadata_json"),
            )
            session.merge(doc)  # Upsert
            inserted += 1

    return {"registered": inserted, "inserted": inserted}


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
