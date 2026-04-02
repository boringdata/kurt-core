"""
Unit tests for ProviderRegistry and provider discovery.
"""

from __future__ import annotations

import pytest

from kurt.tools.core.errors import (
    ProviderNotFoundError,
    ProviderRequirementsError,
)
from kurt.tools.core.provider import ProviderRegistry, get_provider_registry


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset singleton between tests."""
    ProviderRegistry._instance = None
    yield
    ProviderRegistry._instance = None


# ============================================================================
# Singleton Tests
# ============================================================================


class TestProviderRegistrySingleton:
    """Test ProviderRegistry singleton pattern."""

    def test_singleton_pattern(self):
        """Registry is a singleton."""
        reg1 = get_provider_registry()
        reg2 = get_provider_registry()
        assert reg1 is reg2

    def test_singleton_after_reset(self):
        """New instance after reset."""
        reg1 = get_provider_registry()
        ProviderRegistry._instance = None
        reg2 = get_provider_registry()
        assert reg1 is not reg2

    def test_reset_clears_state(self):
        """reset() clears providers and discovery flag."""
        registry = get_provider_registry()
        registry._providers["test"] = {"mock": object}
        registry._discovered = True

        registry.reset()

        assert registry._providers == {}
        assert registry._provider_meta == {}
        assert registry._discovered is False


# ============================================================================
# Discovery Tests with Temp Directories
# ============================================================================


class TestProviderDiscovery:
    """Test provider discovery from filesystem."""

    def _create_provider(self, providers_dir, name, class_content):
        """Helper to create a provider directory with provider.py."""
        provider_dir = providers_dir / name
        provider_dir.mkdir(parents=True, exist_ok=True)
        (provider_dir / "provider.py").write_text(class_content)
        (provider_dir / "__init__.py").write_text("")
        return provider_dir

    def test_discover_from_project_dir(self, tmp_path, monkeypatch):
        """Discovers providers from project tools directory."""
        project_dir = tmp_path / "project"
        tools_dir = project_dir / "kurt" / "tools"

        # Create a fetch provider
        self._create_provider(
            tools_dir / "fetch" / "providers",
            "custom",
            '''
class CustomFetcher:
    """Custom fetcher for testing."""
    name = "custom"
    version = "1.0.0"
    url_patterns = ["custom.example.com/*"]
    requires_env = ["CUSTOM_API_KEY"]

    def fetch(self, url):
        pass
''',
        )

        monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))

        registry = get_provider_registry()
        registry.discover()

        providers = registry.list_providers("fetch")
        names = [p["name"] for p in providers]
        assert "custom" in names

        # Check metadata
        custom = next(p for p in providers if p["name"] == "custom")
        assert custom["version"] == "1.0.0"
        assert "custom.example.com/*" in custom["url_patterns"]
        assert "CUSTOM_API_KEY" in custom["requires_env"]
        assert custom["_source"] == "project"

    def test_discover_from_user_dir(self, tmp_path, monkeypatch):
        """Discovers providers from user ~/.kurt/tools/ directory."""
        user_home = tmp_path / "home"
        user_tools = user_home / ".kurt" / "tools"

        self._create_provider(
            user_tools / "map" / "providers",
            "custom-mapper",
            '''
class CustomMapper:
    """Custom mapper for testing."""
    name = "custom-mapper"
    version = "2.0.0"
    url_patterns = []
    requires_env = []

    def map(self, source):
        pass
''',
        )

        monkeypatch.setenv("HOME", str(user_home))
        monkeypatch.setenv("KURT_PROJECT_ROOT", str(tmp_path / "nonexistent"))

        registry = get_provider_registry()
        registry.discover()

        providers = registry.list_providers("map")
        names = [p["name"] for p in providers]
        assert "custom-mapper" in names

    def test_project_overrides_user(self, tmp_path, monkeypatch):
        """Project providers override user providers with same name."""
        user_home = tmp_path / "home"
        project_dir = tmp_path / "project"

        # User provider (lower priority)
        self._create_provider(
            user_home / ".kurt" / "tools" / "fetch" / "providers",
            "shared",
            '''
class SharedFetcher:
    name = "shared"
    version = "1.0.0"
    url_patterns = []
    requires_env = []
''',
        )

        # Project provider (higher priority, same name)
        self._create_provider(
            project_dir / "kurt" / "tools" / "fetch" / "providers",
            "shared",
            '''
class SharedFetcher:
    name = "shared"
    version = "2.0.0"
    url_patterns = ["override/*"]
    requires_env = []
''',
        )

        monkeypatch.setenv("HOME", str(user_home))
        monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))

        registry = get_provider_registry()
        registry.discover()

        providers = registry.list_providers("fetch")
        shared = next(p for p in providers if p["name"] == "shared")

        # Project version wins
        assert shared["version"] == "2.0.0"
        assert shared["_source"] == "project"
        assert "override/*" in shared["url_patterns"]

    def test_discover_skips_hidden_dirs(self, tmp_path, monkeypatch):
        """Discovery skips directories starting with . or _."""
        project_dir = tmp_path / "project"
        providers_dir = project_dir / "kurt" / "tools" / "fetch" / "providers"

        # Hidden dir - should be skipped
        self._create_provider(
            providers_dir,
            ".hidden",
            '''
class HiddenFetcher:
    name = "hidden"
    url_patterns = []
    requires_env = []
''',
        )

        # Underscore dir - should be skipped
        self._create_provider(
            providers_dir,
            "_internal",
            '''
class InternalFetcher:
    name = "internal"
    url_patterns = []
    requires_env = []
''',
        )

        # Normal dir - should be found
        self._create_provider(
            providers_dir,
            "normal",
            '''
class NormalFetcher:
    name = "normal"
    url_patterns = []
    requires_env = []
''',
        )

        monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))

        registry = get_provider_registry()
        registry.discover()

        providers = registry.list_providers("fetch")
        names = [p["name"] for p in providers]
        assert "normal" in names
        assert "hidden" not in names
        assert "internal" not in names

    def test_discover_skips_invalid_providers(self, tmp_path):
        """Discovery skips files that fail to import or have no provider class."""
        tools_dir = tmp_path / "tools"
        providers_dir = tools_dir / "fetch" / "providers"

        # Provider with syntax error
        bad_dir = providers_dir / "bad"
        bad_dir.mkdir(parents=True)
        (bad_dir / "provider.py").write_text("this is not valid python !!!")

        # Provider without name attribute
        no_name_dir = providers_dir / "noname"
        no_name_dir.mkdir(parents=True)
        (no_name_dir / "provider.py").write_text('''
class SomeFetcher:
    pass
''')

        registry = get_provider_registry()
        registry.discover_from([(tools_dir, "test")])  # Should not raise

        providers = registry.list_providers("fetch")
        assert len(providers) == 0

    def test_discover_is_idempotent(self, tmp_path):
        """Calling discover() multiple times is safe."""
        tools_dir = tmp_path / "tools"
        self._create_provider(
            tools_dir / "fetch" / "providers",
            "test",
            '''
class TestFetcher:
    name = "test"
    url_patterns = []
    requires_env = []
''',
        )

        registry = get_provider_registry()
        registry.discover_from([(tools_dir, "test")])
        # Second discover() is a no-op (idempotent flag set by discover_from)
        registry.discover()
        registry.discover()

        providers = registry.list_providers("fetch")
        assert len(providers) == 1


# ============================================================================
# Get Provider Tests
# ============================================================================


class TestGetProvider:
    """Test get_provider and get_provider_class methods."""

    def test_get_provider_instantiates(self, tmp_path, monkeypatch):
        """get_provider returns an instantiated provider object."""
        project_dir = tmp_path / "project"
        providers_dir = project_dir / "kurt" / "tools" / "fetch" / "providers"
        provider_dir = providers_dir / "test"
        provider_dir.mkdir(parents=True)
        (provider_dir / "provider.py").write_text('''
class TestFetcher:
    name = "test"
    url_patterns = []
    requires_env = []

    def __init__(self):
        self.initialized = True
''')

        monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))

        registry = get_provider_registry()
        provider = registry.get_provider("fetch", "test")

        assert provider is not None
        assert provider.initialized is True

    def test_get_provider_not_found(self):
        """get_provider returns None for unknown provider."""
        registry = get_provider_registry()
        provider = registry.get_provider("fetch", "nonexistent")
        assert provider is None

    def test_get_provider_class(self, tmp_path, monkeypatch):
        """get_provider_class returns class without instantiation."""
        project_dir = tmp_path / "project"
        providers_dir = project_dir / "kurt" / "tools" / "fetch" / "providers"
        provider_dir = providers_dir / "test"
        provider_dir.mkdir(parents=True)
        (provider_dir / "provider.py").write_text('''
class TestFetcher:
    name = "test"
    url_patterns = []
    requires_env = []
''')

        monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))

        registry = get_provider_registry()
        cls = registry.get_provider_class("fetch", "test")

        assert cls is not None
        assert cls.name == "test"

    def test_get_provider_class_not_found(self):
        """get_provider_class returns None for unknown provider."""
        registry = get_provider_registry()
        cls = registry.get_provider_class("fetch", "nonexistent")
        assert cls is None


# ============================================================================
# URL Pattern Matching Tests
# ============================================================================


class TestURLPatternMatching:
    """Test URL pattern matching for provider auto-selection."""

    @pytest.fixture
    def registry_with_providers(self, tmp_path):
        """Set up registry with only test providers (no built-ins)."""
        tools_dir = tmp_path / "tools"
        providers_dir = tools_dir / "fetch" / "providers"

        # Notion provider - specific patterns
        notion_dir = providers_dir / "notion"
        notion_dir.mkdir(parents=True)
        (notion_dir / "provider.py").write_text('''
class NotionFetcher:
    name = "notion"
    url_patterns = ["notion.so/*", "*.notion.site/*"]
    requires_env = ["NOTION_TOKEN"]
''')

        # Twitter provider - specific patterns
        twitter_dir = providers_dir / "twitter"
        twitter_dir.mkdir(parents=True)
        (twitter_dir / "provider.py").write_text('''
class TwitterFetcher:
    name = "twitter"
    url_patterns = ["twitter.com/*", "x.com/*"]
    requires_env = ["TWITTER_TOKEN"]
''')

        # Default provider - wildcard
        default_dir = providers_dir / "default"
        default_dir.mkdir(parents=True)
        (default_dir / "provider.py").write_text('''
class DefaultFetcher:
    name = "default"
    url_patterns = ["*"]
    requires_env = []
''')

        registry = get_provider_registry()
        registry.discover_from([(tools_dir, "test")])
        return registry

    def test_match_specific_pattern(self, registry_with_providers):
        """Matches specific URL patterns over wildcards."""
        matched = registry_with_providers.match_provider(
            "fetch", "https://notion.so/my-page"
        )
        assert matched == "notion"

    def test_match_subdomain_pattern(self, registry_with_providers):
        """Matches subdomain patterns."""
        matched = registry_with_providers.match_provider(
            "fetch", "https://myteam.notion.site/page"
        )
        assert matched == "notion"

    def test_match_twitter_pattern(self, registry_with_providers):
        """Matches twitter URL patterns."""
        matched = registry_with_providers.match_provider(
            "fetch", "https://twitter.com/user/status/123"
        )
        assert matched == "twitter"

    def test_match_x_dot_com(self, registry_with_providers):
        """Matches x.com URL patterns."""
        matched = registry_with_providers.match_provider(
            "fetch", "https://x.com/user/status/123"
        )
        assert matched == "twitter"

    def test_match_wildcard_fallback(self, registry_with_providers):
        """Wildcard fallback only when explicitly requested (include_wildcards=True)."""
        # By default, wildcards are NOT included (to allow tool defaults to take precedence)
        matched = registry_with_providers.match_provider(
            "fetch", "https://random-site.com/article"
        )
        assert matched is None  # No specific match, wildcards excluded

        # With include_wildcards=True, wildcard provider is returned
        matched = registry_with_providers.match_provider(
            "fetch", "https://random-site.com/article", include_wildcards=True
        )
        assert matched == "default"

    def test_match_unknown_tool(self, registry_with_providers):
        """Returns None for unknown tool."""
        matched = registry_with_providers.match_provider(
            "nonexistent", "https://example.com"
        )
        assert matched is None

    def test_match_no_providers(self, tmp_path):
        """Returns None when tool has no providers."""
        # Use empty dir to avoid built-in providers
        tools_dir = tmp_path / "empty_tools"
        tools_dir.mkdir()
        registry = get_provider_registry()
        registry.discover_from([(tools_dir, "test")])
        matched = registry.match_provider("fetch", "https://example.com")
        assert matched is None


# ============================================================================
# Specificity Scoring Tests
# ============================================================================


class TestPatternSpecificity:
    """Test _pattern_specificity and match_provider specificity ranking."""

    def test_specificity_scores(self):
        """Patterns with more literal chars score higher."""
        from kurt.tools.core.provider import _pattern_specificity

        assert _pattern_specificity("*/sitemap*.xml") > _pattern_specificity("*.xml")
        assert _pattern_specificity("*twitter.com/*") > _pattern_specificity("*")
        assert _pattern_specificity("*") == 0
        assert _pattern_specificity("*.xml") == 4  # . x m l

    def test_sitemap_beats_rss_for_sitemap_xml(self, tmp_path):
        """sitemap.xml resolves to sitemap, not rss (regression test)."""
        tools_dir = tmp_path / "tools"

        # Create sitemap provider (more specific pattern)
        sitemap_dir = tools_dir / "map" / "providers" / "sitemap"
        sitemap_dir.mkdir(parents=True)
        (sitemap_dir / "provider.py").write_text('''
class SitemapProvider:
    name = "sitemap"
    url_patterns = ["*/sitemap.xml", "*/sitemap*.xml"]
    requires_env = []
''')

        # Create rss provider (broad *.xml pattern)
        rss_dir = tools_dir / "map" / "providers" / "rss"
        rss_dir.mkdir(parents=True)
        (rss_dir / "provider.py").write_text('''
class RssProvider:
    name = "rss"
    url_patterns = ["*/feed", "*/feed.xml", "*/rss", "*/rss.xml", "*.xml"]
    requires_env = []
''')

        registry = get_provider_registry()
        registry.discover_from([(tools_dir, "builtin")])

        matched = registry.match_provider("map", "https://example.com/sitemap.xml")
        assert matched == "sitemap"

    def test_rss_still_matches_feed_xml(self, tmp_path):
        """feed.xml resolves to rss."""
        tools_dir = tmp_path / "tools"

        sitemap_dir = tools_dir / "map" / "providers" / "sitemap"
        sitemap_dir.mkdir(parents=True)
        (sitemap_dir / "provider.py").write_text('''
class SitemapProvider:
    name = "sitemap"
    url_patterns = ["*/sitemap.xml", "*/sitemap*.xml"]
    requires_env = []
''')

        rss_dir = tools_dir / "map" / "providers" / "rss"
        rss_dir.mkdir(parents=True)
        (rss_dir / "provider.py").write_text('''
class RssProvider:
    name = "rss"
    url_patterns = ["*/feed", "*/feed.xml", "*/rss", "*/rss.xml", "*.xml"]
    requires_env = []
''')

        registry = get_provider_registry()
        registry.discover_from([(tools_dir, "builtin")])

        matched = registry.match_provider("map", "https://example.com/feed.xml")
        assert matched == "rss"

    def test_wildcard_fallback_still_works(self, tmp_path):
        """Wildcard '*' provider is used only when explicitly requested."""
        tools_dir = tmp_path / "tools"

        specific_dir = tools_dir / "fetch" / "providers" / "twitter"
        specific_dir.mkdir(parents=True)
        (specific_dir / "provider.py").write_text('''
class TwitterProvider:
    name = "twitter"
    url_patterns = ["*twitter.com/*", "*x.com/*"]
    requires_env = []
''')

        fallback_dir = tools_dir / "fetch" / "providers" / "default"
        fallback_dir.mkdir(parents=True)
        (fallback_dir / "provider.py").write_text('''
class DefaultProvider:
    name = "default"
    url_patterns = ["*"]
    requires_env = []
''')

        registry = get_provider_registry()
        registry.discover_from([(tools_dir, "builtin")])

        # Specific URL matches specific provider
        assert registry.match_provider("fetch", "https://twitter.com/user") == "twitter"

        # Generic URL: without include_wildcards, returns None (allows tool default)
        assert registry.match_provider("fetch", "https://example.com/page") is None

        # Generic URL: with include_wildcards=True, falls back to wildcard
        assert registry.match_provider(
            "fetch", "https://example.com/page", include_wildcards=True
        ) == "default"

    def test_project_provider_beats_builtin_same_score(self, tmp_path):
        """Project provider wins over builtin when specificity ties."""
        tools_dir = tmp_path / "tools"

        # Builtin provider
        builtin_dir = tools_dir / "fetch" / "providers" / "builtin_fetcher"
        builtin_dir.mkdir(parents=True)
        (builtin_dir / "provider.py").write_text('''
class BuiltinFetcher:
    name = "builtin_fetcher"
    url_patterns = ["*example.com/*"]
    requires_env = []
''')

        # Project provider with same-specificity pattern
        project_dir = tmp_path / "project_tools"
        project_prov = project_dir / "fetch" / "providers" / "project_fetcher"
        project_prov.mkdir(parents=True)
        (project_prov / "provider.py").write_text('''
class ProjectFetcher:
    name = "project_fetcher"
    url_patterns = ["*example.com/*"]
    requires_env = []
''')

        registry = get_provider_registry()
        registry.discover_from([
            (project_dir, "project"),
            (tools_dir, "builtin"),
        ])

        matched = registry.match_provider("fetch", "https://example.com/page")
        assert matched == "project_fetcher"

    def test_more_specific_pattern_wins_regardless_of_order(self, tmp_path):
        """Provider with more specific pattern wins even if discovered later."""
        tools_dir = tmp_path / "tools"

        # Provider "alpha" with broad pattern (discovered first alphabetically)
        alpha_dir = tools_dir / "map" / "providers" / "alpha"
        alpha_dir.mkdir(parents=True)
        (alpha_dir / "provider.py").write_text('''
class AlphaProvider:
    name = "alpha"
    url_patterns = ["*.xml"]
    requires_env = []
''')

        # Provider "beta" with specific pattern (discovered later)
        beta_dir = tools_dir / "map" / "providers" / "beta"
        beta_dir.mkdir(parents=True)
        (beta_dir / "provider.py").write_text('''
class BetaProvider:
    name = "beta"
    url_patterns = ["*/sitemap*.xml"]
    requires_env = []
''')

        registry = get_provider_registry()
        registry.discover_from([(tools_dir, "builtin")])

        matched = registry.match_provider("map", "https://example.com/sitemap.xml")
        assert matched == "beta"


# ============================================================================
# Validation Tests
# ============================================================================


class TestProviderValidation:
    """Test provider requirement validation."""

    def test_validate_no_requirements(self, tmp_path, monkeypatch):
        """Providers with no requirements pass validation."""
        project_dir = tmp_path / "project"
        providers_dir = project_dir / "kurt" / "tools" / "fetch" / "providers"
        provider_dir = providers_dir / "simple"
        provider_dir.mkdir(parents=True)
        (provider_dir / "provider.py").write_text('''
class SimpleFetcher:
    name = "simple"
    url_patterns = []
    requires_env = []
''')

        monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))

        registry = get_provider_registry()
        missing = registry.validate_provider("fetch", "simple")
        assert missing == []

    def test_validate_missing_env_var(self, tmp_path, monkeypatch):
        """Returns missing env vars when not set."""
        project_dir = tmp_path / "project"
        providers_dir = project_dir / "kurt" / "tools" / "fetch" / "providers"
        provider_dir = providers_dir / "api"
        provider_dir.mkdir(parents=True)
        (provider_dir / "provider.py").write_text('''
class ApiFetcher:
    name = "api"
    url_patterns = []
    requires_env = ["MY_API_KEY", "MY_SECRET"]
''')

        monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))
        monkeypatch.delenv("MY_API_KEY", raising=False)
        monkeypatch.delenv("MY_SECRET", raising=False)

        registry = get_provider_registry()
        missing = registry.validate_provider("fetch", "api")
        assert "MY_API_KEY" in missing
        assert "MY_SECRET" in missing

    def test_validate_env_var_present(self, tmp_path, monkeypatch):
        """Returns empty list when env vars are set."""
        project_dir = tmp_path / "project"
        providers_dir = project_dir / "kurt" / "tools" / "fetch" / "providers"
        provider_dir = providers_dir / "api"
        provider_dir.mkdir(parents=True)
        (provider_dir / "provider.py").write_text('''
class ApiFetcher:
    name = "api"
    url_patterns = []
    requires_env = ["MY_API_KEY"]
''')

        monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))
        monkeypatch.setenv("MY_API_KEY", "test-key")

        registry = get_provider_registry()
        missing = registry.validate_provider("fetch", "api")
        assert missing == []

    def test_validate_unknown_provider(self):
        """Returns empty for unknown provider."""
        registry = get_provider_registry()
        missing = registry.validate_provider("fetch", "nonexistent")
        assert missing == []


# ============================================================================
# List Tools with Providers
# ============================================================================


class TestListToolsWithProviders:
    """Test list_tools_with_providers method."""

    def test_list_tools_with_providers(self, tmp_path, monkeypatch):
        """Lists tools that have providers."""
        project_dir = tmp_path / "project"

        # Create fetch provider
        fetch_provider = (
            project_dir / "kurt" / "tools" / "fetch" / "providers" / "test"
        )
        fetch_provider.mkdir(parents=True)
        (fetch_provider / "provider.py").write_text('''
class TestFetcher:
    name = "test"
    url_patterns = []
    requires_env = []
''')

        # Create map provider
        map_provider = (
            project_dir / "kurt" / "tools" / "map" / "providers" / "test"
        )
        map_provider.mkdir(parents=True)
        (map_provider / "provider.py").write_text('''
class TestMapper:
    name = "test"
    url_patterns = []
    requires_env = []
''')

        monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))

        registry = get_provider_registry()
        tools = registry.list_tools_with_providers()

        assert "fetch" in tools
        assert "map" in tools
        assert "test" in tools["fetch"]
        assert "test" in tools["map"]

    def test_empty_when_no_providers(self, tmp_path):
        """Returns empty dict when no providers found."""
        # Use empty dir to avoid built-in providers
        tools_dir = tmp_path / "empty_tools"
        tools_dir.mkdir()
        registry = get_provider_registry()
        registry.discover_from([(tools_dir, "test")])
        tools = registry.list_tools_with_providers()
        assert tools == {}


# ============================================================================
# Error Type Tests
# ============================================================================


class TestProviderNotFoundError:
    """Test ProviderNotFoundError."""

    def test_error_message(self):
        """Error has correct message format."""
        error = ProviderNotFoundError("fetch", "notion")
        assert "notion" in str(error)
        assert "fetch" in str(error)
        assert error.tool_name == "fetch"
        assert error.provider_name == "notion"

    def test_error_details(self):
        """Error has structured details."""
        error = ProviderNotFoundError("map", "custom")
        assert error.details["tool_name"] == "map"
        assert error.details["provider_name"] == "custom"


# ============================================================================
# Integration Tests: Real Built-in Provider Discovery
# ============================================================================


class TestBuiltinProviderDiscovery:
    """Integration tests for discovering real built-in providers."""

    def test_discovers_fetch_providers(self, monkeypatch):
        """Discovers all built-in fetch providers."""
        # Ensure no project/user dirs interfere
        monkeypatch.setenv("KURT_PROJECT_ROOT", "/nonexistent")
        monkeypatch.setenv("HOME", "/nonexistent")

        registry = get_provider_registry()
        registry.discover()

        providers = registry.list_providers("fetch")
        names = sorted(p["name"] for p in providers)
        assert names == ["apify", "firecrawl", "httpx", "tavily", "trafilatura", "twitterapi"]

    def test_discovers_map_providers(self, monkeypatch):
        """Discovers all built-in map providers."""
        monkeypatch.setenv("KURT_PROJECT_ROOT", "/nonexistent")
        monkeypatch.setenv("HOME", "/nonexistent")

        registry = get_provider_registry()
        registry.discover()

        providers = registry.list_providers("map")
        names = sorted(p["name"] for p in providers)
        assert names == ["apify", "cms", "crawl", "folder", "rss", "sitemap"]

    def test_fetch_provider_metadata(self, monkeypatch):
        """Built-in fetch providers have correct metadata."""
        monkeypatch.setenv("KURT_PROJECT_ROOT", "/nonexistent")
        monkeypatch.setenv("HOME", "/nonexistent")

        registry = get_provider_registry()
        registry.discover()

        providers = {p["name"]: p for p in registry.list_providers("fetch")}

        # trafilatura - free, wildcard, no env
        assert providers["trafilatura"]["url_patterns"] == ["*"]
        assert providers["trafilatura"]["requires_env"] == []
        assert providers["trafilatura"]["_source"] == "builtin"

        # tavily - requires API key
        assert providers["tavily"]["requires_env"] == ["TAVILY_API_KEY"]

        # firecrawl - requires API key
        assert providers["firecrawl"]["requires_env"] == ["FIRECRAWL_API_KEY"]

        # apify - social platform patterns (Twitter/X handled by twitterapi)
        assert "*twitter.com/*" not in providers["apify"]["url_patterns"]
        assert "*linkedin.com/*" in providers["apify"]["url_patterns"]
        assert providers["apify"]["requires_env"] == ["APIFY_API_KEY"]

        # twitterapi - twitter-specific patterns
        assert "*twitter.com/*" in providers["twitterapi"]["url_patterns"]
        assert "*x.com/*" in providers["twitterapi"]["url_patterns"]
        assert providers["twitterapi"]["requires_env"] == ["TWITTERAPI_API_KEY"]

    def test_map_provider_metadata(self, monkeypatch):
        """Built-in map providers have correct metadata."""
        monkeypatch.setenv("KURT_PROJECT_ROOT", "/nonexistent")
        monkeypatch.setenv("HOME", "/nonexistent")

        registry = get_provider_registry()
        registry.discover()

        providers = {p["name"]: p for p in registry.list_providers("map")}

        # sitemap - sitemap-specific patterns
        assert "*/sitemap.xml" in providers["sitemap"]["url_patterns"]

        # rss - feed-specific patterns
        assert "*/feed" in providers["rss"]["url_patterns"]

        # crawl - wildcard
        assert providers["crawl"]["url_patterns"] == ["*"]

        # folder - no URL patterns (local filesystem)
        assert providers["folder"]["url_patterns"] == []

        # cms - no URL patterns (CMS-specific)
        assert providers["cms"]["url_patterns"] == []

    def test_url_matching_twitter_prefers_twitterapi(self, monkeypatch):
        """Twitter/X URLs must resolve to twitterapi, not apify (bd-21im.2)."""
        monkeypatch.setenv("KURT_PROJECT_ROOT", "/nonexistent")
        monkeypatch.setenv("HOME", "/nonexistent")

        registry = get_provider_registry()
        registry.discover()

        # twitter.com -> twitterapi (apify excludes twitter patterns)
        matched = registry.match_provider("fetch", "https://twitter.com/user")
        assert matched == "twitterapi"

        # x.com -> twitterapi
        matched = registry.match_provider("fetch", "https://x.com/user/status/123")
        assert matched == "twitterapi"

    def test_url_matching_generic_url_prefers_default(self, monkeypatch):
        """Generic URLs return None from match_provider (wildcards excluded by default).

        This allows resolve_provider to use the tool's default_provider instead
        of a wildcard provider. This is intentional per the provider selection
        contract: generic URLs should use tool defaults (e.g., trafilatura),
        not credentialed wildcard providers (e.g., firecrawl).
        """
        monkeypatch.setenv("KURT_PROJECT_ROOT", "/nonexistent")
        monkeypatch.setenv("HOME", "/nonexistent")

        registry = get_provider_registry()
        registry.discover()

        # match_provider excludes wildcards by default
        matched = registry.match_provider("fetch", "https://example.com/article")
        assert matched is None  # No specific match

        # With include_wildcards=True, wildcard providers match
        # Only trafilatura and httpx retain ["*"] patterns (free, no API key)
        matched = registry.match_provider(
            "fetch", "https://example.com/article", include_wildcards=True
        )
        assert matched is not None
        assert matched in ("trafilatura", "httpx")

        # resolve_provider with default_provider uses the default for generic URLs
        resolved = registry.resolve_provider(
            "fetch",
            url="https://example.com/article",
            default_provider="trafilatura",
        )
        assert resolved == "trafilatura"  # Tool default, not wildcard

    def test_list_tools_shows_fetch_and_map(self, monkeypatch):
        """list_tools_with_providers includes fetch and map."""
        monkeypatch.setenv("KURT_PROJECT_ROOT", "/nonexistent")
        monkeypatch.setenv("HOME", "/nonexistent")

        registry = get_provider_registry()
        tools = registry.list_tools_with_providers()

        assert "fetch" in tools
        assert "map" in tools
        assert len(tools["fetch"]) == 6
        assert len(tools["map"]) == 6

    def test_validate_builtin_provider_missing_env(self, monkeypatch):
        """Validates env requirements for built-in providers."""
        monkeypatch.setenv("KURT_PROJECT_ROOT", "/nonexistent")
        monkeypatch.setenv("HOME", "/nonexistent")
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)

        registry = get_provider_registry()
        missing = registry.validate_provider("fetch", "tavily")
        assert "TAVILY_API_KEY" in missing

    def test_validate_builtin_provider_no_requirements(self, monkeypatch):
        """Providers with no env requirements pass validation."""
        monkeypatch.setenv("KURT_PROJECT_ROOT", "/nonexistent")
        monkeypatch.setenv("HOME", "/nonexistent")

        registry = get_provider_registry()
        missing = registry.validate_provider("fetch", "trafilatura")
        assert missing == []


# ============================================================================
# Validate All Tests
# ============================================================================


class TestValidateAll:
    """Test validate_all method for bulk requirements checking."""

    def test_validate_all_reports_missing_env(self, tmp_path):
        """validate_all reports providers with missing env vars."""
        tools_dir = tmp_path / "tools"
        providers_dir = tools_dir / "fetch" / "providers"

        # Provider with requirements
        api_dir = providers_dir / "api"
        api_dir.mkdir(parents=True)
        (api_dir / "provider.py").write_text('''
class ApiFetcher:
    name = "api"
    url_patterns = []
    requires_env = ["API_KEY", "API_SECRET"]
''')

        # Provider without requirements
        free_dir = providers_dir / "free"
        free_dir.mkdir(parents=True)
        (free_dir / "provider.py").write_text('''
class FreeFetcher:
    name = "free"
    url_patterns = ["*"]
    requires_env = []
''')

        registry = get_provider_registry()
        registry.discover_from([(tools_dir, "test")])

        report = registry.validate_all()

        # Only "api" should be in the report (has missing env vars)
        assert "fetch" in report
        assert "api" in report["fetch"]
        assert "API_KEY" in report["fetch"]["api"]
        assert "API_SECRET" in report["fetch"]["api"]
        # "free" should not be in the report
        assert "free" not in report.get("fetch", {})

    def test_validate_all_empty_when_all_met(self, tmp_path, monkeypatch):
        """validate_all returns empty dict when all requirements are met."""
        tools_dir = tmp_path / "tools"
        providers_dir = tools_dir / "fetch" / "providers"

        api_dir = providers_dir / "api"
        api_dir.mkdir(parents=True)
        (api_dir / "provider.py").write_text('''
class ApiFetcher:
    name = "api"
    url_patterns = []
    requires_env = ["MY_KEY"]
''')

        monkeypatch.setenv("MY_KEY", "test-value")

        registry = get_provider_registry()
        registry.discover_from([(tools_dir, "test")])

        report = registry.validate_all()
        assert report == {}

    def test_validate_all_multiple_tools(self, tmp_path):
        """validate_all works across multiple tools."""
        tools_dir = tmp_path / "tools"

        # Fetch provider with missing env
        fetch_dir = tools_dir / "fetch" / "providers" / "cloud"
        fetch_dir.mkdir(parents=True)
        (fetch_dir / "provider.py").write_text('''
class CloudFetcher:
    name = "cloud"
    url_patterns = []
    requires_env = ["CLOUD_TOKEN"]
''')

        # Map provider with missing env
        map_dir = tools_dir / "map" / "providers" / "special"
        map_dir.mkdir(parents=True)
        (map_dir / "provider.py").write_text('''
class SpecialMapper:
    name = "special"
    url_patterns = []
    requires_env = ["SPECIAL_KEY"]
''')

        registry = get_provider_registry()
        registry.discover_from([(tools_dir, "test")])

        report = registry.validate_all()
        assert "fetch" in report
        assert "map" in report
        assert "CLOUD_TOKEN" in report["fetch"]["cloud"]
        assert "SPECIAL_KEY" in report["map"]["special"]


# ============================================================================
# Get Provider Checked Tests
# ============================================================================


class TestGetProviderChecked:
    """Test get_provider_checked method with validation."""

    def test_get_provider_checked_success(self, tmp_path, monkeypatch):
        """get_provider_checked returns provider when requirements met."""
        tools_dir = tmp_path / "tools"
        provider_dir = tools_dir / "fetch" / "providers" / "test"
        provider_dir.mkdir(parents=True)
        (provider_dir / "provider.py").write_text('''
class TestFetcher:
    name = "test"
    url_patterns = []
    requires_env = ["TEST_KEY"]

    def __init__(self):
        self.ready = True
''')

        monkeypatch.setenv("TEST_KEY", "present")

        registry = get_provider_registry()
        registry.discover_from([(tools_dir, "test")])

        provider = registry.get_provider_checked("fetch", "test")
        assert provider is not None
        assert provider.ready is True

    def test_get_provider_checked_raises_not_found(self, tmp_path):
        """get_provider_checked raises ProviderNotFoundError."""
        tools_dir = tmp_path / "empty"
        tools_dir.mkdir()

        registry = get_provider_registry()
        registry.discover_from([(tools_dir, "test")])

        with pytest.raises(ProviderNotFoundError) as exc_info:
            registry.get_provider_checked("fetch", "nonexistent")

        assert "nonexistent" in str(exc_info.value)
        assert exc_info.value.tool_name == "fetch"
        assert exc_info.value.provider_name == "nonexistent"

    def test_get_provider_checked_raises_requirements_error(self, tmp_path, monkeypatch):
        """get_provider_checked raises ProviderRequirementsError when env missing."""
        tools_dir = tmp_path / "tools"
        provider_dir = tools_dir / "fetch" / "providers" / "paid"
        provider_dir.mkdir(parents=True)
        (provider_dir / "provider.py").write_text('''
class PaidFetcher:
    name = "paid"
    url_patterns = []
    requires_env = ["PAID_API_KEY"]
''')

        monkeypatch.delenv("PAID_API_KEY", raising=False)

        registry = get_provider_registry()
        registry.discover_from([(tools_dir, "test")])

        with pytest.raises(ProviderRequirementsError) as exc_info:
            registry.get_provider_checked("fetch", "paid")

        assert exc_info.value.provider_name == "paid"
        assert "PAID_API_KEY" in exc_info.value.missing

    def test_get_provider_checked_error_includes_available(self, tmp_path):
        """ProviderNotFoundError includes list of available providers."""
        tools_dir = tmp_path / "tools"
        provider_dir = tools_dir / "fetch" / "providers" / "real"
        provider_dir.mkdir(parents=True)
        (provider_dir / "provider.py").write_text('''
class RealFetcher:
    name = "real"
    url_patterns = []
    requires_env = []
''')

        registry = get_provider_registry()
        registry.discover_from([(tools_dir, "test")])

        with pytest.raises(ProviderNotFoundError) as exc_info:
            registry.get_provider_checked("fetch", "wrong")

        assert "real" in exc_info.value.available

    def test_get_provider_checked_no_env_requirements(self, tmp_path):
        """get_provider_checked works for providers with no env requirements."""
        tools_dir = tmp_path / "tools"
        provider_dir = tools_dir / "fetch" / "providers" / "free"
        provider_dir.mkdir(parents=True)
        (provider_dir / "provider.py").write_text('''
class FreeFetcher:
    name = "free"
    url_patterns = ["*"]
    requires_env = []

    def __init__(self):
        self.free = True
''')

        registry = get_provider_registry()
        registry.discover_from([(tools_dir, "test")])

        provider = registry.get_provider_checked("fetch", "free")
        assert provider.free is True


# ============================================================================
# Multi-Location Discovery Tests (Phase 3)
# ============================================================================


class TestMultiLocationDiscovery:
    """Test multi-location tool discovery with precedence."""

    def _create_provider(self, providers_dir, name, class_content):
        """Helper to create a provider directory with provider.py."""
        provider_dir = providers_dir / name
        provider_dir.mkdir(parents=True, exist_ok=True)
        (provider_dir / "provider.py").write_text(class_content)
        (provider_dir / "__init__.py").write_text("")
        return provider_dir

    def test_first_occurrence_wins(self, tmp_path, monkeypatch):
        """First occurrence wins: project provider is kept, user is skipped."""
        user_home = tmp_path / "home"
        project_dir = tmp_path / "project"

        # Project provider (highest priority) - scanned first
        self._create_provider(
            project_dir / "kurt" / "tools" / "fetch" / "providers",
            "shared",
            '''
class SharedFetcher:
    name = "shared"
    version = "1.0.0"
    url_patterns = ["project/*"]
    requires_env = []
''',
        )

        # User provider (lower priority) - same name, scanned second
        self._create_provider(
            user_home / ".kurt" / "tools" / "fetch" / "providers",
            "shared",
            '''
class SharedFetcher:
    name = "shared"
    version = "2.0.0"
    url_patterns = ["user/*"]
    requires_env = []
''',
        )

        monkeypatch.setenv("HOME", str(user_home))
        monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))

        registry = get_provider_registry()
        registry.discover()

        providers = registry.list_providers("fetch")
        shared = next(p for p in providers if p["name"] == "shared")

        # Project version wins (first occurrence)
        assert shared["version"] == "1.0.0"
        assert shared["_source"] == "project"
        assert "project/*" in shared["url_patterns"]

    def test_project_provider_extends_builtin_tool(self, tmp_path, monkeypatch):
        """Project providers can extend builtin tools without tool.py."""
        project_dir = tmp_path / "project"

        # Create a project provider for the builtin "fetch" tool
        self._create_provider(
            project_dir / "kurt" / "tools" / "fetch" / "providers",
            "my-api",
            '''
class MyApiFetcher:
    """Custom API fetcher for our internal service."""
    name = "my-api"
    version = "1.0.0"
    url_patterns = ["api.internal.com/*"]
    requires_env = ["INTERNAL_API_KEY"]
''',
        )

        monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))
        monkeypatch.setenv("HOME", "/nonexistent")

        registry = get_provider_registry()
        registry.discover()

        # Should find both builtin and project providers for "fetch"
        providers = registry.list_providers("fetch")
        names = [p["name"] for p in providers]
        assert "my-api" in names
        # Builtin providers should still be present
        assert "trafilatura" in names

    def test_tool_source_tracking(self, tmp_path, monkeypatch):
        """Tool sources are tracked for debugging."""
        project_dir = tmp_path / "project"

        # Create a project-only tool
        self._create_provider(
            project_dir / "kurt" / "tools" / "custom-tool" / "providers",
            "default",
            '''
class DefaultCustom:
    name = "default"
    url_patterns = []
    requires_env = []
''',
        )

        monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))
        monkeypatch.setenv("HOME", "/nonexistent")

        registry = get_provider_registry()
        registry.discover()

        # custom-tool should be tracked as project source
        info = registry.get_tool_info("custom-tool")
        assert info["name"] == "custom-tool"
        assert info["source"] == "project"
        assert len(info["providers"]) == 1
        assert info["providers"][0]["name"] == "default"
        assert info["providers"][0]["source"] == "project"

    def test_builtin_tool_source_tracking(self, monkeypatch):
        """Builtin tools are tracked with 'builtin' source."""
        monkeypatch.setenv("KURT_PROJECT_ROOT", "/nonexistent")
        monkeypatch.setenv("HOME", "/nonexistent")

        registry = get_provider_registry()
        registry.discover()

        info = registry.get_tool_info("fetch")
        assert info["name"] == "fetch"
        assert info["source"] == "builtin"
        assert len(info["providers"]) > 0

    def test_get_tool_info_unknown_tool(self):
        """get_tool_info returns empty dict for unknown tool."""
        registry = get_provider_registry()
        info = registry.get_tool_info("nonexistent")
        assert info == {}

    def test_find_project_root_env_var(self, tmp_path, monkeypatch):
        """_find_project_root uses KURT_PROJECT_ROOT env var."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()

        monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))

        registry = get_provider_registry()
        root = registry._find_project_root()
        assert root == project_dir

    def test_find_project_root_env_var_nonexistent(self, tmp_path, monkeypatch):
        """_find_project_root returns None for nonexistent KURT_PROJECT_ROOT."""
        monkeypatch.setenv("KURT_PROJECT_ROOT", str(tmp_path / "does-not-exist"))

        registry = get_provider_registry()
        root = registry._find_project_root()
        assert root is None

    def test_find_project_root_kurt_toml(self, tmp_path, monkeypatch):
        """_find_project_root finds kurt.toml marker."""
        monkeypatch.delenv("KURT_PROJECT_ROOT", raising=False)

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "kurt.toml").write_text("[project]\nname = 'test'\n")

        subdir = project_dir / "deep" / "nested"
        subdir.mkdir(parents=True)
        monkeypatch.chdir(subdir)

        registry = get_provider_registry()
        root = registry._find_project_root()
        assert root == project_dir

    def test_find_project_root_git(self, tmp_path, monkeypatch):
        """_find_project_root finds .git marker."""
        monkeypatch.delenv("KURT_PROJECT_ROOT", raising=False)

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / ".git").mkdir()

        monkeypatch.chdir(project_dir)

        registry = get_provider_registry()
        root = registry._find_project_root()
        assert root == project_dir

    def test_skips_template_directory(self, tmp_path, monkeypatch):
        """Discovery skips the 'templates' directory."""
        project_dir = tmp_path / "project"

        # Create a templates dir that should be skipped
        templates_providers = (
            project_dir / "kurt" / "tools" / "templates" / "providers" / "fake"
        )
        templates_providers.mkdir(parents=True)
        (templates_providers / "provider.py").write_text('''
class FakeProvider:
    name = "fake"
    url_patterns = []
    requires_env = []
''')

        monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))
        monkeypatch.setenv("HOME", "/nonexistent")

        registry = get_provider_registry()
        registry.discover()

        info = registry.get_tool_info("templates")
        assert info == {}

    def test_user_provider_extends_builtin_tool(self, tmp_path, monkeypatch):
        """User providers can extend builtin tools."""
        user_home = tmp_path / "home"

        self._create_provider(
            user_home / ".kurt" / "tools" / "fetch" / "providers",
            "my-fetcher",
            '''
class MyFetcher:
    name = "my-fetcher"
    version = "1.0.0"
    url_patterns = []
    requires_env = []
''',
        )

        monkeypatch.setenv("KURT_PROJECT_ROOT", "/nonexistent")
        monkeypatch.setenv("HOME", str(user_home))

        registry = get_provider_registry()
        registry.discover()

        providers = registry.list_providers("fetch")
        names = [p["name"] for p in providers]
        assert "my-fetcher" in names
        assert "trafilatura" in names  # builtin still there

        # Check source
        my_fetcher = next(p for p in providers if p["name"] == "my-fetcher")
        assert my_fetcher["_source"] == "user"

    def test_provider_sources_tracked(self, tmp_path, monkeypatch):
        """Provider sources are tracked separately from tool sources."""
        user_home = tmp_path / "home"
        project_dir = tmp_path / "project"

        # Project adds a new provider to builtin "fetch" tool
        self._create_provider(
            project_dir / "kurt" / "tools" / "fetch" / "providers",
            "custom",
            '''
class CustomFetcher:
    name = "custom"
    url_patterns = []
    requires_env = []
''',
        )

        monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))
        monkeypatch.setenv("HOME", str(user_home))

        registry = get_provider_registry()
        registry.discover()

        info = registry.get_tool_info("fetch")
        # fetch tool itself is from project (scanned first)
        assert info["source"] == "project"

        # custom provider is from project
        custom = next(p for p in info["providers"] if p["name"] == "custom")
        assert custom["source"] == "project"

        # builtin providers are from builtin
        trafilatura = next(
            p for p in info["providers"] if p["name"] == "trafilatura"
        )
        assert trafilatura["source"] == "builtin"

    def test_reset_clears_source_tracking(self):
        """reset() clears tool and provider source tracking."""
        registry = get_provider_registry()
        registry._tool_sources["test"] = "project"
        registry._provider_sources["test"] = {"p1": "project"}

        registry.reset()

        assert registry._tool_sources == {}
        assert registry._provider_sources == {}


