"""Tests for TavilyFetcher engine."""

from unittest.mock import MagicMock, patch

import pytest


class TestTavilyFetcher:
    """Test suite for TavilyFetcher engine class."""

    def test_import(self):
        """Test that TavilyFetcher can be imported."""
        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        assert TavilyFetcher is not None

    def test_engine_alias(self):
        """Test that TavilyEngine alias exists for backwards compatibility."""
        from kurt.tools.fetch.engines.tavily import TavilyEngine, TavilyFetcher

        assert TavilyEngine is TavilyFetcher

    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_requires_api_key(self, mock_getenv):
        """Test that TavilyFetcher returns error on fetch without API key."""
        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        mock_getenv.return_value = None

        # Can be instantiated without API key
        fetcher = TavilyFetcher()
        # But fetch returns error result
        result = fetcher.fetch("https://example.com")
        assert result.success is False
        assert "TAVILY_API_KEY" in result.error

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_fetch_success(self, mock_getenv, mock_client_class):
        """Test successful fetch via TavilyFetcher."""
        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "url": "https://example.com",
                    "raw_content": "# Fetched Content\n\nThis is the content.",
                }
            ],
            "response_time": 1.2,
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        fetcher = TavilyFetcher()
        result = fetcher.fetch("https://example.com")

        assert result.success is True
        assert result.content == "# Fetched Content\n\nThis is the content."
        assert result.metadata["engine"] == "tavily"
        assert result.error is None

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_fetch_empty_result(self, mock_getenv, mock_client_class):
        """Test TavilyFetcher handles empty results."""
        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        fetcher = TavilyFetcher()
        result = fetcher.fetch("https://example.com")

        assert result.success is False
        assert "No result" in result.error

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_fetch_with_config(self, mock_getenv, mock_client_class):
        """Test TavilyFetcher accepts config."""
        from kurt.tools.fetch.core.base import FetcherConfig
        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [{"url": "https://example.com", "raw_content": "Content"}]
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        config = FetcherConfig(timeout=60.0)
        fetcher = TavilyFetcher(config)

        assert fetcher.config.timeout == 60.0

        result = fetcher.fetch("https://example.com")
        assert result.success is True

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_fetch_unexpected_exception(self, mock_getenv, mock_client_class):
        """Test TavilyFetcher handles unexpected exceptions."""
        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        mock_getenv.return_value = "test-api-key"

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = RuntimeError("Unexpected failure")
        mock_client_class.return_value = mock_client

        fetcher = TavilyFetcher()
        result = fetcher.fetch("https://example.com")

        assert result.success is False
        assert "Unexpected error" in result.error
        assert "RuntimeError" in result.error
        assert result.metadata["engine"] == "tavily"

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_fetch_empty_content(self, mock_getenv, mock_client_class):
        """Test TavilyFetcher handles empty content."""
        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [{"url": "https://example.com", "raw_content": ""}],
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        fetcher = TavilyFetcher()
        result = fetcher.fetch("https://example.com")

        assert result.success is False
        assert "Empty content" in result.error

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_fetch_raw_single_url(self, mock_getenv, mock_client_class):
        """Test fetch_raw with single URL."""
        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "url": "https://example.com",
                    "raw_content": "# Content",
                }
            ],
            "response_time": 1.5,
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        fetcher = TavilyFetcher()
        results = fetcher.fetch_raw("https://example.com")

        assert "https://example.com" in results
        content, metadata = results["https://example.com"]
        assert content == "# Content"
        assert metadata["response_time"] == 1.5

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_fetch_raw_batch(self, mock_getenv, mock_client_class):
        """Test fetch_raw with multiple URLs."""
        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"url": "https://example1.com", "raw_content": "# Content 1"},
                {"url": "https://example2.com", "raw_content": "# Content 2"},
            ],
            "response_time": 2.5,
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        fetcher = TavilyFetcher()
        results = fetcher.fetch_raw(["https://example1.com", "https://example2.com"])

        assert len(results) == 2
        assert "https://example1.com" in results
        assert "https://example2.com" in results

    def test_max_urls_limit(self):
        """Test that batch fetch raises error for more than 20 URLs."""
        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        with patch("kurt.tools.fetch.engines.tavily.os.getenv", return_value="test-key"):
            fetcher = TavilyFetcher()
            urls = [f"https://example{i}.com" for i in range(21)]

            with pytest.raises(ValueError, match="Maximum 20 URLs"):
                fetcher.fetch_raw(urls)

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_http_401_error(self, mock_getenv, mock_client_class):
        """Test that 401 response returns invalid API key error."""
        import httpx

        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.status_code = 401
        error = httpx.HTTPStatusError("", request=MagicMock(), response=mock_response)

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = error
        mock_client_class.return_value = mock_client

        fetcher = TavilyFetcher()
        results = fetcher.fetch_raw("https://example.com")

        assert "https://example.com" in results
        assert isinstance(results["https://example.com"], Exception)
        assert "Invalid API key" in str(results["https://example.com"])

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_http_429_rate_limit(self, mock_getenv, mock_client_class):
        """Test that 429 response returns rate limit error."""
        import httpx

        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.status_code = 429
        error = httpx.HTTPStatusError("", request=MagicMock(), response=mock_response)

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = error
        mock_client_class.return_value = mock_client

        fetcher = TavilyFetcher()
        results = fetcher.fetch_raw("https://example.com")

        assert "https://example.com" in results
        assert isinstance(results["https://example.com"], Exception)
        assert "Rate limit exceeded" in str(results["https://example.com"])
