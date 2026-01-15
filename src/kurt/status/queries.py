"""Status queries using SQLAlchemy (works in local and cloud modes)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from sqlmodel import Session


def get_status_data(session: "Session") -> dict:
    """
    Gather all status information using SQLAlchemy queries.

    This function works in both local (SQLite/PostgreSQL) and cloud modes.
    In cloud mode, it's called by the API endpoint on kurt-cloud backend.

    Args:
        session: SQLModel session

    Returns:
        Dict with status data including document counts and domain distribution
    """
    from sqlmodel import func, select

    from kurt.workflows.fetch.models import FetchDocument, FetchStatus
    from kurt.workflows.map.models import MapDocument

    # Get counts
    total = session.exec(select(func.count()).select_from(MapDocument)).one()

    fetched = session.exec(
        select(func.count())
        .select_from(FetchDocument)
        .where(FetchDocument.status == FetchStatus.SUCCESS)
    ).one()

    error = session.exec(
        select(func.count())
        .select_from(FetchDocument)
        .where(FetchDocument.status == FetchStatus.ERROR)
    ).one()

    not_fetched = total - fetched - error

    # Documents by domain
    urls = session.exec(select(MapDocument.source_url).limit(10000)).all()
    domains: dict[str, int] = {}
    for url in urls:
        if url:
            try:
                domain = urlparse(url).netloc
                domains[domain] = domains.get(domain, 0) + 1
            except Exception:
                pass

    return {
        "initialized": True,
        "documents": {
            "total": total,
            "by_status": {
                "fetched": fetched,
                "not_fetched": not_fetched,
                "error": error,
            },
            "by_domain": domains,
        },
    }
