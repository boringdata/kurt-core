"""
Unit tests for tool context loading.

Tests:
- Settings loading from TOML files
- Environment variable precedence
- Config merging
- ToolContext initialization
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kurt.tools.core.context import (
    DoltSettings,
    FetchSettings,
    LLMClient,
    LLMSettings,
    Settings,
    StorageSettings,
    _apply_env_overrides,
    _get_project_config_path,
    _get_user_config_path,
    _init_dolt_db,
    _init_http_client,
    _load_toml,
    _merge_configs,
    load_settings,
    load_tool_context,
    validate_settings,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def tmp_project(tmp_path: Path, monkeypatch):
    """Create a temp project directory and change cwd to it."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)


@pytest.fixture
def clean_env(monkeypatch):
    """Clear relevant environment variables."""
    env_vars = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "TAVILY_API_KEY",
        "FIRECRAWL_API_KEY",
        "KURT_LLM_MODEL",
        "KURT_FETCH_ENGINE",
        "KURT_FETCH_TIMEOUT",
        "KURT_CONTENT_DIR",
        "KURT_DOLT_MODE",
        "KURT_DOLT_PATH",
        "KURT_DOLT_SERVER_URL",
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)
    yield


# ============================================================================
# Settings Model Tests
# ============================================================================


class TestSettingsModels:
    """Test settings Pydantic models."""

    def test_llm_settings_defaults(self):
        """LLMSettings has correct defaults."""
        settings = LLMSettings()
        assert settings.openai_api_key is None
        assert settings.anthropic_api_key is None
        assert settings.default_model == "gpt-4o-mini"

    def test_fetch_settings_defaults(self):
        """FetchSettings has correct defaults."""
        settings = FetchSettings()
        assert settings.default_engine == "trafilatura"
        assert settings.tavily_api_key is None
        assert settings.firecrawl_api_key is None
        assert settings.timeout == 30

    def test_storage_settings_defaults(self):
        """StorageSettings has correct defaults."""
        settings = StorageSettings()
        assert settings.content_dir == "./content"

    def test_dolt_settings_defaults(self):
        """DoltSettings has correct defaults."""
        settings = DoltSettings()
        assert settings.mode == "embedded"
        assert settings.path == ".dolt"
        assert settings.server_url == "localhost:3306"
        assert settings.user == "root"
        assert settings.password == ""

    def test_settings_combined_defaults(self):
        """Settings combines all sub-models with defaults."""
        settings = Settings()
        assert settings.llm.default_model == "gpt-4o-mini"
        assert settings.fetch.default_engine == "trafilatura"
        assert settings.storage.content_dir == "./content"
        assert settings.dolt.mode == "embedded"


# ============================================================================
# TOML Loading Tests
# ============================================================================


class TestTomlLoading:
    """Test TOML file loading."""

    def test_load_toml_nonexistent(self, tmp_path):
        """_load_toml returns empty dict for nonexistent file."""
        result = _load_toml(tmp_path / "nonexistent.toml")
        assert result == {}

    def test_load_toml_valid(self, tmp_path):
        """_load_toml loads valid TOML file."""
        toml_file = tmp_path / "test.toml"
        toml_file.write_text(
            """
[llm]
openai_api_key = "sk-test123"
default_model = "gpt-4"

[fetch]
default_engine = "httpx"
timeout = 60
"""
        )
        result = _load_toml(toml_file)
        assert result["llm"]["openai_api_key"] == "sk-test123"
        assert result["llm"]["default_model"] == "gpt-4"
        assert result["fetch"]["default_engine"] == "httpx"
        assert result["fetch"]["timeout"] == 60

    def test_load_toml_empty(self, tmp_path):
        """_load_toml returns empty dict for empty file."""
        toml_file = tmp_path / "empty.toml"
        toml_file.write_text("")
        result = _load_toml(toml_file)
        assert result == {}


# ============================================================================
# Config Path Tests
# ============================================================================


