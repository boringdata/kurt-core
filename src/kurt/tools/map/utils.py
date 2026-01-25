from __future__ import annotations

import logging
from fnmatch import fnmatch
from typing import Any, Callable, Optional

# Use shared URL canonicalization for consistent document IDs
from kurt.tools.utils import make_document_id

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
        from kurt.db.documents import get_dolt_db

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
    serialized = []
    for row in rows:
        row_copy = dict(row)
        status = row_copy.get("status")
        if isinstance(status, MapStatus):
            row_copy["status"] = status.value
        serialized.append(row_copy)
    return serialized


def persist_map_documents(
    rows: list[dict[str, Any]],
    run_id: str | None = None,
) -> dict[str, int]:
    """Persist map results to tool-owned tables.

    Writes to:
    - document_registry: Central registry (upsert)
    - map_results: Map tool output (insert new row per run)

    Args:
        rows: List of map result dicts
        run_id: Run/batch ID (UUID). If None, generates one.

    Returns:
        Dict with counts: {"registered": N, "inserted": M}
    """
    import uuid

    from kurt.db.documents import get_dolt_db
    from kurt.db.tool_tables import batch_insert_map_results

    if run_id is None:
        run_id = str(uuid.uuid4())

    # Convert to format expected by batch_insert_map_results
    map_results = []
    for row in rows:
        # Map status to string
        status = row.get("status")
        if isinstance(status, MapStatus):
            status = status.value

        result = {
            "url": row.get("source_url"),
            "source_type": row.get("source_type", "url"),
            "discovery_method": row.get("discovery_method", "unknown"),
            "discovery_url": row.get("discovery_url"),
            "title": row.get("title"),
            "status": status or "success",
            "error": row.get("error"),
            "metadata": row.get("metadata_json"),
        }
        map_results.append(result)

    db = get_dolt_db()
    return batch_insert_map_results(db, run_id, map_results)


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
