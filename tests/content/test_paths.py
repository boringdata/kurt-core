"""Unit tests for content path utilities."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from kurt.content.paths import (
    create_cms_content_path,
    create_content_path,
    parse_source_identifier,
)

# ============================================================================
# Tests for parse_source_identifier
# ============================================================================


class TestParseSourceIdentifier:
    """Tests for parse_source_identifier function."""

    def test_detects_web_urls(self):
        """Test detection of web URLs."""
        source_type, data = parse_source_identifier("https://example.com/page")
        assert source_type == "web"
        assert data == {"url": "https://example.com/page"}

        source_type, data = parse_source_identifier("http://example.com/blog")
        assert source_type == "web"
        assert data == {"url": "http://example.com/blog"}

    def test_detects_cms_format_full(self):
        """Test detection of full CMS format (4 parts)."""
        source_type, data = parse_source_identifier("sanity/prod/article/vibe-coding-guide")
        assert source_type == "cms"
        assert data == {
            "platform": "sanity",
            "instance": "prod",
            "schema": "article",
            "slug": "vibe-coding-guide",
        }

    def test_detects_cms_format_legacy(self):
        """Test detection of legacy CMS format (3 parts)."""
        source_type, data = parse_source_identifier("sanity/prod/my-document")
        assert source_type == "cms"
        assert data == {
            "platform": "sanity",
            "instance": "prod",
            "schema": None,
            "slug": "my-document",
        }

    def test_invalid_format_raises_error(self):
        """Test that invalid formats raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_source_identifier("invalid-format")

        assert "Invalid source URL format" in str(exc_info.value)

    def test_different_cms_platforms(self):
        """Test various CMS platform formats."""
        # Contentful
        source_type, data = parse_source_identifier("contentful/staging/page/homepage")
        assert source_type == "cms"
        assert data["platform"] == "contentful"

        # WordPress
        source_type, data = parse_source_identifier("wordpress/prod/post/my-post")
        assert source_type == "cms"
        assert data["platform"] == "wordpress"


# ============================================================================
# Tests for create_cms_content_path
# ============================================================================


class TestCreateCmsContentPath:
    """Tests for create_cms_content_path function."""

    def test_creates_correct_path_structure(self):
        """Test that CMS paths follow sources/cms/{platform}/{instance}/{doc_id}.md structure."""
        # Mock config
        mock_config = Mock()
        mock_config.get_absolute_sources_path.return_value = Path("/sources")

        result = create_cms_content_path("sanity", "prod", "abc-123", mock_config)

        assert result == Path("/sources/cms/sanity/prod/abc-123.md")
        assert result.suffix == ".md"
        assert "cms" in result.parts
        assert "sanity" in result.parts
        assert "prod" in result.parts

    def test_handles_different_platforms(self):
        """Test path creation for different CMS platforms."""
        mock_config = Mock()
        mock_config.get_absolute_sources_path.return_value = Path("/sources")

        # Contentful
        result = create_cms_content_path("contentful", "staging", "doc-456", mock_config)
        assert result == Path("/sources/cms/contentful/staging/doc-456.md")

        # WordPress
        result = create_cms_content_path("wordpress", "prod", "post-789", mock_config)
        assert result == Path("/sources/cms/wordpress/prod/post-789.md")

    def test_handles_complex_doc_ids(self):
        """Test path creation with complex document IDs."""
        mock_config = Mock()
        mock_config.get_absolute_sources_path.return_value = Path("/sources")

        # UUID-like ID
        result = create_cms_content_path(
            "sanity", "prod", "550e8400-e29b-41d4-a716-446655440000", mock_config
        )
        assert result.name == "550e8400-e29b-41d4-a716-446655440000.md"

        # Slug-like ID
        result = create_cms_content_path("sanity", "prod", "my-article-slug", mock_config)
        assert result.name == "my-article-slug.md"


# ============================================================================
# Tests for create_content_path
# ============================================================================


