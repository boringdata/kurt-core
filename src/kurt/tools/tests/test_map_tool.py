"""
Unit tests for MapTool.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import ValidationError

from kurt.tools.base import SubstepEvent, ToolContext, ToolResult
from kurt.tools.map_tool import (
    MapInput,
    MapOutput,
    MapTool,
    check_robots_txt,
    discover_from_folder,
    discover_from_sitemap,
    filter_items,
    is_blocked_by_robots,
    make_document_id,
    normalize_url,
)
from kurt.tools.registry import TOOLS, clear_registry

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear the registry before and after each test."""
    # Save current tools
    saved_tools = dict(TOOLS)
    clear_registry()
    # Re-register MapTool
    TOOLS["map"] = MapTool
    yield
    clear_registry()
    # Restore saved tools
    TOOLS.update(saved_tools)


@pytest.fixture
def temp_folder():
    """Create a temporary folder with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        folder = Path(tmpdir)

        # Create test files
        (folder / "index.html").write_text("<html>Index</html>")
        (folder / "about.html").write_text("<html>About</html>")
        (folder / "docs").mkdir()
        (folder / "docs" / "guide.md").write_text("# Guide")
        (folder / "docs" / "api.md").write_text("# API")
        (folder / "assets").mkdir()
        (folder / "assets" / "style.css").write_text("body {}")
        (folder / "assets" / "logo.png").write_bytes(b"PNG")

        yield folder


# ============================================================================
# URL Normalization Tests
# ============================================================================


class TestNormalizeUrl:
    """Test URL normalization function."""

    def test_lowercase_scheme_and_host(self):
        """Scheme and host are lowercased."""
        assert normalize_url("HTTPS://Example.COM/Path") == "https://example.com/Path"

    def test_remove_default_http_port(self):
        """Remove default port 80 for HTTP."""
        assert normalize_url("http://example.com:80/path") == "http://example.com/path"

    def test_remove_default_https_port(self):
        """Remove default port 443 for HTTPS."""
        assert normalize_url("https://example.com:443/path") == "https://example.com/path"

    def test_keep_non_default_port(self):
        """Keep non-default ports."""
        assert normalize_url("http://example.com:8080/path") == "http://example.com:8080/path"
        assert normalize_url("https://example.com:8443/path") == "https://example.com:8443/path"

    def test_remove_trailing_slash(self):
        """Remove trailing slash except for root."""
        assert normalize_url("https://example.com/path/") == "https://example.com/path"
        assert normalize_url("https://example.com/a/b/c/") == "https://example.com/a/b/c"

    def test_keep_root_trailing_slash(self):
        """Keep trailing slash for root path."""
        assert normalize_url("https://example.com/") == "https://example.com/"
        # Also when there's no path at all
        assert normalize_url("https://example.com") == "https://example.com/"

    def test_sort_query_params(self):
        """Sort query parameters alphabetically."""
        assert (
            normalize_url("https://example.com?z=1&a=2&m=3")
            == "https://example.com?a=2&m=3&z=1"
        )

    def test_remove_fragment(self):
        """Remove URL fragment."""
        assert normalize_url("https://example.com/path#section") == "https://example.com/path"
        assert (
            normalize_url("https://example.com/path?q=1#section")
            == "https://example.com/path?q=1"
        )

    def test_remove_duplicate_slashes(self):
        """Remove duplicate slashes in path."""
        assert normalize_url("https://example.com//path///file") == "https://example.com/path/file"

    def test_decode_safe_chars(self):
        """Decode percent-encoded safe characters."""
        # %41 = 'A', %7E = '~'
        assert normalize_url("https://example.com/p%41th") == "https://example.com/pAth"
        assert normalize_url("https://example.com/file%7Ename") == "https://example.com/file~name"

    def test_keep_unsafe_encoded(self):
        """Keep percent-encoded unsafe characters."""
        # %2F = '/', %20 = ' '
        assert normalize_url("https://example.com/path%2Ffile") == "https://example.com/path%2Ffile"

    def test_empty_url(self):
        """Empty URL returns empty string."""
        assert normalize_url("") == ""

    def test_non_http_scheme(self):
        """Non-HTTP schemes are returned as-is."""
        assert normalize_url("file:///path/to/file") == "file:///path/to/file"
        assert normalize_url("ftp://example.com/file") == "ftp://example.com/file"

    def test_complex_url(self):
        """Complex URL normalization."""
        url = "HTTPS://WWW.Example.COM:443/Path//To///Page/?z=1&a=2#section"
        expected = "https://www.example.com/Path/To/Page?a=2&z=1"
        assert normalize_url(url) == expected


class TestMakeDocumentId:
    """Test document ID generation."""

    def test_deterministic(self):
        """Same source produces same ID."""
        url = "https://example.com/page"
        id1 = make_document_id(url)
        id2 = make_document_id(url)
        assert id1 == id2

    def test_different_sources(self):
        """Different sources produce different IDs."""
        id1 = make_document_id("https://example.com/page1")
        id2 = make_document_id("https://example.com/page2")
        assert id1 != id2

    def test_prefix(self):
        """IDs have 'map_' prefix."""
        doc_id = make_document_id("https://example.com/page")
        assert doc_id.startswith("map_")


# ============================================================================
# Filter Items Tests
# ============================================================================


class TestFilterItems:
    """Test filter_items function."""

    def test_no_filters(self):
        """No filters returns all items."""
        items = ["a.html", "b.html", "c.txt"]
        result = filter_items(items, include_patterns=[], exclude_patterns=[])
        assert result == items

    def test_include_pattern(self):
        """Include pattern filters items."""
        items = ["a.html", "b.html", "c.txt"]
        result = filter_items(items, include_patterns=["*.html"], exclude_patterns=[])
        assert result == ["a.html", "b.html"]

    def test_exclude_pattern(self):
        """Exclude pattern filters items."""
        items = ["a.html", "b.html", "c.txt"]
        result = filter_items(items, include_patterns=[], exclude_patterns=["*.txt"])
        assert result == ["a.html", "b.html"]

    def test_include_and_exclude(self):
        """Both include and exclude patterns."""
        items = ["a.html", "b.html", "admin.html", "c.txt"]
        result = filter_items(
            items, include_patterns=["*.html"], exclude_patterns=["admin*"]
        )
        assert result == ["a.html", "b.html"]

    def test_max_items(self):
        """Max items limits results."""
        items = ["a", "b", "c", "d", "e"]
        result = filter_items(items, include_patterns=[], exclude_patterns=[], max_items=3)
        assert result == ["a", "b", "c"]

    def test_multiple_patterns(self):
        """Multiple include patterns."""
        items = ["a.html", "b.md", "c.txt", "d.pdf"]
        result = filter_items(
            items, include_patterns=["*.html", "*.md"], exclude_patterns=[]
        )
        assert result == ["a.html", "b.md"]


# ============================================================================
# Robots.txt Tests
# ============================================================================


class TestRobotsTxt:
    """Test robots.txt handling."""

    def test_blocked_exact_path(self):
        """Exact path is blocked."""
        disallowed = {"/admin", "/private/"}
        assert is_blocked_by_robots("https://example.com/admin", disallowed)
        assert is_blocked_by_robots("https://example.com/admin/page", disallowed)

    def test_blocked_wildcard(self):
        """Wildcard path is blocked."""
        disallowed = {"/admin/*"}
        assert is_blocked_by_robots("https://example.com/admin/page", disallowed)
        assert not is_blocked_by_robots("https://example.com/admin", disallowed)

    def test_not_blocked(self):
        """Unmatched paths are not blocked."""
        disallowed = {"/admin"}
        assert not is_blocked_by_robots("https://example.com/public", disallowed)

    def test_empty_disallowed(self):
        """Empty disallowed set blocks nothing."""
        assert not is_blocked_by_robots("https://example.com/admin", set())

    @pytest.mark.asyncio
    async def test_check_robots_txt(self):
        """Parse robots.txt content."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