class TestConfigPaths:
    """Test config path resolution."""

    def test_user_config_path(self):
        """_get_user_config_path returns ~/.kurt/config.toml."""
        path = _get_user_config_path()
        assert path == Path.home() / ".kurt" / "config.toml"

    def test_project_config_path_default(self, tmp_project):
        """_get_project_config_path uses cwd by default."""
        path = _get_project_config_path()
        assert path == tmp_project / "kurt.toml"

    def test_project_config_path_custom(self, tmp_path):
        """_get_project_config_path uses provided path."""
        path = _get_project_config_path(tmp_path / "myproject")
        assert path == tmp_path / "myproject" / "kurt.toml"


# ============================================================================
# Environment Override Tests
# ============================================================================


class TestEnvOverrides:
    """Test environment variable overrides."""

    def test_apply_env_overrides_empty(self, clean_env):
        """_apply_env_overrides with no env vars returns input."""
        input_dict = {"llm": {"default_model": "original"}}
        result = _apply_env_overrides(input_dict)
        assert result["llm"]["default_model"] == "original"

    def test_apply_env_overrides_openai_key(self, clean_env, monkeypatch):
        """OPENAI_API_KEY env var overrides llm.openai_api_key."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
        result = _apply_env_overrides({})
        assert result["llm"]["openai_api_key"] == "sk-from-env"

    def test_apply_env_overrides_anthropic_key(self, clean_env, monkeypatch):
        """ANTHROPIC_API_KEY env var overrides llm.anthropic_api_key."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-from-env")
        result = _apply_env_overrides({})
        assert result["llm"]["anthropic_api_key"] == "sk-ant-from-env"

    def test_apply_env_overrides_content_dir(self, clean_env, monkeypatch):
        """KURT_CONTENT_DIR env var overrides storage.content_dir."""
        monkeypatch.setenv("KURT_CONTENT_DIR", "/custom/content")
        result = _apply_env_overrides({})
        assert result["storage"]["content_dir"] == "/custom/content"

    def test_apply_env_overrides_dolt_mode(self, clean_env, monkeypatch):
        """KURT_DOLT_MODE env var overrides dolt.mode."""
        monkeypatch.setenv("KURT_DOLT_MODE", "server")
        result = _apply_env_overrides({})
        assert result["dolt"]["mode"] == "server"

    def test_apply_env_overrides_fetch_timeout_int(self, clean_env, monkeypatch):
        """KURT_FETCH_TIMEOUT is converted to int."""
        monkeypatch.setenv("KURT_FETCH_TIMEOUT", "120")
        result = _apply_env_overrides({})
        assert result["fetch"]["timeout"] == 120


# ============================================================================
# Config Merge Tests
# ============================================================================


class TestConfigMerge:
    """Test config merging."""

    def test_merge_empty_configs(self):
        """_merge_configs with empty dicts returns empty dict."""
        result = _merge_configs({}, {})
        assert result == {}

    def test_merge_flat_configs(self):
        """_merge_configs merges flat dicts with later taking precedence."""
        first = {"a": 1, "b": 2}
        second = {"b": 3, "c": 4}
        result = _merge_configs(first, second)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_nested_configs(self):
        """_merge_configs deep merges nested dicts."""
        first = {"llm": {"model": "gpt-4", "temperature": 0.5}}
        second = {"llm": {"model": "gpt-4o"}}
        result = _merge_configs(first, second)
        assert result == {"llm": {"model": "gpt-4o", "temperature": 0.5}}

    def test_merge_three_configs(self):
        """_merge_configs handles multiple configs."""
        first = {"a": 1}
        second = {"a": 2, "b": 2}
        third = {"c": 3}
        result = _merge_configs(first, second, third)
        assert result == {"a": 2, "b": 2, "c": 3}


# ============================================================================
# Load Settings Tests
# ============================================================================


