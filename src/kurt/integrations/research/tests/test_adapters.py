"""Tests for research adapters."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from kurt.integrations.research.base import Citation, ResearchResult
from kurt.integrations.research.monitoring.apify import ApifyAdapter
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


class TestApifyAdapter:
    """Tests for Apify adapter."""

    def test_init(self):
        """Test adapter initialization."""
        config = {"api_token": "test_token"}
        adapter = ApifyAdapter(config)

        assert adapter.api_token == "test_token"
        assert adapter.default_actor == "apidojo/tweet-scraper"

    def test_init_with_custom_actor(self):
        """Test adapter initialization with custom default actor."""
        config = {
            "api_token": "test_token",
            "default_actor": "custom/actor",
        }
        adapter = ApifyAdapter(config)

        assert adapter.default_actor == "custom/actor"

    @patch("httpx.get")
    def test_test_connection_success(self, mock_get):
        """Test successful connection test."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        adapter = ApifyAdapter({"api_token": "test_token"})
        result = adapter.test_connection()

        assert result is True
        mock_get.assert_called_once()

    @patch("httpx.get")
    def test_test_connection_failure(self, mock_get):
        """Test failed connection test."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        adapter = ApifyAdapter({"api_token": "bad_token"})
        result = adapter.test_connection()

        assert result is False

    @patch("httpx.post")
    def test_fetch_signals_twitter(self, mock_post):
        """Test fetching Twitter signals."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": "123456",
                "text": "This is a test tweet about AI",
                "url": "https://twitter.com/user/status/123456",
                "createdAt": "2024-01-15T12:00:00Z",
                "author": {"username": "testuser"},
                "likeCount": 100,
                "replyCount": 25,
            },
            {
                "id": "789012",
                "text": "Another tweet about machine learning",
                "url": "https://twitter.com/user/status/789012",
                "createdAt": "2024-01-15T11:00:00Z",
                "author": {"username": "anotheruser"},
                "likeCount": 50,
                "replyCount": 10,
            },
        ]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        adapter = ApifyAdapter({"api_token": "test_token"})
        signals = adapter.fetch_signals("AI", max_items=10)

        assert len(signals) == 2
        assert signals[0].signal_id == "twitter_123456"
        assert signals[0].source == "twitter"
        assert "test tweet" in signals[0].title
        assert signals[0].score == 100
        assert signals[0].comment_count == 25
        assert signals[0].author == "testuser"

    @patch("httpx.post")
    def test_fetch_signals_linkedin(self, mock_post):
        """Test fetching LinkedIn signals."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "postId": "urn:li:share:abc123",
                "postContent": "Great insights on B2B marketing",
                "postUrl": "https://linkedin.com/posts/abc123",
                "reactions": 200,
                "numComments": 45,
                "authorName": "Marketing Pro",
            }
        ]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        adapter = ApifyAdapter({"api_token": "test_token"})
        signals = adapter.search_linkedin("B2B marketing", max_items=10)

        assert len(signals) == 1
        assert signals[0].source == "linkedin"
        assert "B2B marketing" in signals[0].title
        assert signals[0].score == 200
        assert signals[0].comment_count == 45

    @patch("httpx.post")
    def test_fetch_signals_with_keyword_filter(self, mock_post):
        """Test keyword filtering on fetched signals."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": "1",
                "text": "Tweet about Python programming",
                "url": "https://twitter.com/1",
                "likeCount": 100,
            },
            {
                "id": "2",
                "text": "Tweet about JavaScript",
                "url": "https://twitter.com/2",
                "likeCount": 50,
            },
        ]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        adapter = ApifyAdapter({"api_token": "test_token"})
        signals = adapter.fetch_signals("programming", keywords=["Python"])

        assert len(signals) == 1
        assert "Python" in signals[0].title

    @patch("httpx.post")
    def test_fetch_signals_sorted_by_relevance(self, mock_post):
        """Test that signals are sorted by relevance score."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": "low",
                "text": "Low engagement post",
                "url": "https://twitter.com/low",
                "likeCount": 5,
                "replyCount": 1,
            },
            {
                "id": "high",
                "text": "High engagement post",
                "url": "https://twitter.com/high",
                "likeCount": 500,
                "replyCount": 100,
            },
        ]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        adapter = ApifyAdapter({"api_token": "test_token"})
        signals = adapter.fetch_signals("test")

        # High engagement should be first
        assert signals[0].signal_id == "twitter_high"
        assert signals[0].relevance_score > signals[1].relevance_score

    def test_actor_to_source_mapping(self):
        """Test actor ID to source name mapping."""
        adapter = ApifyAdapter({"api_token": "test"})

        assert adapter._actor_to_source("apidojo/tweet-scraper") == "twitter"
        assert adapter._actor_to_source("some/twitter-actor") == "twitter"
        assert adapter._actor_to_source("curious_coder/linkedin-post-search-scraper") == "linkedin"
        assert adapter._actor_to_source("apidojo/threads-scraper") == "threads"
        assert adapter._actor_to_source("some/unknown-actor") == "apify"

    def test_parse_date_valid(self):
        """Test parsing valid ISO date."""
        adapter = ApifyAdapter({"api_token": "test"})

        result = adapter._parse_date("2024-01-15T12:00:00Z")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_date_invalid(self):
        """Test parsing invalid date returns now."""
        adapter = ApifyAdapter({"api_token": "test"})

        result = adapter._parse_date("invalid-date")
        assert result is not None
        # Should be close to now
        assert (datetime.now() - result).seconds < 10

    def test_parse_date_none(self):
        """Test parsing None date returns now."""
        adapter = ApifyAdapter({"api_token": "test"})

        result = adapter._parse_date(None)
        assert result is not None

    @patch("httpx.post")
    def test_run_actor_raw_input(self, mock_post):
        """Test run_actor with raw input dict."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"data": "raw"}]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        adapter = ApifyAdapter({"api_token": "test_token"})
        result = adapter.run_actor(
            "custom/actor", {"customField": "customValue", "anotherField": 123}
        )

        assert result == [{"data": "raw"}]
        # Verify the raw input was passed through
        call_args = mock_post.call_args
        assert call_args[1]["json"] == {"customField": "customValue", "anotherField": 123}

    @patch("httpx.post")
    def test_fetch_signals_with_raw_actor_input(self, mock_post):
        """Test fetch_signals with actor_input parameter bypasses input building."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": "1", "text": "Test", "url": "https://example.com", "likeCount": 10}
        ]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        adapter = ApifyAdapter({"api_token": "test_token"})
        signals = adapter.fetch_signals(
            query="ignored",  # Should be ignored when actor_input provided
            actor="custom/actor",
            actor_input={"myCustomInput": "value", "limit": 5},
        )

        # Verify raw input was used
        call_args = mock_post.call_args
        assert call_args[1]["json"] == {"myCustomInput": "value", "limit": 5}
        assert len(signals) == 1

    def test_custom_field_mapping(self):
        """Test parsing with custom field mapping."""
        from kurt.integrations.research.monitoring.apify import FieldMapping

        adapter = ApifyAdapter({"api_token": "test"})

        # Custom mapping for an actor with different field names
        custom_mapping = FieldMapping(
            text="body",
            url="permalink",
            id="postId",
            score="upvotes",
            comments="replies",
            author="poster",
            timestamp="created",
        )

        items = [
            {
                "postId": "abc123",
                "body": "Custom format post",
                "permalink": "https://custom.com/abc123",
                "upvotes": 50,
                "replies": 10,
                "poster": "customuser",
                "created": "2024-01-15T12:00:00Z",
            }
        ]

        signals = adapter.parse_results(items, "custom", "query", custom_mapping)

        assert len(signals) == 1
        assert signals[0].signal_id == "custom_abc123"
        assert signals[0].title == "Custom format post"
        assert signals[0].score == 50
        assert signals[0].comment_count == 10
        assert signals[0].author == "customuser"

    def test_callable_field_mapping(self):
        """Test field mapping with callable extractors."""
        from kurt.integrations.research.monitoring.apify import FieldMapping

        adapter = ApifyAdapter({"api_token": "test"})

        # Custom mapping with callable for complex extraction
        custom_mapping = FieldMapping(
            text=lambda item: f"{item.get('headline', '')} - {item.get('summary', '')}",
            url="link",
            id="uuid",
            score=lambda item: item.get("stats", {}).get("likes", 0),
            comments=lambda item: item.get("stats", {}).get("comments", 0),
            author=lambda item: item.get("creator", {}).get("handle"),
            timestamp="publishedAt",
        )

        items = [
            {
                "uuid": "xyz789",
                "headline": "Breaking News",
                "summary": "Important update",
                "link": "https://news.com/xyz789",
                "stats": {"likes": 100, "comments": 25},
                "creator": {"handle": "newsbot", "name": "News Bot"},
                "publishedAt": "2024-01-15T12:00:00Z",
            }
        ]

        signals = adapter.parse_results(items, "news", "query", custom_mapping)

        assert len(signals) == 1
        assert "Breaking News - Important update" in signals[0].title
        assert signals[0].score == 100
        assert signals[0].comment_count == 25
        assert signals[0].author == "newsbot"

    def test_register_custom_actor(self):
        """Test registering a custom actor configuration."""
        from kurt.integrations.research.monitoring.apify import ActorConfig, FieldMapping

        adapter = ApifyAdapter({"api_token": "test"})

        # Register custom actor
        custom_config = ActorConfig(
            actor_id="my/custom-scraper",
            source_name="custom_platform",
            build_input=lambda q, n, kw: {"query": q, "count": n},
            field_mapping=FieldMapping(text="message", url="href"),
            description="My custom scraper",
        )
        adapter.register_actor(custom_config)

        # Verify it's registered
        assert "my/custom-scraper" in adapter.actor_registry
        assert adapter.actor_registry["my/custom-scraper"].source_name == "custom_platform"

    def test_list_actors(self):
        """Test listing registered actors."""
        adapter = ApifyAdapter({"api_token": "test"})

        actors = adapter.list_actors()

        # Should have the built-in actors
        actor_ids = [a["actor_id"] for a in actors]
        assert "apidojo/tweet-scraper" in actor_ids
        assert "curious_coder/linkedin-post-search-scraper" in actor_ids

        # Each should have required fields
        for actor in actors:
            assert "actor_id" in actor
            assert "source_name" in actor
            assert "description" in actor

    def test_set_field_mapping_for_actor(self):
        """Test setting custom field mapping for specific actor."""
        from kurt.integrations.research.monitoring.apify import FieldMapping

        adapter = ApifyAdapter({"api_token": "test"})

        custom_mapping = FieldMapping(text="custom_text_field")
        adapter.set_field_mapping("some/actor", custom_mapping)

        assert "some/actor" in adapter._custom_mappings
        assert adapter._custom_mappings["some/actor"].text == "custom_text_field"

    def test_nested_field_extraction(self):
        """Test extracting nested fields with dot notation."""
        adapter = ApifyAdapter({"api_token": "test"})

        item = {"user": {"profile": {"name": "Test User"}}}

        result = adapter._get_nested(item, "user.profile.name")
        assert result == "Test User"

        # Non-existent path
        result = adapter._get_nested(item, "user.nonexistent.field")
        assert result is None

    @patch("httpx.post")
    def test_scrape_profile_twitter(self, mock_post):
        """Test scraping Twitter profile."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": "1", "text": "Profile tweet", "url": "https://twitter.com/1", "likeCount": 50}
        ]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        adapter = ApifyAdapter({"api_token": "test_token"})
        signals = adapter.scrape_profile("@elonmusk", platform="twitter", max_items=10)

        assert len(signals) == 1
        # Verify the correct actor was used
        call_args = mock_post.call_args
        assert "twitter-user-scraper" in call_args[0][0]

    def test_scrape_profile_unsupported_platform(self):
        """Test scraping profile for unsupported platform raises error."""
        adapter = ApifyAdapter({"api_token": "test"})

        with pytest.raises(ValueError, match="No profile scraper available"):
            adapter.scrape_profile("@user", platform="tiktok")

    @patch("httpx.post")
    def test_convenience_methods_accept_actor_override(self, mock_post):
        """Test that convenience methods accept actor parameter."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": "1", "text": "Test", "url": "https://twitter.com/1", "likeCount": 10}
        ]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        adapter = ApifyAdapter({"api_token": "test_token"})

        # Use alternative Twitter actor
        adapter.search_twitter("query", actor="quacker/twitter-scraper")

        call_args = mock_post.call_args
        assert "quacker/twitter-scraper" in call_args[0][0]

    def test_init_with_custom_registry(self):
        """Test initializing adapter with custom actor registry."""
        from kurt.integrations.research.monitoring.apify import ActorConfig

        custom_registry = {
            "my/actor": ActorConfig(
                actor_id="my/actor", source_name="my_source", description="My custom actor"
            )
        }

        adapter = ApifyAdapter({"api_token": "test"}, actor_registry=custom_registry)

        # Should have both built-in and custom actors
        assert "apidojo/tweet-scraper" in adapter.actor_registry  # Built-in
        assert "my/actor" in adapter.actor_registry  # Custom
