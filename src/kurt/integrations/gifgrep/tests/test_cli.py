"""Tests for GIF search CLI."""

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from kurt.integrations.gifgrep.cli import gif_group
from kurt.integrations.gifgrep.client import GifgrepError, GifResult

# Sample GifResult for testing
SAMPLE_RESULTS = [
    GifResult(
        id="123",
        title="Funny Cat",
        url="https://example.com/cat.gif",
        preview_url="https://example.com/cat_preview.gif",
        mp4_url="https://example.com/cat.mp4",
        width=480,
        height=360,
        tags=["cat", "funny"],
    ),
    GifResult(
        id="456",
        title="Happy Dog",
        url="https://example.com/dog.gif",
        preview_url="https://example.com/dog_preview.gif",
        mp4_url=None,
        width=320,
        height=240,
        tags=["dog", "happy"],
    ),
]


class TestSearchCommand:
    """Tests for search CLI command."""

    @patch("kurt.integrations.gifgrep.cli.GifgrepClient")
    def test_search_basic(self, mock_client_class):
        """Test basic search command."""
        mock_client = MagicMock()
        mock_client.search.return_value = SAMPLE_RESULTS
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(gif_group, ["search", "funny", "cat"])

        assert result.exit_code == 0
        assert "Funny Cat" in result.output
        assert "https://example.com/cat.gif" in result.output
        mock_client.search.assert_called_once()

    @patch("kurt.integrations.gifgrep.cli.GifgrepClient")
    def test_search_json_output(self, mock_client_class):
        """Test search with JSON output."""
        mock_client = MagicMock()
        mock_client.search.return_value = SAMPLE_RESULTS
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(gif_group, ["search", "cat", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2
        assert data[0]["id"] == "123"
        assert data[0]["title"] == "Funny Cat"

    @patch("kurt.integrations.gifgrep.cli.GifgrepClient")
    def test_search_urls_only(self, mock_client_class):
        """Test search with URLs-only output."""
        mock_client = MagicMock()
        mock_client.search.return_value = SAMPLE_RESULTS
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(gif_group, ["search", "cat", "--urls-only"])

        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert len(lines) == 2
        assert lines[0] == "https://example.com/cat.gif"
        assert lines[1] == "https://example.com/dog.gif"

    @patch("kurt.integrations.gifgrep.cli.GifgrepClient")
    def test_search_no_results(self, mock_client_class):
        """Test search with no results."""
        mock_client = MagicMock()
        mock_client.search.return_value = []
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(gif_group, ["search", "nonexistent"])

        assert result.exit_code == 0
        assert "No GIFs found" in result.output

    @patch("kurt.integrations.gifgrep.cli.GifgrepClient")
    def test_search_error_handling(self, mock_client_class):
        """Test search error handling."""
        mock_client = MagicMock()
        mock_client.search.side_effect = GifgrepError("API error")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(gif_group, ["search", "cat"])

        assert result.exit_code != 0
        assert "API error" in result.output

    @patch("kurt.integrations.gifgrep.cli.GifgrepClient")
    def test_search_with_options(self, mock_client_class):
        """Test search with limit and filter options."""
        mock_client = MagicMock()
        mock_client.search.return_value = SAMPLE_RESULTS[:1]
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(gif_group, ["search", "cat", "--limit", "5", "--filter", "high"])

        assert result.exit_code == 0
        mock_client.search.assert_called_once_with("cat", limit=5, content_filter="high")


class TestTrendingCommand:
    """Tests for trending CLI command."""

    @patch("kurt.integrations.gifgrep.cli.GifgrepClient")
    def test_trending_basic(self, mock_client_class):
        """Test basic trending command."""
        mock_client = MagicMock()
        mock_client.trending.return_value = SAMPLE_RESULTS
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(gif_group, ["trending"])

        assert result.exit_code == 0
        assert "Trending GIFs:" in result.output
        assert "Funny Cat" in result.output

    @patch("kurt.integrations.gifgrep.cli.GifgrepClient")
    def test_trending_json(self, mock_client_class):
        """Test trending with JSON output."""
        mock_client = MagicMock()
        mock_client.trending.return_value = SAMPLE_RESULTS
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(gif_group, ["trending", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2


class TestRandomCommand:
    """Tests for random CLI command."""

    @patch("kurt.integrations.gifgrep.cli.GifgrepClient")
    def test_random_basic(self, mock_client_class):
        """Test basic random command."""
        mock_client = MagicMock()
        mock_client.random.return_value = SAMPLE_RESULTS[0]
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(gif_group, ["random", "success"])

        assert result.exit_code == 0
        assert "Random GIF" in result.output
        assert "Funny Cat" in result.output

    @patch("kurt.integrations.gifgrep.cli.GifgrepClient")
    def test_random_no_result(self, mock_client_class):
        """Test random with no result."""
        mock_client = MagicMock()
        mock_client.random.return_value = None
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(gif_group, ["random", "nonexistent"])

        assert result.exit_code == 0
        assert "No GIF found" in result.output


class TestCLIHelp:
    """Tests for CLI help output."""

    def test_group_help(self):
        """Test main group help."""
        runner = CliRunner()
        result = runner.invoke(gif_group, ["--help"])

        assert result.exit_code == 0
        assert "GIF search integration" in result.output
        assert "search" in result.output
        assert "trending" in result.output
        assert "random" in result.output

    def test_search_help(self):
        """Test search command help."""
        runner = CliRunner()
        result = runner.invoke(gif_group, ["search", "--help"])

        assert result.exit_code == 0
        assert "Search for GIFs" in result.output
        assert "--limit" in result.output
        assert "--filter" in result.output
        assert "--json" in result.output