class TestLoadSettings:
    """Test load_settings function."""

    def test_load_settings_defaults(self, tmp_project, clean_env):
        """load_settings returns defaults when no config files exist."""
        settings = load_settings()
        assert settings.llm.default_model == "gpt-4o-mini"
        assert settings.fetch.default_engine == "trafilatura"

    def test_load_settings_from_project(self, tmp_project, clean_env):
        """load_settings loads from project kurt.toml."""
        config_file = tmp_project / "kurt.toml"
        config_file.write_text(
            """
[llm]
default_model = "custom-model"

[fetch]
default_engine = "httpx"
"""
        )
        settings = load_settings()
        assert settings.llm.default_model == "custom-model"
        assert settings.fetch.default_engine == "httpx"

    def test_load_settings_env_overrides_file(self, tmp_project, clean_env, monkeypatch):
        """Environment variables override file config."""
        config_file = tmp_project / "kurt.toml"
        config_file.write_text(
            """
[llm]
default_model = "from-file"
"""
        )
        monkeypatch.setenv("KURT_LLM_MODEL", "from-env")
        settings = load_settings()
        assert settings.llm.default_model == "from-env"

    def test_load_settings_custom_path(self, tmp_path, clean_env):
        """load_settings uses custom project path."""
        project_dir = tmp_path / "custom-project"
        project_dir.mkdir()
        config_file = project_dir / "kurt.toml"
        config_file.write_text(
            """
[storage]
content_dir = "/custom/path"
"""
        )
        settings = load_settings(project_dir)
        assert settings.storage.content_dir == "/custom/path"


# ============================================================================
# LLMClient Tests
# ============================================================================


class TestLLMClient:
    """Test LLMClient dataclass."""

    def test_llm_client_defaults(self):
        """LLMClient has correct defaults."""
        client = LLMClient()
        assert client.openai_api_key is None
        assert client.anthropic_api_key is None
        assert client.default_model == "gpt-4o-mini"

    def test_llm_client_from_settings(self):
        """LLMClient.from_settings creates client from settings."""
        settings = LLMSettings(
            openai_api_key="sk-test",
            anthropic_api_key="sk-ant-test",
            default_model="gpt-4",
        )
        client = LLMClient.from_settings(settings)
        assert client.openai_api_key == "sk-test"
        assert client.anthropic_api_key == "sk-ant-test"
        assert client.default_model == "gpt-4"


# ============================================================================
# Init Functions Tests
# ============================================================================


class TestInitFunctions:
    """Test initialization helper functions."""

    def test_init_http_client(self):
        """_init_http_client creates AsyncClient."""
        settings = FetchSettings(timeout=60)
        client = _init_http_client(settings)
        assert client is not None
        # Clean up
        import asyncio
        asyncio.run(client.aclose())

    def test_init_dolt_db_embedded(self, tmp_path):
        """_init_dolt_db creates DoltDB in embedded mode."""
        settings = DoltSettings(mode="embedded", path=".dolt")

        # Mock DoltDB to avoid actual dolt CLI check
        with patch("kurt.db.dolt.DoltDB") as mock_dolt:
            mock_instance = MagicMock()
            mock_dolt.return_value = mock_instance

            result = _init_dolt_db(settings, tmp_path)

            assert result == mock_instance
            # DoltDB expects repo root path (parent of .dolt), not .dolt itself
            mock_dolt.assert_called_once_with(
                path=tmp_path,
                mode="embedded",
                host="localhost",
                port=3306,
                user="root",
                password="",
            )

    def test_init_dolt_db_server(self, tmp_path):
        """_init_dolt_db parses server URL correctly."""
        settings = DoltSettings(
            mode="server",
            path=".dolt",
            server_url="myhost:3307",
            user="myuser",
            password="mypass",
        )

        with patch("kurt.db.dolt.DoltDB") as mock_dolt:
            mock_instance = MagicMock()
            mock_dolt.return_value = mock_instance

            _init_dolt_db(settings, tmp_path)

            # DoltDB expects repo root path (parent of .dolt), not .dolt itself
            mock_dolt.assert_called_once_with(
                path=tmp_path,
                mode="server",
                host="myhost",
                port=3307,
                user="myuser",
                password="mypass",
            )


# ============================================================================
# Load ToolContext Tests
# ============================================================================


