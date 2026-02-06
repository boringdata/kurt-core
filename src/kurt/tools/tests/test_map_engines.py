"""Tests for map engines module."""

import os
from unittest.mock import MagicMock, patch

import pytest

from kurt.tools.errors import AuthError
from kurt.tools.map.engines import EngineRegistry
from kurt.tools.map.engines.apify import ApifyEngine, ApifyMapperConfig
from kurt.tools.map.engines.crawl import CrawlEngine
from kurt.tools.map.engines.rss import RssEngine
from kurt.tools.map.engines.sitemap import SitemapEngine
from kurt.tools.map.models import DocType

# Skip Apify tests if no API key is configured
APIFY_API_KEY = os.getenv("APIFY_API_KEY")
skip_without_apify = pytest.mark.skipif(
    not APIFY_API_KEY,
    reason="APIFY_API_KEY not set - skipping Apify integration tests",
)


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
        # Crawl returns at least the source URL when successful
        assert result.count >= 0
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

    def test_apify_engine_requires_api_key(self):
        """Test that Apify engine requires an API key."""
        # Clear env var to test error case
        with patch.dict(os.environ, {}, clear=True):
            if "APIFY_API_KEY" in os.environ:
                del os.environ["APIFY_API_KEY"]
            with pytest.raises(AuthError, match="APIFY_API_KEY"):
                ApifyEngine()

    def test_apify_engine_with_config_validates_api_key(self):
        """Test creating Apify engine with config validates API key."""
        config = ApifyMapperConfig(
            api_key="test_key",
            platform="twitter",
        )
        # Should not raise - api_key is provided in config
        engine = ApifyEngine(config)
        assert engine._config.api_key == "test_key"
        assert engine._config.platform == "twitter"

    @skip_without_apify
    def test_apify_engine_creation(self):
        """Test creating Apify engine with real API key."""
        engine = ApifyEngine()
        assert engine is not None

    @skip_without_apify
    def test_apify_engine_map_profile(self):
        """Test mapping profiles with Apify (requires API key)."""
        config = ApifyMapperConfig(platform="twitter")
        engine = ApifyEngine(config)
        result = engine.map("@testuser", DocType.PROFILE)
        assert result.metadata["engine"] == "apify"
        assert result.metadata["platform"] == "twitter"

    @skip_without_apify
    def test_apify_engine_map_posts(self):
        """Test mapping posts with Apify (requires API key)."""
        config = ApifyMapperConfig(platform="twitter")
        engine = ApifyEngine(config)
        result = engine.map("AI agents", DocType.POSTS)
        assert result.metadata["engine"] == "apify"
        assert result.metadata["platform"] == "twitter"


class TestApifyEngineMocked:
    """Test ApifyEngine with mocked client."""

    @patch("kurt.tools.map.engines.apify.ApifyClient")
    def test_apify_engine_with_mock_client(self, mock_client_class):
        """Test Apify engine with mocked client."""
        # Setup mock
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock the fetch response
        mock_item = MagicMock()
        mock_item.url = "https://twitter.com/testuser"
        mock_item.id = "testuser"
        mock_client.fetch.return_value = [mock_item]

        # Create engine with config
        config = ApifyMapperConfig(api_key="fake_key", platform="twitter")
        engine = ApifyEngine(config)

        # Test mapping
        result = engine.map("AI agents", DocType.POSTS)

        assert result.count == 1
        assert result.urls == ["https://twitter.com/testuser"]
        assert result.metadata["engine"] == "apify"
        assert result.metadata["platform"] == "twitter"

    @patch("kurt.tools.map.engines.apify.ApifyClient")
    def test_apify_engine_detect_platform_from_url(self, mock_client_class):
        """Test platform detection from URL."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.fetch.return_value = []

        config = ApifyMapperConfig(api_key="fake_key")
        engine = ApifyEngine(config)

        # Test Twitter detection
        assert engine._detect_platform("https://twitter.com/user") == "twitter"
        assert engine._detect_platform("https://x.com/user") == "twitter"

        # Test LinkedIn detection
        assert engine._detect_platform("https://linkedin.com/in/user") == "linkedin"

        # Test Substack detection
        assert engine._detect_platform("https://newsletter.substack.com") == "substack"

        # Test Threads detection
        assert engine._detect_platform("https://threads.net/user") == "threads"

        # Test @ prefix (assumes Twitter)
        assert engine._detect_platform("@username") == "twitter"

        # Test unknown
        assert engine._detect_platform("random query") is None


class TestEngineIntegration:
    """Test engine integration."""

    def test_non_apify_engines_inherit_from_base_mapper(self):
        """Test non-Apify engines inherit from BaseMapper."""
        from kurt.tools.map.core import BaseMapper

        engines = [SitemapEngine(), CrawlEngine(), RssEngine()]
        for engine in engines:
            assert isinstance(engine, BaseMapper)

    @patch("kurt.tools.map.engines.apify.ApifyClient")
    def test_apify_engine_inherits_from_base_mapper(self, mock_client_class):
        """Test Apify engine inherits from BaseMapper."""
        from kurt.tools.map.core import BaseMapper

        mock_client_class.return_value = MagicMock()

        config = ApifyMapperConfig(api_key="fake_key", platform="twitter")
        engine = ApifyEngine(config)
        assert isinstance(engine, BaseMapper)

    def test_all_engines_support_doc_types(self):
        """Test all non-Apify engines support different doc types."""
        engines = [SitemapEngine(), CrawlEngine(), RssEngine()]

        for engine in engines:
            for doc_type in [DocType.DOC, DocType.PROFILE, DocType.POSTS]:
                result = engine.map("https://example.com", doc_type)
                assert result is not None

    @patch("kurt.tools.map.engines.apify.ApifyClient")
    def test_apify_with_multiple_platforms(self, mock_client_class):
        """Test Apify engine with different platforms."""
        mock_client_class.return_value = MagicMock()

        platforms = ["twitter", "linkedin"]

        for platform in platforms:
            config = ApifyMapperConfig(api_key="fake_key", platform=platform)
            engine = ApifyEngine(config)
            assert engine._config.platform == platform
