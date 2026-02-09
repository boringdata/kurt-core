"""
Unit tests for ProviderRegistry and provider discovery.
"""

from __future__ import annotations

import pytest

from kurt.tools.core.errors import ProviderNotFoundError
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

    def test_discover_skips_invalid_providers(self, tmp_path, monkeypatch):
        """Discovery skips files that fail to import or have no provider class."""
        project_dir = tmp_path / "project"
        providers_dir = project_dir / "kurt" / "tools" / "fetch" / "providers"

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

        monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))

        registry = get_provider_registry()
        registry.discover()  # Should not raise

        providers = registry.list_providers("fetch")
        assert len(providers) == 0

    def test_discover_is_idempotent(self, tmp_path, monkeypatch):
        """Calling discover() multiple times is safe."""
        project_dir = tmp_path / "project"
        self._create_provider(
            project_dir / "kurt" / "tools" / "fetch" / "providers",
            "test",
            '''
class TestFetcher:
    name = "test"
    url_patterns = []
    requires_env = []
''',
        )

        monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))

        registry = get_provider_registry()
        registry.discover()
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
    def registry_with_providers(self, tmp_path, monkeypatch):
        """Set up registry with multiple providers with URL patterns."""
        project_dir = tmp_path / "project"
        providers_dir = project_dir / "kurt" / "tools" / "fetch" / "providers"

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

        monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))

        registry = get_provider_registry()
        registry.discover()
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
        """Falls back to wildcard provider for unknown URLs."""
        matched = registry_with_providers.match_provider(
            "fetch", "https://random-site.com/article"
        )
        assert matched == "default"

    def test_match_unknown_tool(self, registry_with_providers):
        """Returns None for unknown tool."""
        matched = registry_with_providers.match_provider(
            "nonexistent", "https://example.com"
        )
        assert matched is None

    def test_match_no_providers(self):
        """Returns None when tool has no providers."""
        registry = get_provider_registry()
        matched = registry.match_provider("fetch", "https://example.com")
        assert matched is None


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

    def test_empty_when_no_providers(self):
        """Returns empty dict when no providers found."""
        registry = get_provider_registry()
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
