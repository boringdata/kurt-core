"""Analytics service for managing analytics integration.

This service handles business logic for analytics operations:
- Testing platform connections
- Registering domains for analytics tracking
- Syncing analytics metrics from external platforms
- Managing DocumentAnalytics records

Business logic is separated from CLI commands for testability and reusability.
"""

from datetime import datetime
from typing import Dict, List
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from kurt.db.models import AnalyticsDomain, Document, DocumentAnalytics
from kurt.integrations.analytics.adapters.base import AnalyticsAdapter, AnalyticsMetrics


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
            True if connection successful, False otherwise

        Raises:
            ValueError: If platform is not supported
            ImportError: If platform adapter dependencies are missing
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
    def get_documents_for_domain(session: Session, domain: str) -> List[Document]:
        """
        Get all documents for a domain.

        Handles multiple URL variants:
        - https://domain
        - http://domain
        - https://www.domain

        Args:
            session: Database session
            domain: Domain name (e.g., "docs.company.com")

        Returns:
            List of Document instances
        """
        # Query for all URL variants
        docs = []

        # https://domain
        docs.extend(
            session.query(Document)
            .filter(Document.source_url.startswith(f"https://{domain}"))
            .all()
        )

        # http://domain
        docs.extend(
            session.query(Document).filter(Document.source_url.startswith(f"http://{domain}")).all()
        )

        # https://www.domain
        docs.extend(
            session.query(Document)
            .filter(Document.source_url.startswith(f"https://www.{domain}"))
            .all()
        )

        # Deduplicate by document ID
        unique_docs = {doc.id: doc for doc in docs}
        return list(unique_docs.values())

    @staticmethod
    def upsert_document_analytics(
        session: Session,
        document_id: UUID,
        metrics: AnalyticsMetrics,
    ) -> DocumentAnalytics:
        """
        Create or update DocumentAnalytics record.

        Args:
            session: Database session
            document_id: Document UUID
            metrics: Analytics metrics from platform

        Returns:
            Created or updated DocumentAnalytics instance
        """
        # Check if analytics record exists
        existing = (
            session.query(DocumentAnalytics)
            .filter(DocumentAnalytics.document_id == document_id)
            .first()
        )

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
            new_analytics = DocumentAnalytics(
                id=uuid4(),
                document_id=document_id,
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

        Args:
            session: Database session
            domain_obj: AnalyticsDomain instance to sync
            adapter: Analytics adapter for fetching metrics
            period_days: Number of days to query (default: 60)

        Returns:
            Dictionary with sync results:
            {
                "synced_count": int,
                "total_documents": int,
                "total_pageviews": int,
            }

        Raises:
            Exception: If sync fails
        """
        # Get all documents for domain
        docs = AnalyticsService.get_documents_for_domain(session, domain_obj.domain)

        if not docs:
            return {
                "synced_count": 0,
                "total_documents": 0,
                "total_pageviews": 0,
            }

        # Fetch metrics from platform
        urls = [doc.source_url for doc in docs if doc.source_url]
        metrics_map = adapter.sync_metrics(urls, period_days=period_days)

        # Update or create DocumentAnalytics records
        synced_count = 0
        total_pageviews = 0

        for doc in docs:
            if doc.source_url in metrics_map:
                metrics = metrics_map[doc.source_url]
                AnalyticsService.upsert_document_analytics(session, doc.id, metrics)
                synced_count += 1
                total_pageviews += metrics.pageviews_60d

        # Update domain metadata
        domain_obj.last_synced_at = datetime.utcnow()
        domain_obj.has_data = synced_count > 0
        session.add(domain_obj)

        return {
            "synced_count": synced_count,
            "total_documents": len(docs),
            "total_pageviews": total_pageviews,
        }
