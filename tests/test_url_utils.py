"""Unit tests for URL utility functions."""

from kurt.utils.url_utils import get_url_depth


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
