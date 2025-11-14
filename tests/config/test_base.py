"""Tests for core configuration (base.py) using real config files."""

from pathlib import Path

import pytest

from kurt.config.base import (
    KurtConfig,
    config_exists,
    create_config,
    get_config_file_path,
    get_config_or_default,
    load_config,
    update_config,
    validate_config,
)


class TestKurtConfig:
    """Test KurtConfig model and path resolution."""

    def test_default_values(self, tmp_project):
        """Test KurtConfig default values."""
        config = KurtConfig()
        assert config.PATH_DB == ".kurt/kurt.sqlite"
        assert config.PATH_SOURCES == "sources"
        assert config.PATH_PROJECTS == "projects"
        assert config.PATH_RULES == "rules"
        assert config.INDEXING_LLM_MODEL == "openai/gpt-4o-mini"
        assert config.INGESTION_FETCH_ENGINE == "trafilatura"
        assert config.TELEMETRY_ENABLED is True

    def test_custom_values(self, tmp_project):
        """Test creating KurtConfig with custom values."""
        config = KurtConfig(
            PATH_DB=".data/db.sqlite",
            PATH_SOURCES="content",
            PATH_PROJECTS="work",
            PATH_RULES="config",
            INDEXING_LLM_MODEL="anthropic/claude-3-5-sonnet-20241022",
            INGESTION_FETCH_ENGINE="firecrawl",
            TELEMETRY_ENABLED=False,
        )
        assert config.PATH_DB == ".data/db.sqlite"
        assert config.PATH_SOURCES == "content"
        assert config.PATH_PROJECTS == "work"
        assert config.PATH_RULES == "config"
        assert config.INDEXING_LLM_MODEL == "anthropic/claude-3-5-sonnet-20241022"
        assert config.INGESTION_FETCH_ENGINE == "firecrawl"
        assert config.TELEMETRY_ENABLED is False

    def test_extra_fields_allowed(self, tmp_project):
        """Test that extra fields are allowed (for integrations)."""
        config = KurtConfig(
            ANALYTICS_POSTHOG_API_KEY="phx_test123",
            CMS_SANITY_PROD_PROJECT_ID="sanity123",
        )
        assert config.__pydantic_extra__["ANALYTICS_POSTHOG_API_KEY"] == "phx_test123"
        assert config.__pydantic_extra__["CMS_SANITY_PROD_PROJECT_ID"] == "sanity123"

    def test_get_absolute_db_path_relative(self, tmp_project):
        """Test getting absolute DB path when PATH_DB is relative."""
        config = load_config()
        db_path = config.get_absolute_db_path()

        assert db_path.is_absolute()
        assert db_path.name == "kurt.sqlite"
        assert db_path.parent.name == ".kurt"

    def test_get_absolute_db_path_absolute(self, tmp_project):
        """Test getting absolute DB path when PATH_DB is already absolute."""
        absolute_path = "/tmp/custom/db.sqlite"
        config = KurtConfig(PATH_DB=absolute_path)

        # Mock get_config_file_path to return tmp_project
        db_path = config.get_absolute_db_path()
        assert str(db_path) == absolute_path

    def test_get_db_directory(self, tmp_project):
        """Test getting DB directory path."""
        config = load_config()
        db_dir = config.get_db_directory()

        assert db_dir.is_absolute()
        assert db_dir.name == ".kurt"

    def test_get_absolute_sources_path(self, tmp_project):
        """Test getting absolute sources path."""
        config = load_config()
        sources_path = config.get_absolute_sources_path()

        assert sources_path.is_absolute()
        assert sources_path.name == "sources"

    def test_get_absolute_projects_path(self, tmp_project):
        """Test getting absolute projects path."""
        config = load_config()
        projects_path = config.get_absolute_projects_path()

        assert projects_path.is_absolute()
        assert projects_path.name == "projects"

    def test_get_absolute_rules_path(self, tmp_project):
        """Test getting absolute rules path."""
        config = load_config()
        rules_path = config.get_absolute_rules_path()

        assert rules_path.is_absolute()
        assert rules_path.name == "rules"


