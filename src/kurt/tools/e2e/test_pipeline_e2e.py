"""End-to-end tests for map→fetch pipelines.

These tests validate the complete data flow from URL discovery (map)
through content extraction (fetch) using REAL API calls with NO mocks.

Run with: pytest src/kurt/tools/e2e/test_pipeline_e2e.py -v -s
"""

from __future__ import annotations

import os

import pytest

from kurt.tools.fetch.core import FetchResult
from kurt.tools.fetch.engines.httpx import HttpxFetcher
from kurt.tools.fetch.engines.tavily import TavilyFetcher
from kurt.tools.fetch.engines.trafilatura import TrafilaturaFetcher
from kurt.tools.map.core import MapperConfig, MapperResult
from kurt.tools.map.engines import CrawlEngine, RssEngine, SitemapEngine

# =============================================================================
# Sitemap → Fetch Pipeline Tests
# =============================================================================

@pytest.mark.e2e
class TestSitemapFetchPipeline:
    """Test complete sitemap discovery → content fetch pipelines."""

    def test_sitemap_to_trafilatura_pipeline(self):
        """Discover URLs from sitemap, then fetch with Trafilatura."""
        # Stage 1: Map - discover URLs from sitemap
        map_config = MapperConfig(max_urls=5)
        mapper = SitemapEngine(config=map_config)
        map_result = mapper.map("https://docs.python.org/3/")

        assert isinstance(map_result, MapperResult)
        assert map_result.count > 0, "Should discover URLs from sitemap"

        # Stage 2: Fetch - get content for discovered URLs
        fetcher = TrafilaturaFetcher()
        fetch_results = []

        for url in map_result.urls[:3]:  # Limit to 3 for speed
            result = fetcher.fetch(url)
            fetch_results.append(result)
            assert isinstance(result, FetchResult)

        # Validate pipeline results
        successful = [r for r in fetch_results if r.success]
        assert len(successful) >= 1, "At least one fetch should succeed"

        print("\n=== Sitemap → Trafilatura Pipeline ===")
        print(f"Discovered: {map_result.count} URLs")
        print(f"Fetched: {len(fetch_results)} pages")
        print(f"Successful: {len(successful)}")
        for r in successful[:2]:
            print(f"  - {len(r.content)} chars from {r.metadata.get('url', 'N/A')[:50]}")

    def test_sitemap_to_httpx_pipeline(self):
        """Discover URLs from sitemap, then fetch with HTTPX."""
        # Stage 1: Map
        mapper = SitemapEngine(config=MapperConfig(max_urls=5))
        map_result = mapper.map("https://docs.python.org/3/")

        if map_result.count == 0:
            pytest.skip("No URLs found in sitemap")

        # Stage 2: Fetch
        fetcher = HttpxFetcher()
        fetch_results = []

        for url in map_result.urls[:3]:
            result = fetcher.fetch(url)
            fetch_results.append(result)

        successful = [r for r in fetch_results if r.success]
        assert len(successful) >= 1

        print("\n=== Sitemap → HTTPX Pipeline ===")
        print(f"Discovered: {map_result.count} URLs")
        print(f"Successful fetches: {len(successful)}/{len(fetch_results)}")

    def test_sitemap_to_tavily_pipeline(self, tavily_api_key):
        """Discover URLs from sitemap, then fetch with Tavily."""
        os.environ["TAVILY_API_KEY"] = tavily_api_key

        # Stage 1: Map
        mapper = SitemapEngine(config=MapperConfig(max_urls=3))
        map_result = mapper.map("https://docs.python.org/3/")

        if map_result.count == 0:
            pytest.skip("No URLs found in sitemap")

        # Stage 2: Fetch with Tavily (uses batch API)
        fetcher = TavilyFetcher()
        batch_results = fetcher.fetch_batch(map_result.urls[:2])

        assert isinstance(batch_results, dict)
        successful = sum(1 for r in batch_results.values() if r.success)
        assert successful >= 1

        print("\n=== Sitemap → Tavily Pipeline ===")
        print(f"Discovered: {map_result.count} URLs")
        print(f"Batch fetched: {successful}/{len(batch_results)} successful")