class TestCreateContentPath:
    """Tests for create_content_path function."""

    def test_creates_correct_path_structure(self):
        """Test basic path structure for web URLs."""
        mock_config = Mock()
        mock_config.get_absolute_sources_path.return_value = Path("/sources")

        result = create_content_path("https://docs.example.com/guide/getting-started", mock_config)

        assert result == Path("/sources/docs.example.com/guide/getting-started.md")
        assert result.suffix == ".md"

    def test_strips_www_prefix(self):
        """Test that www. prefix is stripped from domain."""
        mock_config = Mock()
        mock_config.get_absolute_sources_path.return_value = Path("/sources")

        result = create_content_path("https://www.example.com/page", mock_config)

        assert result == Path("/sources/example.com/page.md")
        assert "www." not in str(result)

    def test_handles_root_urls(self):
        """Test handling of root URLs (no path)."""
        mock_config = Mock()
        mock_config.get_absolute_sources_path.return_value = Path("/sources")

        # No path
        result = create_content_path("https://example.com", mock_config)
        assert result == Path("/sources/example.com/index.md")

        # Root slash
        result = create_content_path("https://example.com/", mock_config)
        assert result == Path("/sources/example.com/index.md")

    def test_handles_trailing_slashes(self):
        """Test handling of paths with trailing slashes.

        Note: create_content_path strips trailing slash first via strip("/"),
        so "/docs/" becomes "docs" which is treated as a regular file path.
        """
        mock_config = Mock()
        mock_config.get_absolute_sources_path.return_value = Path("/sources")

        result = create_content_path("https://example.com/docs/", mock_config)

        # After stripping "/", "docs/" becomes "docs" -> "docs.md"
        assert result == Path("/sources/example.com/docs.md")

    def test_adds_md_extension(self):
        """Test that .md extension is added if not present."""
        mock_config = Mock()
        mock_config.get_absolute_sources_path.return_value = Path("/sources")

        result = create_content_path("https://example.com/page", mock_config)
        assert result.suffix == ".md"

        # Path without extension
        result = create_content_path("https://example.com/docs/guide", mock_config)
        assert result.suffix == ".md"

    def test_preserves_existing_md_extension(self):
        """Test that existing .md extension is preserved (not doubled)."""
        mock_config = Mock()
        mock_config.get_absolute_sources_path.return_value = Path("/sources")

        result = create_content_path("https://example.com/page.md", mock_config)
        assert result == Path("/sources/example.com/page.md")
        assert result.name == "page.md"  # Not page.md.md

    def test_handles_subdomains(self):
        """Test handling of subdomains."""
        mock_config = Mock()
        mock_config.get_absolute_sources_path.return_value = Path("/sources")

        result = create_content_path("https://docs.example.com/guide", mock_config)
        assert result == Path("/sources/docs.example.com/guide.md")

        result = create_content_path("https://api.dev.example.com/reference", mock_config)
        assert result == Path("/sources/api.dev.example.com/reference.md")

    def test_handles_nested_paths(self):
        """Test handling of deeply nested URL paths."""
        mock_config = Mock()
        mock_config.get_absolute_sources_path.return_value = Path("/sources")

        result = create_content_path(
            "https://example.com/docs/guide/advanced/security", mock_config
        )
        assert result == Path("/sources/example.com/docs/guide/advanced/security.md")

    def test_handles_urls_with_ports(self):
        """Test handling of URLs with port numbers."""
        mock_config = Mock()
        mock_config.get_absolute_sources_path.return_value = Path("/sources")

        result = create_content_path("https://example.com:8080/docs", mock_config)
        assert result == Path("/sources/example.com:8080/docs.md")


# ============================================================================
# Integration Tests
# ============================================================================


class TestPathsIntegration:
    """Integration tests for path utilities."""

    def test_web_url_end_to_end(self):
        """Test complete flow: parse source -> create path."""
        mock_config = Mock()
        mock_config.get_absolute_sources_path.return_value = Path("/sources")

        # Parse URL
        source_type, data = parse_source_identifier("https://docs.example.com/guide")
        assert source_type == "web"

        # Create path
        path = create_content_path(data["url"], mock_config)
        assert path == Path("/sources/docs.example.com/guide.md")

    def test_cms_identifier_end_to_end(self):
        """Test complete flow: parse CMS identifier -> create path."""
        mock_config = Mock()
        mock_config.get_absolute_sources_path.return_value = Path("/sources")

        # Parse CMS identifier
        source_type, data = parse_source_identifier("sanity/prod/article/my-post")
        assert source_type == "cms"

        # Create path (using slug as doc_id for this example)
        path = create_cms_content_path(
            data["platform"], data["instance"], data["slug"], mock_config
        )
        assert path == Path("/sources/cms/sanity/prod/my-post.md")

    def test_path_consistency_different_www_variants(self):
        """Test that www and non-www URLs map to same path."""
        mock_config = Mock()
        mock_config.get_absolute_sources_path.return_value = Path("/sources")

        path1 = create_content_path("https://www.example.com/docs", mock_config)
        path2 = create_content_path("https://example.com/docs", mock_config)

        assert path1 == path2
        assert path1 == Path("/sources/example.com/docs.md")
