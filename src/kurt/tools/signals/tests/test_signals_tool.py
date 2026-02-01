"""
Unit tests for SignalsTool.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from kurt.tools.core import TOOLS, SubstepEvent, ToolContext, ToolResult, clear_registry, get_tool
from kurt.tools.signals import SignalInput, SignalOutput, SignalsTool

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset tool registry before and after each test."""
    saved_tools = dict(TOOLS)
    clear_registry()

    # Re-register SignalsTool for tests
    TOOLS["signals"] = SignalsTool

    yield

    clear_registry()
    TOOLS.update(saved_tools)


@pytest.fixture
def tool_context():
    """Create a basic tool context."""
    return ToolContext(settings={})


@pytest.fixture
def mock_signal():
    """Create a mock Signal object."""
    signal = MagicMock()
    signal.signal_id = "reddit_abc123"
    signal.source = "reddit"
    signal.title = "Test Signal Title"
    signal.url = "https://reddit.com/r/test/comments/abc123"
    signal.snippet = "This is a test signal"
    signal.author = "test_user"
    signal.score = 42
    signal.comment_count = 10
    signal.subreddit = "test"
    signal.domain = None
    signal.keywords = ["test", "signal"]
    signal.timestamp = datetime(2024, 1, 15, 12, 0, 0)
    signal.to_dict.return_value = {
        "signal_id": "reddit_abc123",
        "source": "reddit",
        "title": "Test Signal Title",
        "url": "https://reddit.com/r/test/comments/abc123",
        "snippet": "This is a test signal",
        "author": "test_user",
        "score": 42,
        "comment_count": 10,
        "subreddit": "test",
        "domain": None,
        "keywords": ["test", "signal"],
        "timestamp": datetime(2024, 1, 15, 12, 0, 0),
    }
    return signal


# ============================================================================
# SignalInput Tests
# ============================================================================


class TestSignalInput:
    """Test SignalInput model validation."""

    def test_valid_reddit_source(self):
        """Valid Reddit source input."""
        inp = SignalInput(source="reddit", subreddit="python")
        assert inp.source == "reddit"
        assert inp.subreddit == "python"

    def test_valid_hackernews_source(self):
        """Valid HackerNews source input."""
        inp = SignalInput(source="hackernews")
        assert inp.source == "hackernews"

    def test_valid_feeds_source(self):
        """Valid feeds source input."""
        inp = SignalInput(source="feeds", feed_url="https://example.com/feed.xml")
        assert inp.source == "feeds"
        assert inp.feed_url == "https://example.com/feed.xml"

    def test_source_required(self):
        """Source is required."""
        with pytest.raises(ValidationError):
            SignalInput()

    def test_invalid_source(self):
        """Invalid source raises validation error."""
        with pytest.raises(ValidationError):
            SignalInput(source="invalid")

    def test_default_values(self):
        """Default values are set correctly."""
        inp = SignalInput(source="hackernews")
        assert inp.timeframe == "day"
        assert inp.min_score == 0
        assert inp.limit == 25
        assert inp.sort == "hot"
        assert inp.dry_run is False

    def test_limit_bounds(self):
        """Limit must be between 1 and 100."""
        with pytest.raises(ValidationError):
            SignalInput(source="hackernews", limit=0)
        with pytest.raises(ValidationError):
            SignalInput(source="hackernews", limit=101)

        SignalInput(source="hackernews", limit=1)
        SignalInput(source="hackernews", limit=100)

    def test_min_score_non_negative(self):
        """min_score must be non-negative."""
        with pytest.raises(ValidationError):
            SignalInput(source="hackernews", min_score=-1)

        SignalInput(source="hackernews", min_score=0)
        SignalInput(source="hackernews", min_score=100)

    def test_keywords_parsing(self):
        """Keywords can be comma-separated string."""
        inp = SignalInput(source="hackernews", keywords="python, rust, go")
        assert inp.keywords == "python, rust, go"

    def test_timeframe_options(self):
        """Valid timeframe options."""
        for tf in ["hour", "day", "week", "month"]:
            inp = SignalInput(source="hackernews", timeframe=tf)
            assert inp.timeframe == tf

    def test_invalid_timeframe(self):
        """Invalid timeframe raises validation error."""
        with pytest.raises(ValidationError):
            SignalInput(source="hackernews", timeframe="year")

    def test_sort_options(self):
        """Valid sort options for Reddit."""
        for sort in ["hot", "new", "top", "rising"]:
            inp = SignalInput(source="reddit", subreddit="python", sort=sort)
            assert inp.sort == sort


