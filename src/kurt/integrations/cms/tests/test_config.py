"""Tests for CMS configuration module."""

import pytest

from kurt.integrations.cms.config import (
    add_platform_instance,
    cms_config_exists,
    create_template_config,
    get_platform_config,
    list_platform_instances,
    load_cms_config,
    platform_configured,
    save_cms_config,
)


class TestLoadCmsConfig:
    """Test load_cms_config function."""

    def test_load_empty_config(self, tmp_project):
        """Test loading when no CMS config exists."""
        result = load_cms_config()
        assert result == {}

    def test_load_with_cms_config(self, tmp_project_with_cms_config):
        """Test loading existing CMS config."""
        result = load_cms_config()

        assert "sanity" in result
        assert "prod" in result["sanity"]
        assert result["sanity"]["prod"]["project_id"] == "test-project-123"
        assert result["sanity"]["prod"]["dataset"] == "production"
        assert result["sanity"]["prod"]["token"] == "sk_test_token"

    def test_load_multiple_instances(self, tmp_project_with_cms_config):
        """Test loading config with multiple instances."""
        result = load_cms_config()

        assert "prod" in result["sanity"]
        assert "staging" in result["sanity"]
        assert result["sanity"]["staging"]["project_id"] == "test-project-staging"


class TestSaveCmsConfig:
    """Test save_cms_config function."""

    def test_save_new_config(self, tmp_project):
        """Test saving new CMS config."""
        config = {"sanity": {"prod": {"project_id": "new-project", "token": "sk_new"}}}

        save_cms_config(config)
        result = load_cms_config()

        assert result["sanity"]["prod"]["project_id"] == "new-project"

    def test_save_overwrites_existing(self, tmp_project_with_cms_config):
        """Test that save overwrites existing config."""
        config = {"sanity": {"prod": {"project_id": "updated-project"}}}

        save_cms_config(config)
        result = load_cms_config()

        assert result["sanity"]["prod"]["project_id"] == "updated-project"
        # Old token should be gone since we replaced the whole config
        assert "token" not in result["sanity"]["prod"]


class TestGetPlatformConfig:
    """Test get_platform_config function."""

    def test_get_existing_platform_instance(self, tmp_project_with_cms_config):
        """Test getting config for existing platform and instance."""
        result = get_platform_config("sanity", "prod")

        assert result["project_id"] == "test-project-123"
        assert result["token"] == "sk_test_token"

    def test_get_platform_default_instance(self, tmp_project_with_cms_config):
        """Test getting first instance when no instance specified."""
        result = get_platform_config("sanity")

        # Should return first available instance (prod)
        assert "project_id" in result

    def test_get_nonexistent_platform_raises(self, tmp_project):
        """Test that nonexistent platform raises ValueError."""
        with pytest.raises(ValueError, match="No configuration found"):
            get_platform_config("nonexistent")

    def test_get_nonexistent_instance_raises(self, tmp_project_with_cms_config):
        """Test that nonexistent instance raises ValueError."""
        with pytest.raises(ValueError, match="Instance 'nonexistent' not found"):
            get_platform_config("sanity", "nonexistent")

    def test_error_message_shows_available_platforms(self, tmp_project_with_cms_config):
        """Test error message lists available platforms."""
        with pytest.raises(ValueError) as exc_info:
            get_platform_config("contentful")

        assert "sanity" in str(exc_info.value)

    def test_error_message_shows_available_instances(self, tmp_project_with_cms_config):
        """Test error message lists available instances."""
        with pytest.raises(ValueError) as exc_info:
            get_platform_config("sanity", "nonexistent")

        assert "prod" in str(exc_info.value)
        assert "staging" in str(exc_info.value)


class TestAddPlatformInstance:
    """Test add_platform_instance function."""

    def test_add_new_platform(self, tmp_project):
        """Test adding a new platform."""
        add_platform_instance("sanity", "prod", {"project_id": "new-project"})

        result = load_cms_config()
        assert result["sanity"]["prod"]["project_id"] == "new-project"

    def test_add_new_instance_to_existing_platform(self, tmp_project_with_cms_config):
        """Test adding a new instance to existing platform."""
        add_platform_instance("sanity", "dev", {"project_id": "dev-project"})

        result = load_cms_config()
        assert result["sanity"]["dev"]["project_id"] == "dev-project"
        # Existing instances should still be there
        assert "prod" in result["sanity"]

    def test_update_existing_instance(self, tmp_project_with_cms_config):
        """Test updating an existing instance."""
        add_platform_instance(
            "sanity", "prod", {"project_id": "updated-project", "new_field": "value"}
        )

        result = load_cms_config()
        assert result["sanity"]["prod"]["project_id"] == "updated-project"
        assert result["sanity"]["prod"]["new_field"] == "value"


class TestCreateTemplateConfig:
    """Test create_template_config function."""

    def test_sanity_template(self):
        """Test Sanity template config."""
        template = create_template_config("sanity")

        assert "project_id" in template
        assert "dataset" in template
        assert "token" in template
        assert template["project_id"] == "YOUR_PROJECT_ID"

    def test_contentful_template(self):
        """Test Contentful template config."""
        template = create_template_config("contentful")

        assert "space_id" in template
        assert "access_token" in template
        assert template["space_id"] == "YOUR_SPACE_ID"

    def test_wordpress_template(self):
        """Test WordPress template config."""
        template = create_template_config("wordpress")

        assert "site_url" in template
        assert "username" in template
        assert "app_password" in template

    def test_unknown_platform_returns_empty(self):
        """Test unknown platform returns empty dict."""
        template = create_template_config("unknown_platform")
        assert template == {}


class TestCmsConfigExists:
    """Test cms_config_exists function."""

    def test_returns_false_when_no_config(self, tmp_project):
        """Test returns False when no CMS config exists."""
        assert cms_config_exists() is False

    def test_returns_true_when_config_exists(self, tmp_project_with_cms_config):
        """Test returns True when CMS config exists."""
        assert cms_config_exists() is True


class TestPlatformConfigured:
    """Test platform_configured function."""

    def test_returns_true_for_configured_platform(self, tmp_project_with_cms_config):
        """Test returns True for fully configured platform."""
        assert platform_configured("sanity") is True

    def test_returns_true_for_configured_instance(self, tmp_project_with_cms_config):
        """Test returns True for configured instance."""
        assert platform_configured("sanity", "prod") is True

    def test_returns_false_for_unconfigured_platform(self, tmp_project):
        """Test returns False for unconfigured platform."""
        assert platform_configured("sanity") is False

    def test_returns_false_for_unconfigured_instance(self, tmp_project_with_cms_config):
        """Test returns False for unconfigured instance."""
        assert platform_configured("sanity", "nonexistent") is False

    def test_returns_false_for_placeholder_values(self, tmp_project_with_placeholder_config):
        """Test returns False when config has placeholder values."""
        assert platform_configured("sanity") is False


class TestListPlatformInstances:
    """Test list_platform_instances function."""

    def test_list_instances(self, tmp_project_with_cms_config):
        """Test listing instances for a platform."""
        instances = list_platform_instances("sanity")

        assert "prod" in instances
        assert "staging" in instances

    def test_list_instances_nonexistent_platform_raises(self, tmp_project):
        """Test that nonexistent platform raises ValueError."""
        with pytest.raises(ValueError, match="No configuration found"):
            list_platform_instances("nonexistent")
