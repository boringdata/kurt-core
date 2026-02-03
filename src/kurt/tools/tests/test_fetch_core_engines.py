"""Tests for fetch core and engines modules."""

import pytest

from kurt.tools.fetch.core import BaseFetcher, FetchDocumentStorage, FetcherConfig, FetchResult
from kurt.tools.fetch.engines import EngineRegistry
from kurt.tools.fetch.engines.apify import ApifyEngine, ApifyFetcherConfig
from kurt.tools.fetch.engines.firecrawl import FirecrawlEngine
from kurt.tools.fetch.engines.tavily import TavilyEngine
from kurt.tools.fetch.engines.trafilatura import TrafilaturaFetcher
from kurt.tools.fetch.models import DocType


class TestFetcherConfig:
    """Test FetcherConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = FetcherConfig()
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.verify_ssl is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = FetcherConfig(
            timeout=60.0,
            max_retries=5,
            verify_ssl=False,
            user_agent="Custom/1.0",
        )
        assert config.timeout == 60.0
        assert config.max_retries == 5
        assert config.user_agent == "Custom/1.0"


class TestFetchResult:
    """Test FetchResult."""

    def test_empty_result(self):
        """Test empty result."""
        result = FetchResult()
        assert result.content == ""
        assert result.success is True
        assert result.error is None

    def test_result_with_content(self):
        """Test result with content."""
        result = FetchResult(
            content="Sample content",
            content_html="<p>Sample content</p>",
            metadata={"source": "example.com"},
        )
        assert result.content == "Sample content"
        assert result.content_html == "<p>Sample content</p>"


class MockFetcher(BaseFetcher):
    """Mock fetcher for testing."""

    def fetch(self, url: str) -> FetchResult:
        """Mock implementation."""
        return FetchResult(
            content=f"Content from {url}",
            metadata={"engine": "mock"},
        )


class TestBaseFetcher:
    """Test BaseFetcher."""

    def test_fetcher_creation(self):
        """Test creating a fetcher."""
        fetcher = MockFetcher()
        assert fetcher.config is not None

    def test_fetcher_with_config(self):
        """Test fetcher with custom config."""
        config = FetcherConfig(timeout=60.0)
        fetcher = MockFetcher(config)
        assert fetcher.config.timeout == 60.0

    def test_fetcher_fetch(self):
        """Test fetch method."""
        fetcher = MockFetcher()
        result = fetcher.fetch("https://example.com")
        assert "example.com" in result.content

    def test_create_document(self):
        """Test document creation."""
        fetcher = MockFetcher()
        doc = fetcher.create_document(
            url="https://example.com",
            content="Sample content",
            doc_type=DocType.PROFILE,
            engine="mock",
        )
        assert doc.public_url == "https://example.com"
        assert doc.doc_type == DocType.PROFILE
        assert doc.fetch_engine == "mock"


class TestFetchDocumentStorage:
    """Test FetchDocumentStorage."""

    def test_save_document(self):
        """Test saving a document."""
        from kurt.tools.fetch.models import FetchDocument

        doc = FetchDocument(document_id="test_1")
        result = FetchDocumentStorage.save_document(doc)
        assert result is True

    def test_get_by_url(self):
        """Test get_by_url returns None (not implemented)."""
        result = FetchDocumentStorage.get_by_url("https://example.com")
        assert result is None

    def test_count_by_status(self):
        """Test count_by_status returns 0 (not implemented)."""
        count = FetchDocumentStorage.count_by_status("SUCCESS")
        assert count == 0

    def test_count_pending(self):
        """Test count_pending returns 0 (not implemented)."""
        count = FetchDocumentStorage.count_pending()
        assert count == 0


class TestEngineRegistry:
    """Test fetch engine registry."""

    def test_register_engine(self):
        """Test registering an engine."""
        EngineRegistry.register("test_fetch", TrafilaturaFetcher)
        assert "test_fetch" in EngineRegistry.list_engines()

    def test_get_engine(self):
        """Test getting a registered engine."""
        EngineRegistry.register("trafilatura", TrafilaturaFetcher)
        engine_class = EngineRegistry.get("trafilatura")
        assert engine_class == TrafilaturaFetcher

    def test_get_unknown_engine_raises(self):
        """Test getting unknown engine raises KeyError."""
        with pytest.raises(KeyError, match="Unknown engine"):
            EngineRegistry.get("nonexistent_fetch")

    def test_is_available(self):
        """Test checking engine availability."""
        EngineRegistry.register("available_fetch", TrafilaturaFetcher)
        assert EngineRegistry.is_available("available_fetch") is True
        assert EngineRegistry.is_available("unavailable_fetch") is False


class TestTrafilaturaFetcher:
    """Test TrafilaturaFetcher."""

    def test_trafilatura_creation(self):
        """Test creating Trafilatura engine."""
        engine = TrafilaturaFetcher()
        assert engine is not None

    def test_trafilatura_fetch(self):
        """Test fetch with Trafilatura."""
        engine = TrafilaturaFetcher()
        result = engine.fetch("https://example.com")
        assert result.metadata["engine"] == "trafilatura"


class TestFirecrawlEngine:
    """Test FirecrawlEngine."""

    def test_firecrawl_creation(self):
        """Test creating Firecrawl engine."""
        engine = FirecrawlEngine()
        assert engine is not None

    def test_firecrawl_with_api_key(self):
        """Test Firecrawl with API key."""
        engine = FirecrawlEngine(api_key="test_key")
        assert engine.api_key == "test_key"

    def test_firecrawl_fetch(self):
        """Test fetch with Firecrawl."""
        engine = FirecrawlEngine()
        result = engine.fetch("https://example.com")
        assert result.metadata["engine"] == "firecrawl"


class TestTavilyEngine:
    """Test TavilyEngine."""

    def test_tavily_creation(self):
        """Test creating Tavily engine."""
        engine = TavilyEngine()
        assert engine is not None

    def test_tavily_with_api_key(self):
        """Test Tavily with API key."""
        engine = TavilyEngine(api_key="test_key")
        assert engine.api_key == "test_key"

    def test_tavily_fetch(self):
        """Test fetch with Tavily."""
        engine = TavilyEngine()
        result = engine.fetch("search query")
        assert result.metadata["engine"] == "tavily"


class TestApifyEngine:
    """Test ApifyEngine."""

    def test_apify_creation(self):
        """Test creating Apify engine."""
        engine = ApifyEngine()
        assert engine is not None

    def test_apify_with_config(self):
        """Test Apify with custom config."""
        config = ApifyFetcherConfig(
            api_key="test_key",
            platform="twitter",
        )
        engine = ApifyEngine(config)
        assert engine.config.api_key == "test_key"

    def test_apify_fetch(self):
        """Test fetch with Apify."""
        engine = ApifyEngine()
        result = engine.fetch("https://twitter.com/user")
        assert result.metadata["engine"] == "apify"


class TestEngineIntegration:
    """Test engine integration."""

    def test_all_fetch_engines_inherit_from_base(self):
        """Test all engines inherit from BaseFetcher."""
        engines = [
            TrafilaturaFetcher(),
            FirecrawlEngine(),
            TavilyEngine(),
            ApifyEngine(),
        ]
        for engine in engines:
            assert isinstance(engine, BaseFetcher)

    def test_all_engines_return_fetch_result(self):
        """Test all engines return FetchResult."""
        engines = [
            TrafilaturaFetcher(),
            FirecrawlEngine(),
            TavilyEngine(),
            ApifyEngine(),
        ]
        for engine in engines:
            result = engine.fetch("https://example.com")
            assert isinstance(result, FetchResult)

    def test_multi_platform_apify_config(self):
        """Test Apify with different platforms."""
        platforms = ["twitter", "linkedin", "instagram"]

        for platform in platforms:
            config = ApifyFetcherConfig(platform=platform)
            engine = ApifyEngine(config)
            assert engine.config.platform == platform
