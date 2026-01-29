"""Tests for map engines module."""

import pytest

from kurt.tools.map.engines import EngineRegistry
from kurt.tools.map.engines.sitemap import SitemapEngine
from kurt.tools.map.engines.crawl import CrawlEngine
from kurt.tools.map.engines.rss import RssEngine
from kurt.tools.map.engines.apify import ApifyEngine, ApifyMapperConfig
from kurt.tools.map.models import DocType


class TestEngineRegistry:
    """Test EngineRegistry."""

    def test_register_engine(self):
        """Test registering an engine."""
        EngineRegistry.register("test_engine", SitemapEngine)
        assert "test_engine" in EngineRegistry.list_engines()

    def test_get_engine(self):
        """Test getting a registered engine."""
        EngineRegistry.register("sitemap", SitemapEngine)
        engine_class = EngineRegistry.get("sitemap")
        assert engine_class == SitemapEngine

    def test_get_unknown_engine_raises(self):
        """Test getting unknown engine raises KeyError."""
        with pytest.raises(KeyError, match="Unknown engine"):
            EngineRegistry.get("nonexistent")

    def test_list_engines(self):
        """Test listing registered engines."""
        EngineRegistry.register("engine1", SitemapEngine)
        EngineRegistry.register("engine2", CrawlEngine)

        engines = EngineRegistry.list_engines()
        assert len(engines) >= 2

    def test_is_available(self):
        """Test checking engine availability."""
        EngineRegistry.register("available", SitemapEngine)
        assert EngineRegistry.is_available("available") is True
        assert EngineRegistry.is_available("unavailable") is False


class TestSitemapEngine:
    """Test SitemapEngine."""

    def test_sitemap_engine_creation(self):
        """Test creating sitemap engine."""
        engine = SitemapEngine()
        assert engine is not None

    def test_sitemap_engine_map(self):
        """Test mapping with sitemap engine."""
        engine = SitemapEngine()
        result = engine.map("https://example.com", DocType.DOC)
        assert result.count == 0
        assert result.urls == []
        assert result.metadata["engine"] == "sitemap"


class TestCrawlEngine:
    """Test CrawlEngine."""

    def test_crawl_engine_creation(self):
        """Test creating crawl engine."""
        engine = CrawlEngine()
        assert engine is not None

    def test_crawl_engine_map(self):
        """Test mapping with crawl engine."""
        engine = CrawlEngine()
        result = engine.map("https://example.com", DocType.DOC)
        assert result.count == 0
        assert result.urls == []
        assert result.metadata["engine"] == "crawl"


class TestRssEngine:
    """Test RssEngine."""

    def test_rss_engine_creation(self):
        """Test creating RSS engine."""
        engine = RssEngine()
        assert engine is not None

    def test_rss_engine_map(self):
        """Test mapping with RSS engine."""
        engine = RssEngine()
        result = engine.map("https://example.com", DocType.DOC)
        assert result.count == 0
        assert result.urls == []
        assert result.metadata["engine"] == "rss"


class TestApifyEngine:
    """Test ApifyEngine."""

    def test_apify_engine_creation(self):
        """Test creating Apify engine."""
        engine = ApifyEngine()
        assert engine is not None

    def test_apify_engine_with_config(self):
        """Test creating Apify engine with config."""
        config = ApifyMapperConfig(
            api_key="test_key",
            platform="twitter",
        )
        engine = ApifyEngine(config)
        assert engine.config.api_key == "test_key"
        assert engine.config.platform == "twitter"

    def test_apify_engine_map_profile(self):
        """Test mapping profiles with Apify."""
        engine = ApifyEngine()
        result = engine.map("twitter_search_query", DocType.PROFILE)
        assert result.count == 0
        assert result.urls == []
        assert result.metadata["engine"] == "apify"

    def test_apify_engine_map_posts(self):
        """Test mapping posts with Apify."""
        engine = ApifyEngine()
        result = engine.map("twitter_user", DocType.POSTS)
        assert result.count == 0
        assert result.urls == []
        assert result.metadata["engine"] == "apify"


class TestEngineIntegration:
    """Test engine integration."""

    def test_all_engines_inherit_from_base_mapper(self):
        """Test all engines inherit from BaseMapper."""
        from kurt.tools.map.core import BaseMapper

        engines = [SitemapEngine(), CrawlEngine(), RssEngine(), ApifyEngine()]
        for engine in engines:
            assert isinstance(engine, BaseMapper)

    def test_all_engines_support_doc_types(self):
        """Test all engines support different doc types."""
        engines = [SitemapEngine(), CrawlEngine(), RssEngine()]

        for engine in engines:
            for doc_type in [DocType.DOC, DocType.PROFILE, DocType.POSTS]:
                result = engine.map("https://example.com", doc_type)
                assert result is not None

    def test_apify_with_multiple_platforms(self):
        """Test Apify engine with different platforms."""
        platforms = ["twitter", "linkedin", "instagram"]

        for platform in platforms:
            config = ApifyMapperConfig(platform=platform)
            engine = ApifyEngine(config)
            assert engine.config.platform == platform
