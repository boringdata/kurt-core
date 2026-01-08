"""Tests for PostHog adapter - testing real implementation with mocked HTTP."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import httpx
import pytest

from kurt_new.integrations.domains_analytics.posthog.adapter import PostHogAdapter


@pytest.fixture
def adapter():
    """Create adapter with test credentials."""
    return PostHogAdapter(
        {
            "project_id": "12345",
            "api_key": "phx_test_key",
            "host": "https://app.posthog.com",
        }
    )


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx client."""
    return MagicMock(spec=httpx.Client)


class TestPostHogAdapterInit:
    """Test adapter initialization."""

    def test_init_with_required_fields(self):
        """Test initialization with required fields only."""
        adapter = PostHogAdapter(
            {
                "project_id": "12345",
                "api_key": "phx_test",
            }
        )

        assert adapter.project_id == "12345"
        assert adapter.api_key == "phx_test"
        assert adapter.base_url == "https://app.posthog.com"

    def test_init_with_custom_host(self):
        """Test initialization with custom host."""
        adapter = PostHogAdapter(
            {
                "project_id": "12345",
                "api_key": "phx_test",
                "host": "https://posthog.mycompany.com/",
            }
        )

        assert adapter.base_url == "https://posthog.mycompany.com"

    def test_init_strips_trailing_slash(self):
        """Test that trailing slashes are stripped from host."""
        adapter = PostHogAdapter(
            {
                "project_id": "12345",
                "api_key": "phx_test",
                "host": "https://app.posthog.com///",
            }
        )

        assert adapter.base_url == "https://app.posthog.com"

    def test_init_missing_project_id_raises(self):
        """Test that missing project_id raises KeyError."""
        with pytest.raises(KeyError):
            PostHogAdapter({"api_key": "phx_test"})

    def test_init_missing_api_key_raises(self):
        """Test that missing api_key raises KeyError."""
        with pytest.raises(KeyError):
            PostHogAdapter({"project_id": "12345"})


