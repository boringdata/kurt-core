from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from dbos import DBOS

from kurt_new.db import ensure_tables, managed_session

from .config import MapConfig
from .map_cms import discover_from_cms
from .map_folder import discover_from_folder
from .map_url import discover_from_url
from .models import MapDocument, MapStatus
from .utils import build_rows, get_source_type, parse_patterns, serialize_rows


@DBOS.step(name="map_url")
def map_url_step(config_dict: dict[str, Any]) -> dict[str, Any]:
    config = MapConfig.model_validate(config_dict)
    include_patterns = parse_patterns(config.include_patterns)
    exclude_patterns = parse_patterns(config.exclude_patterns)

    result = discover_from_url(
        url=config.source_url or "",
        max_depth=config.max_depth,
        max_pages=config.max_pages,
        allow_external=config.allow_external,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        sitemap_path=config.sitemap_path,
    )

    discovered_docs = result.get("discovered", [])
    discovery_method = result.get("method", "sitemap")
    discovery_url = config.source_url or ""
    total = len(discovered_docs)
    source_type = get_source_type(discovery_method)

    rows = build_rows(
        discovered_docs,
        discovery_method=discovery_method,
        discovery_url=discovery_url,
        source_type=source_type,
    )
    DBOS.set_event("stage_total", total)
    for idx, row in enumerate(rows):
        DBOS.set_event("stage_current", idx + 1)
        DBOS.write_stream(
            "progress",
            {
                "step": "map_url",
                "idx": idx,
                "total": total,
                "status": "success" if row["status"] != MapStatus.ERROR else "error",
                "timestamp": time.time(),
            },
        )

    discovered = sum(1 for row in rows if row.get("is_new", False))
    existing = sum(
        1 for row in rows if not row.get("is_new", False) and row["status"] == MapStatus.SUCCESS
    )
    errors = sum(1 for row in rows if row["status"] == MapStatus.ERROR)

    # Note: persistence is handled by workflow calling persist_map_documents transaction
    return {
        "discovery_method": discovery_method,
        "discovery_url": discovery_url,
        "total": total,
        "documents_discovered": discovered,
        "documents_existing": existing,
        "documents_errors": errors,
        "rows_written": 0,
        "rows_updated": 0,
        "rows": serialize_rows(rows),
        "dry_run": config.dry_run,
    }


@DBOS.step(name="map_folder")
def map_folder_step(config_dict: dict[str, Any]) -> dict[str, Any]:
    config = MapConfig.model_validate(config_dict)
    include_patterns = parse_patterns(config.include_patterns)
    exclude_patterns = parse_patterns(config.exclude_patterns)

    result = discover_from_folder(
        folder_path=config.source_folder or "",
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
    )
    discovered_docs = result.get("discovered", [])
    discovery_method = "folder"
    discovery_url = config.source_folder or ""
    total = len(discovered_docs)
    source_type = get_source_type(discovery_method)

    rows = build_rows(
        discovered_docs,
        discovery_method=discovery_method,
        discovery_url=discovery_url,
        source_type=source_type,
    )
    DBOS.set_event("stage_total", total)
    for idx, row in enumerate(rows):
        DBOS.set_event("stage_current", idx + 1)
        DBOS.write_stream(
            "progress",
            {
                "step": "map_folder",
                "idx": idx,
                "total": total,
                "status": "success" if row["status"] != MapStatus.ERROR else "error",
                "timestamp": time.time(),
            },
        )

    discovered = sum(1 for row in rows if row.get("is_new", False))
    existing = sum(
        1 for row in rows if not row.get("is_new", False) and row["status"] == MapStatus.SUCCESS
    )
    errors = sum(1 for row in rows if row["status"] == MapStatus.ERROR)

    # Note: persistence is handled by workflow calling persist_map_documents transaction
    return {
        "discovery_method": discovery_method,
        "discovery_url": discovery_url,
        "total": total,
        "documents_discovered": discovered,
        "documents_existing": existing,
        "documents_errors": errors,
        "rows_written": 0,
        "rows_updated": 0,
        "rows": serialize_rows(rows),
        "dry_run": config.dry_run,
    }


@DBOS.step(name="map_cms")
def map_cms_step(config_dict: dict[str, Any]) -> dict[str, Any]:
    config = MapConfig.model_validate(config_dict)

    result = discover_from_cms(
        platform=config.cms_platform or "",
        instance=config.cms_instance or "",
    )
    discovered_docs = result.get("discovered", [])
    discovery_method = "cms"
    discovery_url = f"{config.cms_platform}/{config.cms_instance}"
    total = len(discovered_docs)
    source_type = get_source_type(discovery_method)

    rows = build_rows(
        discovered_docs,
        discovery_method=discovery_method,
        discovery_url=discovery_url,
        source_type=source_type,
    )
    DBOS.set_event("stage_total", total)
    for idx, row in enumerate(rows):
        DBOS.set_event("stage_current", idx + 1)
        DBOS.write_stream(
            "progress",
            {
                "step": "map_cms",
                "idx": idx,
                "total": total,
                "status": "success" if row["status"] != MapStatus.ERROR else "error",
                "timestamp": time.time(),
            },
        )

    discovered = sum(1 for row in rows if row.get("is_new", False))
    existing = sum(
        1 for row in rows if not row.get("is_new", False) and row["status"] == MapStatus.SUCCESS
    )
    errors = sum(1 for row in rows if row["status"] == MapStatus.ERROR)

    # Note: persistence is handled by workflow calling persist_map_documents transaction
    return {
        "discovery_method": discovery_method,
        "discovery_url": discovery_url,
        "total": total,
        "documents_discovered": discovered,
        "documents_existing": existing,
        "documents_errors": errors,
        "rows_written": 0,
        "rows_updated": 0,
        "rows": serialize_rows(rows),
        "dry_run": config.dry_run,
    }


def map_step(config_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Route to the dedicated map step for the configured source.
    """
    config = MapConfig.model_validate(config_dict)
    if config.source_url:
        return map_url_step(config_dict)
    if config.source_folder:
        return map_folder_step(config_dict)
    if config.cms_platform and config.cms_instance:
        return map_cms_step(config_dict)
    raise ValueError("Must specify source_url, source_folder, or cms_platform+cms_instance")


@DBOS.transaction()
def persist_map_documents(rows: list[dict[str, Any]]) -> dict[str, int]:
    """
    Persist map results in a durable transaction.
    """
    with managed_session() as session:
        ensure_tables([MapDocument], session=session)
        inserted = 0
        updated = 0
        for row in rows:
            existing_row = session.get(MapDocument, row["document_id"])
            if existing_row:
                for key, value in row.items():
                    setattr(existing_row, key, value)
                existing_row.updated_at = datetime.utcnow()
                updated += 1
            else:
                session.add(MapDocument(**row))
                inserted += 1
        return {"rows_written": inserted, "rows_updated": updated}
