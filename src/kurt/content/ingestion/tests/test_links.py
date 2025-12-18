"""
Unit tests for link extraction.

Pure function tests - no mocking needed.
"""

from kurt.content.ingestion.utils.links import extract_document_links


class TestExtractDocumentLinks:
    """Test markdown link extraction - pure functions, no mocks."""

    def test_extract_simple_link(self):
        """Test extracting a simple markdown link."""
        content = "See [Getting Started](https://example.com/getting-started) for details."
        source_url = "https://example.com/intro"

        links = extract_document_links(content, source_url)

        assert len(links) == 1
        assert links[0]["url"] == "https://example.com/getting-started"
        assert links[0]["anchor_text"] == "Getting Started"

    def test_extract_relative_link(self):
        """Test resolving relative URLs."""
        content = "See [Next Page](./next) for more."
        source_url = "https://example.com/docs/intro"

        links = extract_document_links(content, source_url)

        assert len(links) == 1
        assert links[0]["url"] == "https://example.com/docs/next"
        assert links[0]["anchor_text"] == "Next Page"

    def test_extract_parent_relative_link(self):
        """Test resolving parent relative URLs."""
        content = "See [Overview](../overview) for context."
        source_url = "https://example.com/docs/guides/tutorial"

        links = extract_document_links(content, source_url)

        assert len(links) == 1
        assert links[0]["url"] == "https://example.com/docs/overview"
        assert links[0]["anchor_text"] == "Overview"

    def test_skip_external_links(self):
        """Test that external links (different domain) are skipped."""
        content = """
        Internal: [Guide](https://example.com/guide)
        External: [Other Site](https://other.com/page)
        """
        source_url = "https://example.com/intro"

        links = extract_document_links(content, source_url)

        # Should only find internal link
        assert len(links) == 1
        assert links[0]["url"] == "https://example.com/guide"

    def test_skip_anchor_links(self):
        """Test that anchor links are skipped."""
        content = "Jump to [Section](#section) below."
        source_url = "https://example.com/page"

        links = extract_document_links(content, source_url)

        assert len(links) == 0

    def test_skip_mailto_links(self):
        """Test that mailto links are skipped."""
        content = "Contact [support](mailto:support@example.com) for help."
        source_url = "https://example.com/page"

        links = extract_document_links(content, source_url)

        assert len(links) == 0

    def test_skip_sanity_image_links(self):
        """Test that sanity-image links are skipped."""
        content = "See [image](sanity-image-abc123) here."
        source_url = "https://example.com/page"

        links = extract_document_links(content, source_url)

        assert len(links) == 0

    def test_extract_multiple_links(self):
        """Test extracting multiple links from content."""
        content = """
        Prerequisites: [Setup](https://example.com/setup)
        See also: [Advanced Guide](https://example.com/advanced)
        Related: [API Reference](https://example.com/api)
        """
        source_url = "https://example.com/tutorial"

        links = extract_document_links(content, source_url)

        assert len(links) == 3
        assert {link["anchor_text"] for link in links} == {
            "Setup",
            "Advanced Guide",
            "API Reference",
        }

    def test_truncate_long_anchor_text(self):
        """Test that anchor text is truncated to 500 chars."""
        long_text = "A" * 600
        content = f"See [{long_text}](https://example.com/page) for details."
        source_url = "https://example.com/intro"

        links = extract_document_links(content, source_url)

        assert len(links) == 1
        assert len(links[0]["anchor_text"]) == 500
        assert links[0]["anchor_text"] == "A" * 500

    def test_link_with_title_attribute(self):
        """Test extracting link with title attribute."""
        content = '[Guide](https://example.com/guide "Helpful Guide")'
        source_url = "https://example.com/intro"

        links = extract_document_links(content, source_url)

        assert len(links) == 1
        assert links[0]["url"] == "https://example.com/guide"
        assert links[0]["anchor_text"] == "Guide"

    def test_empty_content(self):
        """Test extracting from empty content."""
        links = extract_document_links("", "https://example.com/page")

        assert len(links) == 0

    def test_no_links_in_content(self):
        """Test content with no markdown links."""
        content = "This is plain text with no links."
        links = extract_document_links(content, "https://example.com/page")

        assert len(links) == 0

    def test_cms_document_with_base_url(self):
        """Test CMS document uses base_url for domain matching."""
        content = "See [Context Windows](https://technically.dev/universe/context-windows)."
        source_url = "sanity/prod/article/my-post"  # CMS path, not URL
        base_url = "https://technically.dev"

        links = extract_document_links(content, source_url, base_url=base_url)

        assert len(links) == 1
        assert links[0]["url"] == "https://technically.dev/universe/context-windows"

    def test_cms_document_skips_external_with_base_url(self):
        """Test CMS document skips external links when using base_url."""
        content = """
        Internal: [Article](https://technically.dev/posts/article)
        External: [Other](https://other.com/page)
        """
        source_url = "sanity/prod/article/my-post"
        base_url = "https://technically.dev"

        links = extract_document_links(content, source_url, base_url=base_url)

        assert len(links) == 1
        assert "technically.dev" in links[0]["url"]

    def test_web_document_ignores_base_url(self):
        """Test web document uses source_url even if base_url provided."""
        content = "See [Guide](https://example.com/guide)."
        source_url = "https://example.com/intro"
        base_url = "https://other.com"  # Should be ignored

        links = extract_document_links(content, source_url, base_url=base_url)

        # Should find link because source_url domain matches
        assert len(links) == 1
        assert links[0]["url"] == "https://example.com/guide"

    def test_root_relative_link(self):
        """Test resolving root-relative URLs."""
        content = "See [Home](/home) for more."
        source_url = "https://example.com/docs/intro"

        links = extract_document_links(content, source_url)

        assert len(links) == 1
        assert links[0]["url"] == "https://example.com/home"
