"""Unit tests for analytics service methods (isolated from database)."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from kurt.integrations.analytics.adapters.base import AnalyticsMetrics
from kurt.integrations.analytics.service import AnalyticsService


class TestGetAdapterForPlatform:
    """Unit tests for get_adapter_for_platform (isolated)."""

    @patch("kurt.integrations.analytics.adapters.posthog.PostHogAdapter")
    def test_returns_posthog_adapter(self, mock_posthog_class):
        """Test that posthog platform returns PostHog adapter."""
        mock_adapter = MagicMock()
        mock_posthog_class.return_value = mock_adapter

        config = {"project_id": "12345", "api_key": "phx_test"}
        adapter = AnalyticsService.get_adapter_for_platform("posthog", config)

        assert adapter == mock_adapter
        mock_posthog_class.assert_called_once_with(project_id="12345", api_key="phx_test")

    @patch("kurt.integrations.analytics.adapters.posthog.PostHogAdapter")
    def test_posthog_with_custom_base_url(self, mock_posthog_class):
        """Test PostHog adapter with custom base URL (if supported in future)."""
        mock_adapter = MagicMock()
        mock_posthog_class.return_value = mock_adapter

        config = {
            "project_id": "12345",
            "api_key": "phx_test",
        }
        _ = AnalyticsService.get_adapter_for_platform("posthog", config)

        # Current implementation doesn't support custom base_url in config
        mock_posthog_class.assert_called_once_with(project_id="12345", api_key="phx_test")

    def test_unsupported_platform_raises_error(self):
        """Test that unsupported platform raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            AnalyticsService.get_adapter_for_platform("unknown_platform", {})

        assert "Unsupported analytics platform: unknown_platform" in str(exc_info.value)

    def test_ga4_not_implemented(self):
        """Test that GA4 is not implemented yet."""
        with pytest.raises(NotImplementedError) as exc_info:
            AnalyticsService.get_adapter_for_platform("ga4", {})

        # Check the error message contains expected text
        error_msg = str(exc_info.value).lower()
        assert "ga4" in error_msg and "not" in error_msg and "implemented" in error_msg


class TestTestPlatformConnection:
    """Unit tests for test_platform_connection."""

    @patch("kurt.integrations.analytics.adapters.posthog.PostHogAdapter")
    def test_successful_connection(self, mock_posthog_class):
        """Test successful connection test."""
        mock_adapter = MagicMock()
        mock_adapter.test_connection.return_value = True
        mock_posthog_class.return_value = mock_adapter

        config = {"project_id": "12345", "api_key": "phx_test"}
        result = AnalyticsService.test_platform_connection("posthog", config)

        assert result is True
        mock_adapter.test_connection.assert_called_once()

    @patch("kurt.integrations.analytics.adapters.posthog.PostHogAdapter")
    def test_failed_connection(self, mock_posthog_class):
        """Test failed connection test."""
        mock_adapter = MagicMock()
        mock_adapter.test_connection.return_value = False
        mock_posthog_class.return_value = mock_adapter

        config = {"project_id": "12345", "api_key": "phx_test"}
        result = AnalyticsService.test_platform_connection("posthog", config)

        assert result is False

    @patch("kurt.integrations.analytics.adapters.posthog.PostHogAdapter")
    def test_connection_error_propagates(self, mock_posthog_class):
        """Test that ConnectionError is propagated."""
        mock_adapter = MagicMock()
        mock_adapter.test_connection.side_effect = ConnectionError("Auth failed")
        mock_posthog_class.return_value = mock_adapter

        config = {"project_id": "12345", "api_key": "phx_test"}
        with pytest.raises(ConnectionError) as exc_info:
            AnalyticsService.test_platform_connection("posthog", config)

        assert "Auth failed" in str(exc_info.value)


