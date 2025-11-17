"""Tests for CMS utility functions."""

from kurt.integrations.cms.utils import (
    detect_cms_from_url,
    is_cms_mention,
    parse_cms_source_url,
)


class TestDetectCMSFromURL:
    """Test CMS detection from URLs."""

    def test_detect_sanity_studio_url(self):
        """Test detecting Sanity Studio URLs."""
        url = "https://myproject.sanity.studio/desk/article;abc123"
        platform, metadata = detect_cms_from_url(url)

        assert platform == "sanity"
        # Regex captures everything before .sanity.studio (including protocol)
        assert metadata["project_hint"] == "https://myproject"
        assert metadata["document_id"] == "abc123"

    def test_detect_sanity_without_document_id(self):
        """Test Sanity URL without document ID."""
        url = "https://myproject.sanity.studio/desk"
        platform, metadata = detect_cms_from_url(url)

        assert platform == "sanity"
        assert metadata["project_hint"] == "https://myproject"
        assert metadata["document_id"] is None

    def test_detect_sanity_without_project_match(self):
        """Test Sanity URL without .sanity.studio pattern doesn't match."""
        url = "https://example.com/sanity-studio/desk"
        platform, metadata = detect_cms_from_url(url)

        # Should not match because it doesn't have .sanity.studio
        assert platform is None
        assert metadata == {}

    def test_detect_contentful_url(self):
        """Test detecting Contentful URLs."""
        url = "https://app.contentful.com/spaces/abc123/entries/def456"
        platform, metadata = detect_cms_from_url(url)

        assert platform == "contentful"
        assert metadata["space_id"] == "abc123"
        assert metadata["entry_id"] == "def456"

    def test_detect_contentful_without_entry(self):
        """Test Contentful URL without entry ID."""
        url = "https://app.contentful.com/spaces/abc123"
        platform, metadata = detect_cms_from_url(url)

        assert platform == "contentful"
        assert metadata["space_id"] == "abc123"
        assert metadata["entry_id"] is None

    def test_detect_wordpress_admin(self):
        """Test detecting WordPress admin URLs."""
        url = "https://example.com/wp-admin/post.php?post=123&action=edit"
        platform, metadata = detect_cms_from_url(url)

        assert platform == "wordpress"
        assert metadata["post_id"] == "123"

    def test_detect_wordpress_content(self):
        """Test detecting WordPress content URLs."""
        url = "https://example.com/wp-content/uploads/image.jpg"
        platform, metadata = detect_cms_from_url(url)

        assert platform == "wordpress"
        assert metadata["post_id"] is None

    def test_detect_no_cms(self):
        """Test URL without CMS indicators."""
        url = "https://example.com/blog/article"
        platform, metadata = detect_cms_from_url(url)

        assert platform is None
        assert metadata == {}

    def test_detect_regular_blog_url(self):
        """Test that regular blog URLs don't trigger false positives."""
        url = "https://blog.example.com/my-post"
        platform, metadata = detect_cms_from_url(url)

        assert platform is None
        assert metadata == {}


class TestIsCMSMention:
    """Test CMS mention detection in natural language."""

    def test_sanity_mention(self):
        """Test detecting Sanity mentions."""
        is_cms, platform = is_cms_mention("Can you fetch this from my Sanity CMS?")

        assert is_cms is True
        assert platform == "sanity"

    def test_contentful_mention(self):
        """Test detecting Contentful mentions."""
        is_cms, platform = is_cms_mention("Pull the latest from Contentful")

        assert is_cms is True
        assert platform == "contentful"

    def test_wordpress_mention(self):
        """Test detecting WordPress mentions."""
        is_cms, platform = is_cms_mention("Update the WordPress content")

        assert is_cms is True
        assert platform == "wordpress"

    def test_wp_abbreviation(self):
        """Test detecting WP abbreviation."""
        is_cms, platform = is_cms_mention("Check the WP admin")

        assert is_cms is True
        assert platform == "wordpress"

    def test_generic_cms_mention(self):
        """Test detecting generic CMS mentions."""
        is_cms, platform = is_cms_mention("Grab the article from our CMS")

        assert is_cms is True
        assert platform is None

    def test_content_management_mention(self):
        """Test detecting 'content management' mentions."""
        is_cms, platform = is_cms_mention("The content management system has the data")

        assert is_cms is True
        assert platform is None

    def test_content_system_mention(self):
        """Test detecting 'content system' mentions."""
        is_cms, platform = is_cms_mention("Pull from the content system")

        assert is_cms is True
        assert platform is None

    def test_no_cms_mention(self):
        """Test text without CMS mentions."""
        is_cms, platform = is_cms_mention("Check the website for details")

        assert is_cms is False
        assert platform is None

    def test_case_insensitive(self):
        """Test that detection is case-insensitive."""
        texts = [
            "SANITY CMS",
            "Contentful backend",
            "WordPress site",
            "cms platform",
        ]

        for text in texts:
            is_cms, _ = is_cms_mention(text)
            assert is_cms is True


