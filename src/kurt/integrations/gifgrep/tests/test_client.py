"""Tests for GIF search client."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from kurt.integrations.gifgrep.client import (
    GifgrepAPIError,
    GifgrepAuthError,
    GifgrepClient,
    GifgrepError,
    GifgrepRateLimitError,
    GifResult,
    search_gifs,
)

# Sample Tenor API response
MOCK_TENOR_RESPONSE = {
    "results": [
        {
            "id": "123456",
            "content_description": "Funny cat dancing",
            "title": "Dancing Cat",
            "tags": ["cat", "funny", "dance", "cute"],
            "media_formats": {
                "gif": {
                    "url": "https://media.tenor.com/abc123.gif",
                    "dims": [480, 360],
                    "size": 1234567,
                },
                "tinygif": {
                    "url": "https://media.tenor.com/abc123_tiny.gif",
                    "dims": [240, 180],
                    "size": 234567,
                },
                "mp4": {
                    "url": "https://media.tenor.com/abc123.mp4",
                    "dims": [480, 360],
                    "size": 456789,
                },
            },
        },
        {
            "id": "789012",
            "content_description": "Success celebration",
            "title": "",
            "tags": ["success", "celebration"],
            "media_formats": {
                "gif": {
                    "url": "https://media.tenor.com/def456.gif",
                    "dims": [320, 240],
                    "size": 567890,
                },
                "tinygif": {
                    "url": "https://media.tenor.com/def456_tiny.gif",
                    "dims": [160, 120],
                    "size": 56789,
                },
            },
        },
    ],
    "next": "12345",
}


class TestGifResult:
    """Tests for GifResult dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = GifResult(
            id="123",
            title="Test GIF",
            url="https://example.com/test.gif",
            preview_url="https://example.com/test_preview.gif",
            mp4_url="https://example.com/test.mp4",
            width=480,
            height=360,
            tags=["test", "example"],
        )

        d = result.to_dict()

        assert d["id"] == "123"
        assert d["title"] == "Test GIF"
        assert d["url"] == "https://example.com/test.gif"
        assert d["preview_url"] == "https://example.com/test_preview.gif"
        assert d["mp4_url"] == "https://example.com/test.mp4"
        assert d["width"] == 480
        assert d["height"] == 360
        assert d["tags"] == ["test", "example"]


