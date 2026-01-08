"""Tests for domains_analytics utility functions."""

from kurt_new.integrations.domains_analytics.utils import normalize_url_for_analytics


class TestNormalizeUrlForAnalytics:
    """Test URL normalization for analytics matching."""

    def test_removes_protocol_https(self):
        """Test HTTPS protocol is removed."""
        result = normalize_url_for_analytics("https://example.com/page")
        assert result == "example.com/page"

    def test_removes_protocol_http(self):
        """Test HTTP protocol is removed."""
        result = normalize_url_for_analytics("http://example.com/page")
        assert result == "example.com/page"

    def test_removes_www(self):
        """Test www prefix is removed."""
        result = normalize_url_for_analytics("https://www.example.com/page")
        assert result == "example.com/page"

    def test_removes_trailing_slash(self):
        """Test trailing slash is removed."""
        result = normalize_url_for_analytics("https://example.com/page/")
        assert result == "example.com/page"

    def test_removes_query_params(self):
        """Test query parameters are removed."""
        result = normalize_url_for_analytics("https://example.com/page?utm_source=google&ref=123")
        assert result == "example.com/page"

    def test_removes_fragments(self):
        """Test URL fragments are removed."""
        result = normalize_url_for_analytics("https://example.com/page#section-1")
        assert result == "example.com/page"

    def test_handles_root_path(self):
        """Test root path URL is normalized correctly."""
        result = normalize_url_for_analytics("https://example.com/")
        assert result == "example.com"

    def test_handles_domain_only(self):
        """Test domain-only URL is normalized correctly."""
        result = normalize_url_for_analytics("https://example.com")
        assert result == "example.com"

    def test_handles_empty_string(self):
        """Test empty string returns empty string."""
        result = normalize_url_for_analytics("")
        assert result == ""

    def test_complex_url(self):
        """Test complex URL with all components."""
        url = "https://www.docs.company.com/guides/quickstart/?utm=123#step-1"
        result = normalize_url_for_analytics(url)
        assert result == "docs.company.com/guides/quickstart"

    def test_preserves_subdomain(self):
        """Test subdomains (other than www) are preserved."""
        result = normalize_url_for_analytics("https://blog.example.com/post")
        assert result == "blog.example.com/post"

    def test_deep_path(self):
        """Test deep paths are preserved."""
        result = normalize_url_for_analytics("https://example.com/a/b/c/d/e")
        assert result == "example.com/a/b/c/d/e"
