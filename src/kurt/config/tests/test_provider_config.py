"""Tests for provider configuration resolution."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel

from kurt.config.provider_config import (
    ProviderConfigResolver,
    get_provider_config_resolver,
)

# ---------------------------------------------------------------------------
# Test config models
# ---------------------------------------------------------------------------


class NotionConfig(BaseModel):
    """Example provider config for testing."""

    include_children: bool = True
    max_depth: int = 5
    timeout: int = 30


class SimpleConfig(BaseModel):
    """Minimal config model."""

    api_key: str = ""
    retries: int = 3


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_resolver():
    """Reset the singleton resolver before each test."""
    resolver = ProviderConfigResolver()
    resolver.reset()
    yield
    resolver.reset()


@pytest.fixture
def project_dir(tmp_path, monkeypatch):
    """Create a temporary project with kurt.toml."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def user_config_dir(tmp_path, monkeypatch):
    """Create a temporary user home with .kurt/config.toml."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    return home


def write_project_toml(project_dir: Path, content: str) -> Path:
    """Write a kurt.toml file in the project directory."""
    config_file = project_dir / "kurt.toml"
    config_file.write_text(content)
    return config_file


def write_user_toml(home_dir: Path, content: str) -> Path:
    """Write ~/.kurt/config.toml."""
    config_dir = home_dir / ".kurt"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.toml"
    config_file.write_text(content)
    return config_file


# ---------------------------------------------------------------------------
# Basic resolution
# ---------------------------------------------------------------------------


class TestResolveDefaults:
    def test_returns_defaults_when_no_config(self, project_dir, user_config_dir):
        """When no config files exist, returns model defaults."""
        resolver = get_provider_config_resolver()
        config = resolver.resolve("fetch", "notion", NotionConfig)

        assert config.include_children is True
        assert config.max_depth == 5
        assert config.timeout == 30

    def test_returns_empty_dict_without_model(self, project_dir, user_config_dir):
        """Without config_model, returns empty dict when no config files."""
        resolver = get_provider_config_resolver()
        config = resolver.resolve("fetch", "notion")

        assert config == {}

    def test_cli_overrides_defaults(self, project_dir, user_config_dir):
        """CLI overrides take precedence over defaults."""
        resolver = get_provider_config_resolver()
        config = resolver.resolve(
            "fetch",
            "notion",
            NotionConfig,
            cli_overrides={"max_depth": 10, "timeout": 120},
        )

        assert config.max_depth == 10
        assert config.timeout == 120
        assert config.include_children is True  # Default preserved

    def test_cli_none_values_ignored(self, project_dir, user_config_dir):
        """None values in CLI overrides are ignored."""
        resolver = get_provider_config_resolver()
        config = resolver.resolve(
            "fetch",
            "notion",
            NotionConfig,
            cli_overrides={"max_depth": None, "timeout": 60},
        )

        assert config.max_depth == 5  # Default, not None
        assert config.timeout == 60


# ---------------------------------------------------------------------------
# Project config
# ---------------------------------------------------------------------------


class TestProjectConfig:
    def test_reads_provider_section(self, project_dir, user_config_dir):
        """Reads [tool.fetch.providers.notion] section."""
        write_project_toml(
            project_dir,
            """
