"""End-to-end tests for map engines.

These tests use REAL HTTP requests with NO mocks to validate the complete
URL discovery flow from source input to MapperResult output.

Run with: pytest src/kurt/tools/e2e/test_map_e2e.py -v -s

Required environment variables:
- APIFY_API_KEY: For Apify social media mapping tests (optional - skips if not available)
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from kurt.tools.map.core import MapperConfig, MapperResult
from kurt.tools.map.engines import (
    CrawlEngine,
    RssEngine,
    SitemapEngine,
)

# =============================================================================
# Sitemap Engine E2E Tests (Free - No API Key Required)
# =============================================================================

@pytest.mark.e2e
class TestSitemapEngineE2E:
    """E2E tests for SitemapEngine with real HTTP requests."""

    def test_sitemap_python_docs(self):
        """Discover URLs from Python documentation sitemap."""
        engine = SitemapEngine()
        config = MapperConfig(max_urls=50)
        engine.config = config

        result = engine.map("https://docs.python.org/3/")

        # Validate MapperResult structure
        assert isinstance(result, MapperResult)
        assert result.count > 0, "Should discover URLs from Python docs sitemap"
        assert len(result.urls) == result.count

        # Validate URLs
        for url in result.urls[:10]:  # Check first 10
            assert url.startswith("https://docs.python.org/"), f"URL should be from Python docs: {url}"

        # Validate metadata
        assert result.metadata.get("engine") == "sitemap"
        assert "docs.python.org" in result.metadata.get("source", "")

        print(f"\nDiscovered {result.count} URLs from Python docs sitemap")
        print(f"Sample URLs: {result.urls[:5]}")

    def test_sitemap_with_limit(self):
        """Test that max_urls limit is respected."""
        config = MapperConfig(max_urls=10)
        engine = SitemapEngine(config=config)

        result = engine.map("https://docs.python.org/3/")

        assert result.count <= 10, "Should respect max_urls limit"
        assert len(result.urls) <= 10

    def test_sitemap_nonexistent(self):
        """Test handling of sites without sitemaps."""
        engine = SitemapEngine()
        result = engine.map("https://httpbin.org")

        # Should return empty with errors (httpbin has no sitemap)
        assert isinstance(result, MapperResult)
        # Either no URLs found or an error message
        if result.count == 0:
            assert len(result.errors) > 0, "Should report error for missing sitemap"

        print(f"\nNo sitemap result: {result.count} URLs, errors: {result.errors}")

    def test_sitemap_with_include_pattern(self):
        """Test URL filtering with include pattern."""
        config = MapperConfig(max_urls=100, include_pattern=r"/library/")
        engine = SitemapEngine(config=config)

        result = engine.map("https://docs.python.org/3/")

        # All URLs should match the include pattern
        for url in result.urls:
            assert "/library/" in url, f"URL should match include pattern: {url}"

        print(f"\nFiltered to {result.count} URLs matching '/library/'")

    def test_sitemap_metadata_validation(self):
        """Validate all metadata fields in sitemap results."""
        engine = SitemapEngine()
        result = engine.map("https://www.python.org")

        assert result.metadata is not None
        assert result.metadata.get("engine") == "sitemap"
        assert "source" in result.metadata
        assert "doc_type" in result.metadata

        print(f"\nMetadata fields: {list(result.metadata.keys())}")


# =============================================================================
# RSS Engine E2E Tests (Free - No API Key Required)
# =============================================================================

@pytest.mark.e2e
class TestRssEngineE2E:
    """E2E tests for RssEngine with real RSS/Atom feeds."""

    def test_rss_direct_feed_url(self):
        """Discover URLs from a direct RSS feed URL."""
        engine = RssEngine()

        # BBC News RSS feed (very stable)
        result = engine.map("https://feeds.bbci.co.uk/news/rss.xml")

        assert isinstance(result, MapperResult)
        assert result.count > 0, "Should discover entries from BBC RSS feed"

        # Validate URLs point to BBC articles
        for url in result.urls[:5]:
            assert "bbc.co" in url.lower() or "bbc.com" in url.lower(), f"URL should be from BBC: {url}"

        # Validate metadata
        assert result.metadata.get("engine") == "rss"

        print(f"\nDiscovered {result.count} URLs from BBC RSS feed")
        print(f"Sample URLs: {result.urls[:3]}")

    def test_rss_atom_feed(self):
        """Discover URLs from an Atom feed."""
        engine = RssEngine()

        # GitHub releases feed (Atom format)
        result = engine.map("https://github.com/python/cpython/releases.atom")

        assert isinstance(result, MapperResult)
        # GitHub might limit the feed entries
        if result.count > 0:
            for url in result.urls[:3]:
                assert "github.com" in url, f"URL should be from GitHub: {url}"
            print(f"\nDiscovered {result.count} URLs from GitHub Atom feed")
        else:
            # Atom parsing might fail - log the errors
            print(f"\nAtom feed parsing: {result.errors}")

    def test_rss_auto_discovery(self):
        """Test RSS feed auto-discovery from HTML page."""
        engine = RssEngine()

        # Python blog has RSS link in HTML
        result = engine.map("https://blog.python.org")

        assert isinstance(result, MapperResult)
        # Python blog should have RSS entries
        if result.count > 0:
            print(f"\nAuto-discovered {result.count} URLs from Python blog")
            print(f"Sample URLs: {result.urls[:3]}")
        else:
            # Feed might be empty or unreachable
            print(f"\nNo entries found, errors: {result.errors}")

    def test_rss_with_limit(self):
        """Test that max_urls limit is respected for RSS."""
        config = MapperConfig(max_urls=5)
        engine = RssEngine(config=config)

        result = engine.map("https://feeds.bbci.co.uk/news/rss.xml")

        assert result.count <= 5, "Should respect max_urls limit"

    def test_rss_invalid_feed(self):
        """Test handling of invalid feed URLs."""
        engine = RssEngine()
        result = engine.map("https://example.com")

        # example.com has no RSS feed
        assert isinstance(result, MapperResult)
        # Should either find nothing or report errors
        if result.count == 0:
            assert len(result.errors) > 0, "Should report error for missing feed"

        print(f"\nNo feed result: {result.count} URLs, errors: {result.errors}")


# =============================================================================
# Crawl Engine E2E Tests (Free - No API Key Required)
# =============================================================================

@pytest.mark.e2e
class TestCrawlEngineE2E:
    """E2E tests for CrawlEngine with real web crawling."""

    def test_crawl_simple_site(self):
        """Crawl a simple site with few pages."""
        config = MapperConfig(max_depth=1, max_urls=10, timeout=30.0)
        engine = CrawlEngine(config=config)

        # Example.com is simple and stable
        result = engine.map("https://example.com")

        assert isinstance(result, MapperResult)
        assert result.count >= 1, "Should at least include the start URL"
        assert "https://example.com" in result.urls[0].lower()

        # Validate metadata
        assert result.metadata.get("engine") == "crawl"

        print(f"\nCrawled {result.count} URLs from example.com")
        print(f"URLs: {result.urls}")

    def test_crawl_with_depth(self):
        """Test crawling with specific depth."""
        config = MapperConfig(max_depth=2, max_urls=20, timeout=30.0)
        engine = CrawlEngine(config=config)

        # Python docs have good internal linking
        result = engine.map("https://docs.python.org/3/library/json.html")

        assert isinstance(result, MapperResult)
        assert result.count >= 1

        # Should find links within Python docs
        python_doc_urls = [u for u in result.urls if "docs.python.org" in u]
        assert len(python_doc_urls) >= 1

        print(f"\nCrawled {result.count} URLs with depth=2")
        print(f"Sample URLs: {result.urls[:5]}")

    def test_crawl_respects_limit(self):
        """Test that max_urls limit is respected during crawl."""
        config = MapperConfig(max_depth=3, max_urls=5, timeout=30.0)
        engine = CrawlEngine(config=config)

        result = engine.map("https://docs.python.org/3/")

        assert result.count <= 5, "Should respect max_urls limit"
        assert len(result.urls) <= 5

    def test_crawl_with_exclude_pattern(self):
        """Test URL filtering with exclude pattern."""
        config = MapperConfig(
            max_depth=2,
            max_urls=20,
            timeout=30.0,
            exclude_pattern=r"\.(pdf|zip|gz)$",
        )
        engine = CrawlEngine(config=config)

        result = engine.map("https://www.python.org")

        # No URLs should match the exclude pattern
        for url in result.urls:
            assert not url.endswith(".pdf"), f"Should exclude PDF: {url}"
            assert not url.endswith(".zip"), f"Should exclude ZIP: {url}"

    def test_crawl_external_links_disabled(self):
        """Test that external links are not followed by default."""
        config = MapperConfig(max_depth=2, max_urls=30, timeout=30.0, follow_external=False)
        engine = CrawlEngine(config=config)

        result = engine.map("https://www.python.org")

        # All URLs should be from python.org
        for url in result.urls:
            assert "python.org" in url, f"Should not follow external link: {url}"

        print(f"\nCrawled {result.count} URLs (internal only)")

    def test_crawl_error_handling(self):
        """Test handling of unreachable URLs."""
        config = MapperConfig(max_depth=1, max_urls=5, timeout=10.0)
        engine = CrawlEngine(config=config)

        # Try a URL that might have some 404s in its links
        result = engine.map("https://httpbin.org/html")

        assert isinstance(result, MapperResult)
        # Should at least include the start URL
        assert result.count >= 1

        print(f"\nCrawl result: {result.count} URLs, errors: {result.errors}")


# =============================================================================
# Folder Engine E2E Tests (Local - No Network Required)
# =============================================================================

@pytest.mark.e2e
class TestFolderEngineE2E:
    """E2E tests for FolderEngine with real local files."""

    def test_folder_discover_markdown(self):
        """Discover markdown files from a folder."""
        # Create temp directory with test files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            (Path(tmpdir) / "doc1.md").write_text("# Document 1\nContent here.")
            (Path(tmpdir) / "doc2.md").write_text("# Document 2\nMore content.")
            (Path(tmpdir) / "readme.txt").write_text("This is not markdown.")
            (Path(tmpdir) / "subdir").mkdir()
            (Path(tmpdir) / "subdir" / "nested.md").write_text("# Nested\nNested content.")

            from kurt.tools.map.engines.folder import FolderEngine, FolderMapperConfig

            config = FolderMapperConfig(recursive=True, file_extensions=[".md"])
            engine = FolderEngine(config=config)

            result = engine.map(tmpdir)

            assert isinstance(result, MapperResult)
            assert result.count == 3, "Should find 3 markdown files"

            # Validate paths
            paths = set(result.urls)
            assert any("doc1.md" in p for p in paths)
            assert any("doc2.md" in p for p in paths)
            assert any("nested.md" in p for p in paths)

            # Should not include .txt file
            assert not any("readme.txt" in p for p in paths)

            print(f"\nDiscovered {result.count} files: {result.urls}")

    def test_folder_non_recursive(self):
        """Test non-recursive folder discovery."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "top.md").write_text("# Top\nTop level.")
            (Path(tmpdir) / "subdir").mkdir()
            (Path(tmpdir) / "subdir" / "nested.md").write_text("# Nested\nNested.")

            from kurt.tools.map.engines.folder import FolderEngine, FolderMapperConfig

            config = FolderMapperConfig(recursive=False, file_extensions=[".md"])
            engine = FolderEngine(config=config)

            result = engine.map(tmpdir)

            assert result.count == 1, "Should find only top-level file"
            assert any("top.md" in p for p in result.urls)

    def test_folder_multiple_extensions(self):
        """Test discovery with multiple file extensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "doc.md").write_text("# Markdown")
            (Path(tmpdir) / "doc.mdx").write_text("# MDX")
            (Path(tmpdir) / "doc.txt").write_text("Plain text")

            from kurt.tools.map.engines.folder import FolderEngine, FolderMapperConfig

            config = FolderMapperConfig(recursive=True, file_extensions=[".md", ".mdx"])
            engine = FolderEngine(config=config)

            result = engine.map(tmpdir)

            assert result.count == 2, "Should find .md and .mdx files"
            paths = set(result.urls)
            assert any("doc.md" in p for p in paths)
            assert any("doc.mdx" in p for p in paths)
            assert not any("doc.txt" in p for p in paths)

    def test_folder_empty_directory(self):
        """Test handling of empty directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from kurt.tools.map.engines.folder import FolderEngine, FolderMapperConfig

            config = FolderMapperConfig(file_extensions=[".md"])
            engine = FolderEngine(config=config)

            result = engine.map(tmpdir)

            assert isinstance(result, MapperResult)
            assert result.count == 0, "Should find no files in empty directory"

    def test_folder_nonexistent_path(self):
        """Test handling of nonexistent paths."""
        from kurt.tools.map.engines.folder import FolderEngine

        engine = FolderEngine()
        result = engine.map("/nonexistent/path/that/does/not/exist")

        assert isinstance(result, MapperResult)
        assert result.count == 0
        assert len(result.errors) > 0, "Should report error for nonexistent path"


