"""Tests for analytics CLI commands.

Tests the full CLI integration for analytics commands:
- kurt integrations analytics onboard
- kurt integrations analytics sync
- kurt integrations analytics list
- kurt integrations analytics query
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from click.testing import CliRunner

from kurt.cli import main
from kurt.db.database import get_session
from kurt.db.models import AnalyticsDomain, Document, PageAnalytics, SourceType


@pytest.fixture
def cli_session(tmp_path, monkeypatch):
    """Create a test CLI environment with database."""
    # Create test project directory
    project_dir = tmp_path / "test-analytics-cli"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Initialize Kurt project
    runner = CliRunner()
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 0

    session = get_session()
    yield runner, session
    session.close()


class TestAnalyticsOnboard:
    """Test 'kurt integrations analytics onboard' command."""

    def test_onboard_creates_config_template(self, cli_session):
        """Test that first run creates config template."""
        runner, session = cli_session

        # First run should create template
        result = runner.invoke(main, ["integrations", "analytics", "onboard", "docs.example.com"])

        assert result.exit_code == 0
        assert "Template created" in result.output or "Created" in result.output
        assert "kurt.config" in result.output
        assert "ANALYTICS_" in result.output

    @patch("kurt.integrations.analytics.service.AnalyticsService.test_platform_connection")
    @patch("kurt.integrations.analytics.config.get_platform_config")
    @patch("kurt.integrations.analytics.config.platform_configured")
    @patch("kurt.integrations.analytics.config.analytics_config_exists")
    def test_onboard_with_valid_credentials(
        self,
        mock_config_exists,
        mock_platform_configured,
        mock_get_config,
        mock_test_connection,
        cli_session,
    ):
        """Test onboarding with valid credentials."""
        runner, session = cli_session

        # Mock: config exists and platform configured
        mock_config_exists.return_value = True
        mock_platform_configured.return_value = True
        mock_get_config.return_value = {"project_id": "12345", "api_key": "phx_test"}
        mock_test_connection.return_value = True

        result = runner.invoke(
            main,
            ["integrations", "analytics", "onboard", "docs.example.com"],
            input="n\n",  # Don't sync now
        )

        assert result.exit_code == 0
        assert "Connection successful" in result.output or "✓" in result.output

        # Verify domain was registered
        domain = (
            session.query(AnalyticsDomain)
            .filter(AnalyticsDomain.domain == "docs.example.com")
            .first()
        )
        assert domain is not None
        assert domain.platform == "posthog"  # Default platform

    @patch("kurt.integrations.analytics.service.AnalyticsService.test_platform_connection")
    @patch("kurt.integrations.analytics.config.get_platform_config")
    @patch("kurt.integrations.analytics.config.platform_configured")
    @patch("kurt.integrations.analytics.config.analytics_config_exists")
    def test_onboard_connection_failure(
        self,
        mock_config_exists,
        mock_platform_configured,
        mock_get_config,
        mock_test_connection,
        cli_session,
    ):
        """Test onboarding with connection failure."""
        runner, session = cli_session

        mock_config_exists.return_value = True
        mock_platform_configured.return_value = True
        mock_get_config.return_value = {"project_id": "12345", "api_key": "phx_test"}
        mock_test_connection.side_effect = ConnectionError(
            "Authentication failed. Check your API key."
        )

        result = runner.invoke(main, ["integrations", "analytics", "onboard", "docs.example.com"])

        assert result.exit_code != 0
        assert "Connection failed" in result.output or "Authentication failed" in result.output


class TestAnalyticsSync:
    """Test 'kurt integrations analytics sync' command."""

    @patch("kurt.integrations.analytics.service.AnalyticsService.sync_domain_analytics")
    @patch("kurt.integrations.analytics.service.AnalyticsService.get_adapter_for_platform")
    @patch("kurt.integrations.analytics.config.get_platform_config")
    @patch("kurt.integrations.analytics.config.platform_configured")
    def test_sync_single_domain(
        self,
        mock_platform_configured,
        mock_get_config,
        mock_get_adapter,
        mock_sync,
        cli_session,
    ):
        """Test syncing a single domain."""
        runner, session = cli_session

        # Create domain
        domain = AnalyticsDomain(
            domain="docs.example.com",
            platform="posthog",
            has_data=False,
        )
        session.add(domain)
        session.commit()

        # Mock configuration and sync
        mock_platform_configured.return_value = True
        mock_get_config.return_value = {
            "project_id": "12345",
            "api_key": "phx_test",
        }
        mock_get_adapter.return_value = MagicMock()
        mock_sync.return_value = {
            "synced_count": 10,
            "total_urls": 10,
            "total_pageviews": 5000,
        }

        result = runner.invoke(main, ["integrations", "analytics", "sync", "docs.example.com"])

        assert result.exit_code == 0
        assert "Synced" in result.output or "✓" in result.output
        assert "10" in result.output  # Synced count

    @patch("kurt.integrations.analytics.service.AnalyticsService.sync_domain_analytics")
    @patch("kurt.integrations.analytics.service.AnalyticsService.get_adapter_for_platform")
    @patch("kurt.integrations.analytics.config.get_platform_config")
    @patch("kurt.integrations.analytics.config.platform_configured")
    def test_sync_all_domains(
        self,
        mock_platform_configured,
        mock_get_config,
        mock_get_adapter,
        mock_sync,
        cli_session,
    ):
        """Test syncing all domains with --all flag."""
        runner, session = cli_session

        # Create multiple domains
        domain1 = AnalyticsDomain(domain="docs.example.com", platform="posthog", has_data=False)
        domain2 = AnalyticsDomain(domain="blog.example.com", platform="posthog", has_data=False)
        session.add_all([domain1, domain2])
        session.commit()

        # Mock configuration and sync
        mock_platform_configured.return_value = True
        mock_get_config.return_value = {"project_id": "12345", "api_key": "phx_test"}
        mock_get_adapter.return_value = MagicMock()
        mock_sync.return_value = {
            "synced_count": 5,
            "total_urls": 5,
            "total_pageviews": 2000,
        }

        result = runner.invoke(main, ["integrations", "analytics", "sync", "--all"])

        assert result.exit_code == 0
        # Should sync both domains
        assert "docs.example.com" in result.output
        assert "blog.example.com" in result.output

    def test_sync_nonexistent_domain(self, cli_session):
        """Test syncing a domain that hasn't been onboarded."""
        runner, session = cli_session

        result = runner.invoke(main, ["integrations", "analytics", "sync", "nonexistent.com"])

        # CLI shows error but exits with 0 (doesn't raise click.Abort)
        assert result.exit_code == 0
        assert "not configured" in result.output.lower()