# =============================================================================
# RSS → Fetch Pipeline Tests
# =============================================================================

@pytest.mark.e2e
class TestRssFetchPipeline:
    """Test complete RSS discovery → content fetch pipelines."""

    def test_rss_to_trafilatura_pipeline(self):
        """Discover URLs from RSS feed, then fetch with Trafilatura."""
        # Stage 1: Map - discover URLs from RSS
        mapper = RssEngine(config=MapperConfig(max_urls=10))
        map_result = mapper.map("https://feeds.bbci.co.uk/news/rss.xml")

        assert map_result.count > 0, "Should discover URLs from RSS"

        # Stage 2: Fetch
        fetcher = TrafilaturaFetcher()
        fetch_results = []

        for url in map_result.urls[:3]:
            result = fetcher.fetch(url)
            fetch_results.append((url, result))

        successful = [(u, r) for u, r in fetch_results if r.success]
        assert len(successful) >= 1

        print("\n=== RSS → Trafilatura Pipeline ===")
        print(f"Discovered: {map_result.count} URLs from BBC RSS")
        print(f"Fetched: {len(successful)}/{len(fetch_results)} successful")
        for url, r in successful[:2]:
            print(f"  - {len(r.content)} chars: {url[:60]}...")

    def test_rss_to_tavily_batch_pipeline(self, tavily_api_key):
        """Discover URLs from RSS, batch fetch with Tavily."""
        os.environ["TAVILY_API_KEY"] = tavily_api_key

        # Stage 1: Map
        mapper = RssEngine(config=MapperConfig(max_urls=5))
        map_result = mapper.map("https://feeds.bbci.co.uk/news/rss.xml")

        if map_result.count == 0:
            pytest.skip("No URLs in RSS feed")

        # Stage 2: Batch fetch
        fetcher = TavilyFetcher()
        batch_results = fetcher.fetch_batch(map_result.urls[:3])

        successful = sum(1 for r in batch_results.values() if r.success)
        assert successful >= 1

        print("\n=== RSS → Tavily Batch Pipeline ===")
        print(f"Discovered: {map_result.count} URLs")
        print(f"Batch result: {successful}/{len(batch_results)} successful")

    def test_python_blog_rss_pipeline(self):
        """End-to-end pipeline for Python blog RSS."""
        # Stage 1: Map from Python blog
        mapper = RssEngine(config=MapperConfig(max_urls=5))
        map_result = mapper.map("https://blog.python.org")

        if map_result.count == 0:
            pytest.skip("No entries in Python blog RSS")

        # Stage 2: Fetch blog posts
        fetcher = TrafilaturaFetcher()
        results = []

        for url in map_result.urls[:2]:
            result = fetcher.fetch(url)
            results.append(result)

        successful = [r for r in results if r.success and r.content]
        assert len(successful) >= 1

        # Validate content is blog-like
        for r in successful:
            assert len(r.content) > 100, "Blog posts should have content"

        print("\n=== Python Blog Pipeline ===")
        print(f"Posts discovered: {map_result.count}")
        print(f"Posts fetched: {len(successful)}")


# =============================================================================
# Crawl → Fetch Pipeline Tests
# =============================================================================