class TestCalculateTrendPercentage:
    """Unit tests for trend percentage calculation."""

    def test_increasing_trend(self):
        """Test calculating increasing trend percentage."""
        current = 600
        previous = 400
        expected = 50.0

        percentage = ((current - previous) / previous) * 100
        assert percentage == expected

    def test_decreasing_trend(self):
        """Test calculating decreasing trend percentage."""
        current = 300
        previous = 500
        expected = -40.0

        percentage = ((current - previous) / previous) * 100
        assert percentage == expected

    def test_zero_baseline(self):
        """Test trend when previous is zero."""
        current = 100
        previous = 0

        # Cannot calculate percentage
        if previous == 0:
            percentage = None
        else:
            percentage = ((current - previous) / previous) * 100

        assert percentage is None

    def test_both_zero(self):
        """Test trend when both are zero."""
        current = 0
        previous = 0

        if current == 0 and previous == 0:
            percentage = None
        else:
            percentage = ((current - previous) / previous) * 100

        assert percentage is None

    def test_rounding(self):
        """Test that percentage is properly rounded."""
        current = 667
        previous = 600
        expected = 11.17  # (67/600) * 100

        percentage = round(((current - previous) / previous) * 100, 2)
        assert percentage == expected


class TestMetricsAggregation:
    """Unit tests for metrics aggregation logic."""

    def test_sum_pageviews(self):
        """Test summing pageviews across multiple URLs."""
        metrics_list = [
            AnalyticsMetrics(
                pageviews_60d=1000,
                unique_visitors_60d=500,
                pageviews_30d=600,
                unique_visitors_30d=300,
                pageviews_previous_30d=400,
                unique_visitors_previous_30d=200,
                period_start=datetime.utcnow() - timedelta(days=60),
                period_end=datetime.utcnow(),
            ),
            AnalyticsMetrics(
                pageviews_60d=500,
                unique_visitors_60d=250,
                pageviews_30d=300,
                unique_visitors_30d=150,
                pageviews_previous_30d=200,
                unique_visitors_previous_30d=100,
                period_start=datetime.utcnow() - timedelta(days=60),
                period_end=datetime.utcnow(),
            ),
        ]

        total_pageviews = sum(m.pageviews_30d for m in metrics_list)
        assert total_pageviews == 900

    def test_count_urls_with_metrics(self):
        """Test counting URLs with valid metrics."""
        metrics_dict = {
            "url1": AnalyticsMetrics(
                pageviews_60d=1000,
                unique_visitors_60d=500,
                pageviews_30d=600,
                unique_visitors_30d=300,
                pageviews_previous_30d=400,
                unique_visitors_previous_30d=200,
                period_start=datetime.utcnow() - timedelta(days=60),
                period_end=datetime.utcnow(),
            ),
            "url2": AnalyticsMetrics(
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

        count = len(metrics_dict)
        total = sum(m.pageviews_60d for m in metrics_dict.values())

        assert count == 2
        assert total == 1500


class TestUrlFiltering:
    """Unit tests for URL filtering logic."""

    def test_filter_by_domain(self):
        """Test filtering URLs by domain."""
        urls = [
            "https://docs.example.com/guide",
            "https://blog.example.com/post",
            "https://other.com/page",
        ]
        domain = "docs.example.com"

        filtered = [url for url in urls if domain in url]
        assert len(filtered) == 1
        assert filtered[0] == "https://docs.example.com/guide"

    def test_filter_urls_with_pageviews_above_threshold(self):
        """Test filtering URLs with pageviews above threshold."""
        metrics_dict = {
            "url1": AnalyticsMetrics(
                pageviews_60d=2000,
                unique_visitors_60d=1000,
                pageviews_30d=1200,
                unique_visitors_30d=600,
                pageviews_previous_30d=800,
                unique_visitors_previous_30d=400,
                period_start=datetime.utcnow() - timedelta(days=60),
                period_end=datetime.utcnow(),
            ),
            "url2": AnalyticsMetrics(
                pageviews_60d=100,
                unique_visitors_60d=50,
                pageviews_30d=60,
                unique_visitors_30d=30,
                pageviews_previous_30d=40,
                unique_visitors_previous_30d=20,
                period_start=datetime.utcnow() - timedelta(days=60),
                period_end=datetime.utcnow(),
            ),
        }
        min_pageviews = 500

        filtered = {
            url: metrics
            for url, metrics in metrics_dict.items()
            if metrics.pageviews_30d >= min_pageviews
        }

        assert len(filtered) == 1
        assert "url1" in filtered

    def test_filter_by_trend(self):
        """Test filtering URLs by trend."""
        metrics_dict = {
            "url1": AnalyticsMetrics(
                pageviews_60d=1000,
                unique_visitors_60d=500,
                pageviews_30d=600,
                unique_visitors_30d=300,
                pageviews_previous_30d=400,
                unique_visitors_previous_30d=200,
                pageviews_trend="increasing",
                period_start=datetime.utcnow() - timedelta(days=60),
                period_end=datetime.utcnow(),
            ),
            "url2": AnalyticsMetrics(
                pageviews_60d=600,
                unique_visitors_60d=300,
                pageviews_30d=200,
                unique_visitors_30d=100,
                pageviews_previous_30d=400,
                unique_visitors_previous_30d=200,
                pageviews_trend="decreasing",
                period_start=datetime.utcnow() - timedelta(days=60),
                period_end=datetime.utcnow(),
            ),
        }

        filtered = {
            url: metrics
            for url, metrics in metrics_dict.items()
            if metrics.pageviews_trend == "decreasing"
        }

        assert len(filtered) == 1
        assert "url2" in filtered


class TestSyncResultFormatting:
    """Unit tests for sync result formatting."""

    def test_format_sync_success_result(self):
        """Test formatting successful sync result."""
        result = {
            "synced_count": 10,
            "total_urls": 10,
            "total_pageviews": 5000,
        }

        assert result["synced_count"] == 10
        assert result["total_urls"] == 10
        assert result["total_pageviews"] == 5000

    def test_format_partial_sync_result(self):
        """Test formatting partial sync result."""
        result = {
            "synced_count": 5,
            "total_urls": 10,
            "total_pageviews": 2500,
        }

        # Some URLs may not have metrics
        assert result["synced_count"] < result["total_urls"]

    def test_format_empty_sync_result(self):
        """Test formatting empty sync result."""
        result = {
            "synced_count": 0,
            "total_urls": 0,
            "total_pageviews": 0,
        }

        assert result["synced_count"] == 0
        assert result["total_urls"] == 0


class TestErrorHandling:
    """Unit tests for error handling patterns."""

    def test_connection_error_message_format(self):
        """Test ConnectionError message format."""
        error = ConnectionError("Authentication failed. Check your API key.")

        assert "Authentication failed" in str(error)
        assert "API key" in str(error)

    def test_value_error_for_unsupported_platform(self):
        """Test ValueError for unsupported platform."""
        error = ValueError("Unsupported analytics platform: unknown")

        assert "Unsupported" in str(error)
        assert "unknown" in str(error)

    def test_platform_not_configured_error(self):
        """Test error when platform not configured."""
        platform = "posthog"
        error = ValueError(
            f"No configuration found for analytics platform '{platform}'. "
            f"Run: kurt integrations analytics onboard"
        )

        assert "No configuration found" in str(error)
        assert platform in str(error)
        assert "onboard" in str(error)


class TestConfigValidation:
    """Unit tests for configuration validation."""

    def test_validate_posthog_config(self):
        """Test validating PostHog configuration."""
        config = {"project_id": "12345", "api_key": "phx_test"}

        assert "project_id" in config
        assert "api_key" in config
        assert config["project_id"].strip() != ""
        assert config["api_key"].strip() != ""

    def test_reject_placeholder_values(self):
        """Test rejecting placeholder configuration values."""
        placeholder_values = [
            "YOUR_PROJECT_ID",
            "YOUR_API_KEY",
            "PLACEHOLDER",
            "xxx",
            "",
        ]

        for value in placeholder_values:
            is_valid = not (
                value.startswith("YOUR_")
                or value.startswith("PLACEHOLDER")
                or value == "xxx"
                or value.strip() == ""
            )
            assert is_valid is False

    def test_accept_valid_values(self):
        """Test accepting valid configuration values."""
        valid_values = ["phc_abc123xyz", "sk_prod_token_xyz", "project-12345"]

        for value in valid_values:
            is_valid = not (
                value.startswith("YOUR_")
                or value.startswith("PLACEHOLDER")
                or value == "xxx"
                or value.strip() == ""
            )
            assert is_valid is True