class TestConfigFileOperations:
    """Test config file operations (create, load, update)."""

    def test_get_config_file_path(self, tmp_project):
        """Test getting config file path."""
        config_path = get_config_file_path()
        assert config_path.name == "kurt.config"
        assert config_path.parent == Path.cwd()

    def test_config_exists_true(self, tmp_project):
        """Test config_exists when config file exists."""
        assert config_exists() is True

    def test_config_exists_false(self, tmp_project):
        """Test config_exists when config file doesn't exist."""
        # Remove config file
        config_file = get_config_file_path()
        config_file.unlink()

        assert config_exists() is False

    def test_create_config_default(self, tmp_project):
        """Test creating config with default values."""
        # Remove existing config
        config_file = get_config_file_path()
        config_file.unlink()

        # Create new config
        config = create_config()

        # Verify defaults
        assert config.PATH_DB == ".kurt/kurt.sqlite"
        assert config.PATH_SOURCES == "sources"
        assert config.PATH_PROJECTS == "projects"
        assert config.PATH_RULES == "rules"

        # Verify file was created
        assert config_file.exists()

        # Verify file contents
        content = config_file.read_text()
        assert 'PATH_DB=".kurt/kurt.sqlite"' in content
        assert 'PATH_SOURCES="sources"' in content
        # Boolean written without quotes
        assert "TELEMETRY_ENABLED=True" in content

    def test_create_config_custom(self, tmp_project):
        """Test creating config with custom values."""
        # Remove existing config
        config_file = get_config_file_path()
        config_file.unlink()

        # Create with custom values
        config = create_config(
            db_path=".data/custom.db",
            sources_path="content",
            projects_path="work",
            rules_path="config",
        )

        assert config.PATH_DB == ".data/custom.db"
        assert config.PATH_SOURCES == "content"
        assert config.PATH_PROJECTS == "work"
        assert config.PATH_RULES == "config"

        # Verify file contents
        content = config_file.read_text()
        assert 'PATH_DB=".data/custom.db"' in content
        assert 'PATH_SOURCES="content"' in content

    def test_load_config_success(self, tmp_project):
        """Test loading config successfully."""
        config = load_config()

        assert isinstance(config, KurtConfig)
        assert config.PATH_DB == ".kurt/kurt.sqlite"
        assert config.PATH_SOURCES == "sources"

    def test_load_config_not_found(self, tmp_project):
        """Test loading config when file doesn't exist."""
        # Remove config file
        config_file = get_config_file_path()
        config_file.unlink()

        with pytest.raises(FileNotFoundError) as exc_info:
            load_config()

        assert "Kurt configuration file not found" in str(exc_info.value)
        assert "Run 'kurt init' to initialize a Kurt project" in str(exc_info.value)

    def test_load_config_with_comments(self, tmp_project):
        """Test loading config ignores comments and empty lines."""
        config_file = get_config_file_path()

        # Add comments and empty lines
        with open(config_file, "a") as f:
            f.write("\n# This is a comment\n")
            f.write("\n")
            f.write("# Another comment\n")

        # Should load without errors
        config = load_config()
        assert isinstance(config, KurtConfig)

    def test_load_config_with_extra_fields(self, tmp_project):
        """Test loading config with integration extra fields."""
        config_file = get_config_file_path()

        # Add extra fields
        with open(config_file, "a") as f:
            f.write('\nANALYTICS_POSTHOG_API_KEY="phx_test123"\n')
            f.write('CMS_SANITY_PROD_PROJECT_ID="sanity123"\n')

        config = load_config()
        assert "ANALYTICS_POSTHOG_API_KEY" in config.__pydantic_extra__
        assert config.__pydantic_extra__["ANALYTICS_POSTHOG_API_KEY"] == "phx_test123"
        assert "CMS_SANITY_PROD_PROJECT_ID" in config.__pydantic_extra__
        assert config.__pydantic_extra__["CMS_SANITY_PROD_PROJECT_ID"] == "sanity123"

    def test_get_config_or_default_exists(self, tmp_project):
        """Test get_config_or_default when config exists."""
        config = get_config_or_default()

        assert isinstance(config, KurtConfig)
        assert config.PATH_DB == ".kurt/kurt.sqlite"

    def test_get_config_or_default_not_exists(self, tmp_project):
        """Test get_config_or_default when config doesn't exist."""
        # Remove config file
        config_file = get_config_file_path()
        config_file.unlink()

        config = get_config_or_default()

        # Should return default config (not create file)
        assert isinstance(config, KurtConfig)
        assert config.PATH_DB == ".kurt/kurt.sqlite"
        assert not config_file.exists()  # File should NOT be created

    def test_update_config_basic_fields(self, tmp_project):
        """Test updating config with basic fields."""
        config = load_config()
        config.PATH_DB = ".data/new.db"
        config.INDEXING_LLM_MODEL = "anthropic/claude-3-5-sonnet-20241022"

        update_config(config)

        # Reload and verify
        loaded = load_config()
        assert loaded.PATH_DB == ".data/new.db"
        assert loaded.INDEXING_LLM_MODEL == "anthropic/claude-3-5-sonnet-20241022"

    def test_update_config_preserves_extra_fields(self, tmp_project):
        """Test that update_config preserves extra fields from integrations."""
        # Add extra fields
        config_file = get_config_file_path()
        with open(config_file, "a") as f:
            f.write('\nANALYTICS_POSTHOG_API_KEY="phx_existing"\n')
            f.write('CMS_SANITY_PROD_PROJECT_ID="sanity_existing"\n')

        # Load, modify basic field, and update
        config = load_config()
        config.PATH_DB = ".data/updated.db"
        update_config(config)

        # Verify extra fields preserved
        loaded = load_config()
        assert loaded.PATH_DB == ".data/updated.db"
        assert "ANALYTICS_POSTHOG_API_KEY" in loaded.__pydantic_extra__
        assert loaded.__pydantic_extra__["ANALYTICS_POSTHOG_API_KEY"] == "phx_existing"
        assert "CMS_SANITY_PROD_PROJECT_ID" in loaded.__pydantic_extra__
        assert loaded.__pydantic_extra__["CMS_SANITY_PROD_PROJECT_ID"] == "sanity_existing"

    def test_update_config_groups_by_prefix(self, tmp_project):
        """Test that update_config groups extra fields by prefix with headers."""
        config = load_config()

        # Add multiple prefixes via __pydantic_extra__
        if not hasattr(config, "__pydantic_extra__"):
            config.__pydantic_extra__ = {}

        config.__pydantic_extra__["ANALYTICS_POSTHOG_API_KEY"] = "phx_123"
        config.__pydantic_extra__["ANALYTICS_GA4_PROPERTY_ID"] = "ga4_456"
        config.__pydantic_extra__["CMS_SANITY_PROD_PROJECT_ID"] = "sanity_789"
        config.__pydantic_extra__["RESEARCH_PERPLEXITY_API_KEY"] = "pplx_abc"

        update_config(config)

        # Verify file structure
        content = get_config_file_path().read_text()

        # Should have headers
        assert "# Analytics Provider Configurations" in content
        assert "# CMS Provider Configurations" in content
        assert "# Research Provider Configurations" in content

        # Should have all fields
        assert 'ANALYTICS_POSTHOG_API_KEY="phx_123"' in content
        assert 'ANALYTICS_GA4_PROPERTY_ID="ga4_456"' in content
        assert 'CMS_SANITY_PROD_PROJECT_ID="sanity_789"' in content
        assert 'RESEARCH_PERPLEXITY_API_KEY="pplx_abc"' in content

        # Analytics section should come before CMS (alphabetical)
        analytics_pos = content.find("# Analytics")
        cms_pos = content.find("# CMS")
        research_pos = content.find("# Research")
        assert analytics_pos < cms_pos < research_pos

    def test_update_config_custom_prefix(self, tmp_project):
        """Test that update_config handles custom prefixes (future extensibility)."""
        config = load_config()

        if not hasattr(config, "__pydantic_extra__"):
            config.__pydantic_extra__ = {}

        # Add a custom prefix not in prefix_names dict
        config.__pydantic_extra__["CUSTOM_INTEGRATION_API_KEY"] = "custom_123"

        update_config(config)

        # Verify file structure
        content = get_config_file_path().read_text()

        # Should create generic header
        assert "# CUSTOM Configurations" in content
        assert 'CUSTOM_INTEGRATION_API_KEY="custom_123"' in content