# ============================================================================
# Resolve Provider and Default Provider Tests (Phase 3)
# ============================================================================


class TestResolveProvider:
    """Test resolve_provider fallback chain and default_provider."""

    def _create_provider(self, providers_dir, name, class_content):
        """Helper to create a provider directory with provider.py."""
        provider_dir = providers_dir / name
        provider_dir.mkdir(parents=True, exist_ok=True)
        (provider_dir / "provider.py").write_text(class_content)
        (provider_dir / "__init__.py").write_text("")
        return provider_dir

    @pytest.fixture
    def registry_with_fetch(self, tmp_path):
        """Set up registry with fetch providers."""
        tools_dir = tmp_path / "tools"
        providers_dir = tools_dir / "fetch" / "providers"

        self._create_provider(
            providers_dir,
            "trafilatura",
            '''
class TrafilaturaFetcher:
    name = "trafilatura"
    url_patterns = ["*"]
    requires_env = []
''',
        )

        self._create_provider(
            providers_dir,
            "notion",
            '''
class NotionFetcher:
    name = "notion"
    url_patterns = ["notion.so/*", "*.notion.site/*"]
    requires_env = ["NOTION_TOKEN"]
''',
        )

        registry = get_provider_registry()
        registry.discover_from([(tools_dir, "test")])
        return registry

    def test_resolve_explicit_name(self, registry_with_fetch):
        """Explicit provider_name takes highest priority."""
        result = registry_with_fetch.resolve_provider(
            "fetch",
            provider_name="trafilatura",
            url="https://notion.so/page",
            default_provider="notion",
        )
        assert result == "trafilatura"

    def test_resolve_url_matching(self, registry_with_fetch):
        """URL matching is used when no explicit name."""
        result = registry_with_fetch.resolve_provider(
            "fetch",
            url="https://notion.so/my-page",
        )
        assert result == "notion"

    def test_resolve_default_provider_fallback(self, registry_with_fetch):
        """default_provider is used when URL doesn't match specific patterns."""
        result = registry_with_fetch.resolve_provider(
            "fetch",
            url=None,
            default_provider="trafilatura",
        )
        assert result == "trafilatura"

    def test_resolve_none_when_no_match(self, registry_with_fetch):
        """Returns None when nothing matches."""
        result = registry_with_fetch.resolve_provider(
            "nonexistent-tool",
            provider_name="fake",
        )
        assert result is None

    def test_resolve_explicit_name_not_found(self, registry_with_fetch):
        """Returns None when explicit name doesn't exist."""
        result = registry_with_fetch.resolve_provider(
            "fetch",
            provider_name="nonexistent",
        )
        assert result is None

    def test_resolve_default_not_found(self, registry_with_fetch):
        """Returns None when default_provider doesn't exist."""
        result = registry_with_fetch.resolve_provider(
            "fetch",
            default_provider="nonexistent-default",
        )
        assert result is None

    def test_fetch_tool_has_default_provider(self):
        """FetchTool sets default_provider to 'trafilatura'."""
        from kurt.tools.fetch.tool import FetchTool

        assert FetchTool.default_provider == "trafilatura"

    def test_map_tool_has_default_provider(self):
        """MapTool sets default_provider to 'sitemap'."""
        from kurt.tools.map.tool import MapTool

        assert MapTool.default_provider == "sitemap"

    def test_tool_base_default_provider_is_none(self):
        """Tool base class default_provider is None."""
        from kurt.tools.core.base import Tool

        assert Tool.default_provider is None