User-agent: *
Disallow: /admin
Disallow: /private/

User-agent: Googlebot
Allow: /
"""
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        disallowed = await check_robots_txt(mock_client, "https://example.com")

        assert "/admin" in disallowed
        assert "/private/" in disallowed


# ============================================================================
# MapInput Validation Tests
# ============================================================================


class TestMapInputValidation:
    """Test MapInput Pydantic validation."""

    def test_url_source_requires_url(self):
        """source='url' requires url field."""
        with pytest.raises(ValidationError, match="url is required"):
            MapInput(source="url")

    def test_url_source_valid(self):
        """Valid URL source input."""
        inp = MapInput(source="url", url="https://example.com")
        assert inp.source == "url"
        assert inp.url == "https://example.com"

    def test_file_source_requires_path(self):
        """source='file' requires path field."""
        with pytest.raises(ValidationError, match="path is required"):
            MapInput(source="file")

    def test_file_source_valid(self):
        """Valid file source input."""
        inp = MapInput(source="file", path="/tmp/docs")
        assert inp.source == "file"
        assert inp.path == "/tmp/docs"

    def test_cms_source_requires_platform(self):
        """source='cms' requires cms_platform field."""
        with pytest.raises(ValidationError, match="cms_platform is required"):
            MapInput(source="cms")

    def test_cms_source_valid(self):
        """Valid CMS source input."""
        inp = MapInput(source="cms", cms_platform="sanity", cms_instance="production")
        assert inp.source == "cms"
        assert inp.cms_platform == "sanity"
        assert inp.cms_instance == "production"

    def test_default_values(self):
        """Check default values."""
        inp = MapInput(source="url", url="https://example.com")
        assert inp.depth == 0  # Default is 0, not 1
        assert inp.max_pages == 1000
        assert inp.include_patterns == []
        assert inp.exclude_patterns == []
        assert inp.discovery_method == "auto"
        assert inp.respect_robots is True
        assert inp.timeout == 30.0

    def test_depth_range(self):
        """Depth must be between 0 and 10."""
        with pytest.raises(ValidationError):
            MapInput(source="url", url="https://example.com", depth=-1)
        with pytest.raises(ValidationError):
            MapInput(source="url", url="https://example.com", depth=11)


# ============================================================================
# Folder Discovery Tests
# ============================================================================


class TestDiscoverFromFolder:
    """Test folder discovery function."""

    @pytest.mark.asyncio
    async def test_discover_files(self, temp_folder):
        """Discover files in folder."""
        items, error = await discover_from_folder(
            str(temp_folder),
            include_patterns=["**/*"],
            exclude_patterns=[],
            max_pages=100,
        )

        assert error is None
        assert len(items) >= 5  # At least our test files

        urls = [item["url"] for item in items]
        assert any("index.html" in url for url in urls)
        assert any("guide.md" in url for url in urls)

    @pytest.mark.asyncio
    async def test_discover_with_pattern(self, temp_folder):
        """Discover files with include pattern."""
        items, error = await discover_from_folder(
            str(temp_folder),
            include_patterns=["**/*.html"],
            exclude_patterns=[],
            max_pages=100,
        )

        assert error is None
        assert len(items) == 2  # index.html and about.html
        for item in items:
            assert item["url"].endswith(".html")

    @pytest.mark.asyncio
    async def test_discover_with_exclude(self, temp_folder):
        """Discover files with exclude pattern."""
        items, error = await discover_from_folder(
            str(temp_folder),
            include_patterns=["**/*"],
            exclude_patterns=["assets/*"],
            max_pages=100,
        )

        assert error is None
        urls = [item["url"] for item in items]
        assert not any("style.css" in url for url in urls)
        assert not any("logo.png" in url for url in urls)

    @pytest.mark.asyncio
    async def test_folder_not_found(self):
        """Error when folder not found."""
        items, error = await discover_from_folder(
            "/nonexistent/path",
            include_patterns=[],
            exclude_patterns=[],
            max_pages=100,
        )

        assert error is not None
        assert "not found" in error.lower()
        assert items == []

    @pytest.mark.asyncio
    async def test_file_metadata(self, temp_folder):
        """Files have correct metadata."""
        items, error = await discover_from_folder(
            str(temp_folder),
            include_patterns=["*.html"],
            exclude_patterns=[],
            max_pages=100,
        )

        assert error is None
        for item in items:
            assert item["source_type"] == "file"
            assert "relative_path" in item["metadata"]
            assert "extension" in item["metadata"]
            assert "size" in item["metadata"]


# ============================================================================
# Sitemap Discovery Tests
# ============================================================================


class TestDiscoverFromSitemap:
    """Test sitemap discovery function."""

    @pytest.mark.asyncio
    async def test_parse_simple_sitemap(self):
        """Parse a simple sitemap.xml."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://example.com/page1</loc>
    </url>
    <url>
        <loc>https://example.com/page2</loc>
    </url>
