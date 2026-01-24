"""Tests for map workflow utility functions."""

from unittest.mock import patch

from kurt.tools.map.models import MapStatus
from kurt.tools.map.utils import (
    build_rows,
    compute_status,
    filter_items,
    get_source_identifier,
    get_source_type,
    make_document_id,
    parse_patterns,
    serialize_rows,
)


class TestParsePatterns:
    """Test suite for parse_patterns function."""

    def test_parse_none(self):
        """Test parsing None returns empty tuple."""
        assert parse_patterns(None) == ()

    def test_parse_empty_string(self):
        """Test parsing empty string returns empty tuple."""
        assert parse_patterns("") == ()

    def test_parse_single_pattern(self):
        """Test parsing single pattern."""
        result = parse_patterns("*.md")
        assert result == ("*.md",)

    def test_parse_multiple_patterns(self):
        """Test parsing comma-separated patterns."""
        result = parse_patterns("*.md,*.mdx,*.txt")
        assert result == ("*.md", "*.mdx", "*.txt")

    def test_parse_patterns_strips_whitespace(self):
        """Test that patterns are stripped of whitespace."""
        result = parse_patterns("  *.md  ,  *.mdx  ")
        assert result == ("*.md", "*.mdx")

    def test_parse_patterns_ignores_empty(self):
        """Test that empty patterns are ignored."""
        result = parse_patterns("*.md,,*.mdx")
        assert result == ("*.md", "*.mdx")


class TestComputeStatus:
    """Test suite for compute_status function."""

    def test_error_status(self):
        """Test ERROR status when error is present."""
        row = {"error": "Something went wrong"}
        assert compute_status(row) == MapStatus.ERROR

    def test_success_status_new(self):
        """Test SUCCESS status when is_new is True."""
        row = {"is_new": True}
        assert compute_status(row) == MapStatus.SUCCESS

    def test_success_status_existing(self):
        """Test SUCCESS status when is_new is False."""
        row = {"is_new": False}
        assert compute_status(row) == MapStatus.SUCCESS

    def test_success_status_default(self):
        """Test SUCCESS status when is_new is not set."""
        row = {}
        assert compute_status(row) == MapStatus.SUCCESS


class TestGetSourceType:
    """Test suite for get_source_type function."""

    def test_folder_returns_file(self):
        """Test folder discovery method returns 'file'."""
        assert get_source_type("folder") == "file"

    def test_cms_returns_cms(self):
        """Test cms discovery method returns 'cms'."""
        assert get_source_type("cms") == "cms"

    def test_sitemap_returns_url(self):
        """Test sitemap discovery method returns 'url'."""
        assert get_source_type("sitemap") == "url"

    def test_crawl_returns_url(self):
        """Test crawl discovery method returns 'url'."""
        assert get_source_type("crawl") == "url"

    def test_unknown_returns_url(self):
        """Test unknown discovery method returns 'url'."""
        assert get_source_type("unknown") == "url"


class TestMakeDocumentId:
    """Test suite for make_document_id function."""

    def test_creates_prefixed_hash(self):
        """Test that document ID starts with 'map_' prefix."""
        doc_id = make_document_id("https://example.com/page")
        assert doc_id.startswith("map_")

    def test_consistent_hash(self):
        """Test that same source produces same ID."""
        source = "https://example.com/page"
        id1 = make_document_id(source)
        id2 = make_document_id(source)
        assert id1 == id2

    def test_different_sources_different_ids(self):
        """Test that different sources produce different IDs."""
        id1 = make_document_id("https://example.com/page1")
        id2 = make_document_id("https://example.com/page2")
        assert id1 != id2

    def test_hash_length(self):
        """Test that hash is SHA1 length (40 chars) plus prefix."""
        doc_id = make_document_id("https://example.com")
        # "map_" (4) + SHA1 hex (40) = 44 chars
        assert len(doc_id) == 44


