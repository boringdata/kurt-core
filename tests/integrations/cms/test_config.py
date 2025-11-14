"""Tests for CMS configuration using real config files."""

import pytest

from kurt.config.base import get_config_file_path, load_config
from kurt.integrations.cms.config import (
    add_platform_instance,
    cms_config_exists,
    get_platform_config,
    list_platform_instances,
    load_cms_config,
    platform_configured,
    save_cms_config,
)


class TestCMSConfig:
    """Test CMS configuration functions with real config files."""

    def test_load_cms_config_empty(self, tmp_project):
        """Test loading CMS config when no platforms configured."""
        config = load_cms_config()
        assert config == {}

    def test_save_and_load_cms_config(self, tmp_project):
        """Test saving and loading CMS config."""
        # Save CMS config
        cms_config = {
            "sanity": {
                "prod": {
                    "project_id": "abc123",
                    "dataset": "production",
                    "token": "sk_prod_token",
                },
                "staging": {
                    "project_id": "xyz789",
                    "dataset": "staging",
                },
            },
            "contentful": {
                "default": {
                    "space_id": "space123",
                }
            },
        }
        save_cms_config(cms_config)

        # Load it back
        loaded_config = load_cms_config()

        # Verify all platforms
        assert len(loaded_config) == 2
        assert "sanity" in loaded_config
        assert "contentful" in loaded_config

        # Check Sanity prod config
        assert "prod" in loaded_config["sanity"]
        assert loaded_config["sanity"]["prod"]["project_id"] == "abc123"
        assert loaded_config["sanity"]["prod"]["dataset"] == "production"
        assert loaded_config["sanity"]["prod"]["token"] == "sk_prod_token"

        # Check Sanity staging config
        assert "staging" in loaded_config["sanity"]
        assert loaded_config["sanity"]["staging"]["project_id"] == "xyz789"
        assert loaded_config["sanity"]["staging"]["dataset"] == "staging"

        # Check Contentful config
        assert "default" in loaded_config["contentful"]
        assert loaded_config["contentful"]["default"]["space_id"] == "space123"

    def test_save_cms_config_with_json_fields(self, tmp_project):
        """Test saving CMS config with JSON-encoded nested structures."""
        content_type_mappings = {
            "article": {
                "enabled": True,
                "content_field": "body",
                "title_field": "title",
            }
        }

        cms_config = {
            "sanity": {
                "prod": {
                    "project_id": "abc123",
                    "content_type_mappings": content_type_mappings,
                }
            }
        }
        save_cms_config(cms_config)

        # Load it back
        loaded_config = load_cms_config()

        # JSON should be parsed back to dict
        assert isinstance(loaded_config["sanity"]["prod"]["content_type_mappings"], dict)
        assert (
            loaded_config["sanity"]["prod"]["content_type_mappings"]["article"]["enabled"] is True
        )

    def test_save_cms_config_removes_old_fields(self, tmp_project):
        """Test that saving CMS config removes old CMS fields."""
        # Save initial config
        cms_config_1 = {
            "sanity": {
                "staging": {
                    "old_key": "old_value",
                }
            }
        }
        save_cms_config(cms_config_1)

        # Verify it was saved
        loaded = load_cms_config()
        assert "staging" in loaded["sanity"]

        # Save new config (should remove old instance)
        cms_config_2 = {
            "sanity": {
                "prod": {
                    "project_id": "new123",
                }
            }
        }
        save_cms_config(cms_config_2)

        # Load and verify old fields removed
        loaded = load_cms_config()
        assert "staging" not in loaded["sanity"]
        assert "prod" in loaded["sanity"]
        assert loaded["sanity"]["prod"]["project_id"] == "new123"

    def test_save_cms_config_preserves_analytics_fields(self, tmp_project):
        """
        CRITICAL TEST: Verify that saving CMS config does NOT overwrite analytics fields.
        """
        # Manually add analytics fields to config file
        config_file = get_config_file_path()
        with open(config_file, "a") as f:
            f.write("\n# Analytics Configuration\n")
            f.write('ANALYTICS_POSTHOG_PROJECT_ID="phc_existing"\n')
            f.write('ANALYTICS_POSTHOG_API_KEY="phx_existing"\n')

        # Verify analytics fields exist
        config = load_config()
        assert "ANALYTICS_POSTHOG_PROJECT_ID" in config.__pydantic_extra__
        assert config.__pydantic_extra__["ANALYTICS_POSTHOG_PROJECT_ID"] == "phc_existing"

        # Save CMS config
        cms_config = {
            "sanity": {
                "prod": {
                    "project_id": "sanity123",
                    "token": "sk_token",
                }
            }
        }
        save_cms_config(cms_config)

        # Verify analytics fields are preserved
        config = load_config()
        assert "ANALYTICS_POSTHOG_PROJECT_ID" in config.__pydantic_extra__
        assert config.__pydantic_extra__["ANALYTICS_POSTHOG_PROJECT_ID"] == "phc_existing"
        assert "ANALYTICS_POSTHOG_API_KEY" in config.__pydantic_extra__
        assert config.__pydantic_extra__["ANALYTICS_POSTHOG_API_KEY"] == "phx_existing"

        # Verify CMS fields are added
        assert "CMS_SANITY_PROD_PROJECT_ID" in config.__pydantic_extra__
        assert "CMS_SANITY_PROD_TOKEN" in config.__pydantic_extra__

    def test_get_platform_config_success(self, tmp_project):
        """Test getting platform config successfully."""
        # Save config
        save_cms_config(
            {
                "sanity": {
                    "prod": {
                        "project_id": "abc123",
                        "token": "sk_token",
                    }
                }
            }
        )

        # Get platform config
        config = get_platform_config("sanity", "prod")
        assert config["project_id"] == "abc123"
        assert config["token"] == "sk_token"

    def test_get_platform_config_default_instance(self, tmp_project):
        """Test getting platform config with default instance."""
        save_cms_config(
            {
                "sanity": {
                    "default": {
                        "project_id": "abc123",
                    }
                }
            }
        )

        # Without instance, should use "default"
        config = get_platform_config("sanity")
        assert config["project_id"] == "abc123"

    def test_get_platform_config_first_instance_fallback(self, tmp_project):
        """Test getting platform config falls back to first instance."""
        save_cms_config(
            {
                "sanity": {
                    "prod": {
                        "project_id": "abc123",
                    },
                    "staging": {
                        "project_id": "xyz789",
                    },
                }
            }
        )

        # Without instance and no "default", should use first instance
        config = get_platform_config("sanity")
        assert config["project_id"] in ["abc123", "xyz789"]  # Either is valid

    def test_get_platform_config_platform_not_found(self, tmp_project):
        """Test getting platform config when platform not configured."""
        save_cms_config({"sanity": {"prod": {"project_id": "abc123"}}})

        with pytest.raises(ValueError) as exc_info:
            get_platform_config("contentful")

        assert "No configuration found for CMS platform 'contentful'" in str(exc_info.value)
        assert "Available platforms: sanity" in str(exc_info.value)

    def test_get_platform_config_instance_not_found(self, tmp_project):
        """Test getting platform config when instance not found."""
        save_cms_config({"sanity": {"prod": {"project_id": "abc123"}}})

        with pytest.raises(ValueError) as exc_info:
            get_platform_config("sanity", "staging")

        assert "Instance 'staging' not found" in str(exc_info.value)
        assert "Available instances: prod" in str(exc_info.value)

    def test_add_platform_instance_new(self, tmp_project):
        """Test adding a new platform instance."""
        # Add first instance
        add_platform_instance("sanity", "prod", {"project_id": "abc123"})

        # Verify it was added
        config = load_cms_config()
        assert "sanity" in config
        assert "prod" in config["sanity"]
        assert config["sanity"]["prod"]["project_id"] == "abc123"

    def test_add_platform_instance_update_existing(self, tmp_project):
        """Test updating existing platform instance."""
        # Add initial config
        save_cms_config(
            {
                "sanity": {
                    "prod": {
                        "project_id": "old123",
                    }
                }
            }
        )

        # Update it
        add_platform_instance("sanity", "prod", {"project_id": "new123", "token": "sk_token"})

        # Verify update
        config = load_cms_config()
        assert config["sanity"]["prod"]["project_id"] == "new123"
        assert config["sanity"]["prod"]["token"] == "sk_token"

    def test_add_platform_instance_preserves_other_platforms(self, tmp_project):
        """Test adding platform instance preserves other platforms."""
        # Add Sanity
        save_cms_config(
            {
                "sanity": {
                    "prod": {
                        "project_id": "sanity123",
                    }
                }
            }
        )

        # Add Contentful (should preserve Sanity)
        add_platform_instance("contentful", "default", {"space_id": "contentful456"})

        # Verify both exist
        config = load_cms_config()
        assert "sanity" in config
        assert config["sanity"]["prod"]["project_id"] == "sanity123"
        assert "contentful" in config
        assert config["contentful"]["default"]["space_id"] == "contentful456"

    def test_cms_config_exists_true(self, tmp_project):
        """Test checking if CMS config exists when it does."""
        save_cms_config({"sanity": {"prod": {"project_id": "abc123"}}})

        assert cms_config_exists() is True

    def test_cms_config_exists_false(self, tmp_project):
        """Test checking if CMS config exists when it doesn't."""
        assert cms_config_exists() is False

    def test_platform_configured_true(self, tmp_project):
        """Test checking if platform is configured with valid credentials."""
        save_cms_config(
            {
                "sanity": {
                    "prod": {
                        "project_id": "abc123",
                        "token": "sk_token",
                    }
                }
            }
        )

        assert platform_configured("sanity", "prod") is True

    def test_platform_configured_any_instance(self, tmp_project):
        """Test checking if platform is configured (any instance)."""
        save_cms_config(
            {
                "sanity": {
                    "prod": {"project_id": "abc123"},
                    "staging": {"project_id": "xyz789"},
                }
            }
        )

        # Without specifying instance, should check if ANY instance is configured
        assert platform_configured("sanity") is True

    def test_platform_configured_not_in_config(self, tmp_project):
        """Test checking if platform is configured when it's not."""
        save_cms_config({"sanity": {"prod": {"project_id": "abc123"}}})

        assert platform_configured("contentful") is False

    def test_platform_configured_instance_not_found(self, tmp_project):
        """Test checking if specific instance is configured when it's not."""
        save_cms_config({"sanity": {"prod": {"project_id": "abc123"}}})

        assert platform_configured("sanity", "staging") is False

    def test_platform_configured_placeholder_values(self, tmp_project):
        """Test platform_configured detects placeholder values."""
        # Test with YOUR_ prefix
        save_cms_config({"sanity": {"prod": {"project_id": "YOUR_PROJECT_ID"}}})
        assert platform_configured("sanity", "prod") is False

        # Test with PLACEHOLDER
        save_cms_config({"sanity": {"prod": {"project_id": "PLACEHOLDER_ID"}}})
        assert platform_configured("sanity", "prod") is False

    def test_list_platform_instances(self, tmp_project):
        """Test listing platform instances."""
        save_cms_config(
            {
                "sanity": {
                    "prod": {"project_id": "abc123"},
                    "staging": {"project_id": "xyz789"},
                    "default": {"project_id": "def456"},
                }
            }
        )

        instances = list_platform_instances("sanity")
        assert set(instances) == {"prod", "staging", "default"}

    def test_list_platform_instances_not_found(self, tmp_project):
        """Test listing instances when platform not configured."""
        save_cms_config({"sanity": {"prod": {"project_id": "abc123"}}})

        with pytest.raises(ValueError) as exc_info:
            list_platform_instances("contentful")

        assert "No configuration found for CMS platform 'contentful'" in str(exc_info.value)


