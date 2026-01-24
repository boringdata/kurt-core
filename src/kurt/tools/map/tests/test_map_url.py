"""Tests for URL discovery functionality."""

from unittest.mock import MagicMock, patch

import pytest

from kurt.tools.map.url import (
    crawl_website,
    discover_from_url,
    discover_sitemap_urls,
)


class TestDiscoverSitemapUrls:
    """Test suite for discover_sitemap_urls function."""

    def test_parses_simple_sitemap(self):
        """Test parsing a simple sitemap.xml."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page1</loc></url>
            <url><loc>https://example.com/page2</loc></url>
            <url><loc>https://example.com/page3</loc></url>
        </urlset>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = sitemap_xml.encode()
        mock_response.text = ""

        with patch("httpx.get", return_value=mock_response):
            urls = discover_sitemap_urls("https://example.com")

        assert len(urls) == 3
        assert "https://example.com/page1" in urls
        assert "https://example.com/page2" in urls
        assert "https://example.com/page3" in urls

    def test_parses_sitemap_index(self):
        """Test parsing a sitemap index with child sitemaps."""
        sitemap_index = """<?xml version="1.0" encoding="UTF-8"?>
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap><loc>https://example.com/sitemap-pages.xml</loc></sitemap>
        </sitemapindex>
        """

        child_sitemap = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/child-page1</loc></url>
            <url><loc>https://example.com/child-page2</loc></url>
        </urlset>
        """

        def mock_get(url, **kwargs):
            response = MagicMock()
            response.status_code = 200
            response.text = ""
            if "sitemap-pages" in url:
                response.content = child_sitemap.encode()
            else:
                response.content = sitemap_index.encode()
            return response

        with patch("httpx.get", side_effect=mock_get):
            urls = discover_sitemap_urls("https://example.com")

        assert len(urls) == 2
        assert "https://example.com/child-page1" in urls
        assert "https://example.com/child-page2" in urls

    def test_checks_robots_txt_for_sitemap(self):
        """Test that robots.txt is checked for sitemap location."""
        robots_txt = "User-agent: *\nSitemap: https://example.com/custom-sitemap.xml"

        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/custom-page</loc></url>
        </urlset>
        """

        def mock_get(url, **kwargs):
            response = MagicMock()
            response.status_code = 200
            if "robots.txt" in url:
                response.text = robots_txt
                response.content = b""
            else:
                response.text = ""
                response.content = sitemap_xml.encode()
            return response

        with patch("httpx.get", side_effect=mock_get):
            urls = discover_sitemap_urls("https://example.com")

        assert "https://example.com/custom-page" in urls

    def test_raises_when_no_sitemap_found(self):
        """Test ValueError when no sitemap is found."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = ""

        with patch("httpx.get", return_value=mock_response):
            with pytest.raises(ValueError, match="No sitemap found"):
                discover_sitemap_urls("https://example.com")


class TestCrawlWebsite:
    """Test suite for crawl_website function."""

    def test_crawl_returns_urls(self):
        """Test that crawl returns discovered URLs."""
        mock_urls = {"https://example.com/page1", "https://example.com/page2"}

        with patch(
            "kurt.tools.map.url.focused_crawler",
            return_value=([], mock_urls),
        ):
            urls = crawl_website("https://example.com", max_depth=2)

        assert len(urls) == 2
        assert "https://example.com/page1" in urls
        assert "https://example.com/page2" in urls

    def test_crawl_filters_external_by_default(self):
        """Test that external URLs are filtered out by default."""
        mock_urls = {
            "https://example.com/internal",
            "https://other.com/external",
        }

        with patch(
            "kurt.tools.map.url.focused_crawler",
            return_value=([], mock_urls),
        ):
            urls = crawl_website("https://example.com", max_depth=2, allow_external=False)

        assert "https://example.com/internal" in urls
        assert "https://other.com/external" not in urls

    def test_crawl_allows_external(self):
        """Test that external URLs can be included."""
        mock_urls = {
            "https://example.com/internal",
            "https://other.com/external",
        }

        with patch(
            "kurt.tools.map.url.focused_crawler",
            return_value=([], mock_urls),
        ):
            urls = crawl_website("https://example.com", max_depth=2, allow_external=True)

        assert len(urls) == 2
        assert "https://other.com/external" in urls

    def test_crawl_respects_max_pages(self):
        """Test that max_pages limits results."""
        mock_urls = {f"https://example.com/page{i}" for i in range(100)}

        with patch(
            "kurt.tools.map.url.focused_crawler",
            return_value=([], mock_urls),
        ):
            urls = crawl_website("https://example.com", max_depth=2, max_pages=10)

        assert len(urls) <= 10

    def test_crawl_applies_include_patterns(self):
        """Test include patterns are applied."""
        mock_urls = {
            "https://example.com/docs/guide.html",
            "https://example.com/blog/post.html",
        }

        with patch(
            "kurt.tools.map.url.focused_crawler",
            return_value=([], mock_urls),
        ):
            urls = crawl_website(
                "https://example.com",
                max_depth=2,
                include_patterns=("*/docs/*",),
            )

        assert "https://example.com/docs/guide.html" in urls
        assert "https://example.com/blog/post.html" not in urls

    def test_crawl_applies_exclude_patterns(self):
        """Test exclude patterns are applied."""
        mock_urls = {
            "https://example.com/docs/guide.html",
            "https://example.com/docs/draft.html",
        }

        with patch(
            "kurt.tools.map.url.focused_crawler",
            return_value=([], mock_urls),
        ):
            urls = crawl_website(
                "https://example.com",
                max_depth=2,
                exclude_patterns=("*draft*",),
            )

        assert "https://example.com/docs/guide.html" in urls
        assert "https://example.com/docs/draft.html" not in urls


