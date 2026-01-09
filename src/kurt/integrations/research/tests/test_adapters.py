"""Tests for research adapters."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from kurt.integrations.research.base import Citation, ResearchResult
from kurt.integrations.research.monitoring.feeds import FeedAdapter
from kurt.integrations.research.monitoring.hackernews import HackerNewsAdapter
from kurt.integrations.research.monitoring.models import Signal
from kurt.integrations.research.monitoring.reddit import RedditAdapter


class TestCitation:
    """Tests for Citation dataclass."""

    def test_to_dict(self):
        """Test Citation serialization."""
        citation = Citation(
            title="Test Source",
            url="https://example.com",
            snippet="Test snippet",
            domain="example.com",
        )
        result = citation.to_dict()

        assert result["title"] == "Test Source"
        assert result["url"] == "https://example.com"
        assert result["snippet"] == "Test snippet"
        assert result["domain"] == "example.com"


class TestResearchResult:
    """Tests for ResearchResult dataclass."""

    def test_to_dict(self, sample_citations):
        """Test ResearchResult serialization."""
        result = ResearchResult(
            id="test_123",
            query="Test query",
            answer="Test answer",
            citations=sample_citations,
            source="perplexity",
            model="sonar-reasoning",
            timestamp=datetime(2024, 1, 1),
            response_time_seconds=1.5,
        )
        data = result.to_dict()

        assert data["id"] == "test_123"
        assert data["query"] == "Test query"
        assert data["answer"] == "Test answer"
        assert len(data["citations"]) == 2
        assert data["source"] == "perplexity"

    def test_to_markdown(self, sample_research_result):
        """Test ResearchResult markdown generation."""
        markdown = sample_research_result.to_markdown()

        assert "---" in markdown
        assert "research_id: res_20240101_abc123" in markdown
        assert "research_source: perplexity" in markdown
        assert "# What is machine learning?" in markdown
        assert "## Sources" in markdown


class TestSignal:
    """Tests for Signal dataclass."""

    def test_relevance_score(self, sample_signal):
        """Test relevance score calculation."""
        score = sample_signal.relevance_score

        # Score of 150 -> normalized to 1.0 (capped)
        # Comments of 42 -> normalized to 0.84
        # Expected: 1.0 * 0.7 + 0.84 * 0.3 = 0.952
        assert 0.9 <= score <= 1.0

    def test_to_dict(self, sample_signal):
        """Test Signal serialization."""
        data = sample_signal.to_dict()

        assert data["signal_id"] == "reddit_abc123"
        assert data["source"] == "reddit"
        assert data["title"] == "Interesting discussion about Python"
        assert "relevance_score" in data

    def test_from_dict(self, sample_signal):
        """Test Signal deserialization."""
        data = sample_signal.to_dict()
        restored = Signal.from_dict(data)

        assert restored.signal_id == sample_signal.signal_id
        assert restored.source == sample_signal.source
        assert restored.title == sample_signal.title

    def test_matches_keywords(self, sample_signal):
        """Test keyword matching."""
        assert sample_signal.matches_keywords(["python"]) is True
        assert sample_signal.matches_keywords(["discussion"]) is True
        assert sample_signal.matches_keywords(["nonexistent"]) is False
        assert sample_signal.matches_keywords([]) is True  # Empty = match all


class TestRedditAdapter:
    """Tests for Reddit adapter."""

    @patch("requests.get")
    def test_get_subreddit_posts(self, mock_get):
        """Test fetching subreddit posts."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "abc123",
                            "title": "Test Post",
                            "permalink": "/r/python/comments/abc123",
                            "selftext": "Test content",
                            "created_utc": 1704067200,
                            "author": "testuser",
                            "score": 100,
                            "num_comments": 25,
                        }
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = RedditAdapter()
        signals = adapter.get_subreddit_posts("python", limit=10)

        assert len(signals) == 1
        assert signals[0].signal_id == "reddit_abc123"
        assert signals[0].title == "Test Post"
        assert signals[0].subreddit == "python"
        assert signals[0].score == 100

    @patch("requests.get")
    def test_get_subreddit_posts_with_min_score(self, mock_get):
        """Test filtering by minimum score."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "1",
                            "title": "High score",
                            "score": 100,
                            "created_utc": 0,
                            "permalink": "/1",
                        }
                    },
                    {
                        "data": {
                            "id": "2",
                            "title": "Low score",
                            "score": 5,
                            "created_utc": 0,
                            "permalink": "/2",
                        }
                    },
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = RedditAdapter()
        signals = adapter.get_subreddit_posts("python", min_score=50)

        assert len(signals) == 1
        assert signals[0].title == "High score"


class TestHackerNewsAdapter:
    """Tests for HackerNews adapter."""

    @patch("requests.get")
    def test_search(self, mock_get):
        """Test HN search."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "hits": [
                {
                    "objectID": "12345",
                    "title": "Test Story",
                    "url": "https://example.com",
                    "created_at_i": 1704067200,
                    "author": "testuser",
                    "points": 100,
                    "num_comments": 50,
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        adapter = HackerNewsAdapter()
        signals = adapter.search("test query", limit=10)

        assert len(signals) == 1
        assert signals[0].signal_id == "hn_12345"
        assert signals[0].title == "Test Story"
        assert signals[0].score == 100


class TestFeedAdapter:
    """Tests for RSS/Atom feed adapter."""

    @patch("feedparser.parse")
    def test_get_feed_entries(self, mock_parse):
        """Test fetching feed entries."""
        mock_parse.return_value = MagicMock(
            bozo=False,
            entries=[
                MagicMock(
                    title="Test Entry",
                    link="https://example.com/entry",
                    summary="Test summary",
                    published_parsed=(2024, 1, 1, 12, 0, 0, 0, 0, 0),
                    author="Test Author",
                )
            ],
            feed=MagicMock(link="https://example.com"),
        )

        adapter = FeedAdapter()
        signals = adapter.get_feed_entries("https://example.com/feed")

        assert len(signals) == 1
        assert signals[0].title == "Test Entry"
        assert signals[0].source == "rss"

    @patch("feedparser.parse")
    def test_check_feed_valid(self, mock_parse):
        """Test checking valid feed."""
        mock_parse.return_value = MagicMock(
            bozo=False,
            entries=[MagicMock()],
            feed=MagicMock(
                title="Test Feed",
                description="A test feed",
                link="https://example.com",
            ),
        )

        adapter = FeedAdapter()
        result = adapter.check_feed("https://example.com/feed")

        assert result["valid"] is True
        assert result["title"] == "Test Feed"
        assert result["entry_count"] == 1