class TestAnalyticsList:
    """Test 'kurt integrations analytics list' command."""

    def test_list_no_domains(self, cli_session):
        """Test listing when no domains configured."""
        runner, session = cli_session

        result = runner.invoke(main, ["integrations", "analytics", "list"])

        assert result.exit_code == 0
        assert "No domains" in result.output or "0" in result.output

    def test_list_domains_table_format(self, cli_session):
        """Test listing domains in table format."""
        runner, session = cli_session

        # Create domains
        domain1 = AnalyticsDomain(
            domain="docs.example.com",
            platform="posthog",
            has_data=True,
            last_synced_at=datetime.utcnow(),
        )
        domain2 = AnalyticsDomain(
            domain="blog.example.com",
            platform="posthog",
            has_data=False,
        )
        session.add_all([domain1, domain2])
        session.commit()

        result = runner.invoke(main, ["integrations", "analytics", "list"])

        assert result.exit_code == 0
        assert "docs.example.com" in result.output
        assert "blog.example.com" in result.output
        assert "posthog" in result.output.lower()

    def test_list_domains_json_format(self, cli_session):
        """Test listing domains in JSON format."""
        runner, session = cli_session

        domain = AnalyticsDomain(
            domain="docs.example.com",
            platform="posthog",
            has_data=True,
        )
        session.add(domain)
        session.commit()

        result = runner.invoke(main, ["integrations", "analytics", "list", "--format", "json"])

        assert result.exit_code == 0
        assert "docs.example.com" in result.output
        assert '"platform"' in result.output or "'platform'" in result.output


