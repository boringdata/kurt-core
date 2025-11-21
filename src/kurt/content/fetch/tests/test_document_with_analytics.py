"""Tests for document listing with analytics data integration.

Tests the integration between Documents and PageAnalytics, ensuring
that content commands correctly join and filter by analytics data.
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from kurt.content.document import list_content
from kurt.db.database import get_session
from kurt.db.models import Document, PageAnalytics, SourceType


@pytest.fixture
def content_session(tmp_path, monkeypatch):
    """Create a test database session with documents and analytics."""
    from click.testing import CliRunner

    from kurt.cli import main

    # Create test project directory
    project_dir = tmp_path / "test-content-analytics"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Initialize Kurt project (creates DB)
    runner = CliRunner()
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 0

    session = get_session()
    yield session
    session.close()


class TestListContentWithAnalytics:
    """Test list_content() with analytics integration."""

    def test_list_content_with_analytics_flag(self, content_session):
        """Test that analytics data is attached when with_analytics=True."""
        # Create document
        doc = Document(
            id=uuid4(),
            title="Test Doc",
            source_type=SourceType.URL,
            source_url="https://docs.example.com/guide",
        )
        content_session.add(doc)

        # Create matching PageAnalytics
        analytics = PageAnalytics(
            id=uuid4(),
            url="docs.example.com/guide",  # Normalized
            domain="docs.example.com",
            pageviews_30d=1000,
            pageviews_60d=2000,
            pageviews_previous_30d=800,
            unique_visitors_30d=500,
            unique_visitors_60d=1000,
            pageviews_trend="increasing",
            trend_percentage=25.0,
            bounce_rate=0.35,
            avg_session_duration_seconds=120.5,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )
        content_session.add(analytics)
        content_session.commit()

        # List with analytics
        docs = list_content(with_analytics=True)

        assert len(docs) == 1
        assert docs[0].id == doc.id
        assert hasattr(docs[0], "analytics")
        assert docs[0].analytics is not None
        assert docs[0].analytics["pageviews_30d"] == 1000
        assert docs[0].analytics["pageviews_60d"] == 2000
        assert docs[0].analytics["pageviews_trend"] == "increasing"
        assert docs[0].analytics["trend_percentage"] == 25.0

    def test_list_content_without_analytics_flag(self, content_session):
        """Test that analytics data is NOT attached when with_analytics=False."""
        doc = Document(
            id=uuid4(),
            title="Test Doc",
            source_type=SourceType.URL,
            source_url="https://docs.example.com/guide",
        )
        content_session.add(doc)
        content_session.commit()

        # List without analytics
        docs = list_content(with_analytics=False)

        assert len(docs) == 1
        assert docs[0].id == doc.id
        # Should not have analytics attribute
        assert not hasattr(docs[0], "analytics")

    def test_list_content_url_normalization(self, content_session):
        """Test that URL normalization works when matching documents to analytics."""
        # Document with full URL
        doc = Document(
            id=uuid4(),
            title="Test Doc",
            source_type=SourceType.URL,
            source_url="https://www.docs.example.com/guide/?utm=123#section",
        )
        content_session.add(doc)

        # PageAnalytics with normalized URL
        analytics = PageAnalytics(
            id=uuid4(),
            url="docs.example.com/guide",  # Normalized (no protocol, www, query, fragment)
            domain="docs.example.com",
            pageviews_30d=500,
            pageviews_60d=1000,
            pageviews_previous_30d=400,
            unique_visitors_30d=250,
            unique_visitors_60d=500,
            pageviews_trend="stable",
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )
        content_session.add(analytics)
        content_session.commit()

        # Should match despite different URL formats
        docs = list_content(with_analytics=True)

        assert len(docs) == 1
        assert docs[0].analytics is not None
        assert docs[0].analytics["pageviews_30d"] == 500

    def test_list_content_filter_by_min_pageviews(self, content_session):
        """Test filtering documents by minimum pageviews."""
        # Doc 1: High traffic
        doc1 = Document(
            id=uuid4(),
            title="High Traffic",
            source_type=SourceType.URL,
            source_url="https://docs.example.com/popular",
        )
        analytics1 = PageAnalytics(
            id=uuid4(),
            url="docs.example.com/popular",
            domain="docs.example.com",
            pageviews_30d=1000,
            pageviews_60d=2000,
            pageviews_previous_30d=800,
            unique_visitors_30d=500,
            unique_visitors_60d=1000,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        # Doc 2: Low traffic
        doc2 = Document(
            id=uuid4(),
            title="Low Traffic",
            source_type=SourceType.URL,
            source_url="https://docs.example.com/unpopular",
        )
        analytics2 = PageAnalytics(
            id=uuid4(),
            url="docs.example.com/unpopular",
            domain="docs.example.com",
            pageviews_30d=50,
            pageviews_60d=100,
            pageviews_previous_30d=40,
            unique_visitors_30d=25,
            unique_visitors_60d=50,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        content_session.add_all([doc1, doc2, analytics1, analytics2])
        content_session.commit()

        # Filter for docs with at least 500 pageviews
        docs = list_content(with_analytics=True, min_pageviews=500)

        assert len(docs) == 1
        assert docs[0].id == doc1.id
        assert docs[0].analytics["pageviews_30d"] == 1000

    def test_list_content_filter_by_max_pageviews(self, content_session):
        """Test filtering documents by maximum pageviews."""
        # Doc 1: High traffic
        doc1 = Document(
            id=uuid4(),
            title="High Traffic",
            source_type=SourceType.URL,
            source_url="https://docs.example.com/popular",
        )
        analytics1 = PageAnalytics(
            id=uuid4(),
            url="docs.example.com/popular",
            domain="docs.example.com",
            pageviews_30d=1000,
            pageviews_60d=2000,
            pageviews_previous_30d=800,
            unique_visitors_30d=500,
            unique_visitors_60d=1000,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        # Doc 2: Low traffic
        doc2 = Document(
            id=uuid4(),
            title="Low Traffic",
            source_type=SourceType.URL,
            source_url="https://docs.example.com/unpopular",
        )
        analytics2 = PageAnalytics(
            id=uuid4(),
            url="docs.example.com/unpopular",
            domain="docs.example.com",
            pageviews_30d=50,
            pageviews_60d=100,
            pageviews_previous_30d=40,
            unique_visitors_30d=25,
            unique_visitors_60d=50,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        content_session.add_all([doc1, doc2, analytics1, analytics2])
        content_session.commit()

        # Filter for docs with at most 100 pageviews
        docs = list_content(with_analytics=True, max_pageviews=100)

        assert len(docs) == 1
        assert docs[0].id == doc2.id
        assert docs[0].analytics["pageviews_30d"] == 50

    def test_list_content_filter_by_trend(self, content_session):
        """Test filtering documents by traffic trend."""
        # Doc 1: Increasing traffic
        doc1 = Document(
            id=uuid4(),
            title="Growing",
            source_type=SourceType.URL,
            source_url="https://docs.example.com/growing",
        )
        analytics1 = PageAnalytics(
            id=uuid4(),
            url="docs.example.com/growing",
            domain="docs.example.com",
            pageviews_30d=600,
            pageviews_60d=1000,
            pageviews_previous_30d=400,
            unique_visitors_30d=300,
            unique_visitors_60d=500,
            pageviews_trend="increasing",
            trend_percentage=50.0,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        # Doc 2: Decreasing traffic
        doc2 = Document(
            id=uuid4(),
            title="Declining",
            source_type=SourceType.URL,
            source_url="https://docs.example.com/declining",
        )
        analytics2 = PageAnalytics(
            id=uuid4(),
            url="docs.example.com/declining",
            domain="docs.example.com",
            pageviews_30d=200,
            pageviews_60d=600,
            pageviews_previous_30d=400,
            unique_visitors_30d=100,
            unique_visitors_60d=300,
            pageviews_trend="decreasing",
            trend_percentage=-50.0,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        content_session.add_all([doc1, doc2, analytics1, analytics2])
        content_session.commit()

        # Filter for decreasing traffic
        docs = list_content(with_analytics=True, trend="decreasing")

        assert len(docs) == 1
        assert docs[0].id == doc2.id
        assert docs[0].analytics["pageviews_trend"] == "decreasing"
        assert docs[0].analytics["trend_percentage"] == -50.0

    def test_list_content_order_by_pageviews(self, content_session):
        """Test ordering documents by pageviews."""
        # Create docs with different traffic
        docs_data = [
            ("Low", "https://docs.example.com/low", 100),
            ("High", "https://docs.example.com/high", 1000),
            ("Medium", "https://docs.example.com/medium", 500),
        ]

        for title, url, pageviews in docs_data:
            doc = Document(
                id=uuid4(),
                title=title,
                source_type=SourceType.URL,
                source_url=url,
            )
            analytics = PageAnalytics(
                id=uuid4(),
                url=url.replace("https://", ""),
                domain="docs.example.com",
                pageviews_30d=pageviews,
                pageviews_60d=pageviews * 2,
                pageviews_previous_30d=pageviews - 50,
                unique_visitors_30d=pageviews // 2,
                unique_visitors_60d=pageviews,
                period_start=datetime.utcnow() - timedelta(days=60),
                period_end=datetime.utcnow(),
            )
            content_session.add_all([doc, analytics])

        content_session.commit()

        # Order by pageviews descending
        docs = list_content(with_analytics=True, order_by="pageviews_30d")

        assert len(docs) == 3
        assert docs[0].title == "High"
        assert docs[0].analytics["pageviews_30d"] == 1000
        assert docs[1].title == "Medium"
        assert docs[1].analytics["pageviews_30d"] == 500
        assert docs[2].title == "Low"
        assert docs[2].analytics["pageviews_30d"] == 100

    def test_list_content_document_without_analytics(self, content_session):
        """Test handling documents that have no matching PageAnalytics."""
        # Doc with analytics
        doc1 = Document(
            id=uuid4(),
            title="With Analytics",
            source_type=SourceType.URL,
            source_url="https://docs.example.com/with",
        )
        analytics1 = PageAnalytics(
            id=uuid4(),
            url="docs.example.com/with",
            domain="docs.example.com",
            pageviews_30d=500,
            pageviews_60d=1000,
            pageviews_previous_30d=400,
            unique_visitors_30d=250,
            unique_visitors_60d=500,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        # Doc without analytics
        doc2 = Document(
            id=uuid4(),
            title="Without Analytics",
            source_type=SourceType.URL,
            source_url="https://docs.example.com/without",
        )

        content_session.add_all([doc1, doc2, analytics1])
        content_session.commit()

        # List with analytics
        docs = list_content(with_analytics=True)

        # Both docs should be returned
        assert len(docs) == 2

        # Find each doc
        doc_with = next(d for d in docs if d.id == doc1.id)
        doc_without = next(d for d in docs if d.id == doc2.id)

        # Doc1 has analytics
        assert doc_with.analytics is not None
        assert doc_with.analytics["pageviews_30d"] == 500

        # Doc2 has None analytics
        assert doc_without.analytics is None

    def test_list_content_combined_filters(self, content_session):
        """Test combining multiple analytics filters."""
        # Create various docs
        docs_data = [
            ("High Growing", "https://docs.example.com/1", 1000, "increasing", 50.0),
            ("High Stable", "https://docs.example.com/2", 900, "stable", 5.0),
            (
                "Low Growing",
                "https://docs.example.com/3",
                100,
                "increasing",
                100.0,
            ),  # Won't match
            ("Medium Decreasing", "https://docs.example.com/4", 500, "decreasing", -20.0),
        ]

        for title, url, pageviews, trend, trend_pct in docs_data:
            doc = Document(
                id=uuid4(),
                title=title,
                source_type=SourceType.URL,
                source_url=url,
            )
            analytics = PageAnalytics(
                id=uuid4(),
                url=url.replace("https://", ""),
                domain="docs.example.com",
                pageviews_30d=pageviews,
                pageviews_60d=pageviews * 2,
                pageviews_previous_30d=int(
                    pageviews / (1 + trend_pct / 100)
                ),  # Calculate based on trend
                unique_visitors_30d=pageviews // 2,
                unique_visitors_60d=pageviews,
                pageviews_trend=trend,
                trend_percentage=trend_pct,
                period_start=datetime.utcnow() - timedelta(days=60),
                period_end=datetime.utcnow(),
            )
            content_session.add_all([doc, analytics])

        content_session.commit()

        # Filter: min_pageviews=500 AND trend=increasing
        docs = list_content(
            with_analytics=True,
            min_pageviews=500,
            trend="increasing",
        )

        # Should only match "High Growing"
        assert len(docs) == 1
        assert docs[0].title == "High Growing"
        assert docs[0].analytics["pageviews_30d"] == 1000
        assert docs[0].analytics["pageviews_trend"] == "increasing"
