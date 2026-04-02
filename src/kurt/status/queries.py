"""Status queries using SQLModel on workflow tables."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from sqlalchemy import func
from sqlmodel import Session, select

from kurt.db import managed_session
from kurt.tools.fetch.models import FetchDocument
from kurt.tools.map.models import MapDocument


def get_status_counts(session: Session | None = None) -> dict[str, int]:
    """Get document counts by fetch status.

    Args:
        session: Database session (creates one if not provided)

    Returns:
        Dict mapping fetch_status to count (lowercase keys)
    """
    with managed_session(session) as sess:
        # Query fetch_documents grouped by status
        query = (
            select(
                FetchDocument.status,
                func.count(FetchDocument.document_id).label("count")
            )
            .group_by(FetchDocument.status)
        )
        results = sess.exec(query).all()

        # Convert enum values to lowercase strings
        counts = {}
        for status, count in results:
            # Convert FetchStatus enum to lowercase string
            status_str = status.value.lower() if hasattr(status, 'value') else str(status).lower()
            counts[status_str] = count

        # Add count for documents not yet fetched (in map but not in fetch)
        pending_query = (
            select(func.count(MapDocument.document_id))
            .where(
                ~MapDocument.document_id.in_(
                    select(FetchDocument.document_id)
                )
            )
        )
        pending_count = sess.exec(pending_query).one()
        if pending_count > 0:
            counts["pending"] = counts.get("pending", 0) + pending_count

        return counts


def get_domain_counts(session: Session | None = None, limit: int = 100) -> dict[str, int]:
    """Get document counts by domain.

    Args:
        session: Database session (creates one if not provided)
        limit: Maximum number of domains to return

    Returns:
        Dict mapping domain to count
    """
    with managed_session(session) as sess:
        # Query all source URLs and extract domains in Python
        # (SQLite doesn't have built-in URL parsing functions)
        query = select(MapDocument.source_url)
        results = sess.exec(query).all()

        # Count domains
        domain_counts: dict[str, int] = {}
        for url in results:
            if url:
                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc or ""
                    if domain:
                        domain_counts[domain] = domain_counts.get(domain, 0) + 1
                except Exception:
                    # Skip malformed URLs
                    continue

        # Sort by count and limit
        sorted_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_domains[:limit])


def get_status_data_dolt() -> dict[str, Any]:
    """
    Gather document status from workflow tables.

    Queries FetchDocument and MapDocument tables using SQLModel.

    Returns:
        Dict with status data including document counts and domain distribution
    """
    try:
        # Get status counts
        status_counts = get_status_counts()
        total = sum(status_counts.values())

        # Map fetch_status to display names
        fetched = status_counts.get("success", 0)
        error = status_counts.get("error", 0)
        pending = status_counts.get("pending", 0)
        skipped = status_counts.get("skipped", 0)

        # Get domain distribution
        domains = get_domain_counts(limit=100)

        return {
            "initialized": True,
            "documents": {
                "total": total,
                "by_status": {
                    "fetched": fetched,
                    "not_fetched": pending,
                    "error": error,
                    "skipped": skipped,
                },
                "by_domain": domains,
            },
        }
    except Exception:
        # Database not initialized or error
        return {
            "initialized": False,
            "documents": {
                "total": 0,
                "by_status": {},
                "by_domain": {},
            },
        }


def get_status_data(session: Any = None) -> dict[str, Any]:
    """
    Gather all status information.

    This function now uses Dolt directly. The session parameter is
    kept for backward compatibility but is ignored.

    Args:
        session: Ignored (kept for backward compatibility)

    Returns:
        Dict with status data including document counts and domain distribution
    """
    return get_status_data_dolt()
