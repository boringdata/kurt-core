"""Tests for research configuration using real config files."""

import pytest

from kurt.integrations.research.config import (
    get_source_config,
    load_research_config,
    research_config_exists,
    save_research_config,
    source_configured,
)


class TestResearchConfig:
    """Test research configuration functions with real config files."""

    def test_load_research_config_empty(self, tmp_project):
        """Test loading research config when no sources configured."""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_research_config()

        assert "Research configuration file not found" in str(exc_info.value)
        assert "Create this file with your research API credentials" in str(exc_info.value)

    def test_save_and_load_research_config(self, tmp_project):
        """Test saving and loading research config."""
        # Save research config
        research_config = {
            "perplexity": {
                "api_key": "pplx_test123",
                "default_model": "sonar-reasoning",
                "max_tokens": 4000,
            },
            "tavily": {
                "api_key": "tvly_test456",
            },
            "exa": {
                "api_key": "exa_test789",
            },
        }
        save_research_config(research_config)

        # Load it back
        loaded = load_research_config()

        # Verify all sources
        assert len(loaded) == 3
        assert "perplexity" in loaded
        assert "tavily" in loaded
        assert "exa" in loaded

        # Check Perplexity config
        assert loaded["perplexity"]["api_key"] == "pplx_test123"
        assert loaded["perplexity"]["default_model"] == "sonar-reasoning"
        assert loaded["perplexity"]["max_tokens"] == "4000"  # Config stores as string

        # Check Tavily config
        assert loaded["tavily"]["api_key"] == "tvly_test456"

        # Check Exa config
        assert loaded["exa"]["api_key"] == "exa_test789"

    def test_get_source_config_success(self, tmp_project):
        """Test getting source config successfully."""
        # Save config
        save_research_config(
            {
                "perplexity": {
                    "api_key": "pplx_test123",
                    "default_model": "sonar-reasoning",
                }
            }
        )

        # Get source config
        source_config = get_source_config("perplexity")
        assert source_config["api_key"] == "pplx_test123"
        assert source_config["default_model"] == "sonar-reasoning"

    def test_get_source_config_not_found(self, tmp_project):
        """Test getting source config when source not configured."""
        # Save config with perplexity only
        save_research_config({"perplexity": {"api_key": "pplx_test123"}})

        with pytest.raises(ValueError) as exc_info:
            get_source_config("tavily")

        assert "No configuration found for research source 'tavily'" in str(exc_info.value)
        assert "Available sources: perplexity" in str(exc_info.value)

    def test_get_source_config_placeholder_api_key(self, tmp_project):
        """Test getting source config with placeholder API key."""
        # Test with YOUR_ prefix
        save_research_config({"perplexity": {"api_key": "YOUR_API_KEY"}})

        with pytest.raises(ValueError) as exc_info:
            get_source_config("perplexity")

        assert "API key not configured for 'perplexity'" in str(exc_info.value)

        # Test with PLACEHOLDER
        save_research_config({"perplexity": {"api_key": "PLACEHOLDER_KEY"}})

        with pytest.raises(ValueError) as exc_info:
            get_source_config("perplexity")

        assert "API key not configured for 'perplexity'" in str(exc_info.value)

    def test_research_config_exists_true(self, tmp_project):
        """Test checking if research config exists when it does."""
        save_research_config({"perplexity": {"api_key": "pplx_test123"}})

        assert research_config_exists() is True

    def test_research_config_exists_false(self, tmp_project):
        """Test checking if research config exists when it doesn't."""
        assert research_config_exists() is False

    def test_source_configured_true(self, tmp_project):
        """Test checking if source is configured with valid API key."""
        save_research_config(
            {
                "perplexity": {
                    "api_key": "pplx_test123",
                    "default_model": "sonar-reasoning",
                }
            }
        )

        assert source_configured("perplexity") is True

    def test_source_configured_not_in_config(self, tmp_project):
        """Test checking if source is configured when it's not."""
        save_research_config({"perplexity": {"api_key": "pplx_test123"}})

        assert source_configured("tavily") is False

    def test_source_configured_placeholder_values(self, tmp_project):
        """Test source_configured detects placeholder values."""
        # Test with YOUR_ prefix
        save_research_config({"perplexity": {"api_key": "YOUR_API_KEY"}})
        assert source_configured("perplexity") is False

        # Test with PLACEHOLDER
        save_research_config({"perplexity": {"api_key": "PLACEHOLDER_KEY"}})
        assert source_configured("perplexity") is False

        # Test with empty string
        save_research_config({"perplexity": {"api_key": ""}})
        assert source_configured("perplexity") is False

    def test_source_configured_no_config(self, tmp_project):
        """Test source_configured when config doesn't exist."""
        assert source_configured("perplexity") is False

    def test_save_research_config_preserves_other_fields(self, tmp_project):
        """
        CRITICAL TEST: Verify that saving research config does NOT overwrite CMS/Analytics fields.
        """
        from kurt.config.base import get_config_file_path, load_config

        # Manually add CMS fields to config file
        config_file = get_config_file_path()
        with open(config_file, "a") as f:
            f.write("\n# CMS Configuration\n")
            f.write('CMS_SANITY_PROD_PROJECT_ID="sanity_existing"\n')
            f.write('ANALYTICS_POSTHOG_API_KEY="phx_existing"\n')

        # Verify they exist
        config = load_config()
        assert "CMS_SANITY_PROD_PROJECT_ID" in config.__pydantic_extra__
        assert "ANALYTICS_POSTHOG_API_KEY" in config.__pydantic_extra__

        # Save research config
        save_research_config(
            {
                "perplexity": {
                    "api_key": "pplx_test123",
                }
            }
        )

        # Verify other fields are preserved
        config = load_config()
        assert "CMS_SANITY_PROD_PROJECT_ID" in config.__pydantic_extra__
        assert config.__pydantic_extra__["CMS_SANITY_PROD_PROJECT_ID"] == "sanity_existing"
        assert "ANALYTICS_POSTHOG_API_KEY" in config.__pydantic_extra__
        assert config.__pydantic_extra__["ANALYTICS_POSTHOG_API_KEY"] == "phx_existing"

        # Verify research fields are added
        assert "RESEARCH_PERPLEXITY_API_KEY" in config.__pydantic_extra__

    def test_add_source_config(self, tmp_project):
        """Test adding a new source to existing config."""
        # Add first source
        save_research_config({"perplexity": {"api_key": "pplx_test123"}})

        # Load and add another source
        config = load_research_config()
        config["tavily"] = {"api_key": "tvly_test456"}
        save_research_config(config)

        # Verify both exist
        loaded = load_research_config()
        assert "perplexity" in loaded
        assert loaded["perplexity"]["api_key"] == "pplx_test123"
        assert "tavily" in loaded
        assert loaded["tavily"]["api_key"] == "tvly_test456"
