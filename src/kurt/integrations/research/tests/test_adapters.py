"""Tests for research adapters."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from kurt.integrations.research.base import Citation, ResearchResult
from kurt.integrations.research.monitoring.apify import ApifyAdapter, FieldMapping
from kurt.integrations.research.monitoring.hackernews import HackerNewsAdapter
from kurt.integrations.research.monitoring.models import Signal
from kurt.integrations.research.monitoring.reddit import RedditAdapter

# Check if feedparser is available (optional dependency)
try:
    import feedparser  # noqa: F401

    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

# Import FeedAdapter only if feedparser is available
if HAS_FEEDPARSER:
    from kurt.integrations.research.monitoring.feeds import FeedAdapter


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


@pytest.mark.skipif(not HAS_FEEDPARSER, reason="feedparser not installed")
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


class TestApifyAdapter:
    """Tests for Apify adapter."""

    def test_init_with_api_token(self):
        """Test adapter initialization with api_token."""
        adapter = ApifyAdapter({"api_token": "test_token"})
        assert adapter.api_token == "test_token"

    def test_init_with_api_key(self):
        """Test adapter initialization with api_key (alias)."""
        adapter = ApifyAdapter({"api_key": "test_key"})
        assert adapter.api_token == "test_key"

    def test_init_raises_without_token(self):
        """Test adapter raises error without token."""
        with pytest.raises(ValueError, match="api_token is required"):
            ApifyAdapter({})

    def test_list_actors(self):
        """Test listing registered actors."""
        adapter = ApifyAdapter({"api_token": "test"})
        actors = adapter.list_actors()

        assert len(actors) > 0
        # Check structure
        for actor in actors:
            assert "actor_id" in actor
            assert "source_name" in actor
            assert "description" in actor

        # Check known actors exist
        actor_ids = [a["actor_id"] for a in actors]
        assert "apidojo/tweet-scraper" in actor_ids
        assert "curious_coder/linkedin-post-search-scraper" in actor_ids

    def test_guess_source_twitter(self):
        """Test source guessing for Twitter."""
        adapter = ApifyAdapter({"api_token": "test"})
        assert adapter._guess_source("apidojo/tweet-scraper") == "twitter"
        assert adapter._guess_source("some/twitter-thing") == "twitter"

    def test_guess_source_linkedin(self):
        """Test source guessing for LinkedIn."""
        adapter = ApifyAdapter({"api_token": "test"})
        assert adapter._guess_source("linkedin-scraper") == "linkedin"

    def test_guess_source_threads(self):
        """Test source guessing for Threads."""
        adapter = ApifyAdapter({"api_token": "test"})
        assert adapter._guess_source("threads-posts") == "threads"

    def test_guess_source_unknown(self):
        """Test source guessing for unknown actors."""
        adapter = ApifyAdapter({"api_token": "test"})
        assert adapter._guess_source("some/random-actor") == "apify"

    def test_extract_field_string(self):
        """Test field extraction with string spec."""
        adapter = ApifyAdapter({"api_token": "test"})
        item = {"title": "Test Title"}
        result = adapter._extract_field(item, "title")
        assert result == "Test Title"

    def test_extract_field_list(self):
        """Test field extraction with list spec (fallback)."""
        adapter = ApifyAdapter({"api_token": "test"})

        # First field exists
        item = {"text": "Found text"}
        result = adapter._extract_field(item, ["text", "content", "title"])
        assert result == "Found text"

        # Fallback to second field
        item = {"content": "Fallback content"}
        result = adapter._extract_field(item, ["text", "content", "title"])
        assert result == "Fallback content"

    def test_extract_field_callable(self):
        """Test field extraction with callable spec."""
        adapter = ApifyAdapter({"api_token": "test"})
        item = {"first": "Hello", "last": "World"}
        result = adapter._extract_field(item, lambda x: f"{x['first']} {x['last']}")
        assert result == "Hello World"

    def test_extract_field_nested(self):
        """Test nested field extraction."""
        adapter = ApifyAdapter({"api_token": "test"})
        item = {"author": {"username": "testuser", "name": "Test User"}}
        result = adapter._extract_field(item, "author.username")
        assert result == "testuser"

    def test_parse_results(self):
        """Test parsing raw results into signals."""
        adapter = ApifyAdapter({"api_token": "test"})
        items = [
            {
                "id": "post123",
                "text": "This is a test post about AI",
                "url": "https://twitter.com/post123",
                "likeCount": 100,
                "replyCount": 25,
                "author": "testuser",
                "createdAt": "2024-01-15T10:00:00Z",
            }
        ]

        signals = adapter.parse_results(items, source="twitter", query="AI")

        assert len(signals) == 1
        signal = signals[0]
        assert signal.signal_id == "twitter_post123"
        assert signal.source == "twitter"
        assert "test post" in signal.title.lower()
        assert signal.url == "https://twitter.com/post123"
        assert signal.score == 100
        assert signal.comment_count == 25
        assert signal.author == "testuser"
        assert "AI" in signal.keywords

    def test_parse_results_with_custom_mapping(self):
        """Test parsing with custom field mapping."""
        adapter = ApifyAdapter({"api_token": "test"})
        items = [
            {
                "postId": "custom123",
                "postContent": "Custom content",
                "postUrl": "https://custom.com/123",
                "reactions": 50,
            }
        ]

        mapping = FieldMapping(
            id="postId",
            text="postContent",
            url="postUrl",
            score="reactions",
        )

        signals = adapter.parse_results(items, source="custom", field_mapping=mapping)

        assert len(signals) == 1
        signal = signals[0]
        assert signal.signal_id == "custom_custom123"
        assert "Custom content" in signal.title
        assert signal.score == 50

    @patch("httpx.get")
    def test_test_connection_success(self, mock_get):
        """Test successful connection test."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        adapter = ApifyAdapter({"api_token": "valid_token"})
        result = adapter.test_connection()

        assert result is True
        mock_get.assert_called_once()

    @patch("httpx.get")
    def test_test_connection_failure(self, mock_get):
        """Test failed connection test."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        adapter = ApifyAdapter({"api_token": "invalid_token"})
        result = adapter.test_connection()

        assert result is False

    @patch("httpx.post")
    def test_run_actor(self, mock_post):
        """Test running an actor."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": "1", "text": "Result 1"},
            {"id": "2", "text": "Result 2"},
        ]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        adapter = ApifyAdapter({"api_token": "test"})
        results = adapter.run_actor(
            "apidojo/tweet-scraper", {"searchTerms": ["test"], "maxItems": 10}
        )

        assert len(results) == 2
        mock_post.assert_called_once()

    @patch("httpx.post")
    def test_fetch_signals(self, mock_post):
        """Test fetching signals with actor."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": "tweet1",
                "text": "AI is changing the world",
                "url": "https://twitter.com/tweet1",
                "likeCount": 50,
                "replyCount": 10,
                "createdAt": "2024-01-15T10:00:00Z",
            }
        ]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        adapter = ApifyAdapter({"api_token": "test"})
        signals = adapter.fetch_signals(
            query="AI", actor="apidojo/tweet-scraper", max_items=10
        )

        assert len(signals) == 1
        assert signals[0].source == "twitter"

    @patch("httpx.post")
    def test_search_twitter(self, mock_post):
        """Test Twitter search convenience method."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": "1",
                "text": "Test tweet",
                "url": "https://twitter.com/1",
                "createdAt": "2024-01-15T10:00:00Z",
            }
        ]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        adapter = ApifyAdapter({"api_token": "test"})
        signals = adapter.search_twitter("test query")

        assert len(signals) == 1
        assert signals[0].source == "twitter"

    @patch("httpx.post")
    def test_search_linkedin(self, mock_post):
        """Test LinkedIn search convenience method."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": "post1",
                "postContent": "LinkedIn post",
                "postUrl": "https://linkedin.com/post1",
                "createdAt": "2024-01-15T10:00:00Z",
            }
        ]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        adapter = ApifyAdapter({"api_token": "test"})
        signals = adapter.search_linkedin("B2B marketing")

        assert len(signals) == 1
        assert signals[0].source == "linkedin"

    def test_keyword_filtering(self):
        """Test keyword filtering in fetch_signals."""
        adapter = ApifyAdapter({"api_token": "test"})

        # Test signal that matches keywords
        signal_match = Signal(
            signal_id="test_1",
            source="twitter",
            title="AI and machine learning",
            url="https://example.com",
        )
        assert signal_match.matches_keywords(["AI"]) is True
        assert signal_match.matches_keywords(["python"]) is False

    def test_custom_actor_registration(self):
        """Test registering custom actors."""
        from kurt.integrations.research.monitoring.apify import ActorConfig

        adapter = ApifyAdapter({"api_token": "test"})

        # Register custom actor
        custom_actor = ActorConfig(
            actor_id="my/custom-actor",
            source_name="custom_source",
            description="My custom actor",
        )
        adapter.register_actor(custom_actor)

        # Verify it's registered
        actors = adapter.list_actors()
        actor_ids = [a["actor_id"] for a in actors]
        assert "my/custom-actor" in actor_ids