class TestGetSourceIdentifier:
    """Test suite for get_source_identifier function."""

    def test_prefers_document_id(self):
        """Test document_id is preferred."""
        item = {"document_id": "doc-123", "url": "https://example.com"}
        assert get_source_identifier(item) == "doc-123"

    def test_falls_back_to_doc_id(self):
        """Test fallback to doc_id."""
        item = {"doc_id": "doc-456", "url": "https://example.com"}
        assert get_source_identifier(item) == "doc-456"

    def test_falls_back_to_url(self):
        """Test fallback to url."""
        item = {"url": "https://example.com/page"}
        assert get_source_identifier(item) == "https://example.com/page"

    def test_falls_back_to_path(self):
        """Test fallback to path."""
        item = {"path": "/docs/guide.md"}
        assert get_source_identifier(item) == "/docs/guide.md"

    def test_falls_back_to_source_url(self):
        """Test fallback to source_url."""
        item = {"source_url": "https://example.com"}
        assert get_source_identifier(item) == "https://example.com"

    def test_falls_back_to_cms_id(self):
        """Test fallback to cms_id."""
        item = {"cms_id": "notion-page-123"}
        assert get_source_identifier(item) == "notion-page-123"

    def test_empty_on_no_identifier(self):
        """Test returns empty string when no identifier found."""
        item = {"title": "Some Page"}
        assert get_source_identifier(item) == ""


class TestSerializeRows:
    """Test suite for serialize_rows function."""

    def test_serializes_status_enum(self):
        """Test that MapStatus enum is converted to string value."""
        rows = [{"status": MapStatus.SUCCESS, "id": "1"}]
        result = serialize_rows(rows)

        assert result[0]["status"] == "SUCCESS"
        assert result[0]["id"] == "1"

    def test_preserves_string_status(self):
        """Test that string status is preserved."""
        rows = [{"status": "SUCCESS", "id": "2"}]
        result = serialize_rows(rows)

        assert result[0]["status"] == "SUCCESS"

    def test_multiple_rows(self):
        """Test serializing multiple rows."""
        rows = [
            {"status": MapStatus.SUCCESS, "id": "1"},
            {"status": MapStatus.SUCCESS, "id": "2"},
            {"status": MapStatus.ERROR, "id": "3"},
        ]
        result = serialize_rows(rows)

        assert len(result) == 3
        assert result[0]["status"] == "SUCCESS"
        assert result[1]["status"] == "SUCCESS"
        assert result[2]["status"] == "ERROR"

    def test_does_not_modify_original(self):
        """Test that original rows are not modified."""
        original = [{"status": MapStatus.SUCCESS, "id": "1"}]
        serialize_rows(original)

        assert original[0]["status"] == MapStatus.SUCCESS


class TestFilterItems:
    """Test suite for filter_items function."""

    def test_no_filters(self):
        """Test that items pass through when no filters."""
        items = ["a.md", "b.txt", "c.py"]
        result = filter_items(items)
        assert result == items

    def test_include_patterns(self):
        """Test filtering with include patterns."""
        items = ["doc.md", "guide.mdx", "script.py", "data.json"]
        result = filter_items(items, include_patterns=("*.md", "*.mdx"))

        assert "doc.md" in result
        assert "guide.mdx" in result
        assert "script.py" not in result
        assert "data.json" not in result

    def test_exclude_patterns(self):
        """Test filtering with exclude patterns."""
        items = ["doc.md", "draft.md", "guide.md"]
        result = filter_items(items, exclude_patterns=("draft*",))

        assert "doc.md" in result
        assert "guide.md" in result
        assert "draft.md" not in result

    def test_both_patterns(self):
        """Test filtering with both include and exclude."""
        items = ["doc.md", "draft.md", "guide.mdx", "script.py"]
        result = filter_items(
            items,
            include_patterns=("*.md", "*.mdx"),
            exclude_patterns=("draft*",),
        )

        assert "doc.md" in result
        assert "guide.mdx" in result
        assert "draft.md" not in result
        assert "script.py" not in result

    def test_max_items(self):
        """Test limiting number of items."""
        items = ["a", "b", "c", "d", "e"]
        result = filter_items(items, max_items=3)

        assert len(result) == 3
        assert result == ["a", "b", "c"]

    def test_custom_to_string(self):
        """Test custom to_string function."""
        items = [{"name": "doc.md"}, {"name": "script.py"}]
        result = filter_items(
            items,
            include_patterns=("*.md",),
            to_string=lambda x: x["name"],
        )

        assert len(result) == 1
        assert result[0]["name"] == "doc.md"

    def test_empty_list(self):
        """Test with empty list."""
        result = filter_items([])
        assert result == []


