"""Tests for core configuration (base.py) using real config files."""

from pathlib import Path

import pytest

from kurt.config.base import (
    KurtConfig,
    config_exists,
    create_config,
    get_config_file_path,
    get_config_or_default,
    get_step_config,
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
        config_file = get_config_file_path()
        config_file.unlink()

        assert config_exists() is False

    def test_create_config_default(self, tmp_project):
        """Test creating config with default values."""
        config_file = get_config_file_path()
        config_file.unlink()

        config = create_config()

        assert config.PATH_DB == ".kurt/kurt.sqlite"
        assert config.PATH_SOURCES == "sources"
        assert config.PATH_PROJECTS == "projects"
        assert config.PATH_RULES == "rules"

        assert config_file.exists()

        content = config_file.read_text()
        assert 'PATH_DB=".kurt/kurt.sqlite"' in content
        assert 'PATH_SOURCES="sources"' in content
        assert "TELEMETRY_ENABLED=True" in content

    def test_create_config_custom(self, tmp_project):
        """Test creating config with custom values."""
        config_file = get_config_file_path()
        config_file.unlink()

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
        config_file = get_config_file_path()
        config_file.unlink()

        with pytest.raises(FileNotFoundError) as exc_info:
            load_config()

        assert "Kurt configuration file not found" in str(exc_info.value)
        assert "Run 'kurt init' to initialize a Kurt project" in str(exc_info.value)

    def test_load_config_with_comments(self, tmp_project):
        """Test loading config ignores comments and empty lines."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write("\n# This is a comment\n")
            f.write("\n")
            f.write("# Another comment\n")

        config = load_config()
        assert isinstance(config, KurtConfig)

    def test_load_config_with_extra_fields(self, tmp_project):
        """Test loading config with integration extra fields."""
        config_file = get_config_file_path()

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
        config_file = get_config_file_path()
        config_file.unlink()

        config = get_config_or_default()

        assert isinstance(config, KurtConfig)
        assert config.PATH_DB == ".kurt/kurt.sqlite"
        assert not config_file.exists()

    def test_update_config_basic_fields(self, tmp_project):
        """Test updating config with basic fields."""
        config = load_config()
        config.PATH_DB = ".data/new.db"
        config.INDEXING_LLM_MODEL = "anthropic/claude-3-5-sonnet-20241022"

        update_config(config)

        loaded = load_config()
        assert loaded.PATH_DB == ".data/new.db"
        assert loaded.INDEXING_LLM_MODEL == "anthropic/claude-3-5-sonnet-20241022"

    def test_update_config_preserves_extra_fields(self, tmp_project):
        """Test that update_config preserves extra fields from integrations."""
        config_file = get_config_file_path()
        with open(config_file, "a") as f:
            f.write('\nANALYTICS_POSTHOG_API_KEY="phx_existing"\n')
            f.write('CMS_SANITY_PROD_PROJECT_ID="sanity_existing"\n')

        config = load_config()
        config.PATH_DB = ".data/updated.db"
        update_config(config)

        loaded = load_config()
        assert loaded.PATH_DB == ".data/updated.db"
        assert "ANALYTICS_POSTHOG_API_KEY" in loaded.__pydantic_extra__
        assert loaded.__pydantic_extra__["ANALYTICS_POSTHOG_API_KEY"] == "phx_existing"
        assert "CMS_SANITY_PROD_PROJECT_ID" in loaded.__pydantic_extra__
        assert loaded.__pydantic_extra__["CMS_SANITY_PROD_PROJECT_ID"] == "sanity_existing"


class TestBooleanTypeHandling:
    """Test boolean type handling in config save/load cycle."""

    def test_telemetry_enabled_true_roundtrip(self, tmp_project):
        """Test saving and loading TELEMETRY_ENABLED=True."""
        config = load_config()
        config.TELEMETRY_ENABLED = True
        update_config(config)

        content = get_config_file_path().read_text()
        assert "TELEMETRY_ENABLED=True" in content
        assert 'TELEMETRY_ENABLED="True"' not in content

        loaded = load_config()
        assert loaded.TELEMETRY_ENABLED is True
        assert isinstance(loaded.TELEMETRY_ENABLED, bool)

    def test_telemetry_enabled_false_roundtrip(self, tmp_project):
        """Test saving and loading TELEMETRY_ENABLED=False."""
        config = load_config()
        config.TELEMETRY_ENABLED = False
        update_config(config)

        content = get_config_file_path().read_text()
        assert "TELEMETRY_ENABLED=False" in content

        loaded = load_config()
        assert loaded.TELEMETRY_ENABLED is False
        assert isinstance(loaded.TELEMETRY_ENABLED, bool)

    def test_boolean_string_variations(self, tmp_project):
        """Test loading boolean from various string representations."""
        config_file = get_config_file_path()

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

        set_telemetry("true")
        loaded = load_config()
        assert loaded.TELEMETRY_ENABLED is True

        set_telemetry("1")
        loaded = load_config()
        assert loaded.TELEMETRY_ENABLED is True

        set_telemetry("yes")
        loaded = load_config()
        assert loaded.TELEMETRY_ENABLED is True

        set_telemetry("false")
        loaded = load_config()
        assert loaded.TELEMETRY_ENABLED is False

        set_telemetry("0")
        loaded = load_config()
        assert loaded.TELEMETRY_ENABLED is False


class TestValidateConfig:
    """Test configuration validation."""

    def test_validate_config_all_valid(self, tmp_project):
        """Test that validation passes for properly set up project."""
        config = load_config()
        issues = validate_config(config)

        assert len(issues) == 0

    def test_validate_config_missing_directories(self, tmp_project):
        """Test that validation detects missing directories."""
        config = load_config()

        import shutil

        sources_path = config.get_absolute_sources_path()
        if sources_path.exists():
            shutil.rmtree(sources_path)

        issues = validate_config(config)

        assert len(issues) > 0
        assert any("sources" in issue.lower() for issue in issues)

    def test_validate_config_invalid_llm_model(self, tmp_project):
        """Test validation of LLM model format."""
        config = load_config()
        config.INDEXING_LLM_MODEL = "invalid-model-name"

        issues = validate_config(config)

        assert len(issues) > 0
        assert any("provider/model" in issue for issue in issues)

    def test_validate_config_invalid_fetch_engine(self, tmp_project):
        """Test validation of fetch engine."""
        config = load_config()
        config.INGESTION_FETCH_ENGINE = "invalid_engine"

        issues = validate_config(config)

        assert len(issues) > 0
        assert any("trafilatura" in issue or "firecrawl" in issue for issue in issues)


class TestDotNotationConfig:
    """Test dot notation for module-specific configuration."""

    def test_load_config_with_dot_notation(self, tmp_project):
        """Test loading config with dot notation keys."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write('\nINDEXING.SECTION_EXTRACTIONS.LLM_MODEL="anthropic/claude-3-5-sonnet"\n')
            f.write("INDEXING.ENTITY_CLUSTERING.EPS=0.25\n")
            f.write("INDEXING.ENTITY_CLUSTERING.MIN_SAMPLES=2\n")

        config = load_config()

        assert "INDEXING.SECTION_EXTRACTIONS.LLM_MODEL" in config.__pydantic_extra__
        assert (
            config.__pydantic_extra__["INDEXING.SECTION_EXTRACTIONS.LLM_MODEL"]
            == "anthropic/claude-3-5-sonnet"
        )
        assert config.__pydantic_extra__["INDEXING.ENTITY_CLUSTERING.EPS"] == "0.25"
        assert config.__pydantic_extra__["INDEXING.ENTITY_CLUSTERING.MIN_SAMPLES"] == "2"

    def test_get_step_config_returns_step_specific(self, tmp_project):
        """Test get_step_config returns step-specific value when set."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write('\nINDEXING.SECTION_EXTRACTIONS.LLM_MODEL="anthropic/claude-3-5-sonnet"\n')

        config = load_config()

        result = get_step_config(
            config,
            "INDEXING",
            "SECTION_EXTRACTIONS",
            "LLM_MODEL",
            fallback_key="INDEXING_LLM_MODEL",
            default="default/model",
        )

        assert result == "anthropic/claude-3-5-sonnet"

    def test_get_step_config_falls_back_to_global(self, tmp_project):
        """Test get_step_config falls back to global config when step-specific not set."""
        config = load_config()

        result = get_step_config(
            config,
            "INDEXING",
            "SECTION_EXTRACTIONS",
            "LLM_MODEL",
            fallback_key="INDEXING_LLM_MODEL",
            default="default/model",
        )

        assert result == config.INDEXING_LLM_MODEL

    def test_get_step_config_falls_back_to_default(self, tmp_project):
        """Test get_step_config falls back to default when nothing set."""
        config = load_config()

        result = get_step_config(
            config,
            "INDEXING",
            "SECTION_EXTRACTIONS",
            "CUSTOM_PARAM",
            fallback_key=None,
            default="my_default",
        )

        assert result == "my_default"

    def test_get_step_config_workflow_module(self, tmp_project):
        """Test get_step_config with workflow module like MAP or FETCH."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write("MAP.MAX_PAGES=500\n")
            f.write("MAP.DISCOVERY.MAX_DEPTH=3\n")
            f.write("FETCH.ENGINE=firecrawl\n")

        config = load_config()

        # Module-level: MAP.MAX_PAGES
        result = get_step_config(config, "MAP", None, "MAX_PAGES", default=1000)
        assert result == "500"

        # Step-level: MAP.DISCOVERY.MAX_DEPTH
        result = get_step_config(config, "MAP", "DISCOVERY", "MAX_DEPTH", default=5)
        assert result == "3"

        # Module-level: FETCH.ENGINE
        result = get_step_config(config, "FETCH", None, "ENGINE", default="trafilatura")
        assert result == "firecrawl"

    def test_update_config_preserves_dot_notation(self, tmp_project):
        """Test that update_config preserves dot notation keys."""
        config_file = get_config_file_path()

        with open(config_file, "a") as f:
            f.write('\nINDEXING.SECTION_EXTRACTIONS.LLM_MODEL="anthropic/claude-3-5-sonnet"\n')
            f.write("INDEXING.ENTITY_CLUSTERING.EPS=0.25\n")

        config = load_config()
        config.PATH_DB = ".data/updated.db"
        update_config(config)

        config = load_config()
        assert config.PATH_DB == ".data/updated.db"
        assert "INDEXING.SECTION_EXTRACTIONS.LLM_MODEL" in config.__pydantic_extra__
        assert (
            config.__pydantic_extra__["INDEXING.SECTION_EXTRACTIONS.LLM_MODEL"]
            == "anthropic/claude-3-5-sonnet"
        )
