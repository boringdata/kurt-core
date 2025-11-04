"""Tests for analytics configuration."""

from unittest.mock import patch

import pytest

from kurt.analytics.config import (
    add_platform_config,
    analytics_config_exists,
    get_platform_config,
    load_analytics_config,
    platform_configured,
    save_analytics_config,
)


class MockConfig:
    """Mock config object for testing."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestAnalyticsConfig:
    """Test analytics configuration functions."""

    @patch("kurt.analytics.config.get_config_or_default")
    def test_load_analytics_config_empty(self, mock_get_config):
        """Test loading analytics config when no providers configured."""
        # Mock config with no analytics fields
        mock_config = MockConfig(
            PATH_DB=".kurt/kurt.sqlite",
            TELEMETRY_ENABLED=True,
        )
        mock_get_config.return_value = mock_config

        config = load_analytics_config()
        assert config == {}

    @patch("kurt.analytics.config.get_config_or_default")
    def test_load_analytics_config_with_providers(self, mock_get_config):
        """Test loading analytics config with multiple providers."""
        # Mock config with analytics fields
        mock_config = MockConfig(
            PATH_DB=".kurt/kurt.sqlite",
            TELEMETRY_ENABLED=True,
            ANALYTICS_POSTHOG_PROJECT_ID="phc_abc123",
            ANALYTICS_POSTHOG_API_KEY="phx_xyz789",
            ANALYTICS_GA4_PROPERTY_ID="123456789",
            ANALYTICS_GA4_CREDENTIALS_FILE="path/to/credentials.json",
        )
        mock_get_config.return_value = mock_config

        config = load_analytics_config()

        # Should have two providers
        assert len(config) == 2
        assert "posthog" in config
        assert "ga4" in config

        # Check PostHog config
        assert config["posthog"]["project_id"] == "phc_abc123"
        assert config["posthog"]["api_key"] == "phx_xyz789"

        # Check GA4 config
        assert config["ga4"]["property_id"] == "123456789"
        assert config["ga4"]["credentials_file"] == "path/to/credentials.json"

    @patch("kurt.analytics.config.update_config")
    @patch("kurt.analytics.config.get_config_or_default")
    def test_save_analytics_config(self, mock_get_config, mock_update_config):
        """Test saving analytics config to kurt.config."""
        # Mock existing config
        mock_config = MockConfig(
            PATH_DB=".kurt/kurt.sqlite",
            TELEMETRY_ENABLED=True,
        )
        mock_get_config.return_value = mock_config

        # Save new analytics config
        analytics_config = {
            "posthog": {
                "project_id": "phc_abc123",
                "api_key": "phx_xyz789",
            },
            "ga4": {
                "property_id": "123456789",
            },
        }
        save_analytics_config(analytics_config)

        # Verify fields were set on config
        assert hasattr(mock_config, "ANALYTICS_POSTHOG_PROJECT_ID")
        assert mock_config.ANALYTICS_POSTHOG_PROJECT_ID == "phc_abc123"
        assert hasattr(mock_config, "ANALYTICS_POSTHOG_API_KEY")
        assert mock_config.ANALYTICS_POSTHOG_API_KEY == "phx_xyz789"
        assert hasattr(mock_config, "ANALYTICS_GA4_PROPERTY_ID")
        assert mock_config.ANALYTICS_GA4_PROPERTY_ID == "123456789"

        # Verify update_config was called
        mock_update_config.assert_called_once_with(mock_config)

    @patch("kurt.analytics.config.update_config")
    @patch("kurt.analytics.config.get_config_or_default")
    def test_save_analytics_config_removes_old_fields(self, mock_get_config, mock_update_config):
        """Test that saving analytics config removes old analytics fields."""
        # Mock config with existing analytics fields
        mock_config = MockConfig(
            PATH_DB=".kurt/kurt.sqlite",
            ANALYTICS_OLD_PROVIDER_KEY="old_value",
            ANALYTICS_POSTHOG_OLD_KEY="old_key",
        )
        mock_get_config.return_value = mock_config

        # Save new config with different provider
        analytics_config = {
            "posthog": {
                "project_id": "phc_new123",
            },
        }
        save_analytics_config(analytics_config)

        # Old fields should be removed
        assert not hasattr(mock_config, "ANALYTICS_OLD_PROVIDER_KEY")
        assert not hasattr(mock_config, "ANALYTICS_POSTHOG_OLD_KEY")

        # New field should be added
        assert hasattr(mock_config, "ANALYTICS_POSTHOG_PROJECT_ID")
        assert mock_config.ANALYTICS_POSTHOG_PROJECT_ID == "phc_new123"

    @patch("kurt.analytics.config.load_analytics_config")
    def test_get_platform_config_success(self, mock_load_config):
        """Test getting platform config successfully."""
        mock_load_config.return_value = {
            "posthog": {
                "project_id": "phc_abc123",
                "api_key": "phx_xyz789",
            }
        }

        config = get_platform_config("posthog")
        assert config["project_id"] == "phc_abc123"
        assert config["api_key"] == "phx_xyz789"

    @patch("kurt.analytics.config.load_analytics_config")
    def test_get_platform_config_not_found(self, mock_load_config):
        """Test getting platform config when platform not configured."""
        mock_load_config.return_value = {"posthog": {"project_id": "phc_abc123"}}

        with pytest.raises(ValueError) as exc_info:
            get_platform_config("ga4")

        assert "No configuration found for analytics platform 'ga4'" in str(exc_info.value)
        assert "Available platforms: posthog" in str(exc_info.value)
        assert "kurt analytics onboard --platform ga4" in str(exc_info.value)

    @patch("kurt.analytics.config.save_analytics_config")
    @patch("kurt.analytics.config.load_analytics_config")
    def test_add_platform_config_new(self, mock_load_config, mock_save_config):
        """Test adding a new platform config."""
        # Mock existing config with one provider
        mock_load_config.return_value = {"posthog": {"project_id": "phc_abc123"}}

        # Add new provider
        add_platform_config("ga4", {"property_id": "123456789"})

        # Verify save was called with updated config
        expected_config = {
            "posthog": {"project_id": "phc_abc123"},
            "ga4": {"property_id": "123456789"},
        }
        mock_save_config.assert_called_once_with(expected_config)

    @patch("kurt.analytics.config.save_analytics_config")
    @patch("kurt.analytics.config.load_analytics_config")
    def test_add_platform_config_update(self, mock_load_config, mock_save_config):
        """Test updating existing platform config."""
        # Mock existing config
        mock_load_config.return_value = {"posthog": {"project_id": "phc_old123"}}

        # Update provider
        add_platform_config("posthog", {"project_id": "phc_new123", "api_key": "phx_xyz789"})

        # Verify save was called with updated config
        expected_config = {"posthog": {"project_id": "phc_new123", "api_key": "phx_xyz789"}}
        mock_save_config.assert_called_once_with(expected_config)

    @patch("kurt.analytics.config.load_analytics_config")
    def test_analytics_config_exists_true(self, mock_load_config):
        """Test checking if analytics config exists when it does."""
        mock_load_config.return_value = {"posthog": {"project_id": "phc_abc123"}}

        assert analytics_config_exists() is True

    @patch("kurt.analytics.config.load_analytics_config")
    def test_analytics_config_exists_false(self, mock_load_config):
        """Test checking if analytics config exists when it doesn't."""
        mock_load_config.return_value = {}

        assert analytics_config_exists() is False

    @patch("kurt.analytics.config.load_analytics_config")
    def test_analytics_config_exists_error(self, mock_load_config):
        """Test analytics_config_exists handles errors gracefully."""
        mock_load_config.side_effect = Exception("Config error")

        assert analytics_config_exists() is False

    @patch("kurt.analytics.config.load_analytics_config")
    def test_platform_configured_true(self, mock_load_config):
        """Test checking if platform is configured with valid credentials."""
        mock_load_config.return_value = {
            "posthog": {
                "project_id": "phc_abc123",
                "api_key": "phx_xyz789",
            }
        }

        assert platform_configured("posthog") is True

    @patch("kurt.analytics.config.load_analytics_config")
    def test_platform_configured_not_in_config(self, mock_load_config):
        """Test checking if platform is configured when it's not."""
        mock_load_config.return_value = {"posthog": {"project_id": "phc_abc123"}}

        assert platform_configured("ga4") is False

    @patch("kurt.analytics.config.load_analytics_config")
    def test_platform_configured_placeholder_values(self, mock_load_config):
        """Test platform_configured detects placeholder values."""
        # Test with YOUR_ prefix
        mock_load_config.return_value = {"posthog": {"project_id": "YOUR_PROJECT_ID"}}
        assert platform_configured("posthog") is False

        # Test with PLACEHOLDER
        mock_load_config.return_value = {"posthog": {"project_id": "PLACEHOLDER_ID"}}
        assert platform_configured("posthog") is False

    @patch("kurt.analytics.config.load_analytics_config")
    def test_platform_configured_error(self, mock_load_config):
        """Test platform_configured handles errors gracefully."""
        mock_load_config.side_effect = Exception("Config error")

        assert platform_configured("posthog") is False
