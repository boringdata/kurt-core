"""
Test fixtures for tool tests.

Provides fixtures for testing tools with database persistence and
provider registry mocking.

Uses Dolt-based fixtures from kurt.conftest (discovered automatically by pytest).
"""

from __future__ import annotations

import os

import pytest

from kurt.tools.core.provider import ProviderRegistry

# ============================================================================
# Provider Registry Fixtures
# ============================================================================


@pytest.fixture
def clean_registry():
    """Fresh ProviderRegistry for each test.

    Resets the singleton before and after the test. Does NOT run
    filesystem discovery, so tests start with an empty registry.
    """
    ProviderRegistry._instance = None
    registry = ProviderRegistry()
    yield registry
    ProviderRegistry._instance = None


@pytest.fixture
def mock_fetch_registry(clean_registry):
    """Registry pre-loaded with mock fetch providers.

    Injects mock classes (not instances) into the registry so that
    ``get_provider()`` returns a fresh mock on each call.
    """
    from kurt.tools.fetch.providers.apify.mock import MockApifyFetcher
    from kurt.tools.fetch.providers.firecrawl.mock import MockFirecrawlFetcher
    from kurt.tools.fetch.providers.httpx.mock import MockHttpxFetcher
    from kurt.tools.fetch.providers.tavily.mock import MockTavilyFetcher
    from kurt.tools.fetch.providers.trafilatura.mock import MockTrafilaturaFetcher
    from kurt.tools.fetch.providers.twitterapi.mock import MockTwitterApiFetcher

    clean_registry._providers["fetch"] = {
        "trafilatura": MockTrafilaturaFetcher,
        "httpx": MockHttpxFetcher,
        "tavily": MockTavilyFetcher,
        "firecrawl": MockFirecrawlFetcher,
        "apify": MockApifyFetcher,
        "twitterapi": MockTwitterApiFetcher,
    }
    clean_registry._provider_meta["fetch"] = {
        name: {
            "name": name,
            "version": "mock",
            "url_patterns": cls.url_patterns,
            "requires_env": cls.requires_env,
            "description": (cls.__doc__ or "").strip(),
            "_source": "mock",
        }
        for name, cls in clean_registry._providers["fetch"].items()
    }
    clean_registry._discovered = True
    return clean_registry


@pytest.fixture
def mock_map_registry(clean_registry):
    """Registry pre-loaded with mock map providers.

    Injects mock classes (not instances) into the registry so that
    ``get_provider()`` returns a fresh mock on each call.
    """
    from kurt.tools.map.providers.apify.mock import MockApifyMapper
    from kurt.tools.map.providers.cms.mock import MockCmsMapper
    from kurt.tools.map.providers.crawl.mock import MockCrawlMapper
    from kurt.tools.map.providers.folder.mock import MockFolderMapper
    from kurt.tools.map.providers.rss.mock import MockRssMapper
    from kurt.tools.map.providers.sitemap.mock import MockSitemapMapper

    clean_registry._providers["map"] = {
        "sitemap": MockSitemapMapper,
        "rss": MockRssMapper,
        "crawl": MockCrawlMapper,
        "cms": MockCmsMapper,
        "folder": MockFolderMapper,
        "apify": MockApifyMapper,
    }
    clean_registry._provider_meta["map"] = {
        name: {
            "name": name,
            "version": "mock",
            "url_patterns": cls.url_patterns,
            "requires_env": cls.requires_env,
            "description": (cls.__doc__ or "").strip(),
            "_source": "mock",
        }
        for name, cls in clean_registry._providers["map"].items()
    }
    clean_registry._discovered = True
    return clean_registry


@pytest.fixture
def mock_full_registry(clean_registry):
    """Registry pre-loaded with ALL mock providers (fetch + map)."""
    from kurt.tools.fetch.providers.apify.mock import MockApifyFetcher as MockApifyFetchProvider
    from kurt.tools.fetch.providers.firecrawl.mock import MockFirecrawlFetcher
    from kurt.tools.fetch.providers.httpx.mock import MockHttpxFetcher
    from kurt.tools.fetch.providers.tavily.mock import MockTavilyFetcher
    from kurt.tools.fetch.providers.trafilatura.mock import MockTrafilaturaFetcher
    from kurt.tools.fetch.providers.twitterapi.mock import MockTwitterApiFetcher
    from kurt.tools.map.providers.apify.mock import MockApifyMapper as MockApifyMapProvider
    from kurt.tools.map.providers.cms.mock import MockCmsMapper
    from kurt.tools.map.providers.crawl.mock import MockCrawlMapper
    from kurt.tools.map.providers.folder.mock import MockFolderMapper
    from kurt.tools.map.providers.rss.mock import MockRssMapper
    from kurt.tools.map.providers.sitemap.mock import MockSitemapMapper

    fetch_providers = {
        "trafilatura": MockTrafilaturaFetcher,
        "httpx": MockHttpxFetcher,
        "tavily": MockTavilyFetcher,
        "firecrawl": MockFirecrawlFetcher,
        "apify": MockApifyFetchProvider,
        "twitterapi": MockTwitterApiFetcher,
    }
    map_providers = {
        "sitemap": MockSitemapMapper,
        "rss": MockRssMapper,
        "crawl": MockCrawlMapper,
        "cms": MockCmsMapper,
        "folder": MockFolderMapper,
        "apify": MockApifyMapProvider,
    }

    clean_registry._providers["fetch"] = fetch_providers
    clean_registry._providers["map"] = map_providers

    for tool_name, providers in [("fetch", fetch_providers), ("map", map_providers)]:
        clean_registry._provider_meta[tool_name] = {
            name: {
                "name": name,
                "version": "mock",
                "url_patterns": cls.url_patterns,
                "requires_env": cls.requires_env,
                "description": (cls.__doc__ or "").strip(),
                "_source": "mock",
            }
            for name, cls in providers.items()
        }

    clean_registry._discovered = True
    return clean_registry