# ============================================================================
# SignalOutput Tests
# ============================================================================


class TestSignalOutput:
    """Test SignalOutput model."""

    def test_successful_output(self):
        """Valid signal output."""
        out = SignalOutput(
            signal_id="reddit_abc123",
            source="reddit",
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
            author="test_user",
            score=42,
            comment_count=10,
            subreddit="test",
            keywords=["test"],
            timestamp="2024-01-15T12:00:00",
        )
        assert out.signal_id == "reddit_abc123"
        assert out.source == "reddit"
        assert out.score == 42

    def test_minimal_output(self):
        """Minimal required fields."""
        out = SignalOutput(
            signal_id="hn_123",
            source="hackernews",
            title="Test",
            url="https://example.com",
        )
        assert out.signal_id == "hn_123"
        assert out.snippet is None
        assert out.author is None
        assert out.score == 0
        assert out.comment_count == 0
        assert out.keywords == []


# ============================================================================
# Helper Functions Tests
# ============================================================================


class TestHelperFunctions:
    """Test helper functions."""

    def test_parse_keywords_empty(self):
        """Empty keywords returns empty list."""
        from kurt.tools.signals import _parse_keywords

        assert _parse_keywords(None) == []
        assert _parse_keywords("") == []

    def test_parse_keywords_single(self):
        """Single keyword."""
        from kurt.tools.signals import _parse_keywords

        assert _parse_keywords("python") == ["python"]

    def test_parse_keywords_multiple(self):
        """Multiple keywords."""
        from kurt.tools.signals import _parse_keywords

        result = _parse_keywords("python, rust, go")
        assert result == ["python", "rust", "go"]

    def test_parse_keywords_whitespace(self):
        """Whitespace is trimmed."""
        from kurt.tools.signals import _parse_keywords

        result = _parse_keywords("  python  ,  rust  ")
        assert result == ["python", "rust"]

    def test_parse_subreddits_empty(self):
        """Empty subreddit returns empty list."""
        from kurt.tools.signals import _parse_subreddits

        assert _parse_subreddits(None) == []
        assert _parse_subreddits("") == []

    def test_parse_subreddits_single(self):
        """Single subreddit."""
        from kurt.tools.signals import _parse_subreddits

        assert _parse_subreddits("python") == ["python"]

    def test_parse_subreddits_comma_separated(self):
        """Comma-separated subreddits."""
        from kurt.tools.signals import _parse_subreddits

        result = _parse_subreddits("python, rust, golang")
        assert result == ["python", "rust", "golang"]

    def test_parse_subreddits_plus_separated(self):
        """Plus-separated subreddits (Reddit style)."""
        from kurt.tools.signals import _parse_subreddits

        result = _parse_subreddits("python+rust+golang")
        assert result == ["python", "rust", "golang"]


# ============================================================================
# SignalsTool Registration Tests
# ============================================================================


class TestSignalsToolRegistration:
    """Test SignalsTool registration."""

    def test_tool_registered(self):
        """SignalsTool is registered in TOOLS."""
        assert "signals" in TOOLS

    def test_get_tool(self):
        """get_tool returns SignalsTool."""
        tool_class = get_tool("signals")
        assert tool_class is SignalsTool

    def test_tool_attributes(self):
        """SignalsTool has correct attributes."""
        assert SignalsTool.name == "signals"
        assert SignalsTool.description == "Fetch signals from Reddit, HackerNews, or RSS feeds"
        assert SignalsTool.InputModel is SignalInput
        assert SignalsTool.OutputModel is SignalOutput


# ============================================================================
# SignalsTool Execution Tests - Reddit
# ============================================================================