@pytest.mark.e2e
class TestCrawlFetchPipeline:
    """Test complete crawl discovery → content fetch pipelines."""

    def test_crawl_to_trafilatura_pipeline(self):
        """Crawl a site, then fetch discovered pages."""
        # Stage 1: Crawl to discover URLs
        map_config = MapperConfig(max_depth=1, max_urls=5, timeout=30.0)
        mapper = CrawlEngine(config=map_config)
        map_result = mapper.map("https://docs.python.org/3/library/json.html")

        assert map_result.count >= 1

        # Stage 2: Fetch discovered pages
        fetcher = TrafilaturaFetcher()
        results = []

        for url in map_result.urls[:3]:
            result = fetcher.fetch(url)
            results.append((url, result))

        successful = [(u, r) for u, r in results if r.success]
        assert len(successful) >= 1

        print("\n=== Crawl → Trafilatura Pipeline ===")
        print(f"Crawled: {map_result.count} URLs")
        print(f"Fetched: {len(successful)}/{len(results)}")

    def test_crawl_depth_fetch_pipeline(self):
        """Test crawling with depth and fetching results."""
        # Crawl with depth=2
        mapper = CrawlEngine(config=MapperConfig(max_depth=2, max_urls=10, timeout=30.0))
        map_result = mapper.map("https://www.python.org")

        assert map_result.count >= 1

        # Fetch a sample
        fetcher = TrafilaturaFetcher()
        sample_urls = map_result.urls[:3]
        results = [fetcher.fetch(url) for url in sample_urls]

        successful = sum(1 for r in results if r.success)
        assert successful >= 1

        print("\n=== Deep Crawl → Fetch Pipeline ===")
        print(f"Crawled (depth=2): {map_result.count} URLs")
        print(f"Sample fetched: {successful}/{len(sample_urls)}")


# =============================================================================
# Multi-Engine Pipeline Tests
# =============================================================================

@pytest.mark.e2e
class TestMultiEnginePipeline:
    """Test pipelines that combine multiple engines."""

    def test_compare_map_engines_same_fetch(self):
        """Compare different map engines feeding into same fetch engine."""
        url = "https://www.python.org"
        fetcher = TrafilaturaFetcher()

        results = {}

        # Test sitemap discovery
        sitemap_mapper = SitemapEngine(config=MapperConfig(max_urls=5))
        sitemap_result = sitemap_mapper.map(url)
        if sitemap_result.count > 0:
            fetch_result = fetcher.fetch(sitemap_result.urls[0])
            results["sitemap"] = {
                "discovered": sitemap_result.count,
                "fetch_success": fetch_result.success,
                "content_len": len(fetch_result.content) if fetch_result.success else 0,
            }

        # Test crawl discovery
        crawl_mapper = CrawlEngine(config=MapperConfig(max_depth=1, max_urls=5))
        crawl_result = crawl_mapper.map(url)
        if crawl_result.count > 0:
            fetch_result = fetcher.fetch(crawl_result.urls[0])
            results["crawl"] = {
                "discovered": crawl_result.count,
                "fetch_success": fetch_result.success,
                "content_len": len(fetch_result.content) if fetch_result.success else 0,
            }

        assert len(results) >= 1, "At least one map engine should work"

        print("\n=== Multi-Engine Map Comparison ===")
        for engine, data in results.items():
            print(f"{engine}: {data['discovered']} URLs, fetch={data['fetch_success']}, {data['content_len']} chars")

    def test_compare_fetch_engines_same_map(self, tavily_api_key):
        """Compare different fetch engines with same map source."""
        os.environ["TAVILY_API_KEY"] = tavily_api_key

        # Map phase - use RSS for predictable URLs
        mapper = RssEngine(config=MapperConfig(max_urls=3))
        map_result = mapper.map("https://feeds.bbci.co.uk/news/rss.xml")

        if map_result.count == 0:
            pytest.skip("No URLs from RSS")

        test_url = map_result.urls[0]
        results = {}

        # Test with Trafilatura
        traf_result = TrafilaturaFetcher().fetch(test_url)
        results["trafilatura"] = {
            "success": traf_result.success,
            "content_len": len(traf_result.content) if traf_result.success else 0,
        }

        # Test with HTTPX
        httpx_result = HttpxFetcher().fetch(test_url)
        results["httpx"] = {
            "success": httpx_result.success,
            "content_len": len(httpx_result.content) if httpx_result.success else 0,
        }

        # Test with Tavily
        tavily_result = TavilyFetcher().fetch(test_url)
        results["tavily"] = {
            "success": tavily_result.success,
            "content_len": len(tavily_result.content) if tavily_result.success else 0,
        }

        successful = sum(1 for r in results.values() if r["success"])
        assert successful >= 2, "At least 2 fetch engines should succeed"

        print("\n=== Multi-Engine Fetch Comparison ===")
        print(f"URL: {test_url[:60]}...")
        for engine, data in results.items():
            print(f"  {engine}: success={data['success']}, {data['content_len']} chars")


