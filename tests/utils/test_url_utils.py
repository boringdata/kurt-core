"""Unit tests for URL utility functions."""

from kurt.utils.url_utils import (
    get_domain_from_url,
    get_url_depth,
    is_single_page_url,
    normalize_url_for_analytics,
    normalize_url_for_deduplication,
    normalize_url_for_matching,
    strip_www_prefix,
)

# ============================================================================
# Tests for URL Analysis Functions
# ============================================================================


class TestIsSinglePageUrl:
    """Tests for is_single_page_url function."""

    def test_single_page_urls(self):
        """Test URLs that are single pages."""
        assert is_single_page_url("https://example.com/blog/my-post") is True
        assert is_single_page_url("https://example.com/docs/guide/intro") is True
        assert is_single_page_url("https://example.com/about-us") is True

    def test_multi_page_urls(self):
        """Test URLs that are multi-page sources."""
        assert is_single_page_url("https://example.com/blog/") is False
        assert is_single_page_url("https://example.com") is False
        assert is_single_page_url("https://example.com/") is False

    def test_index_patterns(self):
        """Test common index patterns are treated as multi-page."""
        assert is_single_page_url("https://example.com/blog") is False
        assert is_single_page_url("https://example.com/docs") is False
        assert is_single_page_url("https://example.com/articles") is False
        assert is_single_page_url("https://example.com/news") is False


class TestGetUrlDepth:
    """Tests for get_url_depth function."""

    def test_url_depth_root(self):
        """Test depth 0 for root URLs."""
        assert get_url_depth("https://example.com") == 0
        assert get_url_depth("https://example.com/") == 0
        assert get_url_depth("http://example.com") == 0

    def test_url_depth_one(self):
        """Test depth 1 for single path segment."""
        assert get_url_depth("https://example.com/docs") == 1
        assert get_url_depth("https://example.com/blog") == 1
        assert get_url_depth("https://example.com/api/") == 1

    def test_url_depth_two(self):
        """Test depth 2 for two path segments."""
        assert get_url_depth("https://example.com/docs/guide") == 2
        assert get_url_depth("https://example.com/blog/posts") == 2
        assert get_url_depth("https://example.com/api/v1/") == 2

    def test_url_depth_three(self):
        """Test depth 3 for three path segments."""
        assert get_url_depth("https://example.com/docs/guide/intro") == 3
        assert get_url_depth("https://example.com/blog/2023/post") == 3
        assert get_url_depth("https://example.com/api/v1/users") == 3

    def test_url_depth_deep(self):
        """Test depth for deeply nested URLs."""
        assert get_url_depth("https://example.com/a/b/c/d/e") == 5
        assert get_url_depth("https://example.com/docs/guide/advanced/features/security") == 5

    def test_url_depth_none(self):
        """Test depth 0 for None input."""
        assert get_url_depth(None) == 0

    def test_url_depth_with_query_params(self):
        """Test that query parameters don't affect depth."""
        assert get_url_depth("https://example.com/docs?page=1") == 1
        assert get_url_depth("https://example.com/docs/guide?search=test&filter=all") == 2

    def test_url_depth_with_fragments(self):
        """Test that URL fragments don't affect depth."""
        assert get_url_depth("https://example.com/docs#intro") == 1
        assert get_url_depth("https://example.com/docs/guide#section-1") == 2

    def test_url_depth_with_trailing_slash(self):
        """Test that trailing slashes are handled correctly."""
        assert get_url_depth("https://example.com/docs/") == 1
        assert get_url_depth("https://example.com/docs/guide/") == 2

    def test_url_depth_with_file_extensions(self):
        """Test URLs with file extensions."""
        assert get_url_depth("https://example.com/docs/index.html") == 2
        assert get_url_depth("https://example.com/guide.pdf") == 1


# ============================================================================
# Tests for URL Normalization Functions
# ============================================================================


class TestNormalizeUrlForDeduplication:
    """Tests for normalize_url_for_deduplication function."""

    def test_removes_query_params(self):
        """Test that query parameters are removed."""
        assert (
            normalize_url_for_deduplication("https://example.com/blog?page=1")
            == "https://example.com/blog"
        )
        assert (
            normalize_url_for_deduplication("https://example.com/docs?search=test&filter=all")
            == "https://example.com/docs"
        )

    def test_removes_anchors(self):
        """Test that URL anchors are removed."""
        assert (
            normalize_url_for_deduplication("https://example.com/blog#latest")
            == "https://example.com/blog"
        )
        assert (
            normalize_url_for_deduplication("https://example.com/docs#section-1")
            == "https://example.com/docs"
        )

    def test_removes_both_query_and_anchor(self):
        """Test removing both query params and anchors."""
        assert (
            normalize_url_for_deduplication("https://example.com/blog?page=1#latest")
            == "https://example.com/blog"
        )

    def test_preserves_protocol_and_domain(self):
        """Test that protocol and domain are preserved."""
        assert (
            normalize_url_for_deduplication("https://example.com/blog")
            == "https://example.com/blog"
        )
        assert normalize_url_for_deduplication("http://example.com/") == "http://example.com/"

    def test_preserves_path(self):
        """Test that path is preserved."""
        assert (
            normalize_url_for_deduplication("https://example.com/docs/guide/intro")
            == "https://example.com/docs/guide/intro"
        )