# ============================================================================
# Regression: generic URLs resolve to defaults (bd-21im.1.2)
# ============================================================================


class TestWildcardVsDefaultRegression:
    """Regression tests: generic URLs must resolve to tool defaults,
    NOT to credentialed wildcard providers (bd-21im.1.2).

    Background: multiple builtin providers declare url_patterns=["*"].
    Without proper handling, match_provider returns one of these for any
    URL, bypassing the tool's default_provider. This broke basic fetch/map
    workflows when the wildcard winner required an API key.
    """

    def _create_provider(self, providers_dir, name, class_content):
        provider_dir = providers_dir / name
        provider_dir.mkdir(parents=True, exist_ok=True)
        (provider_dir / "provider.py").write_text(class_content)
        (provider_dir / "__init__.py").write_text("")

    @pytest.fixture
    def registry_multi_wildcard(self, tmp_path):
        """Registry with multiple wildcard providers (simulates real builtin state)."""
        tools_dir = tmp_path / "tools"
        fetch_providers = tools_dir / "fetch" / "providers"
        map_providers = tools_dir / "map" / "providers"

        # Fetch: 4 wildcard providers + 1 specific
        self._create_provider(fetch_providers, "trafilatura", '''
class TrafilaturaFetcher:
    name = "trafilatura"
    url_patterns = ["*"]
    requires_env = []
''')
        self._create_provider(fetch_providers, "firecrawl", '''
class FirecrawlFetcher:
    name = "firecrawl"
    url_patterns = ["*"]
    requires_env = ["FIRECRAWL_API_KEY"]
''')
        self._create_provider(fetch_providers, "tavily", '''
class TavilyFetcher:
    name = "tavily"
    url_patterns = ["*"]
    requires_env = ["TAVILY_API_KEY"]
''')
        self._create_provider(fetch_providers, "notion", '''
class NotionFetcher:
    name = "notion"
    url_patterns = ["*.notion.so/*", "*.notion.site/*"]
    requires_env = ["NOTION_TOKEN"]
''')

        # Map: 1 wildcard + 1 specific
        self._create_provider(map_providers, "crawl", '''
class CrawlMapper:
    name = "crawl"
    url_patterns = ["*"]
    requires_env = []
''')
        self._create_provider(map_providers, "sitemap", '''
class SitemapMapper:
    name = "sitemap"
    url_patterns = ["*/sitemap.xml", "*/sitemap*.xml"]
    requires_env = []
''')

        registry = get_provider_registry()
        registry.discover_from([(tools_dir, "builtin")])
        return registry

    def test_generic_url_uses_fetch_default_not_wildcard(self, registry_multi_wildcard):
        """Generic URL resolves to trafilatura (default), not firecrawl/tavily."""
        result = registry_multi_wildcard.resolve_provider(
            "fetch",
            url="https://example.com/article",
            default_provider="trafilatura",
        )
        assert result == "trafilatura"

    def test_generic_url_uses_map_default_not_wildcard(self, registry_multi_wildcard):
        """Generic URL resolves to sitemap (default), not crawl."""
        result = registry_multi_wildcard.resolve_provider(
            "map",
            url="https://example.com",
            default_provider="sitemap",
        )
        assert result == "sitemap"

    def test_specific_url_still_matches_over_default(self, registry_multi_wildcard):
        """Specific URL pattern wins over default_provider."""
        result = registry_multi_wildcard.resolve_provider(
            "fetch",
            url="https://www.notion.so/my-page",
            default_provider="trafilatura",
        )
        assert result == "notion"

    def test_sitemap_url_still_matches_over_default(self, registry_multi_wildcard):
        """Sitemap URL matches sitemap provider specifically."""
        result = registry_multi_wildcard.resolve_provider(
            "map",
            url="https://example.com/sitemap.xml",
            default_provider="sitemap",
        )
        assert result == "sitemap"

    def test_no_default_allows_wildcard_fallback(self, registry_multi_wildcard):
        """Without default_provider, wildcard providers ARE used."""
        result = registry_multi_wildcard.resolve_provider(
            "fetch",
            url="https://example.com/article",
            default_provider=None,
        )
        # Should pick a wildcard provider (any of the ["*"] ones)
        assert result is not None
        assert result in ("trafilatura", "firecrawl", "tavily")

    def test_match_provider_excludes_wildcards_by_default(self, registry_multi_wildcard):
        """match_provider(include_wildcards=False) returns None for generic URLs."""
        result = registry_multi_wildcard.match_provider(
            "fetch",
            "https://example.com/article",
            include_wildcards=False,
        )
        assert result is None

    def test_match_provider_includes_wildcards_when_requested(self, registry_multi_wildcard):
        """match_provider(include_wildcards=True) returns wildcard match."""
        result = registry_multi_wildcard.match_provider(
            "fetch",
            "https://example.com/article",
            include_wildcards=True,
        )
        assert result is not None

    def test_builtin_fetch_default_is_trafilatura(self):
        """FetchTool.default_provider is trafilatura (regression guard)."""
        from kurt.tools.fetch.tool import FetchTool

        assert FetchTool.default_provider == "trafilatura"

    def test_builtin_map_default_is_sitemap(self):
        """MapTool.default_provider is sitemap (regression guard)."""
        from kurt.tools.map.tool import MapTool

        assert MapTool.default_provider == "sitemap"