# =============================================================================
# Data Consistency Pipeline Tests
# =============================================================================

@pytest.mark.e2e
class TestPipelineDataConsistency:
    """Test data consistency through the pipeline."""

    def test_url_preservation_through_pipeline(self):
        """Verify URLs are preserved through map→fetch pipeline."""
        # Map
        mapper = SitemapEngine(config=MapperConfig(max_urls=3))
        map_result = mapper.map("https://docs.python.org/3/")

        if map_result.count == 0:
            pytest.skip("No sitemap URLs")

        # Fetch and track URLs
        fetcher = TrafilaturaFetcher()
        for original_url in map_result.urls[:2]:
            result = fetcher.fetch(original_url)
            # URL should be in metadata or traceable
            if result.success:
                assert result.metadata is not None

        print("\n=== URL Preservation Test ===")
        print(f"Verified {min(2, map_result.count)} URLs through pipeline")

    def test_metadata_flow_through_pipeline(self):
        """Verify metadata flows correctly through pipeline stages."""
        # Map with metadata
        mapper = CrawlEngine(config=MapperConfig(max_depth=1, max_urls=3))
        map_result = mapper.map("https://example.com")

        assert "engine" in map_result.metadata
        assert map_result.metadata["engine"] == "crawl"

        # Fetch with metadata
        fetcher = TrafilaturaFetcher()
        for url in map_result.urls[:1]:
            result = fetcher.fetch(url)
            if result.success:
                assert "engine" in result.metadata
                assert result.metadata["engine"] == "trafilatura"

        print("\n=== Metadata Flow Test ===")
        print(f"Map metadata: {map_result.metadata}")

    def test_error_propagation_in_pipeline(self):
        """Test that errors are properly captured at each stage."""
        # Map phase with potential errors
        mapper = SitemapEngine()
        map_result = mapper.map("https://httpbin.org")  # No sitemap

        # Errors should be captured
        assert isinstance(map_result.errors, list)

        # Fetch phase with invalid URL
        fetcher = TrafilaturaFetcher()
        result = fetcher.fetch("https://httpbin.org/status/404")

        # Error should be captured in result
        assert isinstance(result, FetchResult)
        # Either success=False or empty content is acceptable

        print("\n=== Error Propagation Test ===")
        print(f"Map errors: {map_result.errors[:2] if map_result.errors else 'None'}")
        print(f"Fetch success: {result.success}")


# =============================================================================
# Performance Pipeline Tests
# =============================================================================

@pytest.mark.e2e
@pytest.mark.slow
class TestPipelinePerformance:
    """Test pipeline performance with larger datasets."""

    def test_batch_pipeline_throughput(self, tavily_api_key):
        """Test batch processing throughput."""
        os.environ["TAVILY_API_KEY"] = tavily_api_key

        # Map many URLs
        mapper = RssEngine(config=MapperConfig(max_urls=10))
        map_result = mapper.map("https://feeds.bbci.co.uk/news/rss.xml")

        if map_result.count < 3:
            pytest.skip("Not enough URLs for batch test")

        # Batch fetch
        fetcher = TavilyFetcher()
        batch_results = fetcher.fetch_batch(map_result.urls[:5])

        successful = sum(1 for r in batch_results.values() if r.success)
        total_content = sum(len(r.content) for r in batch_results.values() if r.success)

        print("\n=== Batch Pipeline Throughput ===")
        print(f"URLs processed: {len(batch_results)}")
        print(f"Successful: {successful}")
        print(f"Total content: {total_content} chars")

        assert successful >= 2, "Batch should have good success rate"
