"""Tests for config utility functions (utils.py) using real config files."""

import json

from kurt.config.base import get_config_file_path
from kurt.config.utils import (
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

    def test_load_empty_config(self, tmp_project):
        """Test loading when no config exists for prefix."""
        result = load_prefixed_config("CUSTOM", levels=1)
        assert result == {}

    def test_load_single_level_config(self, tmp_project):
        """Test loading config with 1 organizational level (like Analytics)."""
        # Add analytics fields to config file
        config_file = get_config_file_path()
        with open(config_file, "a") as f:
            f.write('ANALYTICS_POSTHOG_PROJECT_ID="phc_abc123"\n')
            f.write('ANALYTICS_POSTHOG_API_KEY="phx_xyz789"\n')
            f.write('ANALYTICS_GA4_PROPERTY_ID="123456789"\n')

        result = load_prefixed_config("ANALYTICS", levels=1)

        assert len(result) == 2
        assert "posthog" in result
        assert result["posthog"]["project_id"] == "phc_abc123"
        assert result["posthog"]["api_key"] == "phx_xyz789"
        assert "ga4" in result
        assert result["ga4"]["property_id"] == "123456789"

    def test_load_two_level_config(self, tmp_project):
        """Test loading config with 2 organizational levels (like CMS)."""
        # Add CMS fields to config file
        config_file = get_config_file_path()
        with open(config_file, "a") as f:
            f.write('CMS_SANITY_PROD_PROJECT_ID="abc123"\n')
            f.write('CMS_SANITY_PROD_TOKEN="sk_token"\n')
            f.write('CMS_SANITY_STAGING_PROJECT_ID="xyz789"\n')
            f.write('CMS_CONTENTFUL_DEFAULT_SPACE_ID="space123"\n')

        result = load_prefixed_config("CMS", levels=2)

        assert len(result) == 2
        assert "sanity" in result
        assert "prod" in result["sanity"]
        assert result["sanity"]["prod"]["project_id"] == "abc123"
        assert result["sanity"]["prod"]["token"] == "sk_token"
        assert "staging" in result["sanity"]
        assert result["sanity"]["staging"]["project_id"] == "xyz789"
        assert "contentful" in result
        assert result["contentful"]["default"]["space_id"] == "space123"

    def test_load_config_with_json_values(self, tmp_project):
        """Test loading config with JSON-encoded values."""
        # Add config with JSON value
        config_file = get_config_file_path()
        mapping = {"article": {"enabled": True, "content_field": "body"}}
        with open(config_file, "a") as f:
            f.write(f'CMS_SANITY_PROD_CONTENT_TYPE_MAPPINGS="{json.dumps(mapping)}"\n')

        result = load_prefixed_config("CMS", levels=2)

        # JSON should be parsed back to dict
        assert isinstance(result["sanity"]["prod"]["content_type_mappings"], dict)
        assert result["sanity"]["prod"]["content_type_mappings"]["article"]["enabled"] is True

    def test_load_config_ignores_other_prefixes(self, tmp_project):
        """Test loading config only returns requested prefix."""
        # Add multiple prefixes
        config_file = get_config_file_path()
        with open(config_file, "a") as f:
            f.write('ANALYTICS_POSTHOG_API_KEY="phx_123"\n')
            f.write('CMS_SANITY_PROD_PROJECT_ID="sanity123"\n')
            f.write('RESEARCH_PERPLEXITY_API_KEY="pplx_456"\n')

        # Load only ANALYTICS
        result = load_prefixed_config("ANALYTICS", levels=1)

        assert "posthog" in result
        assert len(result) == 1
        # Should not include CMS or RESEARCH fields
        assert "sanity" not in str(result)
        assert "perplexity" not in str(result)

    def test_load_config_malformed_keys(self, tmp_project):
        """Test loading config with malformed keys (wrong number of parts)."""
        # Add malformed key (too few parts for levels=2)
        config_file = get_config_file_path()
        with open(config_file, "a") as f:
            f.write('CMS_SANITY_PROJECT_ID="abc123"\n')  # Missing instance level
            f.write('CMS_SANITY_PROD_PROJECT_ID="xyz789"\n')  # Valid

        result = load_prefixed_config("CMS", levels=2)

        # Should only load valid keys
        assert "sanity" in result
        assert "prod" in result["sanity"]
        assert result["sanity"]["prod"]["project_id"] == "xyz789"
        # Malformed key should be ignored (not enough parts)


class TestSavePrefixedConfig:
    """Test save_prefixed_config function."""

    def test_save_single_level_config(self, tmp_project):
        """Test saving config with 1 organizational level."""
        config_data = {
            "posthog": {
                "project_id": "phc_abc123",
                "api_key": "phx_xyz789",
            },
            "ga4": {
                "property_id": "123456789",
            },
        }

        save_prefixed_config("ANALYTICS", config_data, levels=1)

        # Verify file contents
        content = get_config_file_path().read_text()
        assert 'ANALYTICS_POSTHOG_PROJECT_ID="phc_abc123"' in content
        assert 'ANALYTICS_POSTHOG_API_KEY="phx_xyz789"' in content
        assert 'ANALYTICS_GA4_PROPERTY_ID="123456789"' in content

        # Verify can be loaded back
        loaded = load_prefixed_config("ANALYTICS", levels=1)
        assert loaded["posthog"]["project_id"] == "phc_abc123"
        assert loaded["ga4"]["property_id"] == "123456789"

    def test_save_two_level_config(self, tmp_project):
        """Test saving config with 2 organizational levels."""
        config_data = {
            "sanity": {
                "prod": {
                    "project_id": "abc123",
                    "token": "sk_token",
                },
                "staging": {
                    "project_id": "xyz789",
                },
            },
        }

        save_prefixed_config("CMS", config_data, levels=2)

        # Verify file contents
        content = get_config_file_path().read_text()
        assert 'CMS_SANITY_PROD_PROJECT_ID="abc123"' in content
        assert 'CMS_SANITY_PROD_TOKEN="sk_token"' in content
        assert 'CMS_SANITY_STAGING_PROJECT_ID="xyz789"' in content

        # Verify can be loaded back
        loaded = load_prefixed_config("CMS", levels=2)
        assert loaded["sanity"]["prod"]["project_id"] == "abc123"
        assert loaded["sanity"]["staging"]["project_id"] == "xyz789"

    def test_save_config_with_json_values(self, tmp_project):
        """Test saving config with nested dict/list values."""
        config_data = {
            "sanity": {
                "prod": {
                    "content_type_mappings": {
                        "article": {"enabled": True, "content_field": "body"}
                    },
                    "excluded_types": ["system", "internal"],
                }
            }
        }

        save_prefixed_config("CMS", config_data, levels=2)

        # Verify JSON encoding in file
        content = get_config_file_path().read_text()
        assert "CMS_SANITY_PROD_CONTENT_TYPE_MAPPINGS=" in content
        assert "CMS_SANITY_PROD_EXCLUDED_TYPES=" in content

        # Verify can be loaded back as dict/list
        loaded = load_prefixed_config("CMS", levels=2)
        assert isinstance(loaded["sanity"]["prod"]["content_type_mappings"], dict)
        assert isinstance(loaded["sanity"]["prod"]["excluded_types"], list)
        assert loaded["sanity"]["prod"]["excluded_types"] == ["system", "internal"]

    def test_save_config_removes_old_fields(self, tmp_project):
        """Test saving config removes old fields for same prefix."""
        # Save initial config
        save_prefixed_config("ANALYTICS", {"posthog": {"old_key": "old_value"}}, levels=1)

        # Verify it exists
        loaded = load_prefixed_config("ANALYTICS", levels=1)
        assert "old_key" in loaded["posthog"]

        # Save new config (should remove old fields)
        save_prefixed_config("ANALYTICS", {"posthog": {"new_key": "new_value"}}, levels=1)

        # Verify old fields removed
        loaded = load_prefixed_config("ANALYTICS", levels=1)
        assert "old_key" not in loaded["posthog"]
        assert loaded["posthog"]["new_key"] == "new_value"

    def test_save_config_preserves_other_prefixes(self, tmp_project):
        """Test saving config preserves fields from other prefixes."""
        # Add CMS config
        save_prefixed_config("CMS", {"sanity": {"prod": {"project_id": "sanity123"}}}, levels=2)

        # Verify CMS exists
        cms_config = load_prefixed_config("CMS", levels=2)
        assert cms_config["sanity"]["prod"]["project_id"] == "sanity123"

        # Save ANALYTICS config (should preserve CMS)
        save_prefixed_config("ANALYTICS", {"posthog": {"project_id": "phc_456"}}, levels=1)

        # Verify both exist
        cms_config = load_prefixed_config("CMS", levels=2)
        assert cms_config["sanity"]["prod"]["project_id"] == "sanity123"
        analytics_config = load_prefixed_config("ANALYTICS", levels=1)
        assert analytics_config["posthog"]["project_id"] == "phc_456"

    def test_save_config_updates_existing(self, tmp_project):
        """Test saving config updates existing fields."""
        # Save initial config
        save_prefixed_config("ANALYTICS", {"posthog": {"project_id": "phc_old123"}}, levels=1)

        # Update it
        save_prefixed_config(
            "ANALYTICS",
            {
                "posthog": {
                    "project_id": "phc_new123",
                    "api_key": "phx_new456",
                }
            },
            levels=1,
        )

        # Verify update
        loaded = load_prefixed_config("ANALYTICS", levels=1)
        assert loaded["posthog"]["project_id"] == "phc_new123"
        assert loaded["posthog"]["api_key"] == "phx_new456"


class TestNestedValueOperations:
    """Test get_nested_value and set_nested_value functions."""

    def test_get_nested_value_success(self, tmp_project):
        """Test getting nested value successfully."""
        config = {
            "sanity": {
                "prod": {
                    "project_id": "abc123",
                }
            }
        }

        value = get_nested_value(config, ["sanity", "prod", "project_id"])
        assert value == "abc123"

    def test_get_nested_value_intermediate_path(self, tmp_project):
        """Test getting intermediate nested value."""
        config = {
            "sanity": {
                "prod": {
                    "project_id": "abc123",
                }
            }
        }

        value = get_nested_value(config, ["sanity", "prod"])
        assert value == {"project_id": "abc123"}

    def test_get_nested_value_not_found(self, tmp_project):
        """Test getting nested value when path doesn't exist."""
        config = {
            "sanity": {
                "prod": {
                    "project_id": "abc123",
                }
            }
        }

        value = get_nested_value(config, ["sanity", "staging"])
        assert value is None

    def test_get_nested_value_with_default(self, tmp_project):
        """Test getting nested value with custom default."""
        config = {
            "sanity": {
                "prod": {
                    "project_id": "abc123",
                }
            }
        }

        value = get_nested_value(config, ["sanity", "staging"], default={})
        assert value == {}

    def test_get_nested_value_non_dict_in_path(self, tmp_project):
        """Test getting nested value when encountering non-dict in path."""
        config = {
            "sanity": {
                "prod": "simple_string",
            }
        }

        value = get_nested_value(config, ["sanity", "prod", "project_id"])
        assert value is None

    def test_set_nested_value_creates_intermediate(self, tmp_project):
        """Test setting nested value creates intermediate dicts."""
        config = {}

        set_nested_value(config, ["sanity", "prod", "project_id"], "abc123")

        assert config == {"sanity": {"prod": {"project_id": "abc123"}}}

    def test_set_nested_value_updates_existing(self, tmp_project):
        """Test setting nested value updates existing value."""
        config = {"sanity": {"prod": {"project_id": "old123"}}}

        set_nested_value(config, ["sanity", "prod", "project_id"], "new123")

        assert config["sanity"]["prod"]["project_id"] == "new123"

    def test_set_nested_value_preserves_siblings(self, tmp_project):
        """Test setting nested value preserves sibling keys."""
        config = {
            "sanity": {
                "prod": {
                    "project_id": "abc123",
                    "token": "sk_token",
                }
            }
        }

        set_nested_value(config, ["sanity", "prod", "dataset"], "production")

        assert config["sanity"]["prod"]["project_id"] == "abc123"
        assert config["sanity"]["prod"]["token"] == "sk_token"
        assert config["sanity"]["prod"]["dataset"] == "production"


class TestConfigExists:
    """Test config_exists function."""

    def test_config_exists_true(self, tmp_project):
        """Test config_exists_for_prefix when config exists."""
        save_prefixed_config("ANALYTICS", {"posthog": {"project_id": "phc_123"}}, levels=1)

        assert config_exists_for_prefix("ANALYTICS", levels=1) is True

    def test_config_exists_false(self, tmp_project):
        """Test config_exists_for_prefix when config doesn't exist."""
        assert config_exists_for_prefix("CUSTOM", levels=1) is False

    def test_config_exists_empty_after_removal(self, tmp_project):
        """Test config_exists_for_prefix after all fields removed."""
        # Add config
        save_prefixed_config("ANALYTICS", {"posthog": {"project_id": "phc_123"}}, levels=1)

        assert config_exists_for_prefix("ANALYTICS", levels=1) is True

        # Remove all fields by saving empty dict
        save_prefixed_config("ANALYTICS", {}, levels=1)

        assert config_exists_for_prefix("ANALYTICS", levels=1) is False


class TestHasPlaceholderValues:
    """Test has_placeholder_values function."""

    def test_has_placeholder_values_your_prefix(self, tmp_project):
        """Test detecting YOUR_ prefix placeholders."""
        config = {"project_id": "YOUR_PROJECT_ID"}
        assert has_placeholder_values(config) is True

    def test_has_placeholder_values_placeholder_keyword(self, tmp_project):
        """Test detecting PLACEHOLDER keyword."""
        config = {"api_key": "PLACEHOLDER_KEY"}
        assert has_placeholder_values(config) is True

    def test_has_placeholder_values_nested(self, tmp_project):
        """Test detecting placeholders in nested values."""
        config = {
            "posthog": {
                "project_id": "phc_real123",
                "api_key": "YOUR_API_KEY",
            }
        }
        assert has_placeholder_values(config) is True

    def test_has_placeholder_values_false(self, tmp_project):
        """Test when no placeholders present."""
        config = {
            "project_id": "abc123",
            "api_key": "real_key_456",
        }
        assert has_placeholder_values(config) is False

    def test_has_placeholder_values_empty(self, tmp_project):
        """Test with empty config."""
        config = {}
        assert has_placeholder_values(config) is False


class TestGetAvailableKeys:
    """Test get_available_keys function."""

    def test_get_available_keys_level_0(self, tmp_project):
        """Test getting keys at top level."""
        config = {
            "sanity": {"prod": {}},
            "contentful": {"default": {}},
        }

        keys = get_available_keys(config, level=0)
        assert set(keys) == {"sanity", "contentful"}

    def test_get_available_keys_level_1(self, tmp_project):
        """Test getting keys at second level."""
        config = {
            "sanity": {
                "prod": {"project_id": "abc123"},
                "staging": {"project_id": "xyz789"},
            }
        }

        keys = get_available_keys(config["sanity"], level=0)
        assert set(keys) == {"prod", "staging"}

    def test_get_available_keys_nested_level(self, tmp_project):
        """Test getting keys from deeper level."""
        config = {
            "sanity": {
                "prod": {"key1": "val1"},
                "staging": {"key2": "val2"},
            },
            "contentful": {"default": {"key3": "val3"}},
        }

        # Get all second-level keys across all platforms
        keys = get_available_keys(config, level=1)
        assert set(keys) == {"prod", "staging", "default"}

    def test_get_available_keys_empty(self, tmp_project):
        """Test getting keys from empty config."""
        config = {}

        keys = get_available_keys(config, level=0)
        assert keys == []

    def test_get_available_keys_sorted(self, tmp_project):
        """Test that keys are sorted when level > 0."""
        config = {
            "platform1": {"z_instance": {}, "a_instance": {}},
            "platform2": {"m_instance": {}},
        }

        keys = get_available_keys(config, level=1)
        # Should be sorted alphabetically
        assert keys == ["a_instance", "m_instance", "z_instance"]


class TestIntegration:
    """Integration tests combining multiple utility functions."""

    def test_full_workflow_single_level(self, tmp_project):
        """Test complete workflow: save, load, check existence, get values."""
        # Save config
        config_data = {
            "posthog": {
                "project_id": "phc_abc123",
                "api_key": "phx_xyz789",
            }
        }
        save_prefixed_config("ANALYTICS", config_data, levels=1)

        # Check existence
        assert config_exists_for_prefix("ANALYTICS", levels=1) is True

        # Load config
        loaded = load_prefixed_config("ANALYTICS", levels=1)

        # Get nested value
        project_id = get_nested_value(loaded, ["posthog", "project_id"])
        assert project_id == "phc_abc123"

        # Check for placeholders
        assert has_placeholder_values(loaded) is False

        # Get available providers
        providers = get_available_keys(loaded, level=0)
        assert providers == ["posthog"]

    def test_full_workflow_two_levels(self, tmp_project):
        """Test complete workflow with 2-level config."""
        # Save config
        config_data = {
            "sanity": {
                "prod": {"project_id": "abc123"},
                "staging": {"project_id": "xyz789"},
            }
        }
        save_prefixed_config("CMS", config_data, levels=2)

        # Check existence
        assert config_exists_for_prefix("CMS", levels=2) is True

        # Load config
        loaded = load_prefixed_config("CMS", levels=2)

        # Get platforms
        platforms = get_available_keys(loaded, level=0)
        assert platforms == ["sanity"]

        # Get instances
        instances = get_available_keys(loaded["sanity"], level=0)
        assert set(instances) == {"prod", "staging"}

        # Update via set_nested_value
        set_nested_value(loaded, ["sanity", "prod", "token"], "sk_token")

        # Save updated config
        save_prefixed_config("CMS", loaded, levels=2)

        # Reload and verify
        reloaded = load_prefixed_config("CMS", levels=2)
        assert reloaded["sanity"]["prod"]["token"] == "sk_token"

    def test_multiple_prefixes_isolation(self, tmp_project):
        """Test that multiple prefixes work independently."""
        # Save CMS config
        save_prefixed_config("CMS", {"sanity": {"prod": {"project_id": "cms123"}}}, levels=2)

        # Save Analytics config
        save_prefixed_config("ANALYTICS", {"posthog": {"project_id": "analytics456"}}, levels=1)

        # Save Research config
        save_prefixed_config("RESEARCH", {"perplexity": {"api_key": "research789"}}, levels=1)

        # Verify all exist
        assert config_exists_for_prefix("CMS", levels=2) is True
        assert config_exists_for_prefix("ANALYTICS", levels=1) is True
        assert config_exists_for_prefix("RESEARCH", levels=1) is True

        # Verify values are isolated
        cms = load_prefixed_config("CMS", levels=2)
        analytics = load_prefixed_config("ANALYTICS", levels=1)
        research = load_prefixed_config("RESEARCH", levels=1)

        assert cms["sanity"]["prod"]["project_id"] == "cms123"
        assert analytics["posthog"]["project_id"] == "analytics456"
        assert research["perplexity"]["api_key"] == "research789"

        # Update one shouldn't affect others
        save_prefixed_config(
            "ANALYTICS", {"posthog": {"project_id": "updated_analytics"}}, levels=1
        )

        # CMS and Research should be unchanged
        cms_after = load_prefixed_config("CMS", levels=2)
        research_after = load_prefixed_config("RESEARCH", levels=1)
        assert cms_after == cms
        assert research_after == research