# ============================================================================
# Module Name Collision Tests (bd-285.1.5)
# ============================================================================


class TestProviderModuleNameCollisions:
    """Test that same-named providers from different sources don't collide."""

    def _create_provider(self, providers_dir, name, class_content):
        provider_dir = providers_dir / name
        provider_dir.mkdir(parents=True, exist_ok=True)
        (provider_dir / "provider.py").write_text(class_content)
        (provider_dir / "__init__.py").write_text("")
        return provider_dir

    def test_same_name_different_sources_no_collision(self, tmp_path, monkeypatch):
        """Same-named providers from project and user don't corrupt each other."""
        project_dir = tmp_path / "project"
        user_home = tmp_path / "home"

        # Project provider (highest priority - wins)
        self._create_provider(
            project_dir / "kurt" / "tools" / "fetch" / "providers",
            "custom",
            '''
class CustomFetcher:
    """Project custom fetcher."""
    name = "custom"
    version = "2.0.0"
    url_patterns = []
    requires_env = []
    _marker = "project"
''',
        )

        # User provider (lower priority - should NOT replace project)
        self._create_provider(
            user_home / ".kurt" / "tools" / "fetch" / "providers",
            "custom",
            '''
class CustomFetcher:
    """User custom fetcher."""
    name = "custom"
    version = "1.0.0"
    url_patterns = []
    requires_env = []
    _marker = "user"
''',
        )

        monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))
        monkeypatch.setenv("HOME", str(user_home))

        registry = get_provider_registry()
        registry.discover()

        # Project provider should win (first occurrence)
        provider_class = registry.get_provider_class("fetch", "custom")
        assert provider_class is not None
        assert getattr(provider_class, "_marker") == "project"

        # Source should be project
        providers = registry.list_providers("fetch")
        custom = next(p for p in providers if p["name"] == "custom")
        assert custom["_source"] == "project"

    def test_module_names_include_source(self, tmp_path):
        """Module names include source to prevent collisions."""
        registry = get_provider_registry()

        # Create two provider files with same name but different paths
        project_providers = tmp_path / "project" / "fetch" / "providers"
        user_providers = tmp_path / "user" / "fetch" / "providers"

        self._create_provider(
            project_providers,
            "myapi",
            '''
class MyApiFetcher:
    name = "myapi"
    url_patterns = []
    requires_env = []
''',
        )

        self._create_provider(
            user_providers,
            "myapi",
            '''
class MyApiFetcher:
    name = "myapi"
    url_patterns = []
    requires_env = []
''',
        )

        # Import both with different source labels
        cls1 = registry._import_provider(
            project_providers / "myapi" / "provider.py",
            tool_name="fetch",
            source="project",
        )
        cls2 = registry._import_provider(
            user_providers / "myapi" / "provider.py",
            tool_name="fetch",
            source="user",
        )

        # Both should import successfully
        assert cls1 is not None
        assert cls2 is not None

        # They should be different classes (from different files)
        assert cls1 is not cls2

    def test_module_names_include_tool_name(self, tmp_path):
        """Module names include tool name so same provider name across tools is safe."""
        registry = get_provider_registry()

        # Create providers with same name for different tools
        fetch_providers = tmp_path / "fetch" / "providers"
        map_providers = tmp_path / "map" / "providers"

        self._create_provider(
            fetch_providers,
            "apify",
            '''
class ApifyFetcher:
    name = "apify"
    url_patterns = []
    requires_env = []
''',
        )

        self._create_provider(
            map_providers,
            "apify",
            '''
class ApifyMapper:
    name = "apify"
    url_patterns = []
    requires_env = []
''',
        )

        cls1 = registry._import_provider(
            fetch_providers / "apify" / "provider.py",
            tool_name="fetch",
            source="builtin",
        )
        cls2 = registry._import_provider(
            map_providers / "apify" / "provider.py",
            tool_name="map",
            source="builtin",
        )

        assert cls1 is not None
        assert cls2 is not None
        assert cls1 is not cls2
        assert cls1.__name__ == "ApifyFetcher"
        assert cls2.__name__ == "ApifyMapper"