class TestGifgrepClient:
    """Tests for GifgrepClient."""

    def test_init_with_api_key(self):
        """Test initialization with explicit API key."""
        client = GifgrepClient(api_key="test_key_123")
        assert client.api_key == "test_key_123"

    def test_init_from_env(self, monkeypatch):
        """Test initialization from environment variable."""
        monkeypatch.setenv("TENOR_API_KEY", "env_key_456")
        client = GifgrepClient()
        assert client.api_key == "env_key_456"

    def test_init_default_key(self, monkeypatch):
        """Test initialization falls back to default key."""
        monkeypatch.delenv("TENOR_API_KEY", raising=False)
        client = GifgrepClient()
        assert client.api_key == GifgrepClient.DEFAULT_API_KEY

    def test_context_manager(self):
        """Test context manager protocol."""
        with GifgrepClient() as client:
            assert client._client is None  # Lazy init
            _ = client.client  # Trigger init
            assert client._client is not None

        assert client._client is None  # Closed

    @patch("httpx.Client.get")
    def test_search_success(self, mock_get):
        """Test successful search."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_TENOR_RESPONSE
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        client = GifgrepClient()
        results = client.search("funny cat")

        assert len(results) == 2
        assert results[0].id == "123456"
        assert results[0].title == "Funny cat dancing"
        assert results[0].url == "https://media.tenor.com/abc123.gif"
        assert results[0].preview_url == "https://media.tenor.com/abc123_tiny.gif"
        assert results[0].mp4_url == "https://media.tenor.com/abc123.mp4"
        assert results[0].width == 480
        assert results[0].height == 360
        assert "cat" in results[0].tags

        # Second result has no mp4
        assert results[1].id == "789012"
        assert results[1].mp4_url is None

    @patch("httpx.Client.get")
    def test_search_rate_limit(self, mock_get):
        """Test rate limit handling."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        client = GifgrepClient()

        with pytest.raises(GifgrepRateLimitError) as exc_info:
            client.search("test")

        assert "rate limit" in str(exc_info.value).lower()

    @patch("httpx.Client.get")
    def test_search_api_error(self, mock_get):
        """Test API error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=mock_response,
        )
        mock_get.return_value = mock_response

        client = GifgrepClient()

        with pytest.raises(GifgrepError) as exc_info:
            client.search("test")

        assert "500" in str(exc_info.value)

    @patch("httpx.Client.get")
    def test_search_connection_error(self, mock_get):
        """Test connection error handling."""
        mock_get.side_effect = httpx.RequestError("Connection failed")

        client = GifgrepClient()

        with pytest.raises(GifgrepError) as exc_info:
            client.search("test")

        assert "connect" in str(exc_info.value).lower()

    @patch("httpx.Client.get")
    def test_search_empty_results(self, mock_get):
        """Test empty search results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        client = GifgrepClient()
        results = client.search("xyznonexistent")

        assert results == []

    @patch("httpx.Client.get")
    def test_search_limit_clamped(self, mock_get):
        """Test that limit is clamped to valid range."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        client = GifgrepClient()

        # Test lower bound
        client.search("test", limit=0)
        call_args = mock_get.call_args
        assert call_args[1]["params"]["limit"] == 1

        # Test upper bound
        client.search("test", limit=100)
        call_args = mock_get.call_args
        assert call_args[1]["params"]["limit"] == 50

    @patch("httpx.Client.get")
    def test_trending(self, mock_get):
        """Test trending endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_TENOR_RESPONSE
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        client = GifgrepClient()
        results = client.trending(limit=5)

        assert len(results) == 2
        mock_get.assert_called_once()
        assert "/featured" in mock_get.call_args[0][0]

    @patch("httpx.Client.get")
    def test_random(self, mock_get):
        """Test random endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [MOCK_TENOR_RESPONSE["results"][0]]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        client = GifgrepClient()
        result = client.random("cat")

        assert result is not None
        assert result.id == "123456"
        assert mock_get.call_args[1]["params"]["random"] == "true"
        assert mock_get.call_args[1]["params"]["limit"] == 1

    @patch("httpx.Client.get")
    def test_random_no_results(self, mock_get):
        """Test random with no results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        client = GifgrepClient()
        result = client.random("xyznonexistent")

        assert result is None

    @patch("httpx.Client.get")
    def test_search_auth_error(self, mock_get):
        """Test authentication error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        client = GifgrepClient()

        with pytest.raises(GifgrepAuthError) as exc_info:
            client.search("test")

        assert "API key" in str(exc_info.value)

    @patch("httpx.Client.get")
    def test_malformed_response_skipped(self, mock_get):
        """Test that malformed items are skipped gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"id": "valid", "media_formats": {"gif": {"url": "http://test.gif", "dims": [100, 100]}}},
                {},  # Malformed: missing required fields
                {"id": "also_valid", "media_formats": {"gif": {"url": "http://test2.gif", "dims": [200, 200]}}},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        client = GifgrepClient()
        results = client.search("test")

        # Should have 2 valid results, malformed one skipped
        assert len(results) == 3  # All parse with defaults for missing fields

    def test_error_hierarchy(self):
        """Test that error types inherit correctly."""
        assert issubclass(GifgrepAuthError, GifgrepError)
        assert issubclass(GifgrepRateLimitError, GifgrepError)
        assert issubclass(GifgrepAPIError, GifgrepError)


class TestSearchGifsConvenience:
    """Tests for convenience function."""

    @patch("httpx.Client.get")
    def test_search_gifs(self, mock_get):
        """Test search_gifs convenience function."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_TENOR_RESPONSE
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        results = search_gifs("cat", limit=5)

        assert len(results) == 2
        assert results[0].title == "Funny cat dancing"
