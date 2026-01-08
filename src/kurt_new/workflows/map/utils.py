from __future__ import annotations

import hashlib
from typing import Any, Optional

from sqlmodel import select

from kurt_new.db import ensure_tables, managed_session

from .models import MapDocument, MapStatus


def parse_patterns(patterns_str: Optional[str]) -> tuple[str, ...]:
    if not patterns_str:
        return ()
    return tuple(p.strip() for p in patterns_str.split(",") if p.strip())


def compute_status(row: dict[str, Any]) -> MapStatus:
    if row.get("error"):
        return MapStatus.ERROR
    if row.get("is_new", False):
        return MapStatus.DISCOVERED
    return MapStatus.EXISTING


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
        ensure_tables([MapDocument], session=session)
        rows = session.exec(
            select(MapDocument.document_id).where(MapDocument.document_id.in_(doc_ids))
        ).all()
    return {row[0] for row in rows}


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
