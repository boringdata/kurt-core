"""Tests for domains_analytics fetch module."""

from unittest.mock import MagicMock, patch

import pytest


class TestSyncDomainMetrics:
    """Test sync_domain_metrics function."""

    def test_sync_returns_metrics(self, tmp_project_with_analytics_config, mock_posthog_adapter):
        """Test successful sync returns metrics map."""
        from kurt_new.integrations.domains_analytics.fetch import sync_domain_metrics

        with patch(
            "kurt_new.integrations.domains_analytics.fetch._get_adapter",
            return_value=mock_posthog_adapter,
        ):
            result = sync_domain_metrics("posthog", "example.com", period_days=60)

            assert "https://example.com/page1" in result
            assert result["https://example.com/page1"].pageviews_60d == 1000

    def test_sync_empty_domain_returns_empty(self, tmp_project_with_analytics_config):
        """Test sync with no URLs returns empty dict."""
        from kurt_new.integrations.domains_analytics.fetch import sync_domain_metrics

        mock_adapter = MagicMock()
        mock_adapter.get_domain_urls.return_value = []

        with patch(
            "kurt_new.integrations.domains_analytics.fetch._get_adapter",
            return_value=mock_adapter,
        ):
            result = sync_domain_metrics("posthog", "empty-domain.com")

            assert result == {}

    def test_sync_raises_on_unconfigured_platform(self, tmp_project):
        """Test sync raises ValueError for unconfigured platform."""
        from kurt_new.integrations.domains_analytics.fetch import sync_domain_metrics

        with pytest.raises(ValueError, match="No configuration found"):
            sync_domain_metrics("posthog", "example.com")


class TestGetDomainUrls:
    """Test get_domain_urls function."""

    def test_get_urls_returns_list(self, tmp_project_with_analytics_config, mock_posthog_adapter):
        """Test getting URLs returns list."""
        from kurt_new.integrations.domains_analytics.fetch import get_domain_urls

        with patch(
            "kurt_new.integrations.domains_analytics.fetch._get_adapter",
            return_value=mock_posthog_adapter,
        ):
            result = get_domain_urls("posthog", "example.com")

            assert len(result) == 3
            assert "https://example.com/page1" in result


class TestTestPlatformConnection:
    """Test test_platform_connection function."""

    def test_connection_success(self, tmp_project_with_analytics_config, mock_posthog_adapter):
        """Test successful connection returns True."""
        from kurt_new.integrations.domains_analytics.fetch import test_platform_connection

        with patch(
            "kurt_new.integrations.domains_analytics.fetch._get_adapter",
            return_value=mock_posthog_adapter,
        ):
            result = test_platform_connection("posthog")

            assert result is True

    def test_connection_raises_on_unconfigured(self, tmp_project):
        """Test connection raises ValueError for unconfigured platform."""
        from kurt_new.integrations.domains_analytics.fetch import test_platform_connection

        with pytest.raises(ValueError, match="No configuration found"):
            test_platform_connection("posthog")
