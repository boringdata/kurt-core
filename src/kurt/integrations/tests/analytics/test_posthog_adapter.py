"""Tests for PostHog analytics adapter."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from kurt.integrations.analytics.adapters.posthog import PostHogAdapter


class TestPostHogAdapterInit:
    """Test PostHog adapter initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default base URL."""
        adapter = PostHogAdapter(
            project_id="12345",
            api_key="phx_test123",
        )

        assert adapter.project_id == "12345"
        assert adapter.api_key == "phx_test123"
        assert adapter.base_url == "https://app.posthog.com"

    def test_init_with_custom_base_url(self):
        """Test initialization with custom PostHog instance URL."""
        adapter = PostHogAdapter(
            project_id="12345",
            api_key="phx_test123",
            base_url="https://eu.posthog.com",
        )

        assert adapter.base_url == "https://eu.posthog.com"

    def test_init_with_trailing_slash_base_url(self):
        """Test initialization strips trailing slash from base URL."""
        adapter = PostHogAdapter(
            project_id="12345",
            api_key="phx_test123",
            base_url="https://app.posthog.com/",
        )

        assert adapter.base_url == "https://app.posthog.com"

    def test_init_creates_http_client(self):
        """Test initialization creates HTTP client with auth headers."""
        adapter = PostHogAdapter(
            project_id="12345",
            api_key="phx_test123",
        )

        assert adapter.client is not None
        assert adapter.client.headers["Authorization"] == "Bearer phx_test123"


class TestPostHogTestConnection:
    """Test PostHog connection testing."""

    @patch("kurt.integrations.analytics.adapters.posthog.httpx.Client")
    def test_connection_success(self, mock_client_class):
        """Test successful connection."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200

        # Mock client
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        adapter = PostHogAdapter(project_id="12345", api_key="phx_test123")
        result = adapter.test_connection()

        assert result is True
        mock_client.get.assert_called_once_with("/api/projects/12345")

    @patch("kurt.integrations.analytics.adapters.posthog.httpx.Client")
    def test_connection_auth_error(self, mock_client_class):
        """Test connection with authentication error."""
        mock_response = Mock()
        mock_response.status_code = 401

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        adapter = PostHogAdapter(project_id="12345", api_key="phx_test123")

        with pytest.raises(ConnectionError) as exc_info:
            adapter.test_connection()

        assert "Authentication failed" in str(exc_info.value)
        assert "API key" in str(exc_info.value)

    @patch("kurt.integrations.analytics.adapters.posthog.httpx.Client")
    def test_connection_permission_denied(self, mock_client_class):
        """Test connection with permission denied."""
        mock_response = Mock()
        mock_response.status_code = 403

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        adapter = PostHogAdapter(project_id="12345", api_key="phx_test123")

        with pytest.raises(ConnectionError) as exc_info:
            adapter.test_connection()

        assert "Access denied" in str(exc_info.value)
        assert "project:read" in str(exc_info.value)

    @patch("kurt.integrations.analytics.adapters.posthog.httpx.Client")
    def test_connection_project_not_found(self, mock_client_class):
        """Test connection with project not found."""
        mock_response = Mock()
        mock_response.status_code = 404

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        adapter = PostHogAdapter(project_id="12345", api_key="phx_test123")

        with pytest.raises(ConnectionError) as exc_info:
            adapter.test_connection()

        assert "Project not found" in str(exc_info.value)
        assert "12345" in str(exc_info.value)

    @patch("kurt.integrations.analytics.adapters.posthog.httpx.Client")
    def test_connection_http_error(self, mock_client_class):
        """Test connection with generic HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        adapter = PostHogAdapter(project_id="12345", api_key="phx_test123")

        with pytest.raises(ConnectionError) as exc_info:
            adapter.test_connection()

        assert "status 500" in str(exc_info.value)

    @patch("kurt.integrations.analytics.adapters.posthog.httpx.Client")
    def test_connection_network_error(self, mock_client_class):
        """Test connection with network error."""
        import httpx

        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.ConnectError("Failed to connect")
        mock_client_class.return_value = mock_client

        adapter = PostHogAdapter(project_id="12345", api_key="phx_test123")

        with pytest.raises(ConnectionError) as exc_info:
            adapter.test_connection()

        assert "Failed to connect" in str(exc_info.value)

    @patch("kurt.integrations.analytics.adapters.posthog.httpx.Client")
    def test_connection_timeout(self, mock_client_class):
        """Test connection with timeout."""
        import httpx

        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.TimeoutException("Timeout")
        mock_client_class.return_value = mock_client

        adapter = PostHogAdapter(project_id="12345", api_key="phx_test123")

        with pytest.raises(ConnectionError) as exc_info:
            adapter.test_connection()

        assert "timed out" in str(exc_info.value)


class TestPostHogGetDomainUrls:
    """Test retrieving domain URLs from PostHog."""

    @patch("kurt.integrations.analytics.adapters.posthog.httpx.Client")
    def test_get_domain_urls_success(self, mock_client_class):
        """Test successfully retrieving URLs for a domain."""
        # Mock PostHog API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                ["https://docs.example.com/guide", 100],
                ["https://docs.example.com/tutorial", 50],
                ["https://docs.example.com/reference", 75],
            ]
        }

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        adapter = PostHogAdapter(project_id="12345", api_key="phx_test123")
        urls = adapter.get_domain_urls("docs.example.com", period_days=60)

        assert len(urls) == 3
        assert "https://docs.example.com/guide" in urls
        assert "https://docs.example.com/tutorial" in urls
        assert "https://docs.example.com/reference" in urls

    @patch("kurt.integrations.analytics.adapters.posthog.httpx.Client")
    def test_get_domain_urls_filters_by_domain(self, mock_client_class):
        """Test that only URLs from the specified domain are returned."""
        # Mock response with mixed domains
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                ["https://docs.example.com/guide", 100],
                ["https://other.com/page", 50],  # Different domain
                ["https://docs.example.com/tutorial", 75],
            ]
        }

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        adapter = PostHogAdapter(project_id="12345", api_key="phx_test123")
        urls = adapter.get_domain_urls("docs.example.com", period_days=60)

        assert len(urls) == 2
        assert "https://docs.example.com/guide" in urls
        assert "https://docs.example.com/tutorial" in urls
        assert "https://other.com/page" not in urls

    @patch("kurt.integrations.analytics.adapters.posthog.httpx.Client")
    def test_get_domain_urls_empty_results(self, mock_client_class):
        """Test retrieving URLs when no data exists."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        adapter = PostHogAdapter(project_id="12345", api_key="phx_test123")
        urls = adapter.get_domain_urls("docs.example.com", period_days=60)

        assert urls == []


