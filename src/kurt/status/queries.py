"""Status queries using repository pattern (works in local and cloud modes)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse

from kurt.db.repository import BaseRepository

if TYPE_CHECKING:
    from sqlmodel import Session

    from kurt.db.cloud import SupabaseSession


class StatusRepository(BaseRepository):
    """Repository for status statistics.

    Provides cloud-aware methods for getting document counts and aggregations.
    Works in both SQLite/PostgreSQL and PostgREST (cloud) modes.
    """

    def __init__(self, session: "Session | SupabaseSession"):
        super().__init__(session)

    def get_document_counts(self) -> dict[str, int]:
        """Get document count statistics.

        Returns:
            Dict with total, fetched, error, and not_fetched counts
        """
        from kurt.workflows.fetch.models import FetchDocument, FetchStatus
        from kurt.workflows.map.models import MapDocument

        # Total documents
        total = self._count(MapDocument)

        # Fetched successfully
        fetched = self._count(FetchDocument, filters={"status": FetchStatus.SUCCESS.value})

        # Failed fetches
        error = self._count(FetchDocument, filters={"status": FetchStatus.ERROR.value})

        # Not yet fetched
        not_fetched = total - fetched - error

        return {
            "total": total,
            "fetched": fetched,
            "error": error,
            "not_fetched": not_fetched,
        }

    def get_domains_distribution(self, limit: int = 10000) -> dict[str, int]:
        """Get document counts by domain.

        Args:
            limit: Maximum number of URLs to fetch for analysis

        Returns:
            Dict mapping domain names to document counts
        """
        from kurt.workflows.map.models import MapDocument

        urls = self._select_column(MapDocument, "source_url", limit=limit)

        domains: dict[str, int] = {}
        for url in urls:
            if url:
                try:
                    domain = urlparse(url).netloc
                    domains[domain] = domains.get(domain, 0) + 1
                except Exception:
                    pass

        return domains


def get_status_data(session: "Session | SupabaseSession") -> dict:
    """
    Gather all status information using repository pattern.

    This function works in both local (SQLite/PostgreSQL) and cloud modes.
    In cloud mode, it's called by the API endpoint on kurt-cloud backend.

    Args:
        session: SQLModel or SupabaseSession

    Returns:
        Dict with status data including document counts and domain distribution
    """
    repo = StatusRepository(session)
    counts = repo.get_document_counts()
    domains = repo.get_domains_distribution()

    return {
        "initialized": True,
        "documents": {
            "total": counts["total"],
            "by_status": {
                "fetched": counts["fetched"],
                "not_fetched": counts["not_fetched"],
                "error": counts["error"],
            },
            "by_domain": domains,
        },
    }
