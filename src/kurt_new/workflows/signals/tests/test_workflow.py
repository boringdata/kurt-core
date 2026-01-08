"""Tests for signals workflow."""

from unittest.mock import MagicMock, patch

from kurt_new.workflows.signals.config import SignalsConfig


class TestSignalsConfig:
    """Tests for SignalsConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SignalsConfig(source="reddit", subreddit="python")

        assert config.source == "reddit"
        assert config.subreddit == "python"
        assert config.timeframe == "day"
        assert config.min_score == 0
        assert config.limit == 25
        assert config.sort == "hot"

    def test_get_keywords_list(self):
        """Test parsing comma-separated keywords."""
        config = SignalsConfig(source="reddit", keywords="python, machine learning, AI")
        keywords = config.get_keywords_list()

        assert len(keywords) == 3
        assert "python" in keywords
        assert "machine learning" in keywords
        assert "AI" in keywords

    def test_get_keywords_list_empty(self):
        """Test empty keywords."""
        config = SignalsConfig(source="reddit")
        keywords = config.get_keywords_list()

        assert keywords == []

    def test_get_subreddits_list_comma_separated(self):
        """Test parsing comma-separated subreddits."""
        config = SignalsConfig(
            source="reddit", subreddit="python, dataengineering, machinelearning"
        )
        subreddits = config.get_subreddits_list()

        assert len(subreddits) == 3
        assert "python" in subreddits
        assert "dataengineering" in subreddits

    def test_get_subreddits_list_plus_separated(self):
        """Test parsing plus-separated subreddits (Reddit style)."""
        config = SignalsConfig(source="reddit", subreddit="python+dataengineering+machinelearning")
        subreddits = config.get_subreddits_list()

        assert len(subreddits) == 3
        assert "python" in subreddits


class TestSignalsWorkflowIntegration:
    """Integration tests for signals workflow (mocked adapters)."""

    @patch("kurt_new.integrations.research.monitoring.reddit.requests.get")
    def test_reddit_adapter_integration(self, mock_get):
        """Test Reddit adapter with mocked HTTP."""
        from kurt_new.integrations.research.monitoring.reddit import RedditAdapter

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "test1",
                            "title": "Test post",
                            "permalink": "/r/test/1",
                            "created_utc": 1704067200,
                            "score": 100,
                            "num_comments": 20,
                        }
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = RedditAdapter()
        signals = adapter.get_subreddit_posts("test")

        assert len(signals) == 1
        assert signals[0].signal_id == "reddit_test1"

    @patch("kurt_new.integrations.research.monitoring.hackernews.requests.get")
    def test_hackernews_adapter_integration(self, mock_get):
        """Test HackerNews adapter with mocked HTTP."""
        from kurt_new.integrations.research.monitoring.hackernews import HackerNewsAdapter

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "hits": [
                {
                    "objectID": "123",
                    "title": "Test HN story",
                    "url": "https://example.com",
                    "created_at_i": 1704067200,
                    "points": 50,
                    "num_comments": 10,
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = HackerNewsAdapter()
        signals = adapter.search("test")

        assert len(signals) == 1
        assert signals[0].signal_id == "hn_123"
