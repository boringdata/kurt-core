"""Test fixtures for research integration tests."""

from datetime import datetime

import pytest

from kurt.integrations.research.base import Citation, ResearchResult
from kurt.integrations.research.monitoring.models import Signal


@pytest.fixture
def sample_citations():
    """Sample citation objects."""
    return [
        Citation(
            title="Source 1",
            url="https://example.com/1",
            snippet="First source snippet",
            domain="example.com",
        ),
        Citation(
            title="Source 2",
            url="https://example.com/2",
            snippet="Second source snippet",
            domain="example.com",
        ),
    ]


@pytest.fixture
def sample_research_result(sample_citations):
    """Sample research result."""
    return ResearchResult(
        id="res_20240101_abc123",
        query="What is machine learning?",
        answer="Machine learning is a subset of AI...",
        citations=sample_citations,
        source="perplexity",
        model="sonar-reasoning",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        response_time_seconds=2.5,
    )


@pytest.fixture
def sample_signal():
    """Sample monitoring signal."""
    return Signal(
        signal_id="reddit_abc123",
        source="reddit",
        title="Interesting discussion about Python",
        url="https://reddit.com/r/python/comments/abc123",
        snippet="This is a great discussion...",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        author="user123",
        score=150,
        comment_count=42,
        subreddit="python",
        keywords=["python", "programming"],
    )


@pytest.fixture
def sample_signals():
    """Sample list of monitoring signals."""
    return [
        Signal(
            signal_id="reddit_1",
            source="reddit",
            title="Python 3.12 released",
            url="https://reddit.com/r/python/1",
            score=500,
            comment_count=120,
            subreddit="python",
        ),
        Signal(
            signal_id="reddit_2",
            source="reddit",
            title="Best Python libraries for ML",
            url="https://reddit.com/r/python/2",
            score=200,
            comment_count=50,
            subreddit="python",
        ),
        Signal(
            signal_id="hn_1",
            source="hackernews",
            title="Show HN: New ML framework",
            url="https://news.ycombinator.com/item?id=123",
            score=100,
            comment_count=30,
        ),
    ]
