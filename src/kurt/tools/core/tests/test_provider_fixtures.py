"""Tests for provider registry fixtures."""

from __future__ import annotations

import os

import pytest

from kurt.tools.core.provider import ProviderRegistry
from kurt.tools.fetch.core.base import FetchResult
from kurt.tools.map.core.base import MapperResult


class TestCleanRegistry:
    """Test clean_registry fixture."""

    def test_clean_registry_is_empty(self, clean_registry):
        assert clean_registry._providers == {}
        assert clean_registry._provider_meta == {}

    def test_clean_registry_not_discovered(self, clean_registry):
        assert clean_registry._discovered is False

    def test_clean_registry_is_singleton(self, clean_registry):
        assert ProviderRegistry() is clean_registry


class TestMockFetchRegistry:
    """Test mock_fetch_registry fixture."""

    def test_has_all_fetch_providers(self, mock_fetch_registry):
        providers = mock_fetch_registry._providers.get("fetch", {})
        expected = {"trafilatura", "httpx", "tavily", "firecrawl", "apify", "twitterapi"}
        assert set(providers.keys()) == expected

    def test_get_provider_returns_mock(self, mock_fetch_registry):
        provider = mock_fetch_registry.get_provider("fetch", "trafilatura")
        assert provider is not None
        assert provider.name == "trafilatura"
        assert provider.version == "mock"

    def test_mock_provider_works(self, mock_fetch_registry):
        provider = mock_fetch_registry.get_provider("fetch", "trafilatura")
        result = provider.fetch("https://example.com/page")
        assert isinstance(result, FetchResult)
        assert result.success is True

    def test_list_providers(self, mock_fetch_registry):
        providers = mock_fetch_registry.list_providers("fetch")
        assert len(providers) == 6

    def test_metadata_populated(self, mock_fetch_registry):
        meta = mock_fetch_registry._provider_meta.get("fetch", {})
        assert "trafilatura" in meta
        assert meta["trafilatura"]["version"] == "mock"
        assert meta["trafilatura"]["requires_env"] == []


class TestMockMapRegistry:
    """Test mock_map_registry fixture."""

    def test_has_all_map_providers(self, mock_map_registry):
        providers = mock_map_registry._providers.get("map", {})
        expected = {"sitemap", "rss", "crawl", "cms", "folder", "apify"}
        assert set(providers.keys()) == expected

    def test_get_provider_returns_mock(self, mock_map_registry):
        provider = mock_map_registry.get_provider("map", "sitemap")
        assert provider is not None
        assert provider.name == "sitemap"
        assert provider.version == "mock"

    def test_mock_provider_works(self, mock_map_registry):
        provider = mock_map_registry.get_provider("map", "sitemap")
        result = provider.map("https://example.com/sitemap.xml")
        assert isinstance(result, MapperResult)
        assert len(result.urls) > 0


class TestMockFullRegistry:
    """Test mock_full_registry fixture."""

    def test_has_both_tools(self, mock_full_registry):
        assert "fetch" in mock_full_registry._providers
        assert "map" in mock_full_registry._providers

    def test_fetch_providers_count(self, mock_full_registry):
        assert len(mock_full_registry._providers["fetch"]) == 6

    def test_map_providers_count(self, mock_full_registry):
        assert len(mock_full_registry._providers["map"]) == 6

    def test_url_matching_works(self, mock_full_registry):
        matched = mock_full_registry.match_provider(
            "fetch", "https://x.com/user/status/123"
        )
        assert matched in ("apify", "twitterapi")

    def test_resolve_provider_works(self, mock_full_registry):
        resolved = mock_full_registry.resolve_provider(
            "fetch", provider_name="trafilatura"
        )
        assert resolved == "trafilatura"


class TestEnvironmentFixtures:
    """Test environment fixtures."""

    def test_clean_env_removes_tokens(self, clean_env):
        assert os.environ.get("TAVILY_API_KEY") is None
        assert os.environ.get("FIRECRAWL_API_KEY") is None
        assert os.environ.get("APIFY_API_KEY") is None
        assert os.environ.get("TWITTERAPI_API_KEY") is None

    def test_all_provider_env_sets_tokens(self, all_provider_env):
        assert os.environ.get("TAVILY_API_KEY") == "test-tavily-key"
        assert os.environ.get("FIRECRAWL_API_KEY") == "test-firecrawl-key"
        assert os.environ.get("APIFY_API_KEY") == "test-apify-key"
        assert os.environ.get("TWITTERAPI_API_KEY") == "test-twitterapi-key"


class TestIndividualMockFixtures:
    """Test individual mock fixtures."""

    def test_mock_trafilatura(self, mock_trafilatura):
        assert mock_trafilatura.name == "trafilatura"
        result = mock_trafilatura.fetch("https://example.com")
        assert result.success is True

    def test_mock_httpx(self, mock_httpx):
        assert mock_httpx.name == "httpx"
        result = mock_httpx.fetch("https://example.com")
        assert result.success is True

    def test_mock_sitemap(self, mock_sitemap):
        assert mock_sitemap.name == "sitemap"
        result = mock_sitemap.map("https://example.com/sitemap.xml")
        assert len(result.urls) > 0

    def test_mock_rss(self, mock_rss):
        assert mock_rss.name == "rss"
        result = mock_rss.map("https://example.com/feed.xml")
        assert len(result.urls) > 0


class TestProjectWithCustomProvider:
    """Test project_with_custom_provider fixture."""

    def test_project_has_kurt_toml(self, project_with_custom_provider):
        assert (project_with_custom_provider / "kurt.toml").exists()

    def test_custom_provider_file_exists(self, project_with_custom_provider):
        provider_py = (
            project_with_custom_provider
            / "kurt"
            / "tools"
            / "fetch"
            / "providers"
            / "custom"
            / "provider.py"
        )
        assert provider_py.exists()

    def test_registry_discovers_custom_provider(self, project_with_custom_provider):
        registry = ProviderRegistry()
        registry.discover()
        provider = registry.get_provider("fetch", "custom")
        assert provider is not None
        result = provider.fetch("https://custom.example.com/page")
        assert result.content == "custom"
        ProviderRegistry._instance = None
