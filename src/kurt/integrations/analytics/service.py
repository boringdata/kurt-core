"""Analytics service for managing analytics integration.

This service handles business logic for analytics operations:
- Testing platform connections
- Registering domains for analytics tracking
- Syncing analytics metrics from external platforms
- Managing PageAnalytics records (URL-based, independent of documents)

Business logic is separated from CLI commands for testability and reusability.
"""

from datetime import datetime
from typing import Dict
from uuid import uuid4

from sqlalchemy.orm import Session

from kurt.db.models import AnalyticsDomain, PageAnalytics
from kurt.integrations.analytics.adapters.base import AnalyticsAdapter, AnalyticsMetrics
from kurt.integrations.analytics.utils import normalize_url_for_analytics


class AnalyticsService:
    """Service for analytics operations."""

    @staticmethod
    def get_adapter_for_platform(
        platform: str, platform_config: Dict[str, str]
    ) -> AnalyticsAdapter:
        """
        Create analytics adapter from platform configuration.

        Args:
            platform: Analytics platform name (e.g., 'posthog', 'ga4')
            platform_config: Platform-specific configuration dictionary

        Returns:
            Initialized analytics adapter

        Raises:
            ValueError: If platform is not supported
            ImportError: If platform adapter dependencies are missing
        """
        if platform == "posthog":
            from kurt.integrations.analytics.adapters.posthog import PostHogAdapter

            return PostHogAdapter(
                project_id=platform_config["project_id"],
                api_key=platform_config["api_key"],
            )
        elif platform == "ga4":
            # TODO: Implement GA4 adapter
            raise NotImplementedError("GA4 adapter not yet implemented")
        elif platform == "plausible":
            # TODO: Implement Plausible adapter
            raise NotImplementedError("Plausible adapter not yet implemented")
        else:
            raise ValueError(f"Unsupported analytics platform: {platform}")

    @staticmethod
    def test_platform_connection(platform: str, platform_config: Dict[str, str]) -> bool:
        """
        Test connection to analytics platform.

        Args:
            platform: Analytics platform name
            platform_config: Platform credentials

        Returns:
            True if connection successful

        Raises:
            ValueError: If platform is not supported
            ImportError: If platform adapter dependencies are missing
            ConnectionError: If connection fails (with details about the failure)
        """
        adapter = AnalyticsService.get_adapter_for_platform(platform, platform_config)
        return adapter.test_connection()

    @staticmethod
    def register_domain(
        session: Session,
        domain: str,
        platform: str,
    ) -> AnalyticsDomain:
        """
        Register or update analytics domain.

        Args:
            session: Database session
            domain: Domain name (e.g., "docs.company.com")
            platform: Analytics platform (e.g., "posthog")

        Returns:
            Created or updated AnalyticsDomain instance
        """
        # Check if domain already exists
        existing = session.query(AnalyticsDomain).filter(AnalyticsDomain.domain == domain).first()

        if existing:
            # Update existing registration
            existing.platform = platform
            existing.updated_at = datetime.utcnow()
            session.add(existing)
            return existing
        else:
            # Create new registration
            analytics_domain = AnalyticsDomain(
                domain=domain,
                platform=platform,
                has_data=False,  # Will be set to True after first sync
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(analytics_domain)
            return analytics_domain

    @staticmethod
    def upsert_page_analytics(
        session: Session,
        url: str,
        domain: str,
        metrics: AnalyticsMetrics,
    ) -> PageAnalytics:
        """
        Create or update PageAnalytics record.

        Args:
            session: Database session
            url: Page URL
            domain: Domain name (for indexing)
            metrics: Analytics metrics from platform

        Returns:
            Created or updated PageAnalytics instance
        """
        # Normalize URL for consistent storage
        normalized_url = normalize_url_for_analytics(url)

        # Check if analytics record exists
        existing = session.query(PageAnalytics).filter(PageAnalytics.url == normalized_url).first()

        if existing:
            # Update existing record
            existing.pageviews_60d = metrics.pageviews_60d
            existing.pageviews_30d = metrics.pageviews_30d
            existing.pageviews_previous_30d = metrics.pageviews_previous_30d
            existing.unique_visitors_60d = metrics.unique_visitors_60d
            existing.unique_visitors_30d = metrics.unique_visitors_30d
            existing.unique_visitors_previous_30d = metrics.unique_visitors_previous_30d
            existing.avg_session_duration_seconds = metrics.avg_session_duration_seconds
            existing.bounce_rate = metrics.bounce_rate
            existing.pageviews_trend = metrics.pageviews_trend
            existing.trend_percentage = metrics.trend_percentage
            existing.period_start = metrics.period_start
            existing.period_end = metrics.period_end
            existing.synced_at = datetime.utcnow()
            session.add(existing)
            return existing
        else:
            # Create new record
            new_analytics = PageAnalytics(
                id=uuid4(),
                url=normalized_url,
                domain=domain,
                pageviews_60d=metrics.pageviews_60d,
                pageviews_30d=metrics.pageviews_30d,
                pageviews_previous_30d=metrics.pageviews_previous_30d,
                unique_visitors_60d=metrics.unique_visitors_60d,
                unique_visitors_30d=metrics.unique_visitors_30d,
                unique_visitors_previous_30d=metrics.unique_visitors_previous_30d,
                avg_session_duration_seconds=metrics.avg_session_duration_seconds,
                bounce_rate=metrics.bounce_rate,
                pageviews_trend=metrics.pageviews_trend,
                trend_percentage=metrics.trend_percentage,
                period_start=metrics.period_start,
                period_end=metrics.period_end,
                synced_at=datetime.utcnow(),
            )
            session.add(new_analytics)
            return new_analytics

    @staticmethod
    def sync_domain_analytics(
        session: Session,
        domain_obj: AnalyticsDomain,
        adapter: AnalyticsAdapter,
        period_days: int = 60,
    ) -> Dict[str, any]:
        """
        Sync analytics metrics for a domain.

        Queries the analytics platform directly for all URLs in the domain,
        independent of whether those URLs exist as documents in Kurt's database.

        Args:
            session: Database session
            domain_obj: AnalyticsDomain instance to sync
            adapter: Analytics adapter for fetching metrics
            period_days: Number of days to query (default: 60)

        Returns:
            Dictionary with sync results:
            {
                "synced_count": int,
                "total_urls": int,
                "total_pageviews": int,
            }

        Raises:
            Exception: If sync fails
        """
        # Get all URLs for this domain from the analytics platform
        urls = adapter.get_domain_urls(domain_obj.domain, period_days=period_days)

        if not urls:
            # No URLs found in analytics platform
            domain_obj.last_synced_at = datetime.utcnow()
            domain_obj.has_data = False
            session.add(domain_obj)
            return {
                "synced_count": 0,
                "total_urls": 0,
                "total_pageviews": 0,
            }

        # Fetch metrics from platform for all URLs
        metrics_map = adapter.sync_metrics(urls, period_days=period_days)

        # Update or create PageAnalytics records for each URL
        synced_count = 0
        total_pageviews = 0

        for url, metrics in metrics_map.items():
            AnalyticsService.upsert_page_analytics(session, url, domain_obj.domain, metrics)
            synced_count += 1
            total_pageviews += metrics.pageviews_60d

        # Update domain metadata
        domain_obj.last_synced_at = datetime.utcnow()
        domain_obj.has_data = synced_count > 0
        session.add(domain_obj)

        return {
            "synced_count": synced_count,
            "total_urls": len(urls),
            "total_pageviews": total_pageviews,
        }
