from __future__ import annotations

import hashlib
from fnmatch import fnmatch
from typing import Any, Callable, Optional

from sqlmodel import select

from kurt_new.db import managed_session

from .models import MapDocument, MapStatus


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
    if not doc_ids:
        return set()
    with managed_session() as session:
        rows = session.exec(
            select(MapDocument.document_id).where(MapDocument.document_id.in_(doc_ids))
        ).all()
    # SQLModel returns raw values for single-column selects, not tuples
    return set(rows)


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
