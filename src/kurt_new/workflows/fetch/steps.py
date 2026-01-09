from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from dbos import DBOS

from kurt_new.core import embedding_to_bytes, generate_embeddings
from kurt_new.db import ensure_tables, managed_session
from kurt_new.integrations.cms import fetch_from_cms

from .config import FetchConfig
from .fetch_file import fetch_from_file
from .fetch_web import fetch_from_web
from .models import FetchDocument, FetchStatus
from .utils import load_document_content, save_content_file

logger = logging.getLogger(__name__)


def _fetch_single_document(doc: dict[str, Any], config: FetchConfig) -> dict[str, Any]:
    """Fetch a single document and return result dict."""
    doc_id = doc.get("document_id")
    source_url = doc.get("source_url")
    source_type = doc.get("source_type", "url")
    metadata_json = doc.get("metadata_json", {})

    try:
        # Fetch content based on source type
        public_url = None
        if source_type == "cms":
            # CMS documents have platform/instance/cms_id in metadata
            cms_platform = metadata_json.get("cms_platform")
            cms_instance = metadata_json.get("cms_instance")
            cms_document_id = metadata_json.get("cms_id") or metadata_json.get("cms_document_id")

            if cms_platform and cms_instance and cms_document_id:
                content, metadata, public_url = fetch_from_cms(
                    platform=cms_platform,
                    instance=cms_instance,
                    cms_document_id=cms_document_id,
                    discovery_url=doc.get("discovery_url"),
                )
            else:
                raise ValueError(f"CMS document missing platform/instance/cms_id: {doc_id}")
        elif source_type == "file":
            # Local file sources
            content, metadata = fetch_from_file(source_url)
        else:
            # Web URL sources
            content, metadata = fetch_from_web(
                source_url=source_url,
                fetch_engine=config.fetch_engine,
            )

        logger.info(f"Fetched {doc_id}: {len(content)} chars")

        return {
            "document_id": str(doc_id),
            "status": FetchStatus.SUCCESS,
            "content": content,
            "content_length": len(content),
            "content_hash": metadata.get("fingerprint"),
            "fetch_engine": config.fetch_engine,
            "public_url": public_url,
            "metadata_json": metadata,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Failed to fetch {doc_id}: {e}")
        return {
            "document_id": str(doc_id),
            "status": FetchStatus.ERROR,
            "content": None,
            "content_length": 0,
            "content_hash": None,
            "fetch_engine": config.fetch_engine,
            "public_url": None,
            "metadata_json": None,
            "error": str(e),
        }


@DBOS.step(name="generate_embeddings")
def embedding_step(rows: list[dict[str, Any]], config_dict: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate embeddings for fetched documents.

    This step runs AFTER save_content_step, so content is loaded from files.
    """
    config = FetchConfig.model_validate(config_dict)

    # Filter to only successfully fetched documents with content_path
    fetchable = [
        r for r in rows if r.get("status") == FetchStatus.SUCCESS and r.get("content_path")
    ]

    if not fetchable:
        for row in rows:
            row["embedding"] = None
        return rows

    # Load content from files and truncate for embedding
    texts = []
    doc_ids = []
    for r in fetchable:
        content = load_document_content(r["content_path"])
        if content:
            texts.append(content[: config.embedding_max_chars])
            doc_ids.append(r["document_id"])

    if not texts:
        for row in rows:
            row["embedding"] = None
        return rows

    # Process in batches
    all_embeddings: list[bytes] = []
    for i in range(0, len(texts), config.embedding_batch_size):
        batch_texts = texts[i : i + config.embedding_batch_size]
        batch_embeddings = generate_embeddings(batch_texts, module_name="FETCH")
        all_embeddings.extend([embedding_to_bytes(e) for e in batch_embeddings])

    # Map embeddings back to rows
    embedding_map = dict(zip(doc_ids, all_embeddings))
    for row in rows:
        row["embedding"] = embedding_map.get(row["document_id"])

    return rows


@DBOS.step(name="save_content")
def save_content_step(
    rows: list[dict[str, Any]], config_dict: dict[str, Any]
) -> list[dict[str, Any]]:
    """Save fetched content to files and add content_path to rows.

    Args:
        rows: List of fetch result dicts with 'content' field
        config_dict: FetchConfig as dict

    Returns:
        Same rows with 'content_path' added and 'content' removed
    """
    config = FetchConfig.model_validate(config_dict)

    if config.dry_run:
        # In dry run, don't save files but keep content for inspection
        for row in rows:
            row["content_path"] = None
        return rows

    for row in rows:
        if row.get("status") == FetchStatus.SUCCESS and row.get("content"):
            try:
                content_path = save_content_file(row["document_id"], row["content"])
                row["content_path"] = content_path
                logger.info(f"Saved content for {row['document_id']} to {content_path}")
            except Exception as e:
                logger.error(f"Failed to save content for {row['document_id']}: {e}")
                row["content_path"] = None
        else:
            row["content_path"] = None

        # Remove content from row to avoid storing in DB
        row.pop("content", None)

    return rows


@DBOS.step(name="fetch_documents")
def fetch_step(docs: list[dict[str, Any]], config_dict: dict[str, Any]) -> dict[str, Any]:
    """Fetch content for documents.

    Args:
        docs: List of dicts with:
            - document_id: str (required)
            - source_url: str (required)
            - source_type: str ("url" | "file" | "cms")
            - discovery_url: Optional[str]
            - metadata_json: Optional[dict]
        config_dict: FetchConfig as dict

    Returns:
        Dict with total, documents_fetched, documents_failed, rows, etc.
    """
    config = FetchConfig.model_validate(config_dict)

    if not docs:
        logger.warning("No documents provided")
        return {
            "total": 0,
            "documents_fetched": 0,
            "documents_failed": 0,
            "rows_written": 0,
            "rows_updated": 0,
            "rows": [],
            "dry_run": config.dry_run,
        }

    total = len(docs)

    logger.info(f"Fetching {total} documents (engine: {config.fetch_engine})")

    rows: list[dict[str, Any]] = []
    DBOS.set_event("stage_total", total)

    for idx, doc in enumerate(docs):
        row = _fetch_single_document(doc, config)
        rows.append(row)

        DBOS.set_event("stage_current", idx + 1)
        DBOS.write_stream(
            "progress",
            {
                "step": "fetch_documents",
                "idx": idx,
                "total": total,
                "status": "success" if row["status"] == FetchStatus.SUCCESS else "error",
                "timestamp": time.time(),
            },
        )

    fetched = sum(1 for row in rows if row["status"] == FetchStatus.SUCCESS)
    failed = sum(1 for row in rows if row["status"] == FetchStatus.ERROR)

    logger.info(f"Fetch complete: {fetched} successful, {failed} failed")

    return {
        "total": total,
        "documents_fetched": fetched,
        "documents_failed": failed,
        "rows": _serialize_rows(rows),
        "dry_run": config.dry_run,
    }


def _serialize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Serialize rows for JSON output."""
    return [
        {
            **r,
            "status": r["status"].value
            if isinstance(r.get("status"), FetchStatus)
            else r.get("status"),
        }
        for r in rows
    ]


@DBOS.transaction()
def persist_fetch_documents(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Persist fetch results in a durable transaction."""
    with managed_session() as session:
        ensure_tables([FetchDocument], session=session)
        inserted = 0
        updated = 0
        for row in rows:
            existing_row = session.get(FetchDocument, row["document_id"])
            if existing_row:
                for key, value in row.items():
                    setattr(existing_row, key, value)
                existing_row.updated_at = datetime.utcnow()
                updated += 1
            else:
                session.add(FetchDocument(**row))
                inserted += 1
        return {"rows_written": inserted, "rows_updated": updated}
