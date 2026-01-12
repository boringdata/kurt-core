"""
Base adapter interface for analytics integrations.

All analytics adapters must implement this interface to provide consistent
operations across different analytics platforms.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AnalyticsMetrics(BaseModel):
    """Analytics metrics for a single page/URL."""

    # Traffic metrics
    pageviews_60d: int = 0
    unique_visitors_60d: int = 0
    pageviews_30d: int = 0
    unique_visitors_30d: int = 0
    pageviews_previous_30d: int = 0
    unique_visitors_previous_30d: int = 0

    # Engagement metrics
    avg_session_duration_seconds: Optional[float] = None
    bounce_rate: Optional[float] = None

    # Trends
    pageviews_trend: str = "stable"
    trend_percentage: Optional[float] = None

    # Time window
    period_start: datetime
    period_end: datetime


class AnalyticsAdapter(ABC):
    """Abstract base class for analytics platform adapters."""

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test connection to analytics platform.

        Returns:
            True if connection successful

        Raises:
            ConnectionError: If connection fails with details about the failure
        """
        pass

    @abstractmethod
    def get_domain_urls(self, domain: str, period_days: int = 60) -> list[str]:
        """
        Get all URLs for a domain from the analytics platform.

        Args:
            domain: Domain to filter by (e.g., "example.com")
            period_days: Number of days to query (default: 60)

        Returns:
            List of unique URLs found in analytics for this domain

        Raises:
            Exception if API call fails
        """
        pass

    @abstractmethod
    def sync_metrics(self, urls: list[str], period_days: int = 60) -> dict[str, AnalyticsMetrics]:
        """
        Fetch analytics metrics for given URLs.

        Args:
            urls: List of URLs to fetch metrics for
            period_days: Number of days to query (default: 60)

        Returns:
            Dict mapping URL -> AnalyticsMetrics
            URLs with no data should return AnalyticsMetrics with zeros

        Raises:
            Exception if API call fails
        """
        pass
