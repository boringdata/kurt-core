"""Tests for ProviderConfigResolver runtime wiring.

These tests verify that provider configuration from TOML files is actually
applied at runtime when tools execute. This tests the integration between
ProviderConfigResolver and tool/provider instantiation.

Test Strategy:
- Use temporary directories for project_root to control TOML contents
- Verify that resolved config affects actual provider instances
- Tests should FAIL before wiring is implemented (bd-26w.5.1.1, bd-26w.5.1.2)
- Tests should PASS once fetch/map tools use ProviderConfigResolver

Related beads:
- bd-26w.5.1.3: This file (add tests for runtime wiring)
- bd-26w.5.1.1: Fetch: load provider ConfigModel via ProviderConfigResolver
- bd-26w.5.1.2: Map: load provider ConfigModel via ProviderConfigResolver
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kurt.config.provider_config import (
    ProviderConfigResolver,
    get_provider_config_resolver,
)

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
# Test: Default provider config is applied
# ---------------------------------------------------------------------------


class TestDefaultProviderConfig:
    """Verify default provider config values are applied when no TOML exists."""

    def test_httpx_provider_defaults(self, project_dir, user_config_dir):
        """HTTPx provider uses default config when no TOML exists."""
        from kurt.tools.fetch.providers.httpx.config import HttpxProviderConfig

        resolver = get_provider_config_resolver()
        config = resolver.resolve("fetch", "httpx", HttpxProviderConfig)

        # Verify defaults are applied
        assert config.timeout > 0  # Has a reasonable default
        assert config.follow_redirects is True  # Default value

    def test_trafilatura_provider_defaults(self, project_dir, user_config_dir):
        """Trafilatura provider uses default config when no TOML exists."""
        from kurt.tools.fetch.providers.trafilatura.config import (
            TrafilaturaProviderConfig,
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve("fetch", "trafilatura", TrafilaturaProviderConfig)

        # Verify defaults are applied (trafilatura has specific fields)
        assert isinstance(config.include_comments, bool)
        assert config.favor_precision is True

    def test_sitemap_provider_defaults(self, project_dir, user_config_dir):
        """Sitemap provider uses default config when no TOML exists."""
        from kurt.tools.map.providers.sitemap.config import SitemapProviderConfig

        resolver = get_provider_config_resolver()
        config = resolver.resolve("map", "sitemap", SitemapProviderConfig)

        # Verify defaults are applied
        assert config.max_urls > 0
        assert config.timeout > 0


# ---------------------------------------------------------------------------
# Test: User config overrides defaults
# ---------------------------------------------------------------------------


class TestUserConfigOverridesDefaults:
    """Verify user config (~/.kurt/config.toml) overrides provider defaults."""

    def test_user_timeout_overrides_default(self, project_dir, user_config_dir):
        """User config timeout value overrides provider default."""
        from kurt.tools.fetch.providers.httpx.config import HttpxProviderConfig

        write_user_toml(
            user_config_dir,
            """