# =============================================================================
# Apify Engine E2E Tests (Requires APIFY_API_KEY)
# =============================================================================

@pytest.mark.e2e
class TestApifyMapEngineE2E:
    """E2E tests for ApifyEngine with real API calls.

    Note: Tests will skip if Apify API key is not available or quota is exceeded.
    """

    @pytest.fixture(autouse=True)
    def setup(self, apify_api_key):
        """Set up Apify API key."""
        self.api_key = apify_api_key
        os.environ["APIFY_API_KEY"] = apify_api_key

    def test_apify_engine_initialization(self):
        """Test ApifyEngine can be initialized with API key."""
        from kurt.tools.map.engines.apify import ApifyEngine

        try:
            engine = ApifyEngine()
            assert engine is not None
            print("\nApifyEngine initialized successfully")
        except Exception as e:
            error_msg = str(e).lower()
            if "403" in error_msg or "limit exceeded" in error_msg:
                pytest.skip("Apify monthly usage limit exceeded")
            raise

    def test_apify_engine_platform_detection(self):
        """Test platform detection from URLs."""
        from kurt.tools.map.engines.apify import ApifyEngine

        engine = ApifyEngine()

        # Test platform detection
        twitter_result = engine._detect_platform("https://twitter.com/example")
        assert twitter_result == "twitter"

        linkedin_result = engine._detect_platform("https://linkedin.com/in/example")
        assert linkedin_result == "linkedin"

        unknown_result = engine._detect_platform("https://example.com")
        assert unknown_result is None

        print("\nPlatform detection working correctly")