class TestParseCMSSourceURL:
    """Test CMS source URL parsing."""

    def test_parse_full_format(self):
        """Test parsing full 4-part CMS URL."""
        url = "sanity/prod/article/vibe-coding-guide"
        result = parse_cms_source_url(url)

        assert result is not None
        assert result["platform"] == "sanity"
        assert result["instance"] == "prod"
        assert result["schema"] == "article"
        assert result["slug"] == "vibe-coding-guide"

    def test_parse_legacy_format(self):
        """Test parsing legacy 3-part format."""
        url = "sanity/prod/vibe-coding-guide"
        result = parse_cms_source_url(url)

        assert result is not None
        assert result["platform"] == "sanity"
        assert result["instance"] == "prod"
        assert result["schema"] is None
        assert result["slug"] == "vibe-coding-guide"

    def test_parse_http_url(self):
        """Test that HTTP URLs are not parsed as CMS format."""
        url = "http://example.com/page"
        result = parse_cms_source_url(url)

        assert result is None

    def test_parse_https_url(self):
        """Test that HTTPS URLs are not parsed as CMS format."""
        url = "https://example.com/page"
        result = parse_cms_source_url(url)

        assert result is None

    def test_parse_insufficient_parts(self):
        """Test that URLs with too few parts return None."""
        url = "sanity/prod"
        result = parse_cms_source_url(url)

        assert result is None

    def test_parse_too_many_parts(self):
        """Test parsing URL with more than 4 parts (uses first 4)."""
        url = "sanity/prod/article/my-slug/extra/parts"
        result = parse_cms_source_url(url)

        # Should parse first 4 parts
        assert result is not None
        assert result["platform"] == "sanity"
        assert result["instance"] == "prod"
        assert result["schema"] == "article"
        assert result["slug"] == "my-slug/extra/parts"

    def test_parse_single_part(self):
        """Test that single part returns None."""
        url = "sanity"
        result = parse_cms_source_url(url)

        assert result is None

    def test_parse_contentful_format(self):
        """Test parsing Contentful CMS format."""
        url = "contentful/production/blogPost/my-first-post"
        result = parse_cms_source_url(url)

        assert result is not None
        assert result["platform"] == "contentful"
        assert result["instance"] == "production"
        assert result["schema"] == "blogPost"
        assert result["slug"] == "my-first-post"

    def test_parse_wordpress_format(self):
        """Test parsing WordPress CMS format."""
        url = "wordpress/main/post/hello-world"
        result = parse_cms_source_url(url)

        assert result is not None
        assert result["platform"] == "wordpress"
        assert result["instance"] == "main"
        assert result["schema"] == "post"
        assert result["slug"] == "hello-world"

    def test_parse_with_hyphens_in_slug(self):
        """Test parsing URLs with hyphens in slug."""
        url = "sanity/prod/article/how-to-build-with-ai-tools"
        result = parse_cms_source_url(url)

        assert result is not None
        assert result["slug"] == "how-to-build-with-ai-tools"

    def test_parse_with_underscores(self):
        """Test parsing URLs with underscores."""
        url = "sanity/prod/blog_post/my_article"
        result = parse_cms_source_url(url)

        assert result is not None
        assert result["schema"] == "blog_post"
        assert result["slug"] == "my_article"

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        url = ""
        result = parse_cms_source_url(url)

        assert result is None
