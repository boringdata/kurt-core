"""
RSS/Atom feed monitoring adapter.

Uses feedparser to parse feeds.
"""

from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

import feedparser

from kurt.integrations.research.monitoring.models import Signal


class FeedAdapter:
    """Adapter for monitoring RSS/Atom feeds."""

    def __init__(self):
        """Initialize feed adapter."""
        pass

    def get_feed_entries(
        self,
        feed_url: str,
        since: Optional[datetime] = None,
        keywords: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[Signal]:
        """
        Get entries from an RSS/Atom feed.

        Args:
            feed_url: URL of the RSS/Atom feed
            since: Only return entries published after this datetime
            keywords: Optional keyword filter
            limit: Maximum entries to return

        Returns:
            List of Signal objects
        """
        try:
            # Parse feed
            feed = feedparser.parse(feed_url)

            if feed.bozo and hasattr(feed, "bozo_exception"):
                raise Exception(f"Failed to parse feed: {feed.bozo_exception}")

            signals = []
            for entry in feed.entries[:limit]:
                # Parse published date
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    from time import mktime

                    published = datetime.fromtimestamp(mktime(entry.published_parsed))
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    from time import mktime

                    published = datetime.fromtimestamp(mktime(entry.updated_parsed))

                # Filter by date if provided
                if since and published and published < since:
                    continue

                # Get summary/description
                summary = None
                if hasattr(entry, "summary"):
                    summary = entry.summary[:500]
                elif hasattr(entry, "description"):
                    summary = entry.description[:500]

                # Extract domain from feed or entry link
                domain = None
                if hasattr(entry, "link"):
                    domain = urlparse(entry.link).netloc
                elif hasattr(feed.feed, "link"):
                    domain = urlparse(feed.feed.link).netloc

                # Create signal
                signal = Signal(
                    signal_id=f"feed_{hash(entry.link if hasattr(entry, 'link') else entry.title)}",
                    source="rss",
                    title=entry.title if hasattr(entry, "title") else "Untitled",
                    url=entry.link if hasattr(entry, "link") else feed_url,
                    snippet=summary,
                    timestamp=published or datetime.now(),
                    author=entry.author if hasattr(entry, "author") else None,
                    score=0,  # RSS feeds don't have scores
                    comment_count=0,
                    domain=domain,
                    keywords=[],
                )

                # Filter by keywords if provided
                if keywords and not signal.matches_keywords(keywords):
                    continue

                # Track which keywords matched
                if keywords:
                    signal.keywords = [
                        kw
                        for kw in keywords
                        if kw.lower() in signal.title.lower()
                        or (signal.snippet and kw.lower() in signal.snippet.lower())
                    ]

                signals.append(signal)

            return signals

        except Exception as e:
            raise Exception(f"Failed to fetch feed {feed_url}: {e}")

    def get_multi_feed_entries(self, feed_urls: List[str], **kwargs) -> List[Signal]:
        """
        Get entries from multiple feeds.

        Args:
            feed_urls: List of feed URLs
            **kwargs: Additional arguments passed to get_feed_entries

        Returns:
            Combined list of Signal objects
        """
        all_signals = []
        for feed_url in feed_urls:
            try:
                signals = self.get_feed_entries(feed_url, **kwargs)
                all_signals.extend(signals)
            except Exception as e:
                print(f"Warning: Failed to fetch feed {feed_url}: {e}")
                continue

        # Sort by timestamp (newest first)
        all_signals.sort(key=lambda s: s.timestamp, reverse=True)
        return all_signals

    def check_feed(self, feed_url: str) -> dict:
        """
        Check if a feed is valid and get metadata.

        Args:
            feed_url: URL of the feed

        Returns:
            Dictionary with feed metadata
        """
        try:
            feed = feedparser.parse(feed_url)

            if feed.bozo and hasattr(feed, "bozo_exception"):
                return {"valid": False, "error": str(feed.bozo_exception)}

            return {
                "valid": True,
                "title": feed.feed.title if hasattr(feed.feed, "title") else None,
                "description": feed.feed.description if hasattr(feed.feed, "description") else None,
                "link": feed.feed.link if hasattr(feed.feed, "link") else None,
                "entry_count": len(feed.entries),
                "last_updated": feed.feed.updated if hasattr(feed.feed, "updated") else None,
            }

        except Exception as e:
            return {"valid": False, "error": str(e)}
