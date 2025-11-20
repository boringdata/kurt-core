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
            project_id: PostHog project ID (numeric, e.g., "12345")
            api_key: PostHog Personal API Key (requires project:read and query:read scopes)
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
        """
        Test PostHog API connection.

        Returns:
            True if connection successful

        Raises:
            ConnectionError: If connection fails with details about the failure
        """
        try:
            response = self.client.get(f"/api/projects/{self.project_id}")

            if response.status_code == 200:
                return True
            elif response.status_code == 401:
                raise ConnectionError(
                    "Authentication failed. Check your API key.\n"
                    "Make sure your Personal API Key has 'project:read' and 'query:read' scopes."
                )
            elif response.status_code == 403:
                raise ConnectionError(
                    "Access denied. Your API key doesn't have permission to access this project.\n"
                    "Required scopes: project:read, query:read"
                )
            elif response.status_code == 404:
                raise ConnectionError(
                    f"Project not found. Check your project ID: {self.project_id}\n"
                    "Find your project ID in the PostHog URL: https://app.posthog.com/project/12345"
                )
            else:
                raise ConnectionError(
                    f"PostHog API returned status {response.status_code}: {response.text}"
                )
        except httpx.ConnectError as e:
            raise ConnectionError(
                f"Failed to connect to PostHog at {self.base_url}\n" f"Error: {e}"
            )
        except httpx.TimeoutException:
            raise ConnectionError(
                f"Connection to PostHog timed out at {self.base_url}\n"
                "Check your network connection or try again later."
            )
        except ConnectionError:
            # Re-raise ConnectionError as-is
            raise
        except Exception as e:
            logger.error(f"PostHog connection test failed: {e}")
            raise ConnectionError(f"Unexpected error during connection test: {e}")

    def get_domain_urls(self, domain: str, period_days: int = 60) -> list[str]:
        """
        Get all URLs for a domain from PostHog pageview events.

        Args:
            domain: Domain to filter by (e.g., "technically.dev")
            period_days: Number of days to query (default: 60)

        Returns:
            List of unique URLs found in PostHog for this domain
        """
        logger.info(f"Querying PostHog for all URLs on domain: {domain}")

        # Calculate time window
        now = datetime.utcnow()
        period_start = now - timedelta(days=period_days)
        period_end = now

        # Query PostHog for all pageviews in this domain
        pageviews = self._query_pageviews(period_start, period_end)

        # Filter URLs by domain
        domain_urls = []
        for url in pageviews.keys():
            # Check if URL belongs to this domain
            # Normalized URLs from PostHog may not have protocol, so check both ways
            if (
                domain in url
                or url.startswith(f"https://{domain}")
                or url.startswith(f"http://{domain}")
            ):
                # Reconstruct full URL if needed
                if not url.startswith("http"):
                    full_url = f"https://{url}" if domain in url else url
                else:
                    full_url = url
                domain_urls.append(full_url)

        logger.info(f"Found {len(domain_urls)} unique URLs for domain {domain}")
        return domain_urls

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
        # Use HogQL for aggregation queries
        # Add explicit LIMIT to ensure we get all results (PostHog default is ~100)
        query = {
            "query": {
                "kind": "HogQLQuery",
                "query": f"""
                    SELECT
                        properties.$current_url as url,
                        count() as pageviews
                    FROM events
                    WHERE event = '$pageview'
                        AND timestamp >= '{start.isoformat()}'
                        AND timestamp < '{end.isoformat()}'
                    GROUP BY properties.$current_url
                    ORDER BY pageviews DESC
                    LIMIT 10000
                """,
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

        except httpx.HTTPStatusError as e:
            logger.error(f"PostHog pageview query failed: {e}")
            logger.error(f"Response body: {e.response.text}")
            return {}
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