class TestPostHogSyncMetrics:
    """Test syncing analytics metrics from PostHog."""

    @patch("kurt.integrations.analytics.adapters.posthog.httpx.Client")
    def test_sync_metrics_success(self, mock_client_class):
        """Test successfully syncing metrics for URLs."""
        # Track which query is being called
        call_count = [0]

        # Mock PostHog responses for different time periods
        def mock_post_response(url, json=None):
            response = Mock()
            response.status_code = 200
            response.raise_for_status = Mock()

            # Return different results for each call (60d, 30d, previous 30d)
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: 60-day period
                response.json.return_value = {
                    "results": [
                        ["https://docs.example.com/guide", 1000],
                    ]
                }
            elif call_count[0] == 2:
                # Second call: Last 30 days
                response.json.return_value = {
                    "results": [
                        ["https://docs.example.com/guide", 600],
                    ]
                }
            else:
                # Third call: Previous 30 days
                response.json.return_value = {
                    "results": [
                        ["https://docs.example.com/guide", 400],
                    ]
                }

            return response

        mock_client = MagicMock()
        mock_client.post.side_effect = mock_post_response
        mock_client_class.return_value = mock_client

        adapter = PostHogAdapter(project_id="12345", api_key="phx_test123")
        results = adapter.sync_metrics(["https://docs.example.com/guide"], period_days=60)

        assert len(results) == 1
        assert "https://docs.example.com/guide" in results

        metrics = results["https://docs.example.com/guide"]
        assert metrics.pageviews_60d == 1000
        assert metrics.pageviews_30d == 600
        assert metrics.pageviews_previous_30d == 400

    @patch("kurt.integrations.analytics.adapters.posthog.httpx.Client")
    def test_sync_metrics_calculates_trend(self, mock_client_class):
        """Test that trend is calculated correctly from pageview data."""
        call_count = [0]

        # Mock increasing traffic
        def mock_post_increasing(url, json=None):
            response = Mock()
            response.status_code = 200
            response.raise_for_status = Mock()

            # Return results for 60d, 30d, previous 30d in order
            call_count[0] += 1
            if call_count[0] == 1:
                # 60d period: 1000 total
                response.json.return_value = {"results": [["https://example.com", 1000]]}
            elif call_count[0] == 2:
                # Last 30d: 600 views
                response.json.return_value = {"results": [["https://example.com", 600]]}
            else:
                # Previous 30d: 400 views (+50% trend)
                response.json.return_value = {"results": [["https://example.com", 400]]}

            return response

        mock_client = MagicMock()
        mock_client.post.side_effect = mock_post_increasing
        mock_client_class.return_value = mock_client

        adapter = PostHogAdapter(project_id="12345", api_key="phx_test123")
        results = adapter.sync_metrics(["https://example.com"], period_days=60)

        metrics = results["https://example.com"]
        assert metrics.pageviews_trend == "increasing"
        assert metrics.trend_percentage == 50.0


class TestPostHogCalculateTrend:
    """Test trend calculation logic."""

    def test_trend_increasing(self):
        """Test trend detection for increasing traffic."""
        adapter = PostHogAdapter(project_id="12345", api_key="phx_test123")

        # 50% increase
        trend, pct = adapter._calculate_trend(600, 400)
        assert trend == "increasing"
        assert pct == 50.0

    def test_trend_decreasing(self):
        """Test trend detection for decreasing traffic."""
        adapter = PostHogAdapter(project_id="12345", api_key="phx_test123")

        # 50% decrease
        trend, pct = adapter._calculate_trend(200, 400)
        assert trend == "decreasing"
        assert pct == -50.0

    def test_trend_stable(self):
        """Test trend detection for stable traffic."""
        adapter = PostHogAdapter(project_id="12345", api_key="phx_test123")

        # 5% increase (within stable threshold)
        trend, pct = adapter._calculate_trend(420, 400)
        assert trend == "stable"
        assert pct == 5.0

    def test_trend_zero_baseline(self):
        """Test trend calculation when previous period has zero views."""
        adapter = PostHogAdapter(project_id="12345", api_key="phx_test123")

        # New content with views
        trend, pct = adapter._calculate_trend(100, 0)
        assert trend == "increasing"
        assert pct is None  # No baseline for percentage

    def test_trend_both_zero(self):
        """Test trend calculation when both periods have zero views."""
        adapter = PostHogAdapter(project_id="12345", api_key="phx_test123")

        trend, pct = adapter._calculate_trend(0, 0)
        assert trend == "stable"
        assert pct is None
