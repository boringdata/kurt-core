"""Status queries using Dolt documents table."""

from __future__ import annotations

from typing import Any


def get_status_data_dolt() -> dict[str, Any]:
    """
    Gather document status from Dolt.

    Queries the unified `documents` table in Dolt.

    Returns:
        Dict with status data including document counts and domain distribution
    """
    from kurt.db.dolt import get_dolt_db
    from kurt.documents.dolt_registry import (
        get_domain_counts,
        get_status_counts,
    )

    try:
        db = get_dolt_db()
    except RuntimeError:
        # Dolt not initialized
        return {
            "initialized": False,
            "documents": {
                "total": 0,
                "by_status": {},
                "by_domain": {},
            },
        }

    # Get status counts
    status_counts = get_status_counts(db)
    total = sum(status_counts.values())

    # Map fetch_status to display names
    fetched = status_counts.get("success", 0)
    error = status_counts.get("error", 0)
    pending = status_counts.get("pending", 0)
    skipped = status_counts.get("skipped", 0)

    # Get domain distribution
    domains = get_domain_counts(db, limit=100)

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
