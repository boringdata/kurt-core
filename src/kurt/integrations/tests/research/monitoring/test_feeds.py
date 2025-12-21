"""Tests for RSS/Atom feed monitoring adapter."""

from datetime import datetime
from time import mktime
from unittest.mock import Mock, patch

import pytest

from kurt.integrations.research.monitoring.feeds import FeedAdapter
from kurt.integrations.research.monitoring.models import Signal


def make_time_tuple(year, month, day, hour, minute, second):
    """Create a proper time tuple for feedparser."""
    return (year, month, day, hour, minute, second, 0, day, 0)


def make_feed_entry(**kwargs):
    """Create a feed entry mock that properly handles hasattr checks.

    By using spec=list(kwargs.keys()), only specified attributes will return True for hasattr().
    """
    entry = Mock(spec=list(kwargs.keys()))
    for key, value in kwargs.items():
        setattr(entry, key, value)
    return entry


class TestFeedAdapter:
    """Test RSS/Atom feed adapter."""

    def test_init(self):
        """Test adapter initialization."""
        adapter = FeedAdapter()
        assert adapter is not None

    @patch("kurt.integrations.research.monitoring.feeds.feedparser")
    def test_get_feed_entries_basic(self, mock_feedparser):
        """Test getting feed entries without filters."""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [
            make_feed_entry(
                title="Test Entry 1",
                link="https://example.com/entry1",
                summary="This is the first entry",
                published_parsed=make_time_tuple(2024, 1, 15, 10, 30, 0),
                author="Author 1",
            ),
            make_feed_entry(
                title="Test Entry 2",
                link="https://example.com/entry2",
                description="This is the second entry",
                updated_parsed=make_time_tuple(2024, 1, 15, 11, 0, 0),
            ),
        ]
        mock_feed.feed = Mock(link="https://example.com")

        mock_feedparser.parse.return_value = mock_feed

        adapter = FeedAdapter()
        signals = adapter.get_feed_entries("https://example.com/feed.xml")

        assert len(signals) == 2
        assert all(isinstance(s, Signal) for s in signals)
        assert signals[0].title == "Test Entry 1"
        assert signals[0].source == "rss"
        assert signals[0].url == "https://example.com/entry1"
        assert signals[0].snippet == "This is the first entry"
        assert signals[0].domain == "example.com"
        assert signals[0].author == "Author 1"

    @patch("kurt.integrations.research.monitoring.feeds.feedparser")
    def test_get_feed_entries_with_keywords(self, mock_feedparser):
        """Test getting entries with keyword filter."""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [
            make_feed_entry(
                title="Python Tutorial",
                link="https://example.com/python",
                summary="Learn Python programming",
                published_parsed=make_time_tuple(2024, 1, 15, 10, 0, 0),
            ),
            make_feed_entry(
                title="JavaScript Guide",
                link="https://example.com/js",
                summary="Learn JavaScript",
                published_parsed=make_time_tuple(2024, 1, 15, 11, 0, 0),
            ),
        ]
        mock_feed.feed = Mock(link="https://example.com")

        mock_feedparser.parse.return_value = mock_feed

        adapter = FeedAdapter()
        signals = adapter.get_feed_entries("https://example.com/feed.xml", keywords=["Python"])

        # Should only match first entry
        assert len(signals) == 1
        assert signals[0].title == "Python Tutorial"
        assert "Python" in signals[0].keywords

    @patch("kurt.integrations.research.monitoring.feeds.feedparser")
    def test_get_feed_entries_with_since_filter(self, mock_feedparser):
        """Test filtering entries by date."""
        cutoff_time = make_time_tuple(2024, 1, 15, 10, 30, 0)
        before_time = make_time_tuple(2024, 1, 15, 9, 0, 0)
        after_time = make_time_tuple(2024, 1, 15, 11, 0, 0)

        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [
            make_feed_entry(
                title="Old Entry", link="https://example.com/old", published_parsed=before_time
            ),
            make_feed_entry(
                title="New Entry", link="https://example.com/new", published_parsed=after_time
            ),
        ]
        mock_feed.feed = Mock(link="https://example.com")

        mock_feedparser.parse.return_value = mock_feed

        adapter = FeedAdapter()
        since_date = datetime.fromtimestamp(mktime(cutoff_time))
        signals = adapter.get_feed_entries("https://example.com/feed.xml", since=since_date)

        # Should only get newer entry
        assert len(signals) == 1
        assert signals[0].title == "New Entry"

    @patch("kurt.integrations.research.monitoring.feeds.feedparser")
    def test_get_feed_entries_with_limit(self, mock_feedparser):
        """Test limit parameter."""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [
            make_feed_entry(
                title=f"Entry {i}",
                link=f"https://example.com/{i}",
                published_parsed=make_time_tuple(2024, 1, 15, 10, min(i, 59), 0),
            )
            for i in range(10)
        ]
        mock_feed.feed = Mock(link="https://example.com")

        mock_feedparser.parse.return_value = mock_feed

        adapter = FeedAdapter()
        signals = adapter.get_feed_entries("https://example.com/feed.xml", limit=5)

        assert len(signals) == 5

    @patch("kurt.integrations.research.monitoring.feeds.feedparser")
    def test_get_feed_entries_handles_updated_parsed(self, mock_feedparser):
        """Test fallback to updated_parsed when published_parsed is missing."""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [
            make_feed_entry(
                title="Entry with updated",
                link="https://example.com/entry",
                # No published_parsed - only updated_parsed
                updated_parsed=make_time_tuple(2024, 1, 15, 10, 0, 0),
            )
        ]
        mock_feed.feed = Mock(link="https://example.com")

        mock_feedparser.parse.return_value = mock_feed

        adapter = FeedAdapter()
        signals = adapter.get_feed_entries("https://example.com/feed.xml")

        assert len(signals) == 1
        assert isinstance(signals[0].timestamp, datetime)

    @patch("kurt.integrations.research.monitoring.feeds.feedparser")
    def test_get_feed_entries_handles_missing_dates(self, mock_feedparser):
        """Test handling entries without date information."""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [
            make_feed_entry(
                title="Dateless Entry",
                link="https://example.com/entry",
                # No date attributes at all
            )
        ]
        mock_feed.feed = Mock(link="https://example.com")

        mock_feedparser.parse.return_value = mock_feed

        adapter = FeedAdapter()
        signals = adapter.get_feed_entries("https://example.com/feed.xml")

        assert len(signals) == 1
        # Should use current time
        assert isinstance(signals[0].timestamp, datetime)

    @patch("kurt.integrations.research.monitoring.feeds.feedparser")
    def test_get_feed_entries_handles_description_fallback(self, mock_feedparser):
        """Test fallback to description when summary is missing."""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [
            Mock(
                title="Entry with description",
                link="https://example.com/entry",
                description="This is the description",
                published_parsed=make_time_tuple(2024, 1, 15, 10, 0, 0),
            )
        ]
        mock_feed.feed = Mock(link="https://example.com")

        # Remove summary attribute
        del mock_feed.entries[0].summary

        mock_feedparser.parse.return_value = mock_feed

        adapter = FeedAdapter()
        signals = adapter.get_feed_entries("https://example.com/feed.xml")

        assert len(signals) == 1
        assert signals[0].snippet == "This is the description"

    @patch("kurt.integrations.research.monitoring.feeds.feedparser")
    def test_get_feed_entries_truncates_long_snippets(self, mock_feedparser):
        """Test that long snippets are truncated."""
        long_text = "a" * 1000

        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [
            Mock(
                title="Entry with long text",
                link="https://example.com/entry",
                summary=long_text,
                published_parsed=make_time_tuple(2024, 1, 15, 10, 0, 0),
            )
        ]
        mock_feed.feed = Mock(link="https://example.com")

        mock_feedparser.parse.return_value = mock_feed

        adapter = FeedAdapter()
        signals = adapter.get_feed_entries("https://example.com/feed.xml")

        assert len(signals) == 1
        assert len(signals[0].snippet) == 500

    @patch("kurt.integrations.research.monitoring.feeds.feedparser")
    def test_get_feed_entries_handles_missing_link(self, mock_feedparser):
        """Test handling entries without link (uses feed URL)."""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [
            make_feed_entry(
                title="Linkless Entry",
                published_parsed=make_time_tuple(2024, 1, 15, 10, 0, 0),
                # No link attribute
            )
        ]
        mock_feed.feed = Mock(link="https://example.com")

        mock_feedparser.parse.return_value = mock_feed

        adapter = FeedAdapter()
        feed_url = "https://example.com/feed.xml"
        signals = adapter.get_feed_entries(feed_url)

        assert len(signals) == 1
        assert signals[0].url == feed_url

    @patch("kurt.integrations.research.monitoring.feeds.feedparser")
    def test_get_feed_entries_extracts_domain(self, mock_feedparser):
        """Test domain extraction from URLs."""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [
            make_feed_entry(
                title="Entry with domain",
                link="https://blog.example.com/2024/01/post",
                published_parsed=make_time_tuple(2024, 1, 15, 10, 0, 0),
            )
        ]
        mock_feed.feed = Mock(link="https://example.com")

        mock_feedparser.parse.return_value = mock_feed

        adapter = FeedAdapter()
        signals = adapter.get_feed_entries("https://example.com/feed.xml")

        assert len(signals) == 1
        assert signals[0].domain == "blog.example.com"

    @patch("kurt.integrations.research.monitoring.feeds.feedparser")
    def test_get_feed_entries_parse_error(self, mock_feedparser):
        """Test handling of feed parse errors."""
        mock_feed = Mock()
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("Invalid XML")

        mock_feedparser.parse.return_value = mock_feed

        adapter = FeedAdapter()
        with pytest.raises(Exception, match="Failed to parse feed"):
            adapter.get_feed_entries("https://example.com/bad-feed.xml")

    @patch("kurt.integrations.research.monitoring.feeds.feedparser")
    def test_get_multi_feed_entries(self, mock_feedparser):
        """Test getting entries from multiple feeds."""
        mock_feed1 = Mock()
        mock_feed1.bozo = False
        mock_feed1.entries = [
            make_feed_entry(
                title="Feed 1 Entry",
                link="https://feed1.com/entry",
                published_parsed=make_time_tuple(2024, 1, 15, 11, 0, 0),
            )
        ]
        mock_feed1.feed = Mock(link="https://feed1.com")

        mock_feed2 = Mock()
        mock_feed2.bozo = False
        mock_feed2.entries = [
            make_feed_entry(
                title="Feed 2 Entry",
                link="https://feed2.com/entry",
                published_parsed=make_time_tuple(2024, 1, 15, 10, 0, 0),
            )
        ]
        mock_feed2.feed = Mock(link="https://feed2.com")

        mock_feedparser.parse.side_effect = [mock_feed1, mock_feed2]

        adapter = FeedAdapter()
        signals = adapter.get_multi_feed_entries(
            ["https://feed1.com/feed.xml", "https://feed2.com/feed.xml"]
        )

        assert len(signals) == 2
        # Should be sorted by timestamp (newest first)
        assert signals[0].title == "Feed 1 Entry"
        assert signals[1].title == "Feed 2 Entry"

    @patch("kurt.integrations.research.monitoring.feeds.feedparser")
    def test_get_multi_feed_entries_handles_errors(self, mock_feedparser):
        """Test that errors in one feed don't stop others."""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [
            make_feed_entry(
                title="Working Feed Entry",
                link="https://working.com/entry",
                published_parsed=make_time_tuple(2024, 1, 15, 10, 0, 0),
            )
        ]
        mock_feed.feed = Mock(link="https://working.com")

        # First fails, second succeeds
        mock_feedparser.parse.side_effect = [
            Mock(bozo=True, bozo_exception=Exception("Parse error")),
            mock_feed,
        ]

        adapter = FeedAdapter()
        signals = adapter.get_multi_feed_entries(
            ["https://failing.com/feed.xml", "https://working.com/feed.xml"]
        )

        # Should still get results from working feed
        assert len(signals) == 1
        assert signals[0].title == "Working Feed Entry"

    @patch("kurt.integrations.research.monitoring.feeds.feedparser")
    def test_check_feed_valid(self, mock_feedparser):
        """Test checking a valid feed."""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = Mock(
            title="Example Blog",
            description="A test blog",
            link="https://example.com",
            updated="2024-01-15T10:30:00Z",
        )
        mock_feed.entries = [Mock(), Mock(), Mock()]

        mock_feedparser.parse.return_value = mock_feed

        adapter = FeedAdapter()
        result = adapter.check_feed("https://example.com/feed.xml")

        assert result["valid"] is True
        assert result["title"] == "Example Blog"
        assert result["description"] == "A test blog"
        assert result["link"] == "https://example.com"
        assert result["entry_count"] == 3
        assert result["last_updated"] == "2024-01-15T10:30:00Z"

    @patch("kurt.integrations.research.monitoring.feeds.feedparser")
    def test_check_feed_invalid(self, mock_feedparser):
        """Test checking an invalid feed."""
        mock_feed = Mock()
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("Invalid XML")

        mock_feedparser.parse.return_value = mock_feed

        adapter = FeedAdapter()
        result = adapter.check_feed("https://example.com/bad-feed.xml")

        assert result["valid"] is False
        assert "error" in result
        assert "Invalid XML" in result["error"]

    @patch("kurt.integrations.research.monitoring.feeds.feedparser")
    def test_check_feed_handles_missing_metadata(self, mock_feedparser):
        """Test check_feed with minimal feed metadata."""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = Mock()
        mock_feed.entries = []

        # Remove optional attributes
        del mock_feed.feed.title
        del mock_feed.feed.description
        del mock_feed.feed.link
        del mock_feed.feed.updated

        mock_feedparser.parse.return_value = mock_feed

        adapter = FeedAdapter()
        result = adapter.check_feed("https://example.com/minimal-feed.xml")

        assert result["valid"] is True
        assert result["title"] is None
        assert result["description"] is None
        assert result["link"] is None
        assert result["entry_count"] == 0
        assert result["last_updated"] is None

    @patch("kurt.integrations.research.monitoring.feeds.feedparser")
    def test_get_feed_entries_keyword_in_snippet(self, mock_feedparser):
        """Test keyword matching in snippet."""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [
            Mock(
                title="Generic Title",
                link="https://example.com/entry",
                summary="This post discusses Kubernetes deployment strategies in detail",
                published_parsed=make_time_tuple(2024, 1, 15, 10, 0, 0),
            )
        ]
        mock_feed.feed = Mock(link="https://example.com")

        mock_feedparser.parse.return_value = mock_feed

        adapter = FeedAdapter()
        signals = adapter.get_feed_entries("https://example.com/feed.xml", keywords=["Kubernetes"])

        assert len(signals) == 1
        assert "Kubernetes" in signals[0].keywords
