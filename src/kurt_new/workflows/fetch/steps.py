from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

import pandas as pd
from dbos import DBOS

from kurt_new.core import EmbeddingStep
from kurt_new.db import ensure_tables, managed_session
from kurt_new.integrations.cms import fetch_from_cms

from .config import FetchConfig
from .fetch_web import fetch_from_web
from .models import FetchDocument, FetchStatus

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
        else:
            # Web/file sources
            content, metadata = fetch_from_web(
                source_url=source_url,
                fetch_engine=config.fetch_engine,
            )

        logger.info(f"Fetched {doc_id}: {len(content)} chars")

        return {
            "document_id": str(doc_id),
            "status": FetchStatus.FETCHED,
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


def _generate_embeddings(rows: list[dict[str, Any]], config: FetchConfig) -> list[dict[str, Any]]:
    """Generate embeddings for fetched documents using EmbeddingStep."""
    # Filter to only successfully fetched documents with content
    fetchable = [r for r in rows if r.get("status") == FetchStatus.FETCHED and r.get("content")]

    if not fetchable:
        # No content to embed - add None embeddings
        for row in rows:
            row["embedding"] = None
        return rows

    # Create DataFrame for EmbeddingStep
    df = pd.DataFrame(fetchable)

    # Create and run EmbeddingStep
    embed_step = EmbeddingStep(
        name="fetch_embed",
        input_column="content",
        output_column="embedding",
        max_chars=config.embedding_max_chars,
        batch_size=config.embedding_batch_size,
        concurrency=config.embedding_concurrency,
        module_name="FETCH",
        as_bytes=True,
    )

    result_df = embed_step.run(df)

    # Map embeddings back to rows by document_id
    embedding_map = dict(zip(result_df["document_id"], result_df["embedding"]))

    for row in rows:
        row["embedding"] = embedding_map.get(row["document_id"])

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
                "status": "success" if row["status"] == FetchStatus.FETCHED else "error",
                "timestamp": time.time(),
            },
        )

    fetched = sum(1 for row in rows if row["status"] == FetchStatus.FETCHED)
    failed = sum(1 for row in rows if row["status"] == FetchStatus.ERROR)

    # Generate embeddings using EmbeddingStep (batched + concurrent)
    rows = _generate_embeddings(rows, config)

    if not config.dry_run:
        persistence = persist_fetch_documents(rows)
        inserted = persistence["rows_written"]
        updated = persistence["rows_updated"]
    else:
        inserted = 0
        updated = 0

    logger.info(f"Fetch complete: {fetched} successful, {failed} failed")

    return {
        "total": total,
        "documents_fetched": fetched,
        "documents_failed": failed,
        "rows_written": inserted,
        "rows_updated": updated,
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