class TestNormalizeUrlForMatching:
    """Tests for normalize_url_for_matching function."""

    def test_lowercases_url(self):
        """Test that URLs are lowercased."""
        assert normalize_url_for_matching("https://Example.com/Blog/") == "https://example.com/blog"
        assert normalize_url_for_matching("HTTPS://EXAMPLE.COM/BLOG") == "https://example.com/blog"

    def test_strips_trailing_slash(self):
        """Test that trailing slashes are removed."""
        assert normalize_url_for_matching("https://example.com/blog/") == "https://example.com/blog"
        assert (
            normalize_url_for_matching("https://example.com/docs/guide/")
            == "https://example.com/docs/guide"
        )

    def test_preserves_root_slash(self):
        """Test that root path slash is preserved."""
        assert normalize_url_for_matching("https://example.com/") == "https://example.com/"

    def test_handles_empty_string(self):
        """Test empty string input."""
        assert normalize_url_for_matching("") == ""

    def test_combined_normalization(self):
        """Test lowercase + trailing slash removal together."""
        assert (
            normalize_url_for_matching("https://Example.COM/Docs/Guide/")
            == "https://example.com/docs/guide"
        )


class TestNormalizeUrlForAnalytics:
    """Tests for normalize_url_for_analytics function."""

    def test_removes_protocol(self):
        """Test that protocol is removed."""
        assert normalize_url_for_analytics("https://example.com/blog") == "example.com/blog"
        assert normalize_url_for_analytics("http://example.com/blog") == "example.com/blog"

    def test_removes_www_prefix(self):
        """Test that www. prefix is removed."""
        assert normalize_url_for_analytics("https://www.example.com/blog") == "example.com/blog"
        assert (
            normalize_url_for_analytics("https://www.docs.example.com/guide")
            == "docs.example.com/guide"
        )

    def test_removes_query_params(self):
        """Test that query parameters are removed."""
        assert normalize_url_for_analytics("https://example.com/blog?page=1") == "example.com/blog"
        assert (
            normalize_url_for_analytics("https://example.com/docs?utm=123&ref=email")
            == "example.com/docs"
        )

    def test_removes_fragments(self):
        """Test that URL fragments are removed."""
        assert (
            normalize_url_for_analytics("https://example.com/blog#section-1") == "example.com/blog"
        )

    def test_strips_trailing_slash(self):
        """Test that trailing slashes are removed."""
        assert normalize_url_for_analytics("https://example.com/blog/") == "example.com/blog"

    def test_handles_root_path(self):
        """Test root path handling."""
        assert normalize_url_for_analytics("https://www.example.com") == "example.com"
        assert normalize_url_for_analytics("https://example.com/") == "example.com"

    def test_full_normalization(self):
        """Test complete normalization with all features."""
        assert (
            normalize_url_for_analytics(
                "https://www.docs.company.com/guides/quickstart/?utm=123#step-1"
            )
            == "docs.company.com/guides/quickstart"
        )

    def test_handles_empty_string(self):
        """Test empty string input."""
        assert normalize_url_for_analytics("") == ""


# ============================================================================
# Tests for Domain Utilities
# ============================================================================


class TestStripWwwPrefix:
    """Tests for strip_www_prefix function."""

    def test_strips_www_prefix(self):
        """Test stripping www. prefix."""
        assert strip_www_prefix("www.example.com") == "example.com"
        assert strip_www_prefix("www.subdomain.example.com") == "subdomain.example.com"

    def test_no_prefix_unchanged(self):
        """Test domains without www. remain unchanged."""
        assert strip_www_prefix("example.com") == "example.com"
        assert strip_www_prefix("subdomain.example.com") == "subdomain.example.com"

    def test_case_sensitive(self):
        """Test that stripping is case-sensitive (only lowercase www.)."""
        assert strip_www_prefix("WWW.example.com") == "WWW.example.com"
        assert strip_www_prefix("Www.example.com") == "Www.example.com"


class TestGetDomainFromUrl:
    """Tests for get_domain_from_url function."""

    def test_extracts_domain(self):
        """Test basic domain extraction."""
        assert get_domain_from_url("https://example.com/path/to/page") == "example.com"
        assert get_domain_from_url("http://example.com") == "example.com"

    def test_strips_www_by_default(self):
        """Test that www. is stripped by default."""
        assert get_domain_from_url("https://www.example.com/path") == "example.com"
        assert get_domain_from_url("https://www.subdomain.example.com") == "subdomain.example.com"

    def test_preserves_www_when_requested(self):
        """Test preserving www. when strip_www=False."""
        assert (
            get_domain_from_url("https://www.example.com/path", strip_www=False)
            == "www.example.com"
        )

    def test_handles_subdomains(self):
        """Test subdomain extraction."""
        assert get_domain_from_url("https://docs.example.com/guide") == "docs.example.com"
        assert get_domain_from_url("https://api.dev.example.com") == "api.dev.example.com"

    def test_handles_ports(self):
        """Test URLs with port numbers."""
        assert get_domain_from_url("https://example.com:8080/path") == "example.com:8080"
        assert get_domain_from_url("https://www.example.com:3000/app") == "example.com:3000"

    def test_handles_missing_domain(self):
        """Test URLs with missing domain (edge case)."""
        # urlparse returns empty string for malformed URLs
        assert get_domain_from_url("not-a-url") == "unknown"
