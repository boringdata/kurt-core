"""Tests for domain_analytics configuration."""

import pytest

from kurt_new.integrations.domains_analytics.config import (
    add_platform_config,
    create_template_config,
    get_platform_config,
    platform_configured,
)
from kurt_new.workflows.domain_analytics.config import DomainAnalyticsConfig


class TestDomainAnalyticsConfig:
    """Test DomainAnalyticsConfig class."""

    def test_config_defaults(self):
        """Test default config values."""
        config = DomainAnalyticsConfig(domain="example.com")

        assert config.domain == "example.com"
        assert config.platform == "posthog"
        assert config.period_days == 60
        assert config.dry_run is False

    def test_config_custom_values(self):
        """Test custom config values."""
        config = DomainAnalyticsConfig(
            domain="test.com",
            platform="ga4",
            period_days=30,
            dry_run=True,
        )

        assert config.domain == "test.com"
        assert config.platform == "ga4"
        assert config.period_days == 30
        assert config.dry_run is True


class TestGetPlatformConfig:
    """Test get_platform_config function."""

    def test_get_existing_platform(self, tmp_project_with_analytics_config):
        """Test getting config for existing platform."""
        result = get_platform_config("posthog")

        assert result["project_id"] == "12345"
        assert result["api_key"] == "phx_test_key"
        assert result["host"] == "https://app.posthog.com"

    def test_get_missing_platform_raises(self, tmp_project):
        """Test that missing platform raises ValueError."""
        with pytest.raises(ValueError, match="No configuration found"):
            get_platform_config("posthog")

    def test_get_unknown_platform_raises(self, tmp_project_with_analytics_config):
        """Test that unknown platform raises ValueError."""
        with pytest.raises(ValueError, match="No configuration found"):
            get_platform_config("unknown_platform")


class TestAddPlatformConfig:
    """Test add_platform_config function."""

    def test_add_new_platform(self, tmp_project):
        """Test adding new platform config."""
        add_platform_config(
            "posthog",
            {"project_id": "new-123", "api_key": "phx_new_key"},
        )

        result = get_platform_config("posthog")
        assert result["project_id"] == "new-123"
        assert result["api_key"] == "phx_new_key"

    def test_update_existing_platform(self, tmp_project_with_analytics_config):
        """Test updating existing platform config."""
        add_platform_config(
            "posthog",
            {"project_id": "updated-456", "api_key": "phx_updated_key"},
        )

        result = get_platform_config("posthog")
        assert result["project_id"] == "updated-456"
        assert result["api_key"] == "phx_updated_key"


class TestPlatformConfigured:
    """Test platform_configured function."""

    def test_configured_platform(self, tmp_project_with_analytics_config):
        """Test that configured platform returns True."""
        assert platform_configured("posthog") is True

    def test_unconfigured_platform(self, tmp_project):
        """Test that unconfigured platform returns False."""
        assert platform_configured("posthog") is False

    def test_placeholder_values_not_configured(self, tmp_project_with_placeholder_config):
        """Test that placeholder values return False."""
        assert platform_configured("posthog") is False


class TestCreateTemplateConfig:
    """Test create_template_config function."""

    def test_posthog_template(self):
        """Test PostHog template config."""
        template = create_template_config("posthog")

        assert "project_id" in template
        assert "api_key" in template
        assert "host" in template
        assert template["project_id"] == "YOUR_PROJECT_ID"

    def test_ga4_template(self):
        """Test GA4 template config."""
        template = create_template_config("ga4")

        assert "property_id" in template
        assert "credentials_file" in template

    def test_plausible_template(self):
        """Test Plausible template config."""
        template = create_template_config("plausible")

        assert "site_id" in template
        assert "api_key" in template

    def test_unknown_platform_template(self):
        """Test unknown platform returns generic template."""
        template = create_template_config("unknown")

        assert "api_key" in template