class TestBooleanTypeHandling:
    """Test boolean type handling in config save/load cycle."""

    def test_telemetry_enabled_true_roundtrip(self, tmp_project):
        """Test saving and loading TELEMETRY_ENABLED=True."""
        config = load_config()
        config.TELEMETRY_ENABLED = True
        update_config(config)

        # Verify file content (should be True, not "True")
        content = get_config_file_path().read_text()
        assert "TELEMETRY_ENABLED=True" in content
        assert 'TELEMETRY_ENABLED="True"' not in content

        # Load and verify type
        loaded = load_config()
        assert loaded.TELEMETRY_ENABLED is True
        assert isinstance(loaded.TELEMETRY_ENABLED, bool)

    def test_telemetry_enabled_false_roundtrip(self, tmp_project):
        """Test saving and loading TELEMETRY_ENABLED=False."""
        config = load_config()
        config.TELEMETRY_ENABLED = False
        update_config(config)

        # Verify file content
        content = get_config_file_path().read_text()
        assert "TELEMETRY_ENABLED=False" in content

        # Load and verify type
        loaded = load_config()
        assert loaded.TELEMETRY_ENABLED is False
        assert isinstance(loaded.TELEMETRY_ENABLED, bool)

    def test_boolean_string_variations(self, tmp_project):
        """Test loading boolean from various string representations."""
        config_file = get_config_file_path()

        # Helper to replace TELEMETRY_ENABLED value
        def set_telemetry(value: str):
            content = config_file.read_text()
            # Replace any existing TELEMETRY_ENABLED line
            lines = content.splitlines()
            new_lines = []
            for line in lines:
                if line.strip().startswith("TELEMETRY_ENABLED"):
                    new_lines.append(f"TELEMETRY_ENABLED={value}")
                else:
                    new_lines.append(line)
            config_file.write_text("\n".join(new_lines) + "\n")

        # Test "true" (lowercase)
        set_telemetry("true")
        loaded = load_config()
        assert loaded.TELEMETRY_ENABLED is True

        # Test "1"
        set_telemetry("1")
        loaded = load_config()
        assert loaded.TELEMETRY_ENABLED is True

        # Test "yes"
        set_telemetry("yes")
        loaded = load_config()
        assert loaded.TELEMETRY_ENABLED is True

        # Test "on"
        set_telemetry("on")
        loaded = load_config()
        assert loaded.TELEMETRY_ENABLED is True

        # Test "false"
        set_telemetry("false")
        loaded = load_config()
        assert loaded.TELEMETRY_ENABLED is False

        # Test "0"
        set_telemetry("0")
        loaded = load_config()
        assert loaded.TELEMETRY_ENABLED is False

        # Test "no"
        set_telemetry("no")
        loaded = load_config()
        assert loaded.TELEMETRY_ENABLED is False

    def test_boolean_with_quotes(self, tmp_project):
        """Test loading boolean values wrapped in quotes."""
        config_file = get_config_file_path()

        # Helper to set TELEMETRY_ENABLED value
        def set_telemetry(value: str):
            content = config_file.read_text()
            lines = content.splitlines()
            new_lines = []
            for line in lines:
                if line.strip().startswith("TELEMETRY_ENABLED"):
                    new_lines.append(f"TELEMETRY_ENABLED={value}")
                else:
                    new_lines.append(line)
            config_file.write_text("\n".join(new_lines) + "\n")

        # Test quoted "True"
        set_telemetry('"True"')
        loaded = load_config()
        assert loaded.TELEMETRY_ENABLED is True

        # Test quoted "false"
        set_telemetry('"false"')
        loaded = load_config()
        assert loaded.TELEMETRY_ENABLED is False

        # Test single-quoted
        set_telemetry("'true'")
        loaded = load_config()
        assert loaded.TELEMETRY_ENABLED is True


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_config_file(self, tmp_project):
        """Test loading from an empty config file."""
        config_file = get_config_file_path()
        config_file.write_text("")

        # Should use defaults
        config = load_config()
        assert config.PATH_DB == ".kurt/kurt.sqlite"
        assert config.TELEMETRY_ENABLED is True

    def test_config_with_only_comments(self, tmp_project):
        """Test loading from config file with only comments."""
        config_file = get_config_file_path()
        config_file.write_text("# This is a comment\n# Another comment\n")

        config = load_config()
        assert config.PATH_DB == ".kurt/kurt.sqlite"

    def test_config_with_unicode_values(self, tmp_project):
        """Test handling unicode in config values."""
        config = load_config()
        if not hasattr(config, "__pydantic_extra__"):
            config.__pydantic_extra__ = {}

        # Add unicode value
        config.__pydantic_extra__["CMS_CUSTOM_SITE_NAME"] = "Café & Résumé 日本語"
        update_config(config)

        # Load and verify
        loaded = load_config()
        assert loaded.__pydantic_extra__["CMS_CUSTOM_SITE_NAME"] == "Café & Résumé 日本語"

    def test_config_with_special_characters(self, tmp_project):
        """Test handling special characters in config values."""
        config = load_config()
        if not hasattr(config, "__pydantic_extra__"):
            config.__pydantic_extra__ = {}

        # Add value with special chars
        config.__pydantic_extra__["ANALYTICS_CUSTOM_URL"] = (
            "https://example.com/path?foo=bar&baz=qux"
        )
        update_config(config)

        loaded = load_config()
        assert (
            loaded.__pydantic_extra__["ANALYTICS_CUSTOM_URL"]
            == "https://example.com/path?foo=bar&baz=qux"
        )

    def test_config_with_very_long_values(self, tmp_project):
        """Test handling very long config values."""
        config = load_config()
        if not hasattr(config, "__pydantic_extra__"):
            config.__pydantic_extra__ = {}

        # Add very long value (e.g., JWT token)
        long_token = "x" * 10000
        config.__pydantic_extra__["CMS_CUSTOM_TOKEN"] = long_token
        update_config(config)

        loaded = load_config()
        assert loaded.__pydantic_extra__["CMS_CUSTOM_TOKEN"] == long_token
        assert len(loaded.__pydantic_extra__["CMS_CUSTOM_TOKEN"]) == 10000

    def test_config_with_newlines_in_values(self, tmp_project):
        """Test that newlines in values are handled (should not break parsing)."""
        config_file = get_config_file_path()

        # Manually add a value with newline (edge case)
        content = config_file.read_text()
        # This shouldn't happen in normal usage, but test robustness
        config_file.write_text(content + '\nCMS_TEST_KEY="value\nwith\nnewlines"\n')

        # Should still load without crashing
        load_config()  # Just verify it doesn't crash
        # The newline handling depends on implementation
        # At minimum, it shouldn't crash

    def test_config_with_equals_in_value(self, tmp_project):
        """Test handling equals sign in config values."""
        config_file = get_config_file_path()

        # Add a value with equals sign (e.g., base64)
        content = config_file.read_text()
        config_file.write_text(content + '\nCMS_TEST_BASE64="SGVsbG8=World="\n')

        config = load_config()
        # Should take everything after first = as value
        assert config.__pydantic_extra__.get("CMS_TEST_BASE64") == "SGVsbG8=World="

    def test_config_file_not_found_error_message(self, tmp_path):
        """Test error message when config file doesn't exist."""
        import os

        os.chdir(tmp_path)

        with pytest.raises(FileNotFoundError) as exc_info:
            load_config()

        error_msg = str(exc_info.value)
        assert "Kurt configuration file not found" in error_msg
        assert "kurt init" in error_msg

    def test_malformed_line_ignored(self, tmp_project):
        """Test that lines without = are ignored."""
        config_file = get_config_file_path()

        content = config_file.read_text()
        config_file.write_text(content + "\nMALFORMED_LINE_NO_EQUALS\n")

        # Should load without error, ignoring malformed line
        config = load_config()
        assert config.PATH_DB == ".kurt/kurt.sqlite"


