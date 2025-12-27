"""Tests for PageAnalytics-related service methods.

Tests the new analytics decoupling where analytics are tracked per-URL
independent of documents.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from kurt.db.models import AnalyticsDomain, Document, PageAnalytics, SourceType
from kurt.integrations.analytics.adapters.base import AnalyticsMetrics
from kurt.integrations.analytics.service import AnalyticsService


class TestUpsertPageAnalytics:
    """Test creating and updating PageAnalytics records."""

    def test_create_new_page_analytics(self, analytics_session):
        """Test creating a new PageAnalytics record."""
        metrics = AnalyticsMetrics(
            pageviews_60d=1000,
            unique_visitors_60d=500,
            pageviews_30d=600,
            unique_visitors_30d=300,
            pageviews_previous_30d=400,
            unique_visitors_previous_30d=200,
            avg_session_duration_seconds=120.5,
            bounce_rate=0.35,
            pageviews_trend="increasing",
            trend_percentage=50.0,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        page_analytics = AnalyticsService.upsert_page_analytics(
            analytics_session,
            url="https://docs.example.com/guide",
            domain="docs.example.com",
            metrics=metrics,
        )

        assert page_analytics.url == "docs.example.com/guide"  # Normalized
        assert page_analytics.domain == "docs.example.com"
        assert page_analytics.pageviews_60d == 1000
        assert page_analytics.unique_visitors_60d == 500
        assert page_analytics.pageviews_30d == 600
        assert page_analytics.avg_session_duration_seconds == 120.5
        assert page_analytics.bounce_rate == 0.35
        assert page_analytics.pageviews_trend == "increasing"
        assert page_analytics.trend_percentage == 50.0
        assert page_analytics.synced_at is not None

    def test_update_existing_page_analytics(self, analytics_session):
        """Test updating an existing PageAnalytics record."""
        # Create initial record
        initial_metrics = AnalyticsMetrics(
            pageviews_60d=1000,
            unique_visitors_60d=500,
            pageviews_30d=600,
            unique_visitors_30d=300,
            pageviews_previous_30d=400,
            unique_visitors_previous_30d=200,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        initial = AnalyticsService.upsert_page_analytics(
            analytics_session,
            url="https://docs.example.com/guide",
            domain="docs.example.com",
            metrics=initial_metrics,
        )
        analytics_session.commit()
        initial_id = initial.id

        # Update with new metrics
        updated_metrics = AnalyticsMetrics(
            pageviews_60d=2000,
            unique_visitors_60d=1000,
            pageviews_30d=1200,
            unique_visitors_30d=600,
            pageviews_previous_30d=800,
            unique_visitors_previous_30d=400,
            pageviews_trend="increasing",
            trend_percentage=100.0,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        updated = AnalyticsService.upsert_page_analytics(
            analytics_session,
            url="https://docs.example.com/guide",
            domain="docs.example.com",
            metrics=updated_metrics,
        )

        assert updated.id == initial_id  # Same record
        assert updated.pageviews_60d == 2000  # Updated values
        assert updated.unique_visitors_60d == 1000
        assert updated.pageviews_trend == "increasing"
        assert updated.trend_percentage == 100.0

    def test_url_normalization_on_upsert(self, analytics_session):
        """Test that URLs are normalized when upserting analytics."""
        metrics = AnalyticsMetrics(
            pageviews_60d=1000,
            unique_visitors_60d=500,
            pageviews_30d=600,
            unique_visitors_30d=300,
            pageviews_previous_30d=400,
            unique_visitors_previous_30d=200,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        # Try different URL variants
        urls = [
            "https://docs.example.com/guide",
            "http://docs.example.com/guide",
            "https://www.docs.example.com/guide",
            "https://docs.example.com/guide/",
            "https://docs.example.com/guide?utm=123",
        ]

        page_analytics_records = []
        for url in urls:
            pa = AnalyticsService.upsert_page_analytics(
                analytics_session,
                url=url,
                domain="docs.example.com",
                metrics=metrics,
            )
            page_analytics_records.append(pa)
            analytics_session.commit()

        # All should map to the same record (same normalized URL)
        assert len(set(pa.id for pa in page_analytics_records)) == 1
        assert page_analytics_records[0].url == "docs.example.com/guide"

    def test_upsert_multiple_different_pages(self, analytics_session):
        """Test upserting analytics for multiple different pages."""
        metrics1 = AnalyticsMetrics(
            pageviews_60d=1000,
            unique_visitors_60d=500,
            pageviews_30d=600,
            unique_visitors_30d=300,
            pageviews_previous_30d=400,
            unique_visitors_previous_30d=200,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        metrics2 = AnalyticsMetrics(
            pageviews_60d=500,
            unique_visitors_60d=250,
            pageviews_30d=300,
            unique_visitors_30d=150,
            pageviews_previous_30d=200,
            unique_visitors_previous_30d=100,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        pa1 = AnalyticsService.upsert_page_analytics(
            analytics_session,
            url="https://docs.example.com/guide",
            domain="docs.example.com",
            metrics=metrics1,
        )

        pa2 = AnalyticsService.upsert_page_analytics(
            analytics_session,
            url="https://docs.example.com/tutorial",
            domain="docs.example.com",
            metrics=metrics2,
        )

        assert pa1.id != pa2.id
        assert pa1.url == "docs.example.com/guide"
        assert pa2.url == "docs.example.com/tutorial"
        assert pa1.pageviews_60d == 1000
        assert pa2.pageviews_60d == 500


class TestSyncDomainAnalyticsWithPageAnalytics:
    """Test syncing analytics to PageAnalytics (not DocumentAnalytics)."""

    def test_sync_creates_page_analytics_without_documents(self, analytics_session):
        """Test syncing analytics when no documents exist (key feature)."""
        # Create domain
        domain = AnalyticsDomain(
            domain="docs.example.com",
            platform="posthog",
            has_data=False,
        )
        analytics_session.add(domain)
        analytics_session.commit()

        # Mock adapter - returns URLs that don't exist as documents
        mock_adapter = MagicMock()
        mock_adapter.get_domain_urls.return_value = [
            "https://docs.example.com/guide",
            "https://docs.example.com/tutorial",
        ]
        mock_adapter.sync_metrics.return_value = {
            "https://docs.example.com/guide": AnalyticsMetrics(
                pageviews_60d=1000,
                unique_visitors_60d=500,
                pageviews_30d=600,
                unique_visitors_30d=300,
                pageviews_previous_30d=400,
                unique_visitors_previous_30d=200,
                period_start=datetime.utcnow() - timedelta(days=60),
                period_end=datetime.utcnow(),
            ),
            "https://docs.example.com/tutorial": AnalyticsMetrics(
                pageviews_60d=500,
                unique_visitors_60d=250,
                pageviews_30d=300,
                unique_visitors_30d=150,
                pageviews_previous_30d=200,
                unique_visitors_previous_30d=100,
                period_start=datetime.utcnow() - timedelta(days=60),
                period_end=datetime.utcnow(),
            ),
        }

        # Sync analytics
        result = AnalyticsService.sync_domain_analytics(
            analytics_session, domain, mock_adapter, period_days=60
        )

        # Verify results
        assert result["synced_count"] == 2
        assert result["total_urls"] == 2
        assert result["total_pageviews"] == 1500

        # Verify PageAnalytics records created
        page_analytics = analytics_session.query(PageAnalytics).all()
        assert len(page_analytics) == 2

        # Find specific records
        guide_analytics = (
            analytics_session.query(PageAnalytics)
            .filter(PageAnalytics.url == "docs.example.com/guide")
            .first()
        )
        assert guide_analytics is not None
        assert guide_analytics.pageviews_60d == 1000
        assert guide_analytics.domain == "docs.example.com"

    def test_sync_with_some_documents_existing(self, analytics_session):
        """Test syncing when some URLs are documents and some aren't."""
        # Create domain
        domain = AnalyticsDomain(
            domain="docs.example.com",
            platform="posthog",
            has_data=False,
        )
        analytics_session.add(domain)

        # Create one document
        doc = Document(
            id=uuid4(),
            title="Guide",
            source_type=SourceType.URL,
            source_url="https://docs.example.com/guide",
        )
        analytics_session.add(doc)
        analytics_session.commit()

        # Mock adapter returns 2 URLs, but only one is a document
        mock_adapter = MagicMock()
        mock_adapter.get_domain_urls.return_value = [
            "https://docs.example.com/guide",  # Exists as document
            "https://docs.example.com/tutorial",  # Doesn't exist
        ]
        mock_adapter.sync_metrics.return_value = {
            "https://docs.example.com/guide": AnalyticsMetrics(
                pageviews_60d=1000,
                unique_visitors_60d=500,
                pageviews_30d=600,
                unique_visitors_30d=300,
                pageviews_previous_30d=400,
                unique_visitors_previous_30d=200,
                period_start=datetime.utcnow() - timedelta(days=60),
                period_end=datetime.utcnow(),
            ),
            "https://docs.example.com/tutorial": AnalyticsMetrics(
                pageviews_60d=500,
                unique_visitors_60d=250,
                pageviews_30d=300,
                unique_visitors_30d=150,
                pageviews_previous_30d=200,
                unique_visitors_previous_30d=100,
                period_start=datetime.utcnow() - timedelta(days=60),
                period_end=datetime.utcnow(),
            ),
        }

        # Sync analytics
        result = AnalyticsService.sync_domain_analytics(
            analytics_session, domain, mock_adapter, period_days=60
        )

        # Both URLs should have PageAnalytics (regardless of document existence)
        assert result["synced_count"] == 2
        page_analytics = analytics_session.query(PageAnalytics).all()
        assert len(page_analytics) == 2

    def test_sync_updates_domain_metadata(self, analytics_session):
        """Test that domain metadata is updated after sync."""
        domain = AnalyticsDomain(
            domain="docs.example.com",
            platform="posthog",
            has_data=False,
            last_synced_at=None,
        )
        analytics_session.add(domain)
        analytics_session.commit()

        # Mock adapter
        mock_adapter = MagicMock()
        mock_adapter.get_domain_urls.return_value = ["https://docs.example.com/guide"]
        mock_adapter.sync_metrics.return_value = {
            "https://docs.example.com/guide": AnalyticsMetrics(
                pageviews_60d=1000,
                unique_visitors_60d=500,
                pageviews_30d=600,
                unique_visitors_30d=300,
                pageviews_previous_30d=400,
                unique_visitors_previous_30d=200,
                period_start=datetime.utcnow() - timedelta(days=60),
                period_end=datetime.utcnow(),
            ),
        }

        # Sync
        AnalyticsService.sync_domain_analytics(analytics_session, domain, mock_adapter)

        # Verify domain metadata updated
        assert domain.has_data is True
        assert domain.last_synced_at is not None

    def test_sync_with_no_urls(self, analytics_session):
        """Test syncing when analytics platform returns no URLs."""
        domain = AnalyticsDomain(
            domain="docs.example.com",
            platform="posthog",
            has_data=False,
        )
        analytics_session.add(domain)
        analytics_session.commit()

        # Mock adapter returns no URLs
        mock_adapter = MagicMock()
        mock_adapter.get_domain_urls.return_value = []

        # Sync
        result = AnalyticsService.sync_domain_analytics(analytics_session, domain, mock_adapter)

        assert result["synced_count"] == 0
        assert result["total_urls"] == 0
        assert result["total_pageviews"] == 0
        assert domain.has_data is False
        assert domain.last_synced_at is not None


# Fixtures
@pytest.fixture
def analytics_session(tmp_path, monkeypatch):
    """Create a test database session with analytics tables."""
    from click.testing import CliRunner

    from kurt.cli import main
    from kurt.db.database import get_session

    # Create test project directory
    project_dir = tmp_path / "test-page-analytics"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Initialize Kurt project (creates DB)
    runner = CliRunner()
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 0

    session = get_session()
    yield session
    session.close()
