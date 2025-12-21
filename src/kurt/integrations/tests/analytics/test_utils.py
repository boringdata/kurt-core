"""Tests for analytics utility functions."""

from kurt.integrations.analytics.utils import normalize_url_for_analytics


class TestNormalizeUrlForAnalytics:
    """Test URL normalization for analytics matching."""

    def test_remove_protocol_https(self):
        """Test removing https:// protocol."""
        url = "https://docs.example.com/guide"
        normalized = normalize_url_for_analytics(url)
        assert normalized == "docs.example.com/guide"

    def test_remove_protocol_http(self):
        """Test removing http:// protocol."""
        url = "http://docs.example.com/guide"
        normalized = normalize_url_for_analytics(url)
        assert normalized == "docs.example.com/guide"

    def test_remove_www_prefix(self):
        """Test removing www. prefix."""
        url = "https://www.docs.example.com/guide"
        normalized = normalize_url_for_analytics(url)
        assert normalized == "docs.example.com/guide"

    def test_remove_trailing_slash(self):
        """Test removing trailing slash from path."""
        url = "https://docs.example.com/guide/"
        normalized = normalize_url_for_analytics(url)
        assert normalized == "docs.example.com/guide"

    def test_remove_query_parameters(self):
        """Test removing query parameters."""
        url = "https://docs.example.com/guide?utm_source=twitter&utm_campaign=launch"
        normalized = normalize_url_for_analytics(url)
        assert normalized == "docs.example.com/guide"

    def test_remove_fragment(self):
        """Test removing URL fragment (hash)."""
        url = "https://docs.example.com/guide#installation"
        normalized = normalize_url_for_analytics(url)
        assert normalized == "docs.example.com/guide"

    def test_all_normalizations_combined(self):
        """Test all normalizations applied together."""
        url = "https://www.docs.example.com/guides/quickstart/?utm=123#step-1"
        normalized = normalize_url_for_analytics(url)
        assert normalized == "docs.example.com/guides/quickstart"

    def test_root_domain_only(self):
        """Test normalization of root domain."""
        url = "https://docs.example.com"
        normalized = normalize_url_for_analytics(url)
        assert normalized == "docs.example.com"

    def test_root_domain_with_trailing_slash(self):
        """Test normalization of root domain with trailing slash."""
        url = "https://docs.example.com/"
        normalized = normalize_url_for_analytics(url)
        assert normalized == "docs.example.com"

    def test_subdomain_preserved(self):
        """Test that subdomains are preserved."""
        url = "https://api.docs.example.com/reference"
        normalized = normalize_url_for_analytics(url)
        assert normalized == "api.docs.example.com/reference"

    def test_path_with_multiple_segments(self):
        """Test normalization preserves path structure."""
        url = "https://docs.example.com/api/v2/authentication/oauth"
        normalized = normalize_url_for_analytics(url)
        assert normalized == "docs.example.com/api/v2/authentication/oauth"

    def test_empty_url(self):
        """Test normalization of empty URL."""
        url = ""
        normalized = normalize_url_for_analytics(url)
        assert normalized == ""

    def test_url_with_port(self):
        """Test normalization preserves port number."""
        url = "https://docs.example.com:8080/guide"
        normalized = normalize_url_for_analytics(url)
        assert normalized == "docs.example.com:8080/guide"

    def test_url_matching_examples(self):
        """Test that different URL variants normalize to same value."""
        urls = [
            "https://docs.example.com/guide",
            "http://docs.example.com/guide",
            "https://www.docs.example.com/guide",
            "https://docs.example.com/guide/",
            "https://docs.example.com/guide?utm=123",
            "https://docs.example.com/guide#section",
            "https://docs.example.com/guide/?utm=123#section",
        ]

        normalized_urls = [normalize_url_for_analytics(url) for url in urls]

        # All should normalize to the same value
        assert len(set(normalized_urls)) == 1
        assert normalized_urls[0] == "docs.example.com/guide"

    def test_preserves_case_sensitivity(self):
        """Test that URL case is preserved (URLs are case-sensitive)."""
        url = "https://docs.example.com/Guide/QuickStart"
        normalized = normalize_url_for_analytics(url)
        assert normalized == "docs.example.com/Guide/QuickStart"

    def test_special_characters_in_path(self):
        """Test normalization preserves special characters in path."""
        url = "https://docs.example.com/api/users/{id}/posts"
        normalized = normalize_url_for_analytics(url)
        assert normalized == "docs.example.com/api/users/{id}/posts"

    def test_encoded_characters_in_url(self):
        """Test normalization preserves URL-encoded characters."""
        url = "https://docs.example.com/search?q=hello%20world"
        normalized = normalize_url_for_analytics(url)
        # Query params are removed, so encoded chars in path would be preserved
        assert normalized == "docs.example.com/search"

    def test_url_with_username_password(self):
        """Test normalization handles URLs with credentials (edge case)."""
        url = "https://user:pass@docs.example.com/guide"
        normalized = normalize_url_for_analytics(url)
        # urlparse should handle this, credentials are part of netloc
        assert "user:pass@" in normalized  # Credentials preserved in netloc

    def test_international_domain(self):
        """Test normalization works with international domain names."""
        url = "https://docs.例え.com/guide"
        normalized = normalize_url_for_analytics(url)
        assert normalized == "docs.例え.com/guide"