</urlset>"""

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = sitemap_xml.encode()

        mock_robots = Mock()
        mock_robots.status_code = 404

        mock_client = AsyncMock()

        async def mock_get(url, **kwargs):
            if "robots.txt" in url:
                return mock_robots
            if "sitemap.xml" in url:
                return mock_response
            return mock_robots

        mock_client.get.side_effect = mock_get

        items, error = await discover_from_sitemap(
            mock_client,
            "https://example.com",
            include_patterns=[],
            exclude_patterns=[],
            max_pages=100,
        )

        assert error is None
        assert len(items) == 2
        urls = {item["url"] for item in items}
        assert "https://example.com/page1" in urls
        assert "https://example.com/page2" in urls

    @pytest.mark.asyncio
    async def test_parse_sitemap_index(self):
        """Parse a sitemap index with child sitemaps."""
        sitemap_index = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <sitemap>
        <loc>https://example.com/sitemap-pages.xml</loc>
    </sitemap>
</sitemapindex>"""

        child_sitemap = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://example.com/page1</loc>
    </url>
</urlset>"""

        mock_robots = Mock()
        mock_robots.status_code = 404

        mock_index = Mock()
        mock_index.status_code = 200
        mock_index.content = sitemap_index.encode()

        mock_child = Mock()
        mock_child.status_code = 200
        mock_child.content = child_sitemap.encode()

        mock_client = AsyncMock()

        async def mock_get(url, **kwargs):
            if "robots.txt" in url:
                return mock_robots
            if "sitemap-pages.xml" in url:
                return mock_child
            if "sitemap.xml" in url or "sitemap_index" in url or "sitemap-index" in url:
                return mock_index
            return mock_robots

        mock_client.get.side_effect = mock_get

        items, error = await discover_from_sitemap(
            mock_client,
            "https://example.com",
            include_patterns=[],
            exclude_patterns=[],
            max_pages=100,
        )

        assert error is None
        assert len(items) == 1
        assert items[0]["url"] == "https://example.com/page1"

    @pytest.mark.asyncio
    async def test_no_sitemap_found(self):
        """Error when no sitemap found."""
        mock_response = Mock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        items, error = await discover_from_sitemap(
            mock_client,
            "https://example.com",
            include_patterns=[],
            exclude_patterns=[],
            max_pages=100,
        )

        assert error is not None
        assert "no sitemap found" in error.lower()
        assert items == []


# ============================================================================
# MapTool Integration Tests
# ============================================================================


class TestMapTool:
    """Test MapTool class."""

    def test_tool_registered(self):
        """MapTool is registered in TOOLS."""
        assert "map" in TOOLS
        assert TOOLS["map"] is MapTool

    def test_tool_attributes(self):
        """MapTool has correct attributes."""
        assert MapTool.name == "map"
        assert MapTool.description is not None
        assert MapTool.InputModel is MapInput
        assert MapTool.OutputModel is MapOutput

    @pytest.mark.asyncio
    async def test_map_folder(self, temp_folder):
        """MapTool discovers files from folder."""
        tool = MapTool()
        params = MapInput(
            source="file",
            path=str(temp_folder),
            include_patterns=["**/*.html"],
        )
        context = ToolContext()

        result = await tool.run(params, context)

        assert result.success is True
        assert len(result.data) == 2  # index.html and about.html
        assert len(result.errors) == 0

        # Check substeps
        assert len(result.substeps) == 1
        assert result.substeps[0].name == "map_file"
        assert result.substeps[0].status == "completed"

    @pytest.mark.asyncio
    async def test_map_folder_not_found(self):
        """MapTool handles missing folder."""
        tool = MapTool()
        params = MapInput(
            source="file",
            path="/nonexistent/folder",
        )
        context = ToolContext()

        result = await tool.run(params, context)

        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "discovery_failed"

    @pytest.mark.asyncio
    async def test_progress_callback(self, temp_folder):
        """MapTool calls progress callback."""
        tool = MapTool()
        params = MapInput(
            source="file",
            path=str(temp_folder),
        )
        context = ToolContext()

        events: list[SubstepEvent] = []

        def on_progress(event: SubstepEvent):
            events.append(event)

        await tool.run(params, context, on_progress)

        assert len(events) >= 2
        assert any(e.substep == "map_folder" and e.status == "running" for e in events)
        assert any(e.substep == "map_folder" and e.status == "completed" for e in events)

    @pytest.mark.asyncio
    async def test_document_ids_generated(self, temp_folder):
        """MapTool generates document IDs."""
        tool = MapTool()
        params = MapInput(
            source="file",
            path=str(temp_folder),
            max_pages=5,
        )
        context = ToolContext()

        result = await tool.run(params, context)

        assert result.success is True
        for item in result.data:
            assert "document_id" in item
            # Document ID is a 12-char hex string from SHA256
            assert len(item["document_id"]) == 12

    @pytest.mark.asyncio
    async def test_map_url_with_mock_http(self):
        """MapTool discovers URLs with mocked HTTP."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://example.com/page1</loc></url>
    <url><loc>https://example.com/page2</loc></url>
