"""Tests for analytics configuration using real config files."""

import pytest

from kurt.config.base import get_config_file_path, load_config
from kurt.integrations.analytics.config import (
    add_platform_config,
    analytics_config_exists,
    get_platform_config,
    load_analytics_config,
    platform_configured,
    save_analytics_config,
)


class TestAnalyticsConfig:
    """Test analytics configuration functions with real config files."""

    def test_load_analytics_config_empty(self, tmp_project):
        """Test loading analytics config when no providers configured."""
        config = load_analytics_config()
        assert config == {}

    def test_save_and_load_analytics_config(self, tmp_project):
        """Test saving and loading analytics config."""
        # Save analytics config
        analytics_config = {
            "posthog": {
                "project_id": "phc_abc123",
                "api_key": "phx_xyz789",
            },
            "ga4": {
                "property_id": "123456789",
                "credentials_file": "path/to/credentials.json",
            },
        }
        save_analytics_config(analytics_config)

        # Load it back
        loaded = load_analytics_config()

        # Should have two providers
        assert len(loaded) == 2
        assert "posthog" in loaded
        assert "ga4" in loaded

        # Check PostHog config
        assert loaded["posthog"]["project_id"] == "phc_abc123"
        assert loaded["posthog"]["api_key"] == "phx_xyz789"

        # Check GA4 config
        assert loaded["ga4"]["property_id"] == "123456789"
        assert loaded["ga4"]["credentials_file"] == "path/to/credentials.json"

    def test_save_analytics_config_removes_old_fields(self, tmp_project):
        """Test that saving analytics config removes old analytics fields."""
        # Save initial config
        save_analytics_config(
            {
                "old": {
                    "provider_key": "old_value",
                },
                "posthog": {
                    "old_key": "old_value",
                },
            }
        )

        # Verify it was saved
        loaded = load_analytics_config()
        assert "old" in loaded
        assert "posthog" in loaded

        # Save new config with different provider
        save_analytics_config(
            {
                "posthog": {
                    "project_id": "phc_new123",
                },
            }
        )

        # Old provider should be removed
        loaded = load_analytics_config()
        assert "old" not in loaded
        assert "posthog" in loaded
        assert loaded["posthog"]["project_id"] == "phc_new123"
        # Old key should be removed
        assert "old_key" not in loaded["posthog"]

    def test_save_analytics_config_preserves_cms_fields(self, tmp_project):
        """
        CRITICAL TEST: Verify that saving analytics config does NOT overwrite CMS fields.
        """
        # Manually add CMS fields to config file
        config_file = get_config_file_path()
        with open(config_file, "a") as f:
            f.write("\n# CMS Configuration\n")
            f.write('CMS_SANITY_PROD_PROJECT_ID="sanity_existing"\n')
            f.write('CMS_SANITY_PROD_TOKEN="sk_existing"\n')

        # Verify CMS fields exist
        config = load_config()
        assert "CMS_SANITY_PROD_PROJECT_ID" in config.__pydantic_extra__

        # Save analytics config
        save_analytics_config(
            {
                "posthog": {
                    "project_id": "phc_abc123",
                    "api_key": "phx_xyz789",
                },
            }
        )

        # Verify CMS fields are preserved
        config = load_config()
        assert "CMS_SANITY_PROD_PROJECT_ID" in config.__pydantic_extra__
        assert config.__pydantic_extra__["CMS_SANITY_PROD_PROJECT_ID"] == "sanity_existing"
        assert "CMS_SANITY_PROD_TOKEN" in config.__pydantic_extra__

        # Verify analytics fields are added
        assert "ANALYTICS_POSTHOG_PROJECT_ID" in config.__pydantic_extra__
        assert "ANALYTICS_POSTHOG_API_KEY" in config.__pydantic_extra__

    def test_get_platform_config_success(self, tmp_project):
        """Test getting platform config successfully."""
        save_analytics_config(
            {
                "posthog": {
                    "project_id": "phc_abc123",
                    "api_key": "phx_xyz789",
                }
            }
        )

        config = get_platform_config("posthog")
        assert config["project_id"] == "phc_abc123"
        assert config["api_key"] == "phx_xyz789"

    def test_get_platform_config_not_found(self, tmp_project):
        """Test getting platform config when platform not configured."""
        save_analytics_config({"posthog": {"project_id": "phc_abc123"}})

        with pytest.raises(ValueError) as exc_info:
            get_platform_config("ga4")

        assert "No configuration found for analytics platform 'ga4'" in str(exc_info.value)
        assert "Available platforms: posthog" in str(exc_info.value)
        assert "kurt integrations analytics onboard --platform ga4" in str(exc_info.value)

    def test_add_platform_config_new(self, tmp_project):
        """Test adding a new platform config."""
        # Add first platform
        save_analytics_config({"posthog": {"project_id": "phc_abc123"}})

        # Add new provider
        add_platform_config("ga4", {"property_id": "123456789"})

        # Verify both exist
        config = load_analytics_config()
        assert "posthog" in config
        assert config["posthog"]["project_id"] == "phc_abc123"
        assert "ga4" in config
        assert config["ga4"]["property_id"] == "123456789"

    def test_add_platform_config_update(self, tmp_project):
        """Test updating existing platform config."""
        # Add initial config
        save_analytics_config({"posthog": {"project_id": "phc_old123"}})

        # Update provider
        add_platform_config("posthog", {"project_id": "phc_new123", "api_key": "phx_xyz789"})

        # Verify update
        config = load_analytics_config()
        assert config["posthog"]["project_id"] == "phc_new123"
        assert config["posthog"]["api_key"] == "phx_xyz789"

    def test_analytics_config_exists_true(self, tmp_project):
        """Test checking if analytics config exists when it does."""
        save_analytics_config({"posthog": {"project_id": "phc_abc123"}})

        assert analytics_config_exists() is True

    def test_analytics_config_exists_false(self, tmp_project):
        """Test checking if analytics config exists when it doesn't."""
        assert analytics_config_exists() is False

    def test_platform_configured_true(self, tmp_project):
        """Test checking if platform is configured with valid credentials."""
        save_analytics_config(
            {
                "posthog": {
                    "project_id": "phc_abc123",
                    "api_key": "phx_xyz789",
                }
            }
        )

        assert platform_configured("posthog") is True

    def test_platform_configured_not_in_config(self, tmp_project):
        """Test checking if platform is configured when it's not."""
        save_analytics_config({"posthog": {"project_id": "phc_abc123"}})

        assert platform_configured("ga4") is False

    def test_platform_configured_placeholder_values(self, tmp_project):
        """Test platform_configured detects placeholder values."""
        # Test with YOUR_ prefix
        save_analytics_config({"posthog": {"project_id": "YOUR_PROJECT_ID"}})
        assert platform_configured("posthog") is False

        # Test with PLACEHOLDER
        save_analytics_config({"posthog": {"project_id": "PLACEHOLDER_ID"}})
        assert platform_configured("posthog") is False