class TestBuildRows:
    """Test suite for build_rows function."""

    def test_preserves_content_hash_from_folder_sources(self):
        """Test that content_hash is preserved for folder-discovered documents."""
        discovered_docs = [
            {
                "path": "/docs/guide.md",
                "title": "Guide",
                "content_hash": "abc123def456" * 5 + "abcd",  # 64 char SHA256
            }
        ]

        with patch("kurt.tools.map.utils.resolve_existing", return_value=set()):
            rows = build_rows(
                discovered_docs,
                discovery_method="folder",
                discovery_url="/docs",
                source_type="file",
            )

        assert len(rows) == 1
        assert rows[0]["content_hash"] == "abc123def456" * 5 + "abcd"

    def test_sets_source_url_from_path(self):
        """Test that source_url is set from path for folder sources."""
        discovered_docs = [{"path": "/docs/guide.md", "title": "Guide"}]

        with patch("kurt.tools.map.utils.resolve_existing", return_value=set()):
            rows = build_rows(
                discovered_docs,
                discovery_method="folder",
                discovery_url="/docs",
                source_type="file",
            )

        assert rows[0]["source_url"] == "/docs/guide.md"

    def test_sets_source_url_from_url(self):
        """Test that source_url is set from url for web sources."""
        discovered_docs = [{"url": "https://example.com/page", "title": "Page"}]

        with patch("kurt.tools.map.utils.resolve_existing", return_value=set()):
            rows = build_rows(
                discovered_docs,
                discovery_method="sitemap",
                discovery_url="https://example.com",
                source_type="url",
            )

        assert rows[0]["source_url"] == "https://example.com/page"

    def test_preserves_metadata_json(self):
        """Test that metadata is preserved in metadata_json field."""
        discovered_docs = [
            {
                "url": "https://example.com/page",
                "title": "Page",
                "metadata": {"cms_platform": "notion", "cms_instance": "workspace"},
            }
        ]

        with patch("kurt.tools.map.utils.resolve_existing", return_value=set()):
            rows = build_rows(
                discovered_docs,
                discovery_method="cms",
                discovery_url="notion/workspace",
                source_type="cms",
            )

        assert rows[0]["metadata_json"]["cms_platform"] == "notion"
        assert rows[0]["metadata_json"]["cms_instance"] == "workspace"

    def test_marks_existing_documents(self):
        """Test that existing documents are marked as not new."""
        discovered_docs = [
            {"url": "https://example.com/new", "title": "New"},
            {"url": "https://example.com/existing", "title": "Existing"},
        ]

        # Simulate that second doc already exists
        with patch("kurt.tools.map.utils.resolve_existing") as mock_resolve:
            mock_resolve.return_value = {"map_" + "x" * 40}  # Mock existing ID

            # Need to also mock make_document_id to return predictable IDs
            with patch("kurt.tools.map.utils.make_document_id") as mock_make_id:
                mock_make_id.side_effect = ["map_new123", "map_" + "x" * 40]

                rows = build_rows(
                    discovered_docs,
                    discovery_method="sitemap",
                    discovery_url="https://example.com",
                    source_type="url",
                )

        assert rows[0]["is_new"] is True
        assert rows[1]["is_new"] is False