class TestConfigValidation:
    """Test config validation and type handling."""

    def test_path_resolution_absolute(self, tmp_project):
        """Test that absolute paths are preserved."""
        config = load_config()
        config.PATH_DB = "/absolute/path/to/db.sqlite"
        update_config(config)

        loaded = load_config()
        assert loaded.get_absolute_db_path() == Path("/absolute/path/to/db.sqlite")

    def test_path_resolution_relative(self, tmp_project):
        """Test that relative paths are resolved relative to config file."""
        config = load_config()
        config.PATH_DB = "data/db.sqlite"
        update_config(config)

        loaded = load_config()
        expected = get_config_file_path().parent / "data" / "db.sqlite"
        assert loaded.get_absolute_db_path() == expected

    def test_get_db_directory(self, tmp_project):
        """Test getting DB directory path."""
        config = load_config()
        db_dir = config.get_db_directory()
        expected = get_config_file_path().parent / ".kurt"
        assert db_dir == expected

    def test_all_path_helpers(self, tmp_project):
        """Test all path helper methods."""
        config = load_config()

        # Test sources path
        sources_path = config.get_absolute_sources_path()
        expected = get_config_file_path().parent / "sources"
        assert sources_path == expected

        # Test projects path
        projects_path = config.get_absolute_projects_path()
        expected = get_config_file_path().parent / "projects"
        assert projects_path == expected

        # Test rules path
        rules_path = config.get_absolute_rules_path()
        expected = get_config_file_path().parent / "rules"
        assert rules_path == expected


