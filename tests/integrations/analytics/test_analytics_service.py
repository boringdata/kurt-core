"""Tests for analytics service."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from kurt.db.models import AnalyticsDomain, Document, DocumentAnalytics, SourceType
from kurt.integrations.analytics.adapters.base import AnalyticsMetrics
from kurt.integrations.analytics.service import AnalyticsService


class TestGetAdapterForPlatform:
    """Test adapter factory method."""

    def test_get_posthog_adapter(self):
        """Test creating PostHog adapter."""
        platform_config = {
            "project_id": "phc_test123",
            "api_key": "phx_test456",
        }

        with patch(
            "kurt.integrations.analytics.adapters.posthog.PostHogAdapter"
        ) as mock_adapter_class:
            AnalyticsService.get_adapter_for_platform("posthog", platform_config)

            # Verify adapter was created with correct credentials
            mock_adapter_class.assert_called_once_with(
                project_id="phc_test123",
                api_key="phx_test456",
            )

    def test_unsupported_platform(self):
        """Test error for unsupported platform."""
        with pytest.raises(ValueError) as exc_info:
            AnalyticsService.get_adapter_for_platform("unknown", {})

        assert "Unsupported analytics platform: unknown" in str(exc_info.value)

    def test_ga4_not_implemented(self):
        """Test GA4 adapter raises NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc_info:
            AnalyticsService.get_adapter_for_platform("ga4", {"property_id": "123"})

        assert "GA4 adapter not yet implemented" in str(exc_info.value)


class TestTestPlatformConnection:
    """Test platform connection testing."""

    def test_connection_successful(self):
        """Test successful connection."""
        platform_config = {"project_id": "phc_test", "api_key": "phx_test"}

        mock_adapter = MagicMock()
        mock_adapter.test_connection.return_value = True

        with patch.object(AnalyticsService, "get_adapter_for_platform", return_value=mock_adapter):
            result = AnalyticsService.test_platform_connection("posthog", platform_config)

            assert result is True
            mock_adapter.test_connection.assert_called_once()

    def test_connection_failed(self):
        """Test failed connection."""
        platform_config = {"project_id": "phc_test", "api_key": "phx_test"}

        mock_adapter = MagicMock()
        mock_adapter.test_connection.return_value = False

        with patch.object(AnalyticsService, "get_adapter_for_platform", return_value=mock_adapter):
            result = AnalyticsService.test_platform_connection("posthog", platform_config)

            assert result is False


