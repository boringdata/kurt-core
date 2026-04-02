"""
Monitoring adapters for research signals.

Provides adapters for Reddit, HackerNews, RSS/Atom feeds, and Apify social media.
"""

from kurt.integrations.research.monitoring.apify import ApifyAdapter
from kurt.integrations.research.monitoring.feeds import FeedAdapter
from kurt.integrations.research.monitoring.hackernews import HackerNewsAdapter
from kurt.integrations.research.monitoring.models import Signal
from kurt.integrations.research.monitoring.reddit import RedditAdapter

__all__ = [
    "Signal",
    "RedditAdapter",
    "HackerNewsAdapter",
    "FeedAdapter",
    "ApifyAdapter",
]