class TestValidateConfig:
    """Test configuration validation."""

    def test_validate_config_all_valid(self, tmp_project):
        """Test that validation passes for properly set up project."""
        config = load_config()
        issues = validate_config(config)

        # tmp_project fixture creates directories, so should be valid
        assert len(issues) == 0

    def test_validate_config_missing_directories(self, tmp_project):
        """Test that validation detects missing directories."""
        config = load_config()

        # Remove directories
        import shutil

        sources_path = config.get_absolute_sources_path()
        if sources_path.exists():
            shutil.rmtree(sources_path)

        issues = validate_config(config)

        # Should have warning about missing sources directory
        assert len(issues) > 0
        assert any("sources" in issue.lower() for issue in issues)

    def test_validate_config_invalid_llm_model(self, tmp_project):
        """Test validation of LLM model format."""
        config = load_config()
        config.INDEXING_LLM_MODEL = "invalid-model-name"

        issues = validate_config(config)

        # Should complain about model format
        assert len(issues) > 0
        assert any("provider/model" in issue for issue in issues)

    def test_validate_config_invalid_fetch_engine(self, tmp_project):
        """Test validation of fetch engine."""
        config = load_config()
        config.INGESTION_FETCH_ENGINE = "invalid_engine"

        issues = validate_config(config)

        # Should complain about invalid engine
        assert len(issues) > 0
        assert any("trafilatura" in issue or "firecrawl" in issue for issue in issues)

    def test_validate_config_empty_llm_model(self, tmp_project):
        """Test validation catches empty LLM model."""
        config = load_config()
        config.INDEXING_LLM_MODEL = ""

        issues = validate_config(config)

        # Should complain about empty model
        assert len(issues) > 0
        assert any("empty" in issue.lower() for issue in issues)
