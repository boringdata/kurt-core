"""
Tool-owned table operations for Dolt.

Each tool writes to its own table:
- MapTool -> map_results
- FetchTool -> fetch_results
- EmbedTool -> embed_results

All tools also register documents in document_registry.
The unified `documents` VIEW joins all tables for queries.

See spec: kurt-core-5v6 "Tool-Owned Tables with Pydantic Schemas"
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from kurt.tools.utils import make_document_id, make_url_hash

if TYPE_CHECKING:
    from kurt.db.dolt import DoltDB

logger = logging.getLogger(__name__)


def register_document(
    db: "DoltDB",
    *,
    url: str,
    source_type: str = "url",
) -> str:
    """
    Register a document in document_registry (if not exists).

    Uses canonicalized URL for both document_id and url_hash
    to ensure consistent deduplication.

    Args:
        db: DoltDB client
        url: Original URL (will be canonicalized internally)
        source_type: Type of source (url, file, cms)

    Returns:
        document_id (12-char hex)
    """
    doc_id = make_document_id(url)
    url_hash = make_url_hash(url)

    # Upsert to registry
    db.execute(
        """
        INSERT INTO document_registry (document_id, url, url_hash, source_type)
        VALUES (?, ?, ?, ?)
        ON DUPLICATE KEY UPDATE url = VALUES(url)
        """,
        [doc_id, url, url_hash, source_type],
    )

    return doc_id


def insert_map_result(
    db: "DoltDB",
    *,
    document_id: str,
    run_id: str,
    url: str,
    discovery_method: str,
    source_type: str = "url",
    discovery_url: str | None = None,
    title: str | None = None,
    status: str = "success",
    error: str | None = None,
    metadata: dict | None = None,
) -> None:
    """
    Insert a row into map_results.

    Note: Does NOT check for duplicates - each (document_id, run_id) is a new row.
    Use register_document() first to ensure document_registry is populated.

    Args:
        db: DoltDB client
        document_id: Document ID (12-char hex)
        run_id: Run/batch ID (UUID)
        url: Original URL
        discovery_method: How this URL was discovered (crawl, sitemap, etc.)
        source_type: url|file|cms
        discovery_url: URL where this was discovered
        title: Page title if known
        status: success|error|skipped
        error: Error message if status=error
        metadata: Additional metadata
    """
    metadata_json = json.dumps(metadata) if metadata else None

    db.execute(
        """
        INSERT INTO map_results
        (document_id, run_id, url, source_type, discovery_method,
         discovery_url, title, status, error, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            document_id,
            run_id,
            url,
            source_type,
            discovery_method,
            discovery_url,
            title,
            status,
            error,
            metadata_json,
        ],
    )


def insert_fetch_result(
    db: "DoltDB",
    *,
    document_id: str,
    run_id: str,
    url: str,
    status: str,
    content_path: str | None = None,
    content_hash: str | None = None,
    content_length: int | None = None,
    fetch_engine: str | None = None,
    error: str | None = None,
    metadata: dict | None = None,
) -> None:
    """
    Insert a row into fetch_results.

    Note: Does NOT check for duplicates - each (document_id, run_id) is a new row.

    Args:
        db: DoltDB client
        document_id: Document ID (12-char hex)
        run_id: Run/batch ID (UUID)
        url: Fetched URL
        status: success|error|skipped
        content_path: Path to content file on disk
        content_hash: SHA256 of content
        content_length: Content length in bytes
        fetch_engine: trafilatura|firecrawl|httpx
        error: Error message if status=error
        metadata: Additional metadata
    """
    metadata_json = json.dumps(metadata) if metadata else None

    db.execute(
        """
        INSERT INTO fetch_results
        (document_id, run_id, url, status, content_path, content_hash,
         content_length, fetch_engine, error, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            document_id,
            run_id,
            url,
            status,
            content_path,
            content_hash,
            content_length,
            fetch_engine,
            error,
            metadata_json,
        ],
    )


def insert_embed_result(
    db: "DoltDB",
    *,
    document_id: str,
    run_id: str,
    embedding_model: str,
    embedding_path: str,
    vector_size: int,
) -> None:
    """
    Insert a row into embed_results.

    File path convention: sources/embeddings/<document_id>/<run_id>/<embedding_model>.npy

    Args:
        db: DoltDB client
        document_id: Document ID (12-char hex)
        run_id: Run/batch ID (UUID)
        embedding_model: Model name (e.g. text-embedding-3-small)
        embedding_path: Path to embedding file
        vector_size: Dimension of embedding vector
    """
    db.execute(
        """
        INSERT INTO embed_results
        (document_id, run_id, embedding_model, embedding_path, vector_size)
        VALUES (?, ?, ?, ?, ?)
        """,
        [document_id, run_id, embedding_model, embedding_path, vector_size],
    )


def batch_insert_map_results(
    db: "DoltDB",
    run_id: str,
    results: list[dict[str, Any]],
) -> dict[str, int]:
    """
    Batch insert map results.

    Each result dict should have:
    - url (required)
    - discovery_method (required)
    - source_type (default: url)
    - discovery_url, title, status, error, metadata (optional)

    Automatically registers documents in document_registry.

    Args:
        db: DoltDB client
        run_id: Run/batch ID for all results
        results: List of result dicts

    Returns:
        Dict with counts: {"registered": N, "inserted": M}
    """
    registered = 0
    inserted = 0

    with db.transaction() as tx:
        for result in results:
            url = result.get("url")
            if not url:
                logger.warning(f"Skipping map result without url: {result}")
                continue

            # Register document
            doc_id = make_document_id(url)
            url_hash = make_url_hash(url)
            source_type = result.get("source_type", "url")

            tx.execute(
                """
                INSERT INTO document_registry (document_id, url, url_hash, source_type)
                VALUES (?, ?, ?, ?)
                ON DUPLICATE KEY UPDATE url = VALUES(url)
                """,
                [doc_id, url, url_hash, source_type],
            )
            registered += 1

            # Insert map result
            metadata = result.get("metadata")
            metadata_json = json.dumps(metadata) if metadata else None

            tx.execute(
                """
                INSERT INTO map_results
                (document_id, run_id, url, source_type, discovery_method,
                 discovery_url, title, status, error, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    doc_id,
                    run_id,
                    url,
                    source_type,
                    result.get("discovery_method", "unknown"),
                    result.get("discovery_url"),
                    result.get("title"),
                    result.get("status", "success"),
                    result.get("error"),
                    metadata_json,
                ],
            )
            inserted += 1

    return {"registered": registered, "inserted": inserted}


