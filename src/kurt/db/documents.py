"""
Dolt-based document operations.

Provides functions for inserting, updating, and querying documents
in the Dolt `documents` table.

The unified `documents` table schema:
- id VARCHAR(36) PRIMARY KEY
- url TEXT NOT NULL UNIQUE
- source_type VARCHAR(20) -- url|file|cms
- content_path TEXT
- content_hash VARCHAR(64)
- embedding BLOB
- fetch_status VARCHAR(20) -- pending|fetching|success|error|skipped
- error TEXT
- metadata JSON
- created_at TIMESTAMP
- updated_at TIMESTAMP
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def get_dolt_db() -> "DoltDB":
    """Get DoltDB client from project directory.

    Looks for .dolt directory in current working directory.
    DoltDB expects the project root (parent of .dolt), not .dolt itself.

    Returns:
        DoltDB instance

    Raises:
        RuntimeError: If Dolt is not initialized
    """
    from kurt.db.dolt import DoltDB

    project_root = Path.cwd()
    dolt_path = project_root / ".dolt"

    if not dolt_path.exists():
        raise RuntimeError(
            f"Dolt database not found at {dolt_path}. "
            "Run 'kurt init' to initialize the project."
        )

    # DoltDB expects project root (parent of .dolt), not .dolt directory
    return DoltDB(project_root)


def upsert_document(
    db: "DoltDB",
    *,
    id: str,
    url: str,
    source_type: str = "url",
    content_path: str | None = None,
    content_hash: str | None = None,
    fetch_status: str = "pending",
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Insert or update a document in Dolt.

    Args:
        db: DoltDB client
        id: Document ID (primary key)
        url: Document URL (unique)
        source_type: Type of source (url, file, cms)
        content_path: Path to content file
        content_hash: SHA256 hash of content
        fetch_status: Fetch status (pending, fetching, success, error, skipped)
        error: Error message if any
        metadata: Additional metadata as JSON

    Returns:
        Dict with 'status' key ('inserted' or 'updated')
    """
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    metadata_json = json.dumps(metadata) if metadata else None

    # Check if document exists
    check_sql = "SELECT id FROM documents WHERE id = ?"
    result = db.query(check_sql, [id])
    exists = len(result) > 0

    if exists:
        # Update existing document
        update_parts = ["updated_at = ?"]
        values = [now]

        if url is not None:
            update_parts.append("url = ?")
            values.append(url)
        if source_type is not None:
            update_parts.append("source_type = ?")
            values.append(source_type)
        if content_path is not None:
            update_parts.append("content_path = ?")
            values.append(content_path)
        if content_hash is not None:
            update_parts.append("content_hash = ?")
            values.append(content_hash)
        if fetch_status is not None:
            update_parts.append("fetch_status = ?")
            values.append(fetch_status)
        if error is not None:
            update_parts.append("error = ?")
            values.append(error)
        if metadata_json is not None:
            update_parts.append("metadata = ?")
            values.append(metadata_json)

        values.append(id)
        update_sql = f"UPDATE documents SET {', '.join(update_parts)} WHERE id = ?"
        db.execute(update_sql, values)
        return {"status": "updated"}
    else:
        # Insert new document
        insert_sql = """
            INSERT INTO documents (id, url, source_type, content_path, content_hash,
                                   fetch_status, error, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        db.execute(insert_sql, [
            id, url, source_type, content_path, content_hash,
            fetch_status, error, metadata_json, now, now
        ])
        return {"status": "inserted"}


def upsert_documents(
    db: "DoltDB",
    documents: list[dict[str, Any]],
) -> dict[str, int]:
    """Batch upsert documents to Dolt.

    Args:
        db: DoltDB client
        documents: List of document dicts with keys matching upsert_document params

    Returns:
        Dict with 'inserted' and 'updated' counts
    """
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


def get_document(db: "DoltDB", doc_id: str) -> dict[str, Any] | None:
    """Get a document by ID.

    Args:
        db: DoltDB client
        doc_id: Document ID

    Returns:
        Document dict or None if not found
    """
    sql = "SELECT * FROM documents WHERE id = ?"
    result = db.query(sql, [doc_id])
    if not result:
        return None
    return result[0]


def get_document_by_url(db: "DoltDB", url: str) -> dict[str, Any] | None:
    """Get a document by URL.

    Args:
        db: DoltDB client
        url: Document URL

    Returns:
        Document dict or None if not found
    """
    sql = "SELECT * FROM documents WHERE url = ?"
    result = db.query(sql, [url])
    if not result:
        return None
    return result[0]


def list_documents(
    db: "DoltDB",
    *,
    fetch_status: str | None = None,
    source_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List documents with optional filtering.

    Args:
        db: DoltDB client
        fetch_status: Filter by fetch status
        source_type: Filter by source type
        limit: Maximum results
        offset: Skip first N results

    Returns:
        List of document dicts
    """
    sql = "SELECT * FROM documents"
    conditions = []
    params = []

    if fetch_status:
        conditions.append("fetch_status = ?")
        params.append(fetch_status)
    if source_type:
        conditions.append("source_type = ?")
        params.append(source_type)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += f" ORDER BY created_at DESC LIMIT {limit} OFFSET {offset}"

    return db.query(sql, params)


def count_documents(
    db: "DoltDB",
    *,
    fetch_status: str | None = None,
    source_type: str | None = None,
) -> int:
    """Count documents with optional filtering.

    Args:
        db: DoltDB client
        fetch_status: Filter by fetch status
        source_type: Filter by source type

    Returns:
        Document count
    """
    sql = "SELECT COUNT(*) as count FROM documents"
    conditions = []
    params = []

    if fetch_status:
        conditions.append("fetch_status = ?")
        params.append(fetch_status)
    if source_type:
        conditions.append("source_type = ?")
        params.append(source_type)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    result = db.query(sql, params)
    return result[0]["count"] if result else 0


def get_existing_ids(db: "DoltDB", doc_ids: list[str]) -> set[str]:
    """Get set of existing document IDs from a list.

    Args:
        db: DoltDB client
        doc_ids: List of document IDs to check

    Returns:
        Set of IDs that exist in the database
    """
    if not doc_ids:
        return set()

    # Build IN clause with placeholders
    placeholders = ", ".join("?" for _ in doc_ids)
    sql = f"SELECT id FROM documents WHERE id IN ({placeholders})"
    result = db.query(sql, doc_ids)
    return {row["id"] for row in result}


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