class TestLoadToolContext:
    """Test load_tool_context function."""

    def test_load_tool_context_minimal(self, tmp_project, clean_env):
        """load_tool_context works with no init flags."""
        context = load_tool_context(
            init_db=False,
            init_http=False,
            init_llm=False,
        )
        assert context.db is None
        assert context.http is None
        assert context.llm is None
        assert context.settings is not None
        assert context.tools is not None

    def test_load_tool_context_with_http(self, tmp_project, clean_env):
        """load_tool_context initializes HTTP client."""
        context = load_tool_context(
            init_db=False,
            init_http=True,
            init_llm=False,
        )
        assert context.http is not None
        # Clean up
        import asyncio
        asyncio.run(context.http.aclose())

    def test_load_tool_context_with_llm(self, tmp_project, clean_env, monkeypatch):
        """load_tool_context initializes LLM config."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        context = load_tool_context(
            init_db=False,
            init_http=False,
            init_llm=True,
        )
        assert context.llm is not None
        assert context.llm["openai_api_key"] == "sk-test-key"

    def test_load_tool_context_settings_in_context(self, tmp_project, clean_env):
        """load_tool_context puts settings dict in context.settings."""
        context = load_tool_context(
            init_db=False,
            init_http=False,
            init_llm=False,
        )
        assert "llm" in context.settings
        assert "fetch" in context.settings
        assert "storage" in context.settings
        assert "dolt" in context.settings

    def test_load_tool_context_tools_registry(self, tmp_project, clean_env):
        """load_tool_context includes TOOLS registry."""
        context = load_tool_context(
            init_db=False,
            init_http=False,
            init_llm=False,
        )
        assert isinstance(context.tools, dict)


# ============================================================================
# Validation Tests
# ============================================================================


class TestValidation:
    """Test settings validation."""

    def test_validate_settings_valid(self):
        """validate_settings returns empty list for valid config."""
        settings = Settings()
        issues = validate_settings(settings)
        assert issues == []

    def test_validate_settings_tavily_missing_key(self):
        """validate_settings catches missing tavily key."""
        settings = Settings(
            fetch=FetchSettings(default_engine="tavily")
        )
        issues = validate_settings(settings)
        assert len(issues) == 1
        assert "TAVILY_API_KEY" in issues[0]

    def test_validate_settings_firecrawl_missing_key(self):
        """validate_settings catches missing firecrawl key."""
        settings = Settings(
            fetch=FetchSettings(default_engine="firecrawl")
        )
        issues = validate_settings(settings)
        assert len(issues) == 1
        assert "FIRECRAWL_API_KEY" in issues[0]

    def test_validate_settings_with_api_keys(self):
        """validate_settings passes with API keys set."""
        settings = Settings(
            fetch=FetchSettings(
                default_engine="tavily",
                tavily_api_key="tvly-test",
            )
        )
        issues = validate_settings(settings)
        assert issues == []


# ============================================================================
# Precedence Integration Tests
# ============================================================================


class TestPrecedence:
    """Test configuration precedence."""

    def test_precedence_env_over_project(self, tmp_project, clean_env, monkeypatch):
        """Environment variables take precedence over project config."""
        # Create project config
        (tmp_project / "kurt.toml").write_text(
            """
[llm]
openai_api_key = "from-project"
default_model = "from-project"
"""
        )
        # Set env var for API key only
        monkeypatch.setenv("OPENAI_API_KEY", "from-env")

        settings = load_settings()

        # API key comes from env
        assert settings.llm.openai_api_key == "from-env"
        # Model comes from project file
        assert settings.llm.default_model == "from-project"

    def test_precedence_project_over_user(self, tmp_project, clean_env, monkeypatch, tmp_path):
        """Project config takes precedence over user config."""
        # Create user config
        user_config_dir = tmp_path / "home" / ".kurt"
        user_config_dir.mkdir(parents=True)
        user_config = user_config_dir / "config.toml"
        user_config.write_text(
            """
[llm]
default_model = "from-user"
"""
        )

        # Create project config
        (tmp_project / "kurt.toml").write_text(
            """
[llm]
default_model = "from-project"
"""
        )

        # Patch user config path
        with patch("kurt.tools.core.context._get_user_config_path", return_value=user_config):
            settings = load_settings()

        assert settings.llm.default_model == "from-project"