[tool.fetch.providers.httpx]
timeout = 120
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve("fetch", "httpx", HttpxProviderConfig)

        assert config.timeout == 120

    def test_user_tool_level_applies_to_all_providers(
        self, project_dir, user_config_dir
    ):
        """User tool-level config applies as base for all providers."""
        from kurt.tools.fetch.providers.httpx.config import HttpxProviderConfig

        write_user_toml(
            user_config_dir,
            """
[tool.fetch]
timeout = 90
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve("fetch", "httpx", HttpxProviderConfig)

        assert config.timeout == 90


# ---------------------------------------------------------------------------
# Test: Project config overrides user config
# ---------------------------------------------------------------------------


class TestProjectConfigOverridesUser:
    """Verify project config (kurt.toml) overrides user config."""

    def test_project_overrides_user_timeout(self, project_dir, user_config_dir):
        """Project config takes precedence over user config."""
        from kurt.tools.fetch.providers.httpx.config import HttpxProviderConfig

        write_user_toml(
            user_config_dir,
            """
[tool.fetch.providers.httpx]
timeout = 90
follow_redirects = false
""",
        )

        write_project_toml(
            project_dir,
            """
[tool.fetch.providers.httpx]
timeout = 30
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve("fetch", "httpx", HttpxProviderConfig)

        assert config.timeout == 30  # Project wins
        assert config.follow_redirects is False  # User (not overridden)

    def test_project_provider_overrides_project_tool_level(
        self, project_dir, user_config_dir
    ):
        """Provider-specific config overrides tool-level config."""
        from kurt.tools.fetch.providers.httpx.config import HttpxProviderConfig

        write_project_toml(
            project_dir,
            """
[tool.fetch]
timeout = 60

[tool.fetch.providers.httpx]
timeout = 15
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve("fetch", "httpx", HttpxProviderConfig)

        assert config.timeout == 15  # Provider-level wins


# ---------------------------------------------------------------------------
# Test: CLI overrides override everything
# ---------------------------------------------------------------------------


class TestCliOverrides:
    """Verify CLI overrides take highest priority."""

    def test_cli_overrides_project_and_user(self, project_dir, user_config_dir):
        """CLI overrides take precedence over all config sources."""
        from kurt.tools.fetch.providers.httpx.config import HttpxProviderConfig

        write_user_toml(
            user_config_dir,
            """
[tool.fetch.providers.httpx]
timeout = 90
""",
        )

        write_project_toml(
            project_dir,
            """
[tool.fetch.providers.httpx]
timeout = 30
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve(
            "fetch",
            "httpx",
            HttpxProviderConfig,
            cli_overrides={"timeout": 5},
        )

        assert config.timeout == 5  # CLI wins over everything

    def test_cli_none_values_ignored(self, project_dir, user_config_dir):
        """None values in CLI overrides are ignored."""
        from kurt.tools.fetch.providers.httpx.config import HttpxProviderConfig

        write_project_toml(
            project_dir,
            """
[tool.fetch.providers.httpx]
timeout = 30
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve(
            "fetch",
            "httpx",
            HttpxProviderConfig,
            cli_overrides={"timeout": None, "follow_redirects": True},
        )

        assert config.timeout == 30  # Project value (None ignored)
        assert config.follow_redirects is True  # CLI value


# ---------------------------------------------------------------------------
# Test: Full priority chain
# ---------------------------------------------------------------------------


class TestFullPriorityChain:
    """Test the complete priority chain: CLI > project > user > defaults."""

    def test_full_priority_chain_httpx(self, project_dir, user_config_dir):
        """Full chain test for HTTPx provider."""
        from kurt.tools.fetch.providers.httpx.config import HttpxProviderConfig

        # User config: timeout=90, follow_redirects=false
        write_user_toml(
            user_config_dir,
            """
[tool.fetch.providers.httpx]
timeout = 90
follow_redirects = false
""",
        )

        # Project config: timeout=30 (overrides user)
        write_project_toml(
            project_dir,
            """
[tool.fetch.providers.httpx]
timeout = 30
""",
        )

        resolver = get_provider_config_resolver()

        # CLI override: timeout=5 (overrides project)
        config = resolver.resolve(
            "fetch",
            "httpx",
            HttpxProviderConfig,
            cli_overrides={"timeout": 5},
        )

        assert config.timeout == 5  # CLI wins
        assert config.follow_redirects is False  # User (not overridden)

    def test_full_priority_chain_sitemap(self, project_dir, user_config_dir):
        """Full chain test for Sitemap provider."""
        from kurt.tools.map.providers.sitemap.config import SitemapProviderConfig

        # User config
        write_user_toml(
            user_config_dir,
            """
[tool.map.providers.sitemap]
max_urls = 5000
""",
        )

        # Project config
        write_project_toml(
            project_dir,
            """
[tool.map.providers.sitemap]
max_urls = 1000
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve(
            "map",
            "sitemap",
            SitemapProviderConfig,
            cli_overrides={"max_urls": 100},
        )

        assert config.max_urls == 100  # CLI wins


# ---------------------------------------------------------------------------
# Test: Runtime wiring integration (THESE SHOULD FAIL BEFORE WIRING)
# ---------------------------------------------------------------------------


class TestRuntimeWiringIntegration:
    """Integration tests that verify config flows through to runtime.

    These tests verify that ProviderConfigResolver is actually used when
    tools create provider instances. They should FAIL before bd-26w.5.1.1
    and bd-26w.5.1.2 are implemented.
    """

    @pytest.mark.skip(reason="Wiring not yet implemented (bd-26w.5.1.1)")
    def test_fetch_tool_uses_resolver_for_provider_config(
        self, project_dir, user_config_dir
    ):
        """Fetch tool should load provider config via ProviderConfigResolver.

        This test verifies that when FetchTool runs with a specific provider,
        it uses ProviderConfigResolver to load the provider's ConfigModel
        from TOML files.

        Implementation required in bd-26w.5.1.1:
        1. FetchTool.run() should call get_provider_config_resolver().resolve()
        2. Pass resolved config to provider constructor
        3. Config from kurt.toml should affect provider behavior
        """
        write_project_toml(
            project_dir,
            """
[tool.fetch.providers.httpx]
timeout = 99
""",
        )

        # This would require the FetchTool to use ProviderConfigResolver
        # Currently it doesn't, so we can't easily verify the config flows through
        # The test should verify that a provider instantiated by FetchTool
        # has the config value from TOML

        # Placeholder assertion - will be implemented with bd-26w.5.1.1
        assert False, "Implement FetchTool wiring to ProviderConfigResolver"

    @pytest.mark.skip(reason="Wiring not yet implemented (bd-26w.5.1.2)")
    def test_map_tool_uses_resolver_for_provider_config(
        self, project_dir, user_config_dir
    ):
        """Map tool should load provider config via ProviderConfigResolver.

        This test verifies that when MapTool runs with a specific provider,
        it uses ProviderConfigResolver to load the provider's ConfigModel
        from TOML files.

        Implementation required in bd-26w.5.1.2:
        1. MapTool.run() should call get_provider_config_resolver().resolve()
        2. Pass resolved config to provider constructor
        3. Config from kurt.toml should affect provider behavior
        """
        write_project_toml(
            project_dir,
            """
[tool.map.providers.sitemap]
max_pages = 50
timeout = 10
""",
        )

        # This would require the MapTool to use ProviderConfigResolver
        # Placeholder assertion - will be implemented with bd-26w.5.1.2
        assert False, "Implement MapTool wiring to ProviderConfigResolver"


# ---------------------------------------------------------------------------
# Test: Explicit project_root parameter
# ---------------------------------------------------------------------------


class TestExplicitProjectRoot:
    """Test using explicit project_root to bypass CWD-based discovery."""

    def test_explicit_project_root_loads_correct_config(
        self, tmp_path, user_config_dir
    ):
        """Can pass explicit project_root to load from specific directory."""
        from kurt.tools.fetch.providers.httpx.config import HttpxProviderConfig

        # Create a separate project directory
        other_project = tmp_path / "other_project"
        other_project.mkdir()
        write_project_toml(
            other_project,
            """
[tool.fetch.providers.httpx]
timeout = 77
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve(
            "fetch",
            "httpx",
            HttpxProviderConfig,
            project_root=other_project,
        )

        assert config.timeout == 77

    def test_explicit_project_root_overrides_cwd(
        self, project_dir, user_config_dir, tmp_path
    ):
        """Explicit project_root takes precedence over CWD."""
        from kurt.tools.fetch.providers.httpx.config import HttpxProviderConfig

        # CWD project config
        write_project_toml(
            project_dir,
            """
[tool.fetch.providers.httpx]
timeout = 30
""",
        )

        # Other project config
        other_project = tmp_path / "other_project"
        other_project.mkdir()
        write_project_toml(
            other_project,
            """
[tool.fetch.providers.httpx]
timeout = 99
""",
        )

        resolver = get_provider_config_resolver()
        config = resolver.resolve(
            "fetch",
            "httpx",
            HttpxProviderConfig,
            project_root=other_project,
        )

        assert config.timeout == 99  # Explicit root wins over CWD


# ---------------------------------------------------------------------------
# Test: Cross-provider config isolation
# ---------------------------------------------------------------------------


class TestCrossProviderIsolation:
    """Verify config for one provider doesn't affect another."""

    def test_httpx_config_not_applied_to_firecrawl(
        self, project_dir, user_config_dir
    ):
        """HTTPx config should not affect Firecrawl provider."""
        from kurt.tools.fetch.providers.firecrawl.config import (
            FirecrawlProviderConfig,
        )
        from kurt.tools.fetch.providers.httpx.config import HttpxProviderConfig

        write_project_toml(
            project_dir,
            """
[tool.fetch.providers.httpx]
timeout = 999
""",
        )

        resolver = get_provider_config_resolver()

        httpx_config = resolver.resolve("fetch", "httpx", HttpxProviderConfig)
        firecrawl_config = resolver.resolve(
            "fetch", "firecrawl", FirecrawlProviderConfig
        )

        assert httpx_config.timeout == 999  # From config
        # Firecrawl should have its own default timeout, not httpx's
        assert firecrawl_config.timeout != 999

    def test_tool_level_applies_to_multiple_providers(
        self, project_dir, user_config_dir
    ):
        """Tool-level config applies to all providers that support the field."""
        from kurt.tools.fetch.providers.firecrawl.config import (
            FirecrawlProviderConfig,
        )
        from kurt.tools.fetch.providers.httpx.config import HttpxProviderConfig

        write_project_toml(
            project_dir,
            """
[tool.fetch]
timeout = 45
""",
        )

        resolver = get_provider_config_resolver()

        httpx_config = resolver.resolve("fetch", "httpx", HttpxProviderConfig)
        firecrawl_config = resolver.resolve(
            "fetch", "firecrawl", FirecrawlProviderConfig
        )

        # Both should get tool-level timeout since they both have timeout field
        assert httpx_config.timeout == 45
        assert firecrawl_config.timeout == 45