# ============================================================================
# Environment Fixtures
# ============================================================================


@pytest.fixture
def clean_env(monkeypatch):
    """Environment without any provider API tokens."""
    for var in [
        "TAVILY_API_KEY",
        "FIRECRAWL_API_KEY",
        "APIFY_API_KEY",
        "TWITTERAPI_API_KEY",
        "NOTION_TOKEN",
        "SANITY_TOKEN",
    ]:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def all_provider_env(monkeypatch):
    """Environment with all provider tokens set to test values."""
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-firecrawl-key")
    monkeypatch.setenv("APIFY_API_KEY", "test-apify-key")
    monkeypatch.setenv("TWITTERAPI_API_KEY", "test-twitterapi-key")


# ============================================================================
# Project Fixtures
# ============================================================================


@pytest.fixture
def project_with_custom_provider(tmp_path):
    """Temporary project with a custom provider for testing discovery.

    Creates:
    - kurt.toml (project marker)
    - kurt/tools/fetch/providers/custom/provider.py (custom provider)

    Yields (project_path, old_cwd) tuple.
    """
    project = tmp_path / "test-project"
    project.mkdir()
    (project / "kurt.toml").write_text('[project]\nname = "test"\n')

    provider_dir = project / "kurt" / "tools" / "fetch" / "providers" / "custom"
    provider_dir.mkdir(parents=True)
    (provider_dir / "provider.py").write_text(
        'class CustomFetcher:\n'
        '    name = "custom"\n'
        '    version = "1.0.0"\n'
        '    url_patterns = ["*custom.example.com/*"]\n'
        '    requires_env = []\n'
        '    def fetch(self, url, **kwargs):\n'
        '        from kurt.tools.fetch.core.base import FetchResult\n'
        '        return FetchResult(content="custom", success=True)\n'
    )

    old_cwd = os.getcwd()
    os.chdir(project)
    yield project
    os.chdir(old_cwd)


# ============================================================================
# Individual Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_trafilatura(mock_fetch_registry):
    """Configured trafilatura mock instance."""
    return mock_fetch_registry.get_provider("fetch", "trafilatura")


@pytest.fixture
def mock_httpx(mock_fetch_registry):
    """Configured httpx mock instance."""
    return mock_fetch_registry.get_provider("fetch", "httpx")


@pytest.fixture
def mock_sitemap(mock_map_registry):
    """Configured sitemap mock instance."""
    return mock_map_registry.get_provider("map", "sitemap")


@pytest.fixture
def mock_rss(mock_map_registry):
    """Configured RSS mock instance."""
    return mock_map_registry.get_provider("map", "rss")


# ============================================================================
# Database Fixtures (original)
# ============================================================================


@pytest.fixture
def tmp_sqlmodel_project(tmp_project):
    """
    Create a temporary project with SQLModel tables for tool persistence tests.

    This fixture now uses Dolt (not SQLite) since SQLite support was removed.
    It wraps the tmp_project fixture from kurt.conftest.

    Sets up:
    - Temp directory with .dolt database
    - kurt.config file
    - Dolt SQL server on a unique port
    - map_documents and fetch_documents tables

    Yields:
        Path: The temp project path
    """
    # tmp_project already sets up everything needed
    yield tmp_project


@pytest.fixture
def tmp_dolt_project(tmp_project):
    """
    Alias for tmp_project.

    Use tmp_sqlmodel_project or tmp_project instead.
    """
    yield tmp_project


@pytest.fixture
def tool_context_with_sqlmodel(tmp_sqlmodel_project):
    """
    Create a ToolContext with database project for testing persistence.

    Use this fixture when testing tool execution with real database writes.
    """
    from kurt.tools.core.base import ToolContext

    repo_path = tmp_sqlmodel_project
    return ToolContext(
        settings={"project_root": str(repo_path)},
    )


@pytest.fixture
def tool_context_with_dolt(tmp_dolt_project):
    """
    Alias for tool_context_with_sqlmodel.
    """
    from kurt.tools.core.base import ToolContext

    repo_path = tmp_dolt_project
    return ToolContext(
        settings={"project_root": str(repo_path)},
    )
