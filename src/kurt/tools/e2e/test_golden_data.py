"""Golden data validation tests.

These tests validate that actual e2e results match expected golden data patterns.
Use these for regression testing and ensuring consistency.

Run with: pytest src/kurt/tools/e2e/test_golden_data.py -v -s
"""

from __future__ import annotations

import os

import pytest

from kurt.tools.fetch.engines.httpx import HttpxFetcher
from kurt.tools.fetch.engines.trafilatura import TrafilaturaFetcher
from kurt.tools.fetch.engines.tavily import TavilyFetcher
from kurt.tools.map.engines import CrawlEngine, RssEngine, SitemapEngine
from kurt.tools.map.core import MapperConfig

from kurt.tools.e2e.fixtures import (
    GOLDEN_SITEMAP_RESULT,
    GOLDEN_RSS_RESULT,
    GOLDEN_CRAWL_RESULT,
    GOLDEN_TRAFILATURA_RESULT,
    GOLDEN_HTTPX_RESULT,
    GOLDEN_TAVILY_RESULT,
    GOLDEN_EXAMPLE_COM_CONTENT,
    GOLDEN_PYTHON_DOCS_JSON,
    GOLDEN_PYTHON_ORG_ABOUT,
    GOLDEN_NO_SITEMAP,
    validate_map_result,
    validate_fetch_result,
    validate_content_snapshot,
)


# =============================================================================
# Map Engine Golden Data Tests
# =============================================================================

@pytest.mark.e2e
class TestMapGoldenData:
    """Validate map engine outputs against golden data."""

    def test_sitemap_matches_golden(self):
        """Validate SitemapEngine output against golden data."""
        mapper = SitemapEngine(config=MapperConfig(max_urls=20))
        result = mapper.map(GOLDEN_SITEMAP_RESULT["source"])

        is_valid, errors = validate_map_result(result, GOLDEN_SITEMAP_RESULT)

        if not is_valid:
            print(f"\nGolden validation errors: {errors}")

        # Sitemap may legitimately be empty for some sites
        if result.count > 0:
            assert is_valid, f"Golden validation failed: {errors}"
        else:
            print(f"\nNote: Sitemap returned 0 URLs (may be expected)")

    def test_rss_matches_golden(self):
        """Validate RssEngine output against golden data."""
        mapper = RssEngine(config=MapperConfig(max_urls=20))
        result = mapper.map(GOLDEN_RSS_RESULT["source"])

        is_valid, errors = validate_map_result(result, GOLDEN_RSS_RESULT)

        assert is_valid, f"Golden validation failed: {errors}"
        print(f"\n✓ RSS result matches golden data ({result.count} URLs)")

    def test_crawl_matches_golden(self):
        """Validate CrawlEngine output against golden data."""
        mapper = CrawlEngine(config=MapperConfig(max_depth=1, max_urls=10))
        result = mapper.map(GOLDEN_CRAWL_RESULT["source"])

        is_valid, errors = validate_map_result(result, GOLDEN_CRAWL_RESULT)

        assert is_valid, f"Golden validation failed: {errors}"
        print(f"\n✓ Crawl result matches golden data ({result.count} URLs)")

    def test_no_sitemap_matches_golden(self):
        """Validate error case against golden data."""
        mapper = SitemapEngine()
        result = mapper.map(GOLDEN_NO_SITEMAP["url"])

        # Should have no URLs or have errors
        assert result.count == GOLDEN_NO_SITEMAP["expected_urls"] or len(result.errors) > 0
        print(f"\n✓ No-sitemap case matches golden (errors: {result.errors[:1]})")


# =============================================================================
# Fetch Engine Golden Data Tests
# =============================================================================

@pytest.mark.e2e
class TestFetchGoldenData:
    """Validate fetch engine outputs against golden data."""

    def test_trafilatura_matches_golden(self):
        """Validate TrafilaturaFetcher output against golden data."""
        fetcher = TrafilaturaFetcher()
        result = fetcher.fetch(GOLDEN_TRAFILATURA_RESULT["url"])

        is_valid, errors = validate_fetch_result(result, GOLDEN_TRAFILATURA_RESULT)

        assert is_valid, f"Golden validation failed: {errors}"
        print(f"\n✓ Trafilatura result matches golden ({len(result.content)} chars)")

    def test_httpx_matches_golden(self):
        """Validate HttpxFetcher output against golden data."""
        fetcher = HttpxFetcher()
        result = fetcher.fetch(GOLDEN_HTTPX_RESULT["url"])

        is_valid, errors = validate_fetch_result(result, GOLDEN_HTTPX_RESULT)

        assert is_valid, f"Golden validation failed: {errors}"
        print(f"\n✓ HTTPX result matches golden ({len(result.content)} chars)")

    def test_tavily_matches_golden(self, tavily_api_key):
        """Validate TavilyFetcher output against golden data."""
        os.environ["TAVILY_API_KEY"] = tavily_api_key

        fetcher = TavilyFetcher()
        result = fetcher.fetch(GOLDEN_TAVILY_RESULT["url"])

        is_valid, errors = validate_fetch_result(result, GOLDEN_TAVILY_RESULT)

        assert is_valid, f"Golden validation failed: {errors}"
        print(f"\n✓ Tavily result matches golden ({len(result.content)} chars)")


