"""Tests for domains_analytics configuration module."""

import pytest

from kurt_new.integrations.domains_analytics.config import (
    add_platform_config,
    analytics_config_exists,
    create_template_config,
    get_platform_config,
    list_platforms,
    load_analytics_config,
    platform_configured,
    save_analytics_config,
)


class TestLoadAnalyticsConfig:
    """Test load_analytics_config function."""

    def test_load_empty_config(self, tmp_project):
        """Test loading when no analytics config exists."""
        result = load_analytics_config()
        assert result == {}

    def test_load_with_analytics_config(self, tmp_project_with_analytics_config):
        """Test loading existing analytics config."""
        result = load_analytics_config()

        assert "posthog" in result
        assert result["posthog"]["project_id"] == "12345"
        assert result["posthog"]["api_key"] == "phx_test_key"
        assert result["posthog"]["host"] == "https://app.posthog.com"

    def test_load_multiple_platforms(self, tmp_project_with_analytics_config):
        """Test loading config with multiple platforms."""
        result = load_analytics_config()

        assert "posthog" in result
        assert "ga4" in result
        assert result["ga4"]["property_id"] == "UA-12345"


class TestSaveAnalyticsConfig:
    """Test save_analytics_config function."""

    def test_save_new_config(self, tmp_project):
        """Test saving new analytics config."""
        config = {"posthog": {"project_id": "new-project", "api_key": "phx_new"}}

        save_analytics_config(config)
        result = load_analytics_config()

        assert result["posthog"]["project_id"] == "new-project"

    def test_save_overwrites_existing(self, tmp_project_with_analytics_config):
        """Test that save overwrites existing config."""
        config = {"posthog": {"project_id": "updated-project"}}

        save_analytics_config(config)
        result = load_analytics_config()

        assert result["posthog"]["project_id"] == "updated-project"
        # Old api_key should be gone since we replaced the whole config
        assert "api_key" not in result["posthog"]


class TestGetPlatformConfig:
    """Test get_platform_config function."""

    def test_get_existing_platform(self, tmp_project_with_analytics_config):
        """Test getting config for existing platform."""
        result = get_platform_config("posthog")

        assert result["project_id"] == "12345"
        assert result["api_key"] == "phx_test_key"

    def test_get_nonexistent_platform_raises(self, tmp_project):
        """Test that nonexistent platform raises ValueError."""
        with pytest.raises(ValueError, match="No configuration found"):
            get_platform_config("posthog")

    def test_error_message_shows_available_platforms(self, tmp_project_with_analytics_config):
        """Test error message lists available platforms."""
        with pytest.raises(ValueError) as exc_info:
            get_platform_config("plausible")

        assert "posthog" in str(exc_info.value)


class TestAddPlatformConfig:
    """Test add_platform_config function."""

    def test_add_new_platform(self, tmp_project):
        """Test adding a new platform."""
        add_platform_config("posthog", {"project_id": "new-project", "api_key": "phx_new"})

        result = load_analytics_config()
        assert result["posthog"]["project_id"] == "new-project"

    def test_update_existing_platform(self, tmp_project_with_analytics_config):
        """Test updating an existing platform."""
        add_platform_config("posthog", {"project_id": "updated-project", "new_field": "value"})

        result = load_analytics_config()
        assert result["posthog"]["project_id"] == "updated-project"
        assert result["posthog"]["new_field"] == "value"

    def test_add_preserves_other_platforms(self, tmp_project_with_analytics_config):
        """Test adding a platform preserves other platforms."""
        add_platform_config("plausible", {"site_id": "example.com", "api_key": "plausible_key"})

        result = load_analytics_config()
        assert "posthog" in result
        assert "ga4" in result
        assert "plausible" in result


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
        assert template["property_id"] == "YOUR_PROPERTY_ID"

    def test_plausible_template(self):
        """Test Plausible template config."""
        template = create_template_config("plausible")

        assert "site_id" in template
        assert "api_key" in template

    def test_unknown_platform_returns_generic(self):
        """Test unknown platform returns generic template."""
        template = create_template_config("unknown_platform")

        assert "api_key" in template


class TestAnalyticsConfigExists:
    """Test analytics_config_exists function."""

    def test_returns_false_when_no_config(self, tmp_project):
        """Test returns False when no analytics config exists."""
        assert analytics_config_exists() is False

    def test_returns_true_when_config_exists(self, tmp_project_with_analytics_config):
        """Test returns True when analytics config exists."""
        assert analytics_config_exists() is True


class TestPlatformConfigured:
    """Test platform_configured function."""

    def test_returns_true_for_configured_platform(self, tmp_project_with_analytics_config):
        """Test returns True for fully configured platform."""
        assert platform_configured("posthog") is True

    def test_returns_false_for_unconfigured_platform(self, tmp_project):
        """Test returns False for unconfigured platform."""
        assert platform_configured("posthog") is False

    def test_returns_false_for_unknown_platform(self, tmp_project_with_analytics_config):
        """Test returns False for unknown platform."""
        assert platform_configured("unknown") is False

    def test_returns_false_for_placeholder_values(self, tmp_project_with_placeholder_config):
        """Test returns False when config has placeholder values."""
        assert platform_configured("posthog") is False


class TestListPlatforms:
    """Test list_platforms function."""

    def test_list_platforms(self, tmp_project_with_analytics_config):
        """Test listing platforms."""
        platforms = list_platforms()

        assert "posthog" in platforms
        assert "ga4" in platforms

    def test_list_empty_when_no_config(self, tmp_project):
        """Test returns empty list when no config."""
        platforms = list_platforms()
        assert platforms == []