class TestTestConnection:
    """Test connection testing."""

    def test_connection_success(self, adapter):
        """Test successful connection returns True."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        adapter.client = MagicMock()
        adapter.client.get.return_value = mock_response

        result = adapter.test_connection()

        assert result is True
        adapter.client.get.assert_called_once_with("/api/projects/12345")

    def test_connection_401_raises_auth_error(self, adapter):
        """Test 401 response raises ConnectionError with auth message."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        adapter.client = MagicMock()
        adapter.client.get.return_value = mock_response

        with pytest.raises(ConnectionError, match="Authentication failed"):
            adapter.test_connection()

    def test_connection_403_raises_permission_error(self, adapter):
        """Test 403 response raises ConnectionError with permission message."""
        mock_response = MagicMock()
        mock_response.status_code = 403

        adapter.client = MagicMock()
        adapter.client.get.return_value = mock_response

        with pytest.raises(ConnectionError, match="Access denied"):
            adapter.test_connection()

    def test_connection_404_raises_project_not_found(self, adapter):
        """Test 404 response raises ConnectionError with project message."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        adapter.client = MagicMock()
        adapter.client.get.return_value = mock_response

        with pytest.raises(ConnectionError, match="Project not found"):
            adapter.test_connection()

    def test_connection_timeout_raises(self, adapter):
        """Test timeout raises ConnectionError."""
        adapter.client = MagicMock()
        adapter.client.get.side_effect = httpx.TimeoutException("Connection timed out")

        with pytest.raises(ConnectionError, match="timed out"):
            adapter.test_connection()

    def test_connection_error_raises(self, adapter):
        """Test connection error raises ConnectionError."""
        adapter.client = MagicMock()
        adapter.client.get.side_effect = httpx.ConnectError("Failed to connect")

        with pytest.raises(ConnectionError, match="Failed to connect"):
            adapter.test_connection()


class TestQueryPageviews:
    """Test pageview querying."""

    def test_query_pageviews_parses_response(self, adapter):
        """Test pageview query parses response correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                ["https://example.com/page1", 100],
                ["https://example.com/page2", 50],
                ["https://www.example.com/page1", 25],  # Should merge with page1
            ]
        }

        adapter.client = MagicMock()
        adapter.client.post.return_value = mock_response

        now = datetime.utcnow()
        result = adapter._query_pageviews(now - timedelta(days=30), now)

        # www.example.com should normalize to example.com
        assert result["example.com/page1"] == 125  # 100 + 25
        assert result["example.com/page2"] == 50

    def test_query_pageviews_handles_empty_response(self, adapter):
        """Test pageview query handles empty results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}

        adapter.client = MagicMock()
        adapter.client.post.return_value = mock_response

        now = datetime.utcnow()
        result = adapter._query_pageviews(now - timedelta(days=30), now)

        assert result == {}

    def test_query_pageviews_handles_null_urls(self, adapter):
        """Test pageview query handles null URLs in response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                [None, 100],
                ["https://example.com/page1", 50],
            ]
        }

        adapter.client = MagicMock()
        adapter.client.post.return_value = mock_response

        now = datetime.utcnow()
        result = adapter._query_pageviews(now - timedelta(days=30), now)

        # Null URL should be skipped
        assert len(result) == 1
        assert result["example.com/page1"] == 50

    def test_query_pageviews_api_error_returns_empty(self, adapter):
        """Test API error returns empty dict (graceful degradation)."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Error", request=MagicMock(), response=mock_response
        )

        adapter.client = MagicMock()
        adapter.client.post.return_value = mock_response

        now = datetime.utcnow()
        result = adapter._query_pageviews(now - timedelta(days=30), now)

        assert result == {}


class TestCalculateTrend:
    """Test trend calculation."""

    def test_increasing_trend(self, adapter):
        """Test trend is 'increasing' when current > previous by >10%."""
        trend, pct = adapter._calculate_trend(current_30d=120, previous_30d=100)

        assert trend == "increasing"
        assert pct == 20.0

    def test_decreasing_trend(self, adapter):
        """Test trend is 'decreasing' when current < previous by >10%."""
        trend, pct = adapter._calculate_trend(current_30d=80, previous_30d=100)

        assert trend == "decreasing"
        assert pct == -20.0

    def test_stable_trend(self, adapter):
        """Test trend is 'stable' when change is within ±10%."""
        trend, pct = adapter._calculate_trend(current_30d=105, previous_30d=100)

        assert trend == "stable"
        assert pct == 5.0

    def test_no_previous_data_with_current(self, adapter):
        """Test trend when no previous data but has current."""
        trend, pct = adapter._calculate_trend(current_30d=100, previous_30d=0)

        assert trend == "increasing"
        assert pct is None

    def test_no_data_at_all(self, adapter):
        """Test trend when no data at all."""
        trend, pct = adapter._calculate_trend(current_30d=0, previous_30d=0)

        assert trend == "stable"
        assert pct is None


class TestSyncMetrics:
    """Test metrics syncing."""

    def test_sync_metrics_returns_metrics_for_all_urls(self, adapter):
        """Test sync returns metrics for all requested URLs."""
        # Mock the internal query methods
        adapter._query_pageviews = MagicMock(
            side_effect=[
                {"example.com/page1": 100, "example.com/page2": 50},  # 60d
                {"example.com/page1": 60, "example.com/page2": 30},  # 30d
                {"example.com/page1": 40, "example.com/page2": 20},  # prev 30d
            ]
        )
        adapter._query_engagement = MagicMock(return_value={})

        urls = ["https://example.com/page1", "https://example.com/page2"]
        result = adapter.sync_metrics(urls, period_days=60)

        assert len(result) == 2
        assert "https://example.com/page1" in result
        assert result["https://example.com/page1"].pageviews_60d == 100
        assert result["https://example.com/page1"].pageviews_30d == 60
        assert result["https://example.com/page1"].pageviews_previous_30d == 40

    def test_sync_metrics_handles_missing_url_data(self, adapter):
        """Test sync handles URLs with no data (returns zeros)."""
        adapter._query_pageviews = MagicMock(return_value={})
        adapter._query_engagement = MagicMock(return_value={})

        urls = ["https://example.com/missing-page"]
        result = adapter.sync_metrics(urls, period_days=60)

        assert len(result) == 1
        assert result["https://example.com/missing-page"].pageviews_60d == 0
        assert result["https://example.com/missing-page"].pageviews_30d == 0


class TestGetDomainUrls:
    """Test domain URL discovery."""

    def test_get_domain_urls_filters_by_domain(self, adapter):
        """Test URL discovery filters by domain."""
        adapter._query_pageviews = MagicMock(
            return_value={
                "example.com/page1": 100,
                "example.com/page2": 50,
                "other.com/page1": 200,
            }
        )

        result = adapter.get_domain_urls("example.com", period_days=60)

        assert len(result) == 2
        assert "https://example.com/page1" in result
        assert "https://example.com/page2" in result
        assert "https://other.com/page1" not in result

    def test_get_domain_urls_handles_subdomains(self, adapter):
        """Test URL discovery handles subdomains."""
        adapter._query_pageviews = MagicMock(
            return_value={
                "docs.example.com/guide": 100,
                "blog.example.com/post": 50,
                "example.com/home": 200,
            }
        )

        result = adapter.get_domain_urls("example.com", period_days=60)

        # All should match since they contain "example.com"
        assert len(result) == 3