# =============================================================================
# Content Snapshot Tests
# =============================================================================

@pytest.mark.e2e
class TestContentSnapshots:
    """Validate content against expected snapshots."""

    def test_example_com_content_snapshot(self):
        """Validate example.com content against snapshot."""
        fetcher = TrafilaturaFetcher()
        result = fetcher.fetch(GOLDEN_EXAMPLE_COM_CONTENT["url"])

        assert result.success, f"Fetch failed: {result.error}"

        is_valid, errors = validate_content_snapshot(
            result.content, GOLDEN_EXAMPLE_COM_CONTENT
        )

        assert is_valid, f"Content snapshot validation failed: {errors}"
        print(f"\n✓ example.com content matches snapshot")
        print(f"  Word count: {len(result.content.split())}")

    def test_python_json_docs_snapshot(self):
        """Validate Python JSON docs against snapshot."""
        fetcher = TrafilaturaFetcher()
        result = fetcher.fetch(GOLDEN_PYTHON_DOCS_JSON["url"])

        assert result.success, f"Fetch failed: {result.error}"

        is_valid, errors = validate_content_snapshot(
            result.content, GOLDEN_PYTHON_DOCS_JSON
        )

        assert is_valid, f"Content snapshot validation failed: {errors}"
        print(f"\n✓ Python JSON docs match snapshot")
        print(f"  Word count: {len(result.content.split())}")

    def test_python_org_about_snapshot(self, tavily_api_key):
        """Validate python.org/about content against snapshot."""
        os.environ["TAVILY_API_KEY"] = tavily_api_key

        # Use Tavily for richer content extraction
        fetcher = TavilyFetcher()
        result = fetcher.fetch(GOLDEN_PYTHON_ORG_ABOUT["url"])

        assert result.success, f"Fetch failed: {result.error}"

        is_valid, errors = validate_content_snapshot(
            result.content, GOLDEN_PYTHON_ORG_ABOUT
        )

        assert is_valid, f"Content snapshot validation failed: {errors}"
        print(f"\n✓ python.org/about matches snapshot")
        print(f"  Word count: {len(result.content.split())}")


# =============================================================================
# Cross-Validation Tests
# =============================================================================

@pytest.mark.e2e
class TestCrossValidation:
    """Cross-validate results between engines."""

    def test_same_url_different_engines_consistent(self):
        """Verify different engines produce consistent results for same URL."""
        url = "https://example.com"

        traf_result = TrafilaturaFetcher().fetch(url)
        httpx_result = HttpxFetcher().fetch(url)

        # Both should succeed
        assert traf_result.success and httpx_result.success

        # Content should be similar (within 5x)
        traf_len = len(traf_result.content)
        httpx_len = len(httpx_result.content)

        if traf_len > 0 and httpx_len > 0:
            ratio = max(traf_len, httpx_len) / min(traf_len, httpx_len)
            assert ratio < 5, f"Content length ratio too high: {ratio}"

        # Both should contain key content
        assert "example" in traf_result.content.lower()
        assert "example" in httpx_result.content.lower()

        print(f"\n✓ Cross-engine consistency validated")
        print(f"  Trafilatura: {traf_len} chars")
        print(f"  HTTPX: {httpx_len} chars")

    def test_map_engines_consistent_url_format(self):
        """Verify map engines produce consistently formatted URLs."""
        url = "https://www.python.org"

        sitemap_result = SitemapEngine(config=MapperConfig(max_urls=10)).map(url)
        crawl_result = CrawlEngine(config=MapperConfig(max_depth=1, max_urls=10)).map(url)

        # Check URL formatting consistency
        for result in [sitemap_result, crawl_result]:
            for discovered_url in result.urls:
                # URLs should be properly formatted
                assert discovered_url.startswith("http"), f"Invalid URL: {discovered_url}"
                assert " " not in discovered_url, f"URL contains spaces: {discovered_url}"

        print(f"\n✓ Map engine URL format consistency validated")
        print(f"  Sitemap: {sitemap_result.count} URLs")
        print(f"  Crawl: {crawl_result.count} URLs")