class TestRegisterDomain:
    """Test domain registration."""

    def test_register_new_domain(self, analytics_session):
        """Test registering a new domain."""
        domain_obj = AnalyticsService.register_domain(
            analytics_session, "docs.example.com", "posthog"
        )

        assert domain_obj.domain == "docs.example.com"
        assert domain_obj.platform == "posthog"
        assert domain_obj.has_data is False
        assert domain_obj.created_at is not None
        assert domain_obj.updated_at is not None

        # Verify saved to database
        analytics_session.commit()
        saved = (
            analytics_session.query(AnalyticsDomain)
            .filter(AnalyticsDomain.domain == "docs.example.com")
            .first()
        )
        assert saved is not None
        assert saved.id == domain_obj.id

    def test_update_existing_domain(self, analytics_session):
        """Test updating an existing domain registration."""
        # Create initial domain
        initial = AnalyticsDomain(
            domain="docs.example.com",
            platform="ga4",
            has_data=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        analytics_session.add(initial)
        analytics_session.commit()

        initial_id = initial.id
        initial_created_at = initial.created_at

        # Update to different platform
        updated = AnalyticsService.register_domain(analytics_session, "docs.example.com", "posthog")

        assert updated.id == initial_id  # Same record
        assert updated.platform == "posthog"  # Updated platform
        assert updated.created_at == initial_created_at  # Created date unchanged
        assert updated.updated_at > initial_created_at  # Updated date changed


class TestGetDocumentsForDomain:
    """Test document retrieval for domains."""

    def test_get_documents_https_variant(self, analytics_session):
        """Test getting documents with https:// prefix."""
        doc1 = Document(
            id=uuid4(),
            title="Doc 1",
            source_type=SourceType.URL,
            source_url="https://docs.example.com/guide",
        )
        doc2 = Document(
            id=uuid4(),
            title="Doc 2",
            source_type=SourceType.URL,
            source_url="https://other.com/page",
        )
        analytics_session.add_all([doc1, doc2])
        analytics_session.commit()

        docs = AnalyticsService.get_documents_for_domain(analytics_session, "docs.example.com")

        assert len(docs) == 1
        assert docs[0].id == doc1.id

    def test_get_documents_http_variant(self, analytics_session):
        """Test getting documents with http:// prefix."""
        doc = Document(
            id=uuid4(),
            title="HTTP Doc",
            source_type=SourceType.URL,
            source_url="http://docs.example.com/page",
        )
        analytics_session.add(doc)
        analytics_session.commit()

        docs = AnalyticsService.get_documents_for_domain(analytics_session, "docs.example.com")

        assert len(docs) == 1
        assert docs[0].id == doc.id

    def test_get_documents_www_variant(self, analytics_session):
        """Test getting documents with www. prefix."""
        doc = Document(
            id=uuid4(),
            title="WWW Doc",
            source_type=SourceType.URL,
            source_url="https://www.docs.example.com/page",
        )
        analytics_session.add(doc)
        analytics_session.commit()

        docs = AnalyticsService.get_documents_for_domain(analytics_session, "docs.example.com")

        assert len(docs) == 1
        assert docs[0].id == doc.id

    def test_get_documents_all_variants(self, analytics_session):
        """Test getting documents across all URL variants."""
        doc1 = Document(
            id=uuid4(),
            title="HTTPS",
            source_type=SourceType.URL,
            source_url="https://docs.example.com/a",
        )
        doc2 = Document(
            id=uuid4(),
            title="HTTP",
            source_type=SourceType.URL,
            source_url="http://docs.example.com/b",
        )
        doc3 = Document(
            id=uuid4(),
            title="WWW",
            source_type=SourceType.URL,
            source_url="https://www.docs.example.com/c",
        )
        analytics_session.add_all([doc1, doc2, doc3])
        analytics_session.commit()

        docs = AnalyticsService.get_documents_for_domain(analytics_session, "docs.example.com")

        assert len(docs) == 3
        doc_ids = {doc.id for doc in docs}
        assert doc_ids == {doc1.id, doc2.id, doc3.id}

    def test_get_documents_deduplication(self, analytics_session):
        """Test that duplicate documents are deduplicated."""
        # This shouldn't normally happen, but test the deduplication logic
        doc_id = uuid4()
        doc1 = Document(
            id=doc_id,
            title="Doc",
            source_type=SourceType.URL,
            source_url="https://docs.example.com/page",
        )
        analytics_session.add(doc1)
        analytics_session.commit()

        docs = AnalyticsService.get_documents_for_domain(analytics_session, "docs.example.com")

        # Should only return one instance even if query logic could return duplicates
        assert len(docs) == 1
        assert docs[0].id == doc_id


class TestUpsertDocumentAnalytics:
    """Test creating/updating DocumentAnalytics records."""

    def test_create_new_analytics(self, analytics_session):
        """Test creating new DocumentAnalytics record."""
        doc = Document(
            id=uuid4(),
            title="Test Doc",
            source_type=SourceType.URL,
            source_url="https://example.com",
        )
        analytics_session.add(doc)
        analytics_session.commit()

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

        analytics_obj = AnalyticsService.upsert_document_analytics(
            analytics_session, doc.id, metrics
        )

        assert analytics_obj.document_id == doc.id
        assert analytics_obj.pageviews_60d == 1000
        assert analytics_obj.unique_visitors_60d == 500
        assert analytics_obj.pageviews_30d == 600
        assert analytics_obj.avg_session_duration_seconds == 120.5
        assert analytics_obj.bounce_rate == 0.35
        assert analytics_obj.pageviews_trend == "increasing"
        assert analytics_obj.trend_percentage == 50.0
        assert analytics_obj.synced_at is not None

    def test_update_existing_analytics(self, analytics_session):
        """Test updating existing DocumentAnalytics record."""
        doc = Document(
            id=uuid4(),
            title="Test Doc",
            source_type=SourceType.URL,
            source_url="https://example.com",
        )
        analytics_session.add(doc)
        analytics_session.commit()

        # Create initial analytics
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

        initial = AnalyticsService.upsert_document_analytics(
            analytics_session, doc.id, initial_metrics
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

        updated = AnalyticsService.upsert_document_analytics(
            analytics_session, doc.id, updated_metrics
        )

        assert updated.id == initial_id  # Same record
        assert updated.pageviews_60d == 2000  # Updated values
        assert updated.unique_visitors_60d == 1000
        assert updated.pageviews_trend == "increasing"
        assert updated.trend_percentage == 100.0


class TestSyncDomainAnalytics:
    """Test syncing analytics for a domain."""

    def test_sync_domain_with_documents(self, analytics_session):
        """Test successful sync with documents."""
        # Create domain
        domain = AnalyticsDomain(
            domain="docs.example.com",
            platform="posthog",
            has_data=False,
        )
        analytics_session.add(domain)

        # Create documents
        doc1 = Document(
            id=uuid4(),
            title="Guide",
            source_type=SourceType.URL,
            source_url="https://docs.example.com/guide",
        )
        doc2 = Document(
            id=uuid4(),
            title="Tutorial",
            source_type=SourceType.URL,
            source_url="https://docs.example.com/tutorial",
        )
        analytics_session.add_all([doc1, doc2])
        analytics_session.commit()

        # Mock adapter
        mock_adapter = MagicMock()
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

        # Sync
        result = AnalyticsService.sync_domain_analytics(
            analytics_session, domain, mock_adapter, period_days=60
        )

        # Verify results
        assert result["synced_count"] == 2
        assert result["total_documents"] == 2
        assert result["total_pageviews"] == 1500  # 1000 + 500

        # Verify domain updated
        assert domain.has_data is True
        assert domain.last_synced_at is not None

        # Verify analytics records created
        analytics1 = (
            analytics_session.query(DocumentAnalytics)
            .filter(DocumentAnalytics.document_id == doc1.id)
            .first()
        )
        assert analytics1 is not None
        assert analytics1.pageviews_60d == 1000

        analytics2 = (
            analytics_session.query(DocumentAnalytics)
            .filter(DocumentAnalytics.document_id == doc2.id)
            .first()
        )
        assert analytics2 is not None
        assert analytics2.pageviews_60d == 500

    def test_sync_domain_no_documents(self, analytics_session):
        """Test sync with no documents."""
        domain = AnalyticsDomain(
            domain="docs.example.com",
            platform="posthog",
            has_data=False,
        )
        analytics_session.add(domain)
        analytics_session.commit()

        mock_adapter = MagicMock()

        result = AnalyticsService.sync_domain_analytics(analytics_session, domain, mock_adapter)

        assert result["synced_count"] == 0
        assert result["total_documents"] == 0
        assert result["total_pageviews"] == 0

        # Adapter should not be called
        mock_adapter.sync_metrics.assert_not_called()


# Fixtures
@pytest.fixture
def analytics_session(tmp_path, monkeypatch):
    """Create a test database session with analytics tables."""
    from click.testing import CliRunner

    from kurt.cli import main
    from kurt.db.database import get_session

    # Create test project directory
    project_dir = tmp_path / "test-analytics-service"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Initialize Kurt project (creates DB)
    runner = CliRunner()
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 0

    session = get_session()
    yield session
    session.close()