class TestSignalsToolReddit:
    """Test SignalsTool execution for Reddit source."""

    @pytest.mark.asyncio
    async def test_reddit_missing_subreddit(self, tool_context):
        """Reddit source without subreddit returns error."""
        tool = SignalsTool()
        params = SignalInput(source="reddit")

        result = await tool.run(params, tool_context)

        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "missing_subreddit"

    @pytest.mark.asyncio
    async def test_reddit_single_subreddit(self, tool_context, mock_signal):
        """Reddit source with single subreddit."""
        tool = SignalsTool()
        params = SignalInput(source="reddit", subreddit="python", limit=10)

        with patch(
            "kurt.integrations.research.monitoring.RedditAdapter"
        ) as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter.get_subreddit_posts.return_value = [mock_signal]
            mock_adapter_class.return_value = mock_adapter

            result = await tool.run(params, tool_context)

        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["signal_id"] == "reddit_abc123"
        assert result.data[0]["source"] == "reddit"
        mock_adapter.get_subreddit_posts.assert_called_once_with(
            subreddit="python",
            timeframe="day",
            sort="hot",
            limit=10,
            keywords=None,
            min_score=0,
        )

    @pytest.mark.asyncio
    async def test_reddit_multiple_subreddits(self, tool_context, mock_signal):
        """Reddit source with multiple subreddits."""
        tool = SignalsTool()
        params = SignalInput(source="reddit", subreddit="python+rust", limit=10)

        with patch(
            "kurt.integrations.research.monitoring.RedditAdapter"
        ) as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter.get_multi_subreddit_posts.return_value = [mock_signal]
            mock_adapter_class.return_value = mock_adapter

            result = await tool.run(params, tool_context)

        assert result.success is True
        mock_adapter.get_multi_subreddit_posts.assert_called_once_with(
            subreddits=["python", "rust"],
            timeframe="day",
            sort="hot",
            limit=10,
            keywords=None,
            min_score=0,
        )

    @pytest.mark.asyncio
    async def test_reddit_with_keywords(self, tool_context, mock_signal):
        """Reddit source with keyword filtering."""
        tool = SignalsTool()
        params = SignalInput(
            source="reddit",
            subreddit="python",
            keywords="django, flask",
            limit=10,
        )

        with patch(
            "kurt.integrations.research.monitoring.RedditAdapter"
        ) as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter.get_subreddit_posts.return_value = [mock_signal]
            mock_adapter_class.return_value = mock_adapter

            result = await tool.run(params, tool_context)

        assert result.success is True
        mock_adapter.get_subreddit_posts.assert_called_once_with(
            subreddit="python",
            timeframe="day",
            sort="hot",
            limit=10,
            keywords=["django", "flask"],
            min_score=0,
        )


# ============================================================================
# SignalsTool Execution Tests - HackerNews
# ============================================================================