[tool.fetch.providers.notion]
include_children = false
max_depth = 3
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve("fetch", "notion", NotionConfig)

        assert config.include_children is False
        assert config.max_depth == 3
        assert config.timeout == 30  # Default

    def test_tool_level_settings_as_base(self, project_dir, user_config_dir):
        """Tool-level [tool.fetch] settings provide base for all providers."""
        write_project_toml(
            project_dir,
            """
[tool.fetch]
timeout = 60
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve("fetch", "notion", NotionConfig)

        assert config.timeout == 60  # From tool-level
        assert config.max_depth == 5  # Default

    def test_provider_overrides_tool_level(self, project_dir, user_config_dir):
        """Provider section overrides tool-level settings."""
        write_project_toml(
            project_dir,
            """
[tool.fetch]
timeout = 60

[tool.fetch.providers.notion]
timeout = 120
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve("fetch", "notion", NotionConfig)

        assert config.timeout == 120  # Provider-level wins

    def test_cli_overrides_project(self, project_dir, user_config_dir):
        """CLI overrides take precedence over project config."""
        write_project_toml(
            project_dir,
            """
[tool.fetch.providers.notion]
max_depth = 3
timeout = 60
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve(
            "fetch",
            "notion",
            NotionConfig,
            cli_overrides={"timeout": 10},
        )

        assert config.max_depth == 3  # From project
        assert config.timeout == 10  # CLI wins

    def test_explicit_project_root(self, tmp_path, user_config_dir):
        """Can pass explicit project_root to bypass CWD search."""
        other_dir = tmp_path / "other_project"
        other_dir.mkdir()
        write_project_toml(
            other_dir,
            """
[tool.fetch.providers.notion]
max_depth = 7
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve(
            "fetch",
            "notion",
            NotionConfig,
            project_root=other_dir,
        )

        assert config.max_depth == 7


# ---------------------------------------------------------------------------
# User config
# ---------------------------------------------------------------------------


class TestUserConfig:
    def test_reads_user_config(self, project_dir, user_config_dir):
        """Reads provider config from ~/.kurt/config.toml."""
        write_user_toml(
            user_config_dir,
            """
[tool.fetch.providers.notion]
include_children = false
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve("fetch", "notion", NotionConfig)

        assert config.include_children is False

    def test_project_overrides_user(self, project_dir, user_config_dir):
        """Project config overrides user config."""
        write_user_toml(
            user_config_dir,
            """
[tool.fetch.providers.notion]
max_depth = 10
timeout = 90
""",
        )

        write_project_toml(
            project_dir,
            """
[tool.fetch.providers.notion]
max_depth = 3
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve("fetch", "notion", NotionConfig)

        assert config.max_depth == 3  # Project wins
        assert config.timeout == 90  # User (not overridden by project)


# ---------------------------------------------------------------------------
# Full priority chain
# ---------------------------------------------------------------------------


class TestFullPriorityChain:
    def test_full_chain(self, project_dir, user_config_dir):
        """CLI > project > user > defaults."""
        write_user_toml(
            user_config_dir,
            """
[tool.fetch]
timeout = 45

[tool.fetch.providers.notion]
include_children = false
max_depth = 10
timeout = 90
""",
        )

        write_project_toml(
            project_dir,
            """
[tool.fetch.providers.notion]
max_depth = 3
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve(
            "fetch",
            "notion",
            NotionConfig,
            cli_overrides={"timeout": 5},
        )

        assert config.include_children is False  # User config
        assert config.max_depth == 3  # Project overrides user
        assert config.timeout == 5  # CLI overrides everything


# ---------------------------------------------------------------------------
# Tool-level config
# ---------------------------------------------------------------------------


class TestToolConfig:
    def test_resolve_tool_config(self, project_dir, user_config_dir):
        """resolve_tool_config returns tool-level settings."""
        write_project_toml(
            project_dir,
            """
[tool.fetch]
provider = "trafilatura"
timeout = 30
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve_tool_config("fetch")

        assert config["provider"] == "trafilatura"
        assert config["timeout"] == 30

    def test_tool_config_merges_user_and_project(self, project_dir, user_config_dir):
        """Tool config merges user and project, project wins."""
        write_user_toml(
            user_config_dir,
            """
[tool.fetch]
timeout = 60
retries = 3
""",
        )

        write_project_toml(
            project_dir,
            """
[tool.fetch]
timeout = 30
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve_tool_config("fetch")

        assert config["timeout"] == 30  # Project wins
        assert config["retries"] == 3  # User (not in project)


# ---------------------------------------------------------------------------
# Without config model (dict mode)
# ---------------------------------------------------------------------------


class TestDictMode:
    def test_returns_dict_without_model(self, project_dir, user_config_dir):
        """Without config_model, returns merged dict."""
        write_project_toml(
            project_dir,
            """
[tool.fetch.providers.notion]
include_children = false
max_depth = 3
custom_setting = "hello"
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve("fetch", "notion")

        assert isinstance(config, dict)
        assert config["include_children"] is False
        assert config["max_depth"] == 3
        assert config["custom_setting"] == "hello"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_unknown_provider_returns_defaults(self, project_dir, user_config_dir):
        """Unknown provider name returns only defaults."""
        write_project_toml(
            project_dir,
            """
[tool.fetch.providers.notion]
max_depth = 3
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve("fetch", "unknown-provider", NotionConfig)

        assert config.max_depth == 5  # Default, not notion's value

    def test_unknown_tool_returns_defaults(self, project_dir, user_config_dir):
        """Unknown tool name returns only defaults."""
        resolver = get_provider_config_resolver()
        config = resolver.resolve("nonexistent", "anything", NotionConfig)

        assert config.max_depth == 5
        assert config.timeout == 30

    def test_malformed_toml_returns_empty(self, project_dir, user_config_dir):
        """Malformed TOML file is treated as empty."""
        config_file = project_dir / "kurt.toml"
        config_file.write_text("this is [not valid { toml")

        resolver = get_provider_config_resolver()
        config = resolver.resolve("fetch", "notion", NotionConfig)

        assert config.max_depth == 5  # Default

    def test_providers_key_excluded_from_result(self, project_dir, user_config_dir):
        """The 'providers' nested dict is not included in resolved config."""
        write_project_toml(
            project_dir,
            """
[tool.fetch]
timeout = 30

[tool.fetch.providers.notion]
max_depth = 3
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve("fetch", "notion")

        assert "providers" not in config

    def test_singleton_returns_same_instance(self):
        """get_provider_config_resolver returns singleton."""
        a = get_provider_config_resolver()
        b = get_provider_config_resolver()
        assert a is b


# ---------------------------------------------------------------------------
# Reset and caching
# ---------------------------------------------------------------------------


class TestCaching:
    def test_reset_clears_cache(self, project_dir, user_config_dir):
        """After reset, config is re-read from disk."""
        write_project_toml(project_dir, "")

        resolver = get_provider_config_resolver()
        config1 = resolver.resolve("fetch", "notion", NotionConfig)
        assert config1.max_depth == 5  # Default

        # Write new config and reset
        write_project_toml(
            project_dir,
            """
[tool.fetch.providers.notion]
max_depth = 99
""",
        )
        resolver.reset()

        config2 = resolver.resolve("fetch", "notion", NotionConfig)
        assert config2.max_depth == 99  # New value