class TestConfigIsolation:
    """
    CRITICAL TESTS: Verify that CMS and Analytics configs don't interfere with each other.
    This ensures both features can be onboarded independently without conflicts.
    """

    def test_cms_onboarding_with_existing_analytics(self, tmp_project):
        """Test onboarding CMS when analytics is already configured."""
        # Add analytics config to file
        config_file = get_config_file_path()
        with open(config_file, "a") as f:
            f.write("\n# Analytics Configuration\n")
            f.write('ANALYTICS_POSTHOG_PROJECT_ID="phc_existing"\n')
            f.write('ANALYTICS_POSTHOG_API_KEY="phx_existing"\n')

        # Verify analytics exists
        config = load_config()
        assert config.__pydantic_extra__["ANALYTICS_POSTHOG_PROJECT_ID"] == "phc_existing"

        # Onboard CMS
        cms_config = {
            "sanity": {
                "prod": {
                    "project_id": "sanity123",
                    "token": "sk_token",
                }
            }
        }
        save_cms_config(cms_config)

        # Verify both exist
        config = load_config()
        assert "ANALYTICS_POSTHOG_PROJECT_ID" in config.__pydantic_extra__
        assert config.__pydantic_extra__["ANALYTICS_POSTHOG_PROJECT_ID"] == "phc_existing"
        assert "ANALYTICS_POSTHOG_API_KEY" in config.__pydantic_extra__
        assert config.__pydantic_extra__["ANALYTICS_POSTHOG_API_KEY"] == "phx_existing"
        assert "CMS_SANITY_PROD_PROJECT_ID" in config.__pydantic_extra__
        assert "CMS_SANITY_PROD_TOKEN" in config.__pydantic_extra__

    def test_analytics_onboarding_with_existing_cms(self, tmp_project):
        """Test onboarding analytics when CMS is already configured."""
        from kurt.integrations.analytics.config import save_analytics_config

        # Add CMS config
        save_cms_config(
            {
                "sanity": {
                    "prod": {
                        "project_id": "sanity_existing",
                        "token": "sk_existing",
                    }
                }
            }
        )

        # Verify CMS exists
        config = load_config()
        assert config.__pydantic_extra__["CMS_SANITY_PROD_PROJECT_ID"] == "sanity_existing"

        # Onboard analytics
        analytics_config = {
            "posthog": {
                "project_id": "phc_123",
                "api_key": "phx_456",
            }
        }
        save_analytics_config(analytics_config)

        # Verify both exist
        config = load_config()
        assert "CMS_SANITY_PROD_PROJECT_ID" in config.__pydantic_extra__
        assert config.__pydantic_extra__["CMS_SANITY_PROD_PROJECT_ID"] == "sanity_existing"
        assert "CMS_SANITY_PROD_TOKEN" in config.__pydantic_extra__
        assert config.__pydantic_extra__["CMS_SANITY_PROD_TOKEN"] == "sk_existing"
        assert "ANALYTICS_POSTHOG_PROJECT_ID" in config.__pydantic_extra__
        assert "ANALYTICS_POSTHOG_API_KEY" in config.__pydantic_extra__

    def test_multiple_cms_platform_onboarding(self, tmp_project):
        """Test onboarding multiple CMS platforms sequentially."""
        # Onboard Sanity
        save_cms_config({"sanity": {"prod": {"project_id": "sanity123"}}})

        # Verify Sanity added
        config = load_config()
        assert "CMS_SANITY_PROD_PROJECT_ID" in config.__pydantic_extra__

        # Onboard Contentful (should preserve Sanity)
        add_platform_instance("contentful", "default", {"space_id": "contentful456"})

        # Verify both exist
        config = load_config()
        assert "CMS_SANITY_PROD_PROJECT_ID" in config.__pydantic_extra__
        assert "CMS_CONTENTFUL_DEFAULT_SPACE_ID" in config.__pydantic_extra__
