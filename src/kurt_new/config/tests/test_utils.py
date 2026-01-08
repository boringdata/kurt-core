"""Tests for config utilities (utils.py)."""

from kurt_new.config.base import get_config_file_path
from kurt_new.config.utils import (
    config_exists_for_prefix,
    get_available_keys,
    get_nested_value,
    has_placeholder_values,
    load_prefixed_config,
    save_prefixed_config,
    set_nested_value,
)


class TestLoadPrefixedConfig:
    """Test load_prefixed_config function."""

    def test_load_prefixed_config_cms_2_levels(self, tmp_project):
        """Test loading CMS config with 2 levels."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write('CMS_SANITY_PROD_PROJECT_ID="abc123"\n')
            f.write('CMS_SANITY_PROD_TOKEN="sk_prod"\n')
            f.write('CMS_SANITY_STAGING_PROJECT_ID="xyz789"\n')

        result = load_prefixed_config("CMS", levels=2)

        assert "sanity" in result
        assert "prod" in result["sanity"]
        assert result["sanity"]["prod"]["project_id"] == "abc123"
        assert result["sanity"]["prod"]["token"] == "sk_prod"
        assert "staging" in result["sanity"]
        assert result["sanity"]["staging"]["project_id"] == "xyz789"

    def test_load_prefixed_config_analytics_1_level(self, tmp_project):
        """Test loading Analytics config with 1 level."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write('ANALYTICS_POSTHOG_PROJECT_ID="phc_123"\n')
            f.write('ANALYTICS_POSTHOG_API_KEY="phx_456"\n')
            f.write('ANALYTICS_GA4_PROPERTY_ID="123456789"\n')

        result = load_prefixed_config("ANALYTICS", levels=1)

        assert "posthog" in result
        assert result["posthog"]["project_id"] == "phc_123"
        assert result["posthog"]["api_key"] == "phx_456"
        assert "ga4" in result
        assert result["ga4"]["property_id"] == "123456789"

    def test_load_prefixed_config_empty(self, tmp_project):
        """Test loading config when no prefixed keys exist."""
        result = load_prefixed_config("NONEXISTENT", levels=2)
        assert result == {}

    def test_load_prefixed_config_json_values(self, tmp_project):
        """Test loading config with JSON-encoded values."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write('CMS_SANITY_PROD_MAPPINGS={"page": "document", "post": "article"}\n')

        result = load_prefixed_config("CMS", levels=2)

        assert result["sanity"]["prod"]["mappings"] == {"page": "document", "post": "article"}


class TestSavePrefixedConfig:
    """Test save_prefixed_config function."""

    def test_save_prefixed_config_cms_2_levels(self, tmp_project):
        """Test saving CMS config with 2 levels."""
        config_data = {
            "sanity": {
                "prod": {"project_id": "abc123", "token": "sk_prod"},
                "staging": {"project_id": "xyz789"},
            }
        }

        save_prefixed_config("CMS", config_data, levels=2)

        # Verify by loading back
        result = load_prefixed_config("CMS", levels=2)
        assert result["sanity"]["prod"]["project_id"] == "abc123"
        assert result["sanity"]["prod"]["token"] == "sk_prod"
        assert result["sanity"]["staging"]["project_id"] == "xyz789"

    def test_save_prefixed_config_analytics_1_level(self, tmp_project):
        """Test saving Analytics config with 1 level."""
        config_data = {
            "posthog": {"project_id": "phc_123", "api_key": "phx_456"},
            "ga4": {"property_id": "123456789"},
        }

        save_prefixed_config("ANALYTICS", config_data, levels=1)

        result = load_prefixed_config("ANALYTICS", levels=1)
        assert result["posthog"]["project_id"] == "phc_123"
        assert result["ga4"]["property_id"] == "123456789"

    def test_save_prefixed_config_replaces_existing(self, tmp_project):
        """Test that save_prefixed_config replaces existing keys."""
        # First save
        save_prefixed_config("CMS", {"sanity": {"prod": {"project_id": "old"}}}, levels=2)

        # Second save (replace)
        save_prefixed_config("CMS", {"sanity": {"prod": {"project_id": "new"}}}, levels=2)

        result = load_prefixed_config("CMS", levels=2)
        assert result["sanity"]["prod"]["project_id"] == "new"

    def test_save_prefixed_config_preserves_other_prefixes(self, tmp_project):
        """Test that saving one prefix doesn't affect others."""
        save_prefixed_config("CMS", {"sanity": {"prod": {"project_id": "cms123"}}}, levels=2)
        save_prefixed_config("ANALYTICS", {"posthog": {"api_key": "phx_456"}}, levels=1)

        # Verify both exist
        cms_result = load_prefixed_config("CMS", levels=2)
        analytics_result = load_prefixed_config("ANALYTICS", levels=1)

        assert cms_result["sanity"]["prod"]["project_id"] == "cms123"
        assert analytics_result["posthog"]["api_key"] == "phx_456"