def batch_insert_fetch_results(
    db: "DoltDB",
    run_id: str,
    results: list[dict[str, Any]],
) -> dict[str, int]:
    """
    Batch insert fetch results.

    Each result dict should have:
    - url or document_id (required)
    - status (required)
    - content_path, content_hash, content_length, fetch_engine, error, metadata (optional)

    Args:
        db: DoltDB client
        run_id: Run/batch ID for all results
        results: List of result dicts

    Returns:
        Dict with counts: {"inserted": N}
    """
    inserted = 0

    with db.transaction() as tx:
        for result in results:
            url = result.get("url") or result.get("source_url")
            doc_id = result.get("document_id") or (make_document_id(url) if url else None)

            if not doc_id:
                logger.warning(f"Skipping fetch result without document_id or url: {result}")
                continue

            if not url:
                # Try to get URL from registry
                rows = tx.query(
                    "SELECT url FROM document_registry WHERE document_id = ?", [doc_id]
                )
                if rows:
                    url = rows[0]["url"]
                else:
                    logger.warning(f"Skipping fetch result - document not in registry: {doc_id}")
                    continue

            metadata = result.get("metadata")
            metadata_json = json.dumps(metadata) if metadata else None

            tx.execute(
                """
                INSERT INTO fetch_results
                (document_id, run_id, url, status, content_path, content_hash,
                 content_length, fetch_engine, error, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    doc_id,
                    run_id,
                    url,
                    result.get("status", "success"),
                    result.get("content_path"),
                    result.get("content_hash"),
                    result.get("content_length"),
                    result.get("fetch_engine"),
                    result.get("error"),
                    metadata_json,
                ],
            )
            inserted += 1

    return {"inserted": inserted}


def get_documents_for_fetch(
    db: "DoltDB",
    *,
    limit: int = 100,
    status_filter: str | None = None,
) -> list[dict[str, Any]]:
    """
    Get documents that need fetching.

    Uses the documents VIEW which joins all tool tables.

    Args:
        db: DoltDB client
        limit: Maximum documents to return
        status_filter: Filter by fetch_status (pending, success, error, etc.)

    Returns:
        List of document dicts with document_id, url, fetch_status, etc.
    """
    sql = """
        SELECT document_id, url, source_type, fetch_status, content_path
        FROM documents
    """
    params = []

    if status_filter:
        sql += " WHERE fetch_status = ? OR fetch_status IS NULL"
        params.append(status_filter)
    else:
        sql += " WHERE fetch_status IS NULL OR fetch_status = 'pending'"

    sql += f" LIMIT {limit}"

    return db.query(sql, params)


def get_existing_document_ids(db: "DoltDB", urls: list[str]) -> set[str]:
    """
    Get document IDs for URLs that already exist in registry.

    Args:
        db: DoltDB client
        urls: List of URLs to check

    Returns:
        Set of document_ids that exist
    """
    if not urls:
        return set()

    # Compute document_ids from URLs
    doc_ids = [make_document_id(url) for url in urls]

    placeholders = ", ".join("?" for _ in doc_ids)
    sql = f"SELECT document_id FROM document_registry WHERE document_id IN ({placeholders})"
    result = db.query(sql, doc_ids)

    return {row["document_id"] for row in result}