class TestAnalyticsQuery:
    """Test 'kurt integrations analytics query' command."""

    def test_query_domain_with_analytics(self, cli_session):
        """Test querying analytics for a domain."""
        runner, session = cli_session

        # Create domain
        domain = AnalyticsDomain(
            domain="docs.example.com",
            platform="posthog",
            has_data=True,
        )
        session.add(domain)

        # Create PageAnalytics records
        analytics1 = PageAnalytics(
            id=uuid4(),
            url="docs.example.com/guide",
            domain="docs.example.com",
            pageviews_30d=1000,
            pageviews_60d=2000,
            pageviews_previous_30d=800,
            unique_visitors_30d=500,
            unique_visitors_60d=1000,
            pageviews_trend="increasing",
            trend_percentage=25.0,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )
        analytics2 = PageAnalytics(
            id=uuid4(),
            url="docs.example.com/tutorial",
            domain="docs.example.com",
            pageviews_30d=500,
            pageviews_60d=1000,
            pageviews_previous_30d=450,
            unique_visitors_30d=250,
            unique_visitors_60d=500,
            pageviews_trend="stable",
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )
        session.add_all([analytics1, analytics2])
        session.commit()

        result = runner.invoke(main, ["integrations", "analytics", "query", "docs.example.com"])

        assert result.exit_code == 0
        # Check that both URLs appear in the output
        assert "guide" in result.output
        assert "tutorial" in result.output
        # Should show pageview counts
        assert "1,000" in result.output or "1000" in result.output

    def test_query_filter_by_min_pageviews(self, cli_session):
        """Test querying with minimum pageviews filter."""
        runner, session = cli_session

        domain = AnalyticsDomain(domain="docs.example.com", platform="posthog", has_data=True)
        session.add(domain)

        # High traffic page
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

        # Low traffic page
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

        session.add_all([analytics1, analytics2])
        session.commit()

        result = runner.invoke(
            main,
            [
                "integrations",
                "analytics",
                "query",
                "docs.example.com",
                "--min-pageviews",
                "500",
            ],
        )

        assert result.exit_code == 0
        assert "popular" in result.output
        assert "unpopular" not in result.output

    def test_query_filter_by_trend(self, cli_session):
        """Test querying with trend filter."""
        runner, session = cli_session

        domain = AnalyticsDomain(domain="docs.example.com", platform="posthog", has_data=True)
        session.add(domain)

        # Increasing traffic
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

        # Decreasing traffic
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

        session.add_all([analytics1, analytics2])
        session.commit()

        result = runner.invoke(
            main,
            [
                "integrations",
                "analytics",
                "query",
                "docs.example.com",
                "--trend",
                "decreasing",
            ],
        )

        assert result.exit_code == 0
        assert "declining" in result.output
        assert "growing" not in result.output

    def test_query_missing_docs_flag(self, cli_session):
        """Test querying for pages with analytics but no documents."""
        runner, session = cli_session

        domain = AnalyticsDomain(domain="docs.example.com", platform="posthog", has_data=True)
        session.add(domain)

        # Page WITH document
        doc = Document(
            id=uuid4(),
            title="Indexed Guide",
            source_type=SourceType.URL,
            source_url="https://docs.example.com/indexed",
        )
        analytics1 = PageAnalytics(
            id=uuid4(),
            url="docs.example.com/indexed",
            domain="docs.example.com",
            pageviews_30d=500,
            pageviews_60d=1000,
            pageviews_previous_30d=400,
            unique_visitors_30d=250,
            unique_visitors_60d=500,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        # Page WITHOUT document (not indexed yet)
        analytics2 = PageAnalytics(
            id=uuid4(),
            url="docs.example.com/not-indexed",
            domain="docs.example.com",
            pageviews_30d=300,
            pageviews_60d=600,
            pageviews_previous_30d=250,
            unique_visitors_30d=150,
            unique_visitors_60d=300,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        session.add_all([doc, analytics1, analytics2])
        session.commit()

        result = runner.invoke(
            main,
            ["integrations", "analytics", "query", "docs.example.com", "--missing-docs"],
        )

        assert result.exit_code == 0
        # The page WITHOUT a document should appear
        assert "not-indexed" in result.output
        # The page WITH a document (indexed) should NOT appear in the analytics results
        # Check that we only have 1 result (the not-indexed page)
        assert "1 shown" in result.output or "1 total" in result.output

    def test_query_json_output(self, cli_session):
        """Test JSON output format for analytics query."""
        runner, session = cli_session

        domain = AnalyticsDomain(domain="docs.example.com", platform="posthog", has_data=True)
        session.add(domain)

        analytics = PageAnalytics(
            id=uuid4(),
            url="docs.example.com/guide",
            domain="docs.example.com",
            pageviews_30d=1000,
            pageviews_60d=2000,
            pageviews_previous_30d=800,
            unique_visitors_30d=500,
            unique_visitors_60d=1000,
            pageviews_trend="increasing",
            trend_percentage=25.0,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )
        session.add(analytics)
        session.commit()

        result = runner.invoke(
            main,
            [
                "integrations",
                "analytics",
                "query",
                "docs.example.com",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0
        # Should be valid JSON with analytics fields
        assert '"url"' in result.output or "'url'" in result.output
        assert '"pageviews_30d"' in result.output or "'pageviews_30d'" in result.output
        assert "1000" in result.output

    def test_query_nonexistent_domain(self, cli_session):
        """Test querying a domain that doesn't exist."""
        runner, session = cli_session

        result = runner.invoke(main, ["integrations", "analytics", "query", "nonexistent.com"])

        assert result.exit_code != 0
        assert "not configured" in result.output.lower()
