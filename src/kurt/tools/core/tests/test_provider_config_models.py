"""Tests for provider ConfigModel class attributes.

Verifies that all builtin providers have ConfigModel set and that
the models are valid Pydantic BaseModel subclasses.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel


class TestFetchProviderConfigModels:
    """Verify all fetch providers have ConfigModel."""

    def test_trafilatura_has_config_model(self):
        from kurt.tools.fetch.engines.trafilatura import TrafilaturaFetcher

        assert hasattr(TrafilaturaFetcher, "ConfigModel")
        assert issubclass(TrafilaturaFetcher.ConfigModel, BaseModel)

    def test_httpx_has_config_model(self):
        from kurt.tools.fetch.engines.httpx import HttpxFetcher

        assert hasattr(HttpxFetcher, "ConfigModel")
        assert issubclass(HttpxFetcher.ConfigModel, BaseModel)

    def test_tavily_has_config_model(self):
        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        assert hasattr(TavilyFetcher, "ConfigModel")
        assert issubclass(TavilyFetcher.ConfigModel, BaseModel)

    def test_firecrawl_has_config_model(self):
        from kurt.tools.fetch.engines.firecrawl import FirecrawlFetcher

        assert hasattr(FirecrawlFetcher, "ConfigModel")
        assert issubclass(FirecrawlFetcher.ConfigModel, BaseModel)

    def test_apify_has_config_model(self):
        from kurt.tools.fetch.engines.apify import ApifyFetcher

        assert hasattr(ApifyFetcher, "ConfigModel")
        assert issubclass(ApifyFetcher.ConfigModel, BaseModel)

    def test_twitterapi_has_config_model(self):
        from kurt.tools.fetch.engines.twitterapi import TwitterApiFetcher

        assert hasattr(TwitterApiFetcher, "ConfigModel")
        assert issubclass(TwitterApiFetcher.ConfigModel, BaseModel)


class TestMapProviderConfigModels:
    """Verify all map providers have ConfigModel."""

    def test_sitemap_has_config_model(self):
        from kurt.tools.map.engines.sitemap import SitemapEngine

        assert hasattr(SitemapEngine, "ConfigModel")
        assert issubclass(SitemapEngine.ConfigModel, BaseModel)

    def test_rss_has_config_model(self):
        from kurt.tools.map.engines.rss import RssEngine

        assert hasattr(RssEngine, "ConfigModel")
        assert issubclass(RssEngine.ConfigModel, BaseModel)

    def test_crawl_has_config_model(self):
        from kurt.tools.map.engines.crawl import CrawlEngine

        assert hasattr(CrawlEngine, "ConfigModel")
        assert issubclass(CrawlEngine.ConfigModel, BaseModel)

    def test_cms_has_config_model(self):
        from kurt.tools.map.engines.cms import CmsEngine

        assert hasattr(CmsEngine, "ConfigModel")
        assert issubclass(CmsEngine.ConfigModel, BaseModel)

    def test_folder_has_config_model(self):
        from kurt.tools.map.engines.folder import FolderEngine

        assert hasattr(FolderEngine, "ConfigModel")
        assert issubclass(FolderEngine.ConfigModel, BaseModel)

    def test_apify_has_config_model(self):
        from kurt.tools.map.engines.apify import ApifyEngine

        assert hasattr(ApifyEngine, "ConfigModel")
        assert issubclass(ApifyEngine.ConfigModel, BaseModel)


class TestConfigModelDefaults:
    """Verify config models can be instantiated with defaults."""

    @pytest.mark.parametrize(
        "config_path",
        [
            "kurt.tools.fetch.providers.trafilatura.config.TrafilaturaProviderConfig",
            "kurt.tools.fetch.providers.httpx.config.HttpxProviderConfig",
            "kurt.tools.fetch.providers.tavily.config.TavilyProviderConfig",
            "kurt.tools.fetch.providers.firecrawl.config.FirecrawlProviderConfig",
            "kurt.tools.fetch.providers.apify.config.ApifyFetchProviderConfig",
            "kurt.tools.fetch.providers.twitterapi.config.TwitterApiProviderConfig",
            "kurt.tools.map.providers.sitemap.config.SitemapProviderConfig",
            "kurt.tools.map.providers.rss.config.RssProviderConfig",
            "kurt.tools.map.providers.crawl.config.CrawlProviderConfig",
            "kurt.tools.map.providers.cms.config.CmsProviderConfig",
            "kurt.tools.map.providers.folder.config.FolderProviderConfig",
            "kurt.tools.map.providers.apify.config.ApifyMapProviderConfig",
        ],
    )
    def test_config_model_has_defaults(self, config_path: str):
        """All config models can be instantiated with no arguments."""
        import importlib

        module_path, class_name = config_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        config_class = getattr(module, class_name)

        # Should not raise
        instance = config_class()
        assert isinstance(instance, BaseModel)

    @pytest.mark.parametrize(
        "config_path",
        [
            "kurt.tools.fetch.providers.trafilatura.config.TrafilaturaProviderConfig",
            "kurt.tools.fetch.providers.httpx.config.HttpxProviderConfig",
            "kurt.tools.fetch.providers.tavily.config.TavilyProviderConfig",
            "kurt.tools.fetch.providers.firecrawl.config.FirecrawlProviderConfig",
            "kurt.tools.fetch.providers.apify.config.ApifyFetchProviderConfig",
            "kurt.tools.fetch.providers.twitterapi.config.TwitterApiProviderConfig",
            "kurt.tools.map.providers.sitemap.config.SitemapProviderConfig",
            "kurt.tools.map.providers.rss.config.RssProviderConfig",
            "kurt.tools.map.providers.crawl.config.CrawlProviderConfig",
            "kurt.tools.map.providers.cms.config.CmsProviderConfig",
            "kurt.tools.map.providers.folder.config.FolderProviderConfig",
            "kurt.tools.map.providers.apify.config.ApifyMapProviderConfig",
        ],
    )
    def test_config_model_serializes_to_dict(self, config_path: str):
        """All config models can serialize to dict."""
        import importlib

        module_path, class_name = config_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        config_class = getattr(module, class_name)

        instance = config_class()
        d = instance.model_dump()
        assert isinstance(d, dict)
        assert len(d) > 0