class TestNestedValueHelpers:
    """Test get_nested_value and set_nested_value functions."""

    def test_get_nested_value_found(self):
        """Test getting existing nested value."""
        config = {"sanity": {"prod": {"project_id": "abc123"}}}
        result = get_nested_value(config, ["sanity", "prod", "project_id"])
        assert result == "abc123"

    def test_get_nested_value_not_found(self):
        """Test getting non-existent path returns default."""
        config = {"sanity": {"prod": {}}}
        result = get_nested_value(config, ["sanity", "staging", "project_id"], default="default")
        assert result == "default"

    def test_get_nested_value_empty_path(self):
        """Test getting with empty path returns whole dict."""
        config = {"key": "value"}
        result = get_nested_value(config, [])
        assert result == config

    def test_set_nested_value_creates_path(self):
        """Test setting value creates intermediate dicts."""
        config = {}
        set_nested_value(config, ["sanity", "prod", "project_id"], "abc123")
        assert config == {"sanity": {"prod": {"project_id": "abc123"}}}

    def test_set_nested_value_overwrites(self):
        """Test setting value overwrites existing."""
        config = {"sanity": {"prod": {"project_id": "old"}}}
        set_nested_value(config, ["sanity", "prod", "project_id"], "new")
        assert config["sanity"]["prod"]["project_id"] == "new"


class TestConfigExistsForPrefix:
    """Test config_exists_for_prefix function."""

    def test_config_exists_for_prefix_true(self, tmp_project):
        """Test returns True when config exists."""
        save_prefixed_config("CMS", {"sanity": {"prod": {"project_id": "abc"}}}, levels=2)
        assert config_exists_for_prefix("CMS", levels=2) is True

    def test_config_exists_for_prefix_false(self, tmp_project):
        """Test returns False when no config exists."""
        assert config_exists_for_prefix("NONEXISTENT", levels=2) is False


class TestHasPlaceholderValues:
    """Test has_placeholder_values function."""

    def test_has_placeholder_values_your(self):
        """Test detects YOUR_ placeholders."""
        assert has_placeholder_values({"project_id": "YOUR_PROJECT_ID"}) is True

    def test_has_placeholder_values_placeholder(self):
        """Test detects PLACEHOLDER markers."""
        assert has_placeholder_values({"token": "PLACEHOLDER"}) is True

    def test_has_placeholder_values_none(self):
        """Test returns False for real values."""
        assert has_placeholder_values({"project_id": "abc123", "token": "sk_prod"}) is False

    def test_has_placeholder_values_nested(self):
        """Test detects placeholders in nested structures."""
        assert has_placeholder_values({"prod": {"token": "YOUR_TOKEN"}}) is True


class TestGetAvailableKeys:
    """Test get_available_keys function."""

    def test_get_available_keys_level_0(self):
        """Test getting top-level keys."""
        config = {"sanity": {}, "contentful": {}}
        result = get_available_keys(config, level=0)
        assert sorted(result) == ["contentful", "sanity"]

    def test_get_available_keys_level_1(self):
        """Test getting second-level keys."""
        config = {
            "sanity": {"prod": {}, "staging": {}},
            "contentful": {"default": {}},
        }
        result = get_available_keys(config, level=1)
        assert sorted(result) == ["default", "prod", "staging"]