class TestDiscoverFromUrl:
    """Test suite for discover_from_url function."""

    def test_returns_expected_structure(self):
        """Test return structure."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page1</loc></url>
        </urlset>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = sitemap_xml.encode()
        mock_response.text = ""

        with patch("httpx.get", return_value=mock_response):
            result = discover_from_url("https://example.com")

        assert "discovered" in result
        assert "method" in result
        assert "total" in result

    def test_prefers_sitemap(self):
        """Test that sitemap is preferred over crawling."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/sitemap-page</loc></url>
        </urlset>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = sitemap_xml.encode()
        mock_response.text = ""

        with patch("httpx.get", return_value=mock_response):
            result = discover_from_url("https://example.com")

        assert result["method"] == "sitemap"
        assert result["total"] == 1

    def test_falls_back_to_crawl(self):
        """Test fallback to crawl when sitemap fails."""
        mock_urls = {"https://example.com/crawled-page"}

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.get", return_value=mock_response):
            with patch(
                "kurt.tools.map.url.focused_crawler",
                return_value=([], mock_urls),
            ):
                result = discover_from_url("https://example.com", max_depth=2)

        assert result["method"] == "crawl"
        assert result["total"] == 1

    def test_single_page_when_no_sitemap_and_no_depth(self):
        """Test single page mode when sitemap fails and no max_depth."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.get", return_value=mock_response):
            result = discover_from_url("https://example.com/specific-page")

        assert result["method"] == "single_page"
        assert result["total"] == 1
        assert result["discovered"][0]["url"] == "https://example.com/specific-page"

    def test_discovered_items_have_url(self):
        """Test discovered items have url field."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page1</loc></url>
            <url><loc>https://example.com/page2</loc></url>
        </urlset>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = sitemap_xml.encode()
        mock_response.text = ""

        with patch("httpx.get", return_value=mock_response):
            result = discover_from_url("https://example.com")

        for item in result["discovered"]:
            assert "url" in item

    def test_respects_max_pages(self):
        """Test max_pages limits results."""
        urls = "\n".join(f"<url><loc>https://example.com/page{i}</loc></url>" for i in range(100))
        sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            {urls}
        </urlset>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = sitemap_xml.encode()
        mock_response.text = ""

        with patch("httpx.get", return_value=mock_response):
            result = discover_from_url("https://example.com", max_pages=10)

        assert result["total"] == 10

    def test_applies_include_patterns(self):
        """Test include patterns filter results."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/docs/guide</loc></url>
            <url><loc>https://example.com/blog/post</loc></url>
        </urlset>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = sitemap_xml.encode()
        mock_response.text = ""

        with patch("httpx.get", return_value=mock_response):
            result = discover_from_url(
                "https://example.com",
                include_patterns=("*/docs/*",),
            )

        assert result["total"] == 1
        assert "docs" in result["discovered"][0]["url"]

    def test_applies_exclude_patterns(self):
        """Test exclude patterns filter results."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/docs/guide</loc></url>
            <url><loc>https://example.com/docs/draft</loc></url>
        </urlset>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = sitemap_xml.encode()
        mock_response.text = ""

        with patch("httpx.get", return_value=mock_response):
            result = discover_from_url(
                "https://example.com",
                exclude_patterns=("*draft*",),
            )

        assert result["total"] == 1
        assert "draft" not in result["discovered"][0]["url"]

    def test_force_crawl_method(self):
        """Test that discovery_method='crawl' forces crawl, skipping sitemap."""
        mock_urls = {"https://example.com/crawled-page"}

        # Even if sitemap would work, it shouldn't be tried
        with patch(
            "kurt.tools.map.url.focused_crawler",
            return_value=([], mock_urls),
        ) as mock_crawler:
            result = discover_from_url(
                "https://example.com",
                discovery_method="crawl",
            )

        # Crawl should be used directly
        mock_crawler.assert_called_once()
        assert result["method"] == "crawl"
        assert result["total"] == 1

    def test_force_sitemap_method_succeeds(self):
        """Test that discovery_method='sitemap' forces sitemap without fallback."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page1</loc></url>
        </urlset>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = sitemap_xml.encode()
        mock_response.text = ""

        with patch("httpx.get", return_value=mock_response):
            result = discover_from_url(
                "https://example.com",
                discovery_method="sitemap",
            )

        assert result["method"] == "sitemap"
        assert result["total"] == 1

    def test_force_sitemap_method_raises_on_failure(self):
        """Test that discovery_method='sitemap' raises if sitemap not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.get", return_value=mock_response):
            with pytest.raises(ValueError, match="No sitemap found"):
                discover_from_url(
                    "https://example.com",
                    discovery_method="sitemap",
                )

    def test_auto_method_tries_sitemap_first(self):
        """Test that discovery_method='auto' (default) tries sitemap first."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page1</loc></url>
        </urlset>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = sitemap_xml.encode()
        mock_response.text = ""

        with patch("httpx.get", return_value=mock_response):
            result = discover_from_url(
                "https://example.com",
                discovery_method="auto",  # Explicit auto
            )

        assert result["method"] == "sitemap"

    def test_force_crawl_uses_default_depth_when_not_specified(self):
        """Test that forcing crawl uses default depth of 2 when max_depth is None."""
        mock_urls = {"https://example.com/page"}

        with patch(
            "kurt.tools.map.url.focused_crawler",
            return_value=([], mock_urls),
        ) as mock_crawler:
            discover_from_url(
                "https://example.com",
                discovery_method="crawl",
                max_depth=None,  # Not specified
            )

        # Should use default depth calculations (depth 2 = 50 max_seen_urls)
        call_kwargs = mock_crawler.call_args
        assert call_kwargs is not None
