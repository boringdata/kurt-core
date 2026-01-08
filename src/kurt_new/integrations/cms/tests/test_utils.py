"""Tests for CMS utility functions."""

from kurt_new.integrations.cms.utils import (
    build_document_url,
    detect_cms_from_url,
    extract_field_value,
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
        assert metadata["document_id"] == "abc123"

    def test_detect_sanity_without_document_id(self):
        """Test Sanity URL without document ID."""
        url = "https://myproject.sanity.studio/desk"
        platform, metadata = detect_cms_from_url(url)

        assert platform == "sanity"
        assert metadata["document_id"] is None

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

    def test_generic_cms_mention(self):
        """Test detecting generic CMS mentions."""
        is_cms, platform = is_cms_mention("Grab the article from our CMS")

        assert is_cms is True
        assert platform is None

    def test_no_cms_mention(self):
        """Test text without CMS mentions."""
        is_cms, platform = is_cms_mention("Check the website for details")

        assert is_cms is False
        assert platform is None


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

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        url = ""
        result = parse_cms_source_url(url)

        assert result is None


class TestExtractFieldValue:
    """Test field value extraction from documents."""

    def test_simple_field(self):
        """Test extracting simple field."""
        doc = {"title": "My Article", "status": "published"}
        result = extract_field_value(doc, "title")

        assert result == "My Article"

    def test_nested_field(self):
        """Test extracting nested field with dot notation."""
        doc = {"slug": {"current": "my-article"}}
        result = extract_field_value(doc, "slug.current")

        assert result == "my-article"

    def test_deeply_nested_field(self):
        """Test extracting deeply nested field."""
        doc = {"author": {"profile": {"displayName": "Jane Doe"}}}
        result = extract_field_value(doc, "author.profile.displayName")

        assert result == "Jane Doe"

    def test_missing_field(self):
        """Test extracting missing field returns None."""
        doc = {"title": "My Article"}
        result = extract_field_value(doc, "nonexistent")

        assert result is None

    def test_missing_nested_field(self):
        """Test extracting missing nested field returns None."""
        doc = {"author": {"name": "Jane"}}
        result = extract_field_value(doc, "author.profile.displayName")

        assert result is None

    def test_array_notation(self):
        """Test extracting array field."""
        doc = {"tags": ["python", "testing", "cms"]}
        result = extract_field_value(doc, "tags[]")

        assert result == ["python", "testing", "cms"]

    def test_array_notation_missing(self):
        """Test array notation on missing field returns empty list."""
        doc = {"title": "Article"}
        result = extract_field_value(doc, "tags[]")

        assert result == []

    def test_array_notation_not_array(self):
        """Test array notation on non-array field returns empty list."""
        doc = {"tags": "single-tag"}
        result = extract_field_value(doc, "tags[]")

        assert result == []

    def test_reference_notation(self):
        """Test reference resolution with -> notation."""
        doc = {"author": {"name": "Jane Doe", "email": "jane@example.com"}}
        result = extract_field_value(doc, "author->name")

        assert result == "Jane Doe"

    def test_reference_array(self):
        """Test reference resolution on array of objects."""
        doc = {
            "categories": [
                {"title": "Tech", "slug": "tech"},
                {"title": "News", "slug": "news"},
            ]
        }
        result = extract_field_value(doc, "categories[]->title")

        assert result == ["Tech", "News"]

    def test_reference_missing(self):
        """Test reference on missing field returns None."""
        doc = {"title": "Article"}
        result = extract_field_value(doc, "author->name")

        assert result is None

    def test_empty_field_path(self):
        """Test empty field path returns None."""
        doc = {"title": "Article"}
        result = extract_field_value(doc, "")

        assert result is None

    def test_none_field_path(self):
        """Test None field path returns None."""
        doc = {"title": "Article"}
        result = extract_field_value(doc, None)

        assert result is None


class TestBuildDocumentURL:
    """Test document URL building."""

    def test_no_base_url(self):
        """Test returns None when no base_url provided."""
        doc = {"slug": {"current": "my-article"}}
        mappings = {"article": {"slug_field": "slug.current"}}

        result = build_document_url(doc, "article", "", mappings)

        assert result is None

    def test_no_url_config_uses_slug_directly(self):
        """Test legacy behavior: slug appended directly when no url_config."""
        doc = {"slug": {"current": "my-article"}}
        mappings = {"article": {"slug_field": "slug.current"}}

        result = build_document_url(doc, "article", "https://example.com", mappings)

        assert result == "https://example.com/my-article"

    def test_static_path_prefix(self):
        """Test static url_config with path_prefix."""
        doc = {"slug": {"current": "my-article"}}
        mappings = {
            "article": {
                "slug_field": "slug.current",
                "url_config": {"type": "static", "path_prefix": "/blog/"},
            }
        }

        result = build_document_url(doc, "article", "https://example.com", mappings)

        assert result == "https://example.com/blog/my-article"

    def test_static_path_prefix_without_trailing_slash(self):
        """Test static url_config normalizes path_prefix without trailing slash."""
        doc = {"slug": {"current": "my-article"}}
        mappings = {
            "article": {
                "slug_field": "slug.current",
                "url_config": {"type": "static", "path_prefix": "/posts"},
            }
        }

        result = build_document_url(doc, "article", "https://example.com", mappings)

        assert result == "https://example.com/posts/my-article"

    def test_conditional_url_config(self):
        """Test conditional url_config based on field value."""
        doc = {"slug": {"current": "breaking-story"}, "category": "news"}
        mappings = {
            "article": {
                "slug_field": "slug.current",
                "url_config": {
                    "type": "conditional",
                    "field": "category",
                    "mappings": {"news": "/news/", "blog": "/blog/", "default": "/posts/"},
                },
            }
        }

        result = build_document_url(doc, "article", "https://example.com", mappings)

        assert result == "https://example.com/news/breaking-story"

    def test_conditional_url_config_default_fallback(self):
        """Test conditional url_config falls back to default."""
        doc = {"slug": {"current": "random-post"}, "category": "unknown"}
        mappings = {
            "article": {
                "slug_field": "slug.current",
                "url_config": {
                    "type": "conditional",
                    "field": "category",
                    "mappings": {"news": "/news/", "default": "/posts/"},
                },
            }
        }

        result = build_document_url(doc, "article", "https://example.com", mappings)

        assert result == "https://example.com/posts/random-post"

    def test_conditional_url_config_missing_field(self):
        """Test conditional url_config when field is missing from config."""
        doc = {"slug": {"current": "my-article"}}
        mappings = {
            "article": {
                "slug_field": "slug.current",
                "url_config": {"type": "conditional", "mappings": {}},
            }
        }

        result = build_document_url(doc, "article", "https://example.com", mappings)

        # Falls back to direct slug when field config missing
        assert result == "https://example.com/my-article"

    def test_missing_slug(self):
        """Test returns None when slug cannot be extracted."""
        doc = {"title": "Article without slug"}
        mappings = {"article": {"slug_field": "slug.current"}}

        result = build_document_url(doc, "article", "https://example.com", mappings)

        assert result is None

    def test_unknown_content_type_uses_defaults(self):
        """Test unknown content type uses default slug field."""
        doc = {"slug": "simple-slug"}
        mappings = {}  # No mappings for this type

        result = build_document_url(doc, "unknown_type", "https://example.com", mappings)

        assert result == "https://example.com/simple-slug"

    def test_sanity_slug_object(self):
        """Test handling Sanity slug objects with _type and current."""
        doc = {"slug": {"_type": "slug", "current": "my-sanity-slug"}}
        mappings = {"article": {"slug_field": "slug"}}

        result = build_document_url(doc, "article", "https://example.com", mappings)

        assert result == "https://example.com/my-sanity-slug"

    def test_base_url_with_trailing_slash(self):
        """Test base_url with trailing slash is handled correctly."""
        doc = {"slug": {"current": "my-article"}}
        mappings = {"article": {"slug_field": "slug.current"}}

        result = build_document_url(doc, "article", "https://example.com/", mappings)

        assert result == "https://example.com/my-article"