class TestSignalsToolHackerNews:
    """Test SignalsTool execution for HackerNews source."""

    @pytest.mark.asyncio
    async def test_hackernews_basic(self, tool_context, mock_signal):
        """HackerNews source basic fetch."""
        tool = SignalsTool()
        params = SignalInput(source="hackernews", limit=10)

        mock_signal.source = "hackernews"
        mock_signal.to_dict.return_value["source"] = "hackernews"

        with patch(
            "kurt.integrations.research.monitoring.HackerNewsAdapter"
        ) as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter.get_recent.return_value = [mock_signal]
            mock_adapter_class.return_value = mock_adapter

            result = await tool.run(params, tool_context)

        assert result.success is True
        assert len(result.data) == 1
        mock_adapter.get_recent.assert_called_once_with(
            hours=24,  # day = 24 hours
            keywords=None,
            min_score=0,
        )

    @pytest.mark.asyncio
    async def test_hackernews_timeframe_hour(self, tool_context, mock_signal):
        """HackerNews with hour timeframe."""
        tool = SignalsTool()
        params = SignalInput(source="hackernews", timeframe="hour", limit=10)

        with patch(
            "kurt.integrations.research.monitoring.HackerNewsAdapter"
        ) as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter.get_recent.return_value = [mock_signal]
            mock_adapter_class.return_value = mock_adapter

            await tool.run(params, tool_context)

        mock_adapter.get_recent.assert_called_once_with(
            hours=1,
            keywords=None,
            min_score=0,
        )

    @pytest.mark.asyncio
    async def test_hackernews_timeframe_week(self, tool_context, mock_signal):
        """HackerNews with week timeframe."""
        tool = SignalsTool()
        params = SignalInput(source="hackernews", timeframe="week", limit=10)

        with patch(
            "kurt.integrations.research.monitoring.HackerNewsAdapter"
        ) as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter.get_recent.return_value = [mock_signal]
            mock_adapter_class.return_value = mock_adapter

            await tool.run(params, tool_context)

        mock_adapter.get_recent.assert_called_once_with(
            hours=168,  # week = 168 hours
            keywords=None,
            min_score=0,
        )

    @pytest.mark.asyncio
    async def test_hackernews_limit_applied(self, tool_context, mock_signal):
        """HackerNews results are limited."""
        tool = SignalsTool()
        params = SignalInput(source="hackernews", limit=2)

        # Create multiple signals
        signals = [mock_signal, mock_signal, mock_signal, mock_signal, mock_signal]

        with patch(
            "kurt.integrations.research.monitoring.HackerNewsAdapter"
        ) as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter.get_recent.return_value = signals
            mock_adapter_class.return_value = mock_adapter

            result = await tool.run(params, tool_context)

        assert result.success is True
        assert len(result.data) == 2  # Limited to 2


# ============================================================================
# SignalsTool Execution Tests - Feeds
# ============================================================================


class TestSignalsToolFeeds:
    """Test SignalsTool execution for feeds source."""

    @pytest.mark.asyncio
    async def test_feeds_missing_url(self, tool_context):
        """Feeds source without feed_url returns error."""
        tool = SignalsTool()
        params = SignalInput(source="feeds")

        result = await tool.run(params, tool_context)

        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "missing_feed_url"

    @pytest.mark.asyncio
    async def test_feeds_basic(self, tool_context, mock_signal):
        """Feeds source basic fetch."""
        tool = SignalsTool()
        params = SignalInput(
            source="feeds",
            feed_url="https://example.com/feed.xml",
            limit=10,
        )

        mock_signal.source = "feeds"
        mock_signal.to_dict.return_value["source"] = "feeds"

        with patch("kurt.integrations.research.monitoring.FeedAdapter") as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter.get_feed_entries.return_value = [mock_signal]
            mock_adapter_class.return_value = mock_adapter

            result = await tool.run(params, tool_context)

        assert result.success is True
        assert len(result.data) == 1
        mock_adapter.get_feed_entries.assert_called_once_with(
            feed_url="https://example.com/feed.xml",
            keywords=None,
            limit=10,
        )


# ============================================================================
# SignalsTool Error Handling Tests
# ============================================================================


class TestSignalsToolErrorHandling:
    """Test SignalsTool error handling."""

    @pytest.mark.asyncio
    async def test_adapter_exception(self, tool_context):
        """Adapter exception is handled gracefully."""
        tool = SignalsTool()
        params = SignalInput(source="hackernews", limit=10)

        with patch(
            "kurt.integrations.research.monitoring.HackerNewsAdapter"
        ) as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter.get_recent.side_effect = Exception("Network error")
            mock_adapter_class.return_value = mock_adapter

            result = await tool.run(params, tool_context)

        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "fetch_failed"
        assert "Network error" in result.errors[0].message


# ============================================================================
# SignalsTool Progress Callback Tests
# ============================================================================


