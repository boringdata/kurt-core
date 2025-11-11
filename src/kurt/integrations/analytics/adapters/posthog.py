"""PostHog analytics adapter."""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

import httpx

from kurt.integrations.analytics.adapters.base import AnalyticsAdapter, AnalyticsMetrics
from kurt.integrations.analytics.utils import normalize_url_for_analytics

logger = logging.getLogger(__name__)


class PostHogAdapter(AnalyticsAdapter):
    """PostHog analytics platform adapter."""

    def __init__(
        self,
        project_id: str,
        api_key: str,
        base_url: str = "https://app.posthog.com",
    ):
        """
        Initialize PostHog adapter.

        Args:
            project_id: PostHog project ID (e.g., "phc_abc123")
            api_key: PostHog API key
            base_url: PostHog instance URL (default: cloud)
        """
        self.project_id = project_id
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    def test_connection(self) -> bool:
        """Test PostHog API connection."""
        try:
            response = self.client.get(f"/api/projects/{self.project_id}")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"PostHog connection test failed: {e}")
            return False

    def sync_metrics(self, urls: list[str], period_days: int = 60) -> dict[str, AnalyticsMetrics]:
        """
        Fetch analytics metrics from PostHog for given URLs.

        Args:
            urls: List of document URLs to fetch metrics for
            period_days: Number of days to query (default: 60)

        Returns:
            Dict mapping URL -> AnalyticsMetrics
        """
        logger.info(f"Syncing PostHog metrics for {len(urls)} URLs (period: {period_days} days)")

        # Calculate time windows
        now = datetime.utcnow()
        period_end = now
        period_start = now - timedelta(days=period_days)
        mid_point = now - timedelta(days=period_days // 2)

        # Query pageviews for each time window
        logger.info("Querying PostHog for pageview events...")
        pageviews_60d = self._query_pageviews(period_start, period_end)
        pageviews_30d = self._query_pageviews(mid_point, period_end)
        pageviews_previous_30d = self._query_pageviews(period_start, mid_point)

        # Query engagement metrics
        logger.info("Querying PostHog for engagement metrics...")
        engagement = self._query_engagement(period_start, period_end)

        # Build results for each URL
        results = {}
        for url in urls:
            normalized = normalize_url_for_analytics(url)

            pv_60d = pageviews_60d.get(normalized, 0)
            pv_30d = pageviews_30d.get(normalized, 0)
            pv_prev_30d = pageviews_previous_30d.get(normalized, 0)

            # Calculate trend
            trend, trend_pct = self._calculate_trend(pv_30d, pv_prev_30d)

            # Get engagement metrics
            eng = engagement.get(normalized, {})

            results[url] = AnalyticsMetrics(
                pageviews_60d=pv_60d,
                pageviews_30d=pv_30d,
                pageviews_previous_30d=pv_prev_30d,
                unique_visitors_60d=0,  # Not queried yet (simplification)
                unique_visitors_30d=0,
                unique_visitors_previous_30d=0,
                bounce_rate=eng.get("bounce_rate"),
                avg_session_duration_seconds=eng.get("avg_duration"),
                pageviews_trend=trend,
                trend_percentage=trend_pct,
                period_start=period_start,
                period_end=period_end,
            )

        logger.info(f"Synced metrics for {len(results)} URLs")
        return results

    def _query_pageviews(self, start: datetime, end: datetime) -> dict[str, int]:
        """
        Query PostHog for pageview counts by URL.

        Args:
            start: Start of time window
            end: End of time window

        Returns:
            Dict mapping normalized_url -> pageview_count
        """
        query = {
            "query": {
                "kind": "EventsQuery",
                "event": "$pageview",
                "after": start.isoformat(),
                "before": end.isoformat(),
                "select": ["properties.$current_url", "count()"],
                "group_by": ["properties.$current_url"],
            }
        }

        try:
            response = self.client.post(f"/api/projects/{self.project_id}/query", json=query)
            response.raise_for_status()
            data = response.json()

            # Parse results and normalize URLs
            results = defaultdict(int)
            for row in data.get("results", []):
                if len(row) >= 2:
                    url = row[0]
                    count = row[1]
                    if url:  # Skip null URLs
                        normalized = normalize_url_for_analytics(url)
                        results[normalized] += count

            logger.debug(
                f"Queried {len(results)} unique URLs "
                f"({sum(results.values())} total pageviews) "
                f"from {start.date()} to {end.date()}"
            )
            return dict(results)

        except Exception as e:
            logger.error(f"PostHog pageview query failed: {e}")
            return {}

    def _query_engagement(self, start: datetime, end: datetime) -> dict[str, dict]:
        """
        Query PostHog for engagement metrics (bounce rate, session duration).

        Args:
            start: Start of time window
            end: End of time window

        Returns:
            Dict mapping normalized_url -> {"bounce_rate": float, "avg_duration": float}
        """
        # Simplified implementation - PostHog engagement queries are more complex
        # For now, return empty dict (can be enhanced later)
        logger.debug("Engagement metrics query not yet implemented, returning empty")
        return {}

    def _calculate_trend(self, current_30d: int, previous_30d: int) -> tuple[str, Optional[float]]:
        """
        Calculate trend and percentage change.

        Args:
            current_30d: Pageviews in last 30 days
            previous_30d: Pageviews in previous 30 days

        Returns:
            Tuple of (trend_label, trend_percentage)
            trend_label: "increasing", "stable", or "decreasing"
            trend_percentage: Percentage change (or None if no baseline)
        """
        if previous_30d == 0:
            if current_30d > 0:
                return ("increasing", None)
            else:
                return ("stable", None)

        trend_pct = ((current_30d - previous_30d) / previous_30d) * 100

        if trend_pct > 10:
            trend = "increasing"
        elif trend_pct < -10:
            trend = "decreasing"
        else:
            trend = "stable"

        return (trend, round(trend_pct, 1))

    def __del__(self):
        """Close HTTP client on cleanup."""
        try:
            self.client.close()
        except Exception:
            pass
