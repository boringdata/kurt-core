"""
Monitoring adapters for research signals.

Provides adapters for Reddit, HackerNews, and RSS/Atom feeds.
"""

from kurt_new.integrations.research.monitoring.feeds import FeedAdapter
from kurt_new.integrations.research.monitoring.hackernews import HackerNewsAdapter
from kurt_new.integrations.research.monitoring.models import Signal
from kurt_new.integrations.research.monitoring.reddit import RedditAdapter

__all__ = [
    "Signal",
    "RedditAdapter",
    "HackerNewsAdapter",
    "FeedAdapter",
]
