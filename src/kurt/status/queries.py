"""Status queries using direct SQLModel queries."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from sqlmodel import Session


def get_status_data(session: "Session") -> dict:
    """
    Gather all status information.

    In cloud mode, this function is called by the kurt-cloud API endpoint.

    Args:
        session: SQLModel session

    Returns:
        Dict with status data including document counts and domain distribution
    """
    from sqlmodel import func, select

    from kurt.workflows.fetch.models import FetchDocument, FetchStatus
    from kurt.workflows.map.models import MapDocument

    # Total documents
    total = session.exec(select(func.count()).select_from(MapDocument)).one()

    # Fetched successfully
    fetched = session.exec(
        select(func.count())
        .select_from(FetchDocument)
        .where(FetchDocument.status == FetchStatus.SUCCESS.value)
    ).one()

    # Failed fetches
    error = session.exec(
        select(func.count())
        .select_from(FetchDocument)
        .where(FetchDocument.status == FetchStatus.ERROR.value)
    ).one()

    # Not yet fetched
    not_fetched = total - fetched - error

    # Get domain distribution
    # Use SQL GROUP BY for PostgreSQL, fall back to Python parsing for SQLite
    from sqlalchemy import text

    # Check if we're using PostgreSQL (has better regex support)
    try:
        dialect_name = session.get_bind().dialect.name
        is_postgres = dialect_name == "postgresql"
    except Exception:
        is_postgres = False

    if is_postgres:
        # PostgreSQL: Extract domain using SQL regex and GROUP BY
        # Pattern: https://example.com/path -> example.com
        query = text("""
            SELECT
                substring(source_url from '://([^/]+)') as domain,
                COUNT(*) as count
            FROM map_documents
            WHERE source_url IS NOT NULL
            GROUP BY domain
            ORDER BY count DESC
            LIMIT 100
        """)
        result = session.exec(query)
        domains = {row[0]: row[1] for row in result if row[0]}
    else:
        # SQLite: Fall back to Python parsing (regex support limited)
        urls = session.exec(select(MapDocument.source_url).limit(10000)).all()
        domains = {}
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