# =============================================================================
# Cross-Engine Comparison Tests
# =============================================================================

@pytest.mark.e2e
class TestCrossEngineComparison:
    """Compare URL discovery across different engines for the same site."""

    def test_python_org_all_engines(self):
        """Compare sitemap vs crawl engines on python.org."""
        sitemap_config = MapperConfig(max_urls=50)
        sitemap_engine = SitemapEngine(config=sitemap_config)

        crawl_config = MapperConfig(max_depth=1, max_urls=20)
        crawl_engine = CrawlEngine(config=crawl_config)

        # Run both engines on python.org
        sitemap_result = sitemap_engine.map("https://www.python.org")
        crawl_result = crawl_engine.map("https://www.python.org")

        print("\n=== Cross-Engine Comparison: python.org ===")
        print("\nSitemap engine:")
        print(f"  URLs found: {sitemap_result.count}")
        print(f"  Errors: {len(sitemap_result.errors)}")
        print(f"  Sample: {sitemap_result.urls[:3] if sitemap_result.urls else 'None'}")

        print("\nCrawl engine:")
        print(f"  URLs found: {crawl_result.count}")
        print(f"  Errors: {len(crawl_result.errors)}")
        print(f"  Sample: {crawl_result.urls[:3] if crawl_result.urls else 'None'}")

        # Both should find some URLs
        assert sitemap_result.count > 0 or crawl_result.count > 0, "At least one engine should find URLs"

        # Check for overlap
        if sitemap_result.urls and crawl_result.urls:
            sitemap_set = set(sitemap_result.urls)
            crawl_set = set(crawl_result.urls)
            overlap = sitemap_set.intersection(crawl_set)
            print(f"\nOverlap: {len(overlap)} URLs found by both engines")

    def test_blog_rss_vs_crawl(self):
        """Compare RSS vs crawl for a blog site."""
        rss_config = MapperConfig(max_urls=20)
        rss_engine = RssEngine(config=rss_config)

        crawl_config = MapperConfig(max_depth=2, max_urls=20)
        crawl_engine = CrawlEngine(config=crawl_config)

        # Test on Python blog
        rss_result = rss_engine.map("https://blog.python.org")
        crawl_result = crawl_engine.map("https://blog.python.org")

        print("\n=== Cross-Engine Comparison: blog.python.org ===")
        print("\nRSS engine:")
        print(f"  URLs found: {rss_result.count}")
        print(f"  Errors: {rss_result.errors[:2] if rss_result.errors else 'None'}")

        print("\nCrawl engine:")
        print(f"  URLs found: {crawl_result.count}")
        print(f"  Errors: {crawl_result.errors[:2] if crawl_result.errors else 'None'}")

        # RSS might find recent posts, crawl finds any linked pages
        # Both are valid discovery methods


# =============================================================================
# Engine Registry Tests
# =============================================================================

@pytest.mark.e2e
class TestEngineRegistry:
    """Test the engine registry functionality."""

    def test_registry_lists_all_engines(self):
        """Test that all engines are registered."""
        from kurt.tools.map.engines import EngineRegistry

        engines = EngineRegistry.list_engines()

        expected = ["sitemap", "rss", "crawl", "cms", "folder", "apify"]
        for name in expected:
            assert name in engines, f"Engine '{name}' should be registered"

        print(f"\nRegistered engines: {engines}")

    def test_registry_get_engine(self):
        """Test retrieving engines by name."""
        from kurt.tools.map.engines import EngineRegistry

        sitemap_class = EngineRegistry.get("sitemap")
        assert sitemap_class == SitemapEngine

        rss_class = EngineRegistry.get("rss")
        assert rss_class == RssEngine

        crawl_class = EngineRegistry.get("crawl")
        assert crawl_class == CrawlEngine

    def test_registry_unknown_engine(self):
        """Test error handling for unknown engines."""
        from kurt.tools.map.engines import EngineRegistry

        with pytest.raises(KeyError):
            EngineRegistry.get("nonexistent_engine")