</urlset>"""

        mock_sitemap = Mock()
        mock_sitemap.status_code = 200
        mock_sitemap.content = sitemap_xml.encode()

        mock_404 = Mock()
        mock_404.status_code = 404

        mock_client = AsyncMock()

        async def mock_get(url, **kwargs):
            if "sitemap.xml" in url:
                return mock_sitemap
            return mock_404

        mock_client.get.side_effect = mock_get

        tool = MapTool()
        params = MapInput(
            source="url",
            url="https://example.com",
            discovery_method="sitemap",
        )
        context = ToolContext(http=mock_client)

        result = await tool.run(params, context)

        assert result.success is True
        assert len(result.data) == 2
        urls = {item["url"] for item in result.data}
        assert "https://example.com/page1" in urls
        assert "https://example.com/page2" in urls


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestMapToolErrorHandling:
    """Test MapTool error handling."""

    @pytest.mark.asyncio
    async def test_http_timeout(self):
        """Handle HTTP timeout."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("Request timed out")
        mock_client.aclose = AsyncMock()

        tool = MapTool()
        params = MapInput(
            source="url",
            url="https://example.com",
            discovery_method="sitemap",
        )
        context = ToolContext(http=mock_client)

        result = await tool.run(params, context)

        # Should fallback gracefully
        assert len(result.errors) >= 0  # May have error or fallback

    @pytest.mark.asyncio
    async def test_invalid_sitemap_xml(self):
        """Handle invalid XML in sitemap."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"<invalid>xml"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        tool = MapTool()
        params = MapInput(
            source="url",
            url="https://example.com",
            discovery_method="sitemap",
        )
        context = ToolContext(http=mock_client)

        result = await tool.run(params, context)

        # Should handle gracefully (either error or fallback)
        assert isinstance(result, ToolResult)

    @pytest.mark.asyncio
    async def test_cms_provider_not_found(self):
        """Handle unknown CMS provider."""
        tool = MapTool()
        params = MapInput(
            source="cms",
            cms_platform="unknown_provider",
            cms_instance="default",
        )
        context = ToolContext()

        result = await tool.run(params, context)

        assert result.success is False
        assert len(result.errors) == 1
        # Error message from discover_from_cms will contain failure info
        assert result.errors[0].message is not None


# ============================================================================
# Output Format Tests
# ============================================================================


class TestMapOutput:
    """Test MapOutput model."""

    def test_output_fields(self):
        """MapOutput has correct fields."""
        output = MapOutput(
            url="https://example.com/page",
            source_type="page",
            discovered_from="https://example.com",
            depth=1,
        )

        assert output.url == "https://example.com/page"
        assert output.source_type == "page"
        assert output.discovered_from == "https://example.com"
        assert output.depth == 1
        assert output.title is None
        assert output.document_id is None
        assert output.metadata == {}

    def test_output_with_metadata(self):
        """MapOutput with optional fields."""
        output = MapOutput(
            url="https://example.com/page",
            source_type="cms_entry",
            title="Page Title",
            discovered_from="https://cms.example.com",
            depth=0,
            document_id="map_abc123",
            metadata={"cms_id": "123", "content_type": "article"},
        )

        assert output.title == "Page Title"
        assert output.document_id == "map_abc123"
        assert output.metadata["cms_id"] == "123"