class TestSignalsToolProgress:
    """Test SignalsTool progress callbacks."""

    @pytest.mark.asyncio
    async def test_progress_callback_called(self, tool_context, mock_signal):
        """Progress callback is called with SubstepEvents."""
        events: list[SubstepEvent] = []

        def on_progress(event: SubstepEvent):
            events.append(event)

        tool = SignalsTool()
        params = SignalInput(source="hackernews", limit=10)

        with patch(
            "kurt.integrations.research.monitoring.HackerNewsAdapter"
        ) as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter.get_recent.return_value = [mock_signal]
            mock_adapter_class.return_value = mock_adapter

            await tool.run(params, tool_context, on_progress)

        # Check that progress events were emitted
        assert len(events) > 0

        # Check fetch_signals substep events
        fetch_events = [e for e in events if e.substep == "fetch_signals"]
        assert any(e.status == "running" for e in fetch_events)
        assert any(e.status == "completed" for e in fetch_events)

    @pytest.mark.asyncio
    async def test_progress_includes_metadata(self, tool_context, mock_signal):
        """Progress events include signal metadata."""
        events: list[SubstepEvent] = []

        def on_progress(event: SubstepEvent):
            events.append(event)

        tool = SignalsTool()
        params = SignalInput(source="hackernews", limit=10)

        with patch(
            "kurt.integrations.research.monitoring.HackerNewsAdapter"
        ) as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter.get_recent.return_value = [mock_signal]
            mock_adapter_class.return_value = mock_adapter

            await tool.run(params, tool_context, on_progress)

        # Find progress event with metadata
        progress_events = [e for e in events if e.status == "progress"]
        assert len(progress_events) > 0
        assert progress_events[0].metadata.get("signal_id") == "reddit_abc123"


# ============================================================================
# SignalsTool Result Structure Tests
# ============================================================================


class TestSignalsToolResult:
    """Test SignalsTool result structure."""

    @pytest.mark.asyncio
    async def test_result_structure(self, tool_context, mock_signal):
        """Result has correct structure."""
        tool = SignalsTool()
        params = SignalInput(source="hackernews", limit=10)

        with patch(
            "kurt.integrations.research.monitoring.HackerNewsAdapter"
        ) as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter.get_recent.return_value = [mock_signal]
            mock_adapter_class.return_value = mock_adapter

            result = await tool.run(params, tool_context)

        assert isinstance(result, ToolResult)
        assert result.success is True
        assert isinstance(result.data, list)
        assert len(result.substeps) == 1
        assert result.substeps[0].name == "fetch_signals"
        assert result.substeps[0].status == "completed"

    @pytest.mark.asyncio
    async def test_output_data_fields(self, tool_context, mock_signal):
        """Output data contains all expected fields."""
        tool = SignalsTool()
        params = SignalInput(source="hackernews", limit=10)

        with patch(
            "kurt.integrations.research.monitoring.HackerNewsAdapter"
        ) as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter.get_recent.return_value = [mock_signal]
            mock_adapter_class.return_value = mock_adapter

            result = await tool.run(params, tool_context)

        data = result.data[0]
        assert "signal_id" in data
        assert "source" in data
        assert "title" in data
        assert "url" in data
        assert "snippet" in data
        assert "author" in data
        assert "score" in data
        assert "comment_count" in data
        assert "subreddit" in data
        assert "domain" in data
        assert "keywords" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_timestamp_converted_to_iso(self, tool_context, mock_signal):
        """Datetime timestamps are converted to ISO strings."""
        tool = SignalsTool()
        params = SignalInput(source="hackernews", limit=10)

        with patch(
            "kurt.integrations.research.monitoring.HackerNewsAdapter"
        ) as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter.get_recent.return_value = [mock_signal]
            mock_adapter_class.return_value = mock_adapter

            result = await tool.run(params, tool_context)

        # Timestamp should be ISO string
        timestamp = result.data[0]["timestamp"]
        assert isinstance(timestamp, str)
        assert "2024-01-15" in timestamp

    @pytest.mark.asyncio
    async def test_empty_results(self, tool_context):
        """Empty results are handled correctly."""
        tool = SignalsTool()
        params = SignalInput(source="hackernews", limit=10)

        with patch(
            "kurt.integrations.research.monitoring.HackerNewsAdapter"
        ) as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter.get_recent.return_value = []
            mock_adapter_class.return_value = mock_adapter

            result = await tool.run(params, tool_context)

        assert result.success is True
        assert result.data == []
        assert result.substeps[0].current == 0
        assert result.substeps[0].total == 0
