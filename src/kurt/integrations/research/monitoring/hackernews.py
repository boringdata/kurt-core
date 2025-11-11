"""
Hacker News monitoring adapter.

Uses HN's Algolia API for search and the official Firebase API for top stories.
"""

from datetime import datetime, timedelta
from typing import List, Optional

import requests

from kurt.integrations.research.monitoring.models import Signal


class HackerNewsAdapter:
    """Adapter for monitoring Hacker News posts."""

    ALGOLIA_URL = "https://hn.algolia.com/api/v1"
    FIREBASE_URL = "https://hacker-news.firebaseio.com/v0"

    def __init__(self):
        """Initialize Hacker News adapter."""
        pass

    def get_top_stories(
        self, limit: int = 30, keywords: Optional[List[str]] = None, min_score: int = 0
    ) -> List[Signal]:
        """
        Get current top stories from Hacker News front page.

        Args:
            limit: Maximum stories to fetch
            keywords: Optional keyword filter
            min_score: Minimum score threshold

        Returns:
            List of Signal objects
        """
        # Get top story IDs
        response = requests.get(f"{self.FIREBASE_URL}/topstories.json", timeout=10)
        response.raise_for_status()
        story_ids = response.json()[:limit]

        signals = []
        for story_id in story_ids:
            try:
                # Fetch story details
                story_response = requests.get(
                    f"{self.FIREBASE_URL}/item/{story_id}.json", timeout=5
                )
                story_response.raise_for_status()
                story = story_response.json()

                if not story or story.get("type") != "story":
                    continue

                # Skip if below score threshold
                if story.get("score", 0) < min_score:
                    continue

                # Create signal
                signal = Signal(
                    signal_id=f"hn_{story.get('id')}",
                    source="hackernews",
                    title=story.get("title", ""),
                    url=story.get("url")
                    or f"https://news.ycombinator.com/item?id={story.get('id')}",
                    snippet=story.get("text", "")[:500] if story.get("text") else None,
                    timestamp=datetime.fromtimestamp(story.get("time", 0)),
                    author=story.get("by"),
                    score=story.get("score", 0),
                    comment_count=story.get("descendants", 0),
                    keywords=[],
                )

                # Filter by keywords if provided
                if keywords and not signal.matches_keywords(keywords):
                    continue

                # Track which keywords matched
                if keywords:
                    signal.keywords = [kw for kw in keywords if kw.lower() in signal.title.lower()]

                signals.append(signal)

            except Exception as e:
                print(f"Warning: Failed to fetch HN story {story_id}: {e}")
                continue

        return signals

    def search(
        self,
        query: str,
        timeframe: str = "week",
        sort: str = "relevance",
        limit: int = 30,
        min_score: int = 0,
    ) -> List[Signal]:
        """
        Search Hacker News using Algolia API.

        Args:
            query: Search query
            timeframe: Time filter ("day", "week", "month", "year", "all")
            sort: Sort order ("relevance" or "date")
            limit: Maximum results
            min_score: Minimum score threshold

        Returns:
            List of Signal objects
        """
        # Map timeframe to seconds
        timeframe_seconds = {
            "hour": 3600,
            "day": 86400,
            "week": 604800,
            "month": 2592000,
            "year": 31536000,
            "all": None,
        }

        # Build search params
        params = {
            "query": query,
            "tags": "story",  # Only stories, not comments
            "hitsPerPage": limit,
        }

        # Add time filter if not "all"
        if timeframe != "all" and timeframe in timeframe_seconds:
            timestamp = int(
                (datetime.now() - timedelta(seconds=timeframe_seconds[timeframe])).timestamp()
            )
            params["numericFilters"] = f"created_at_i>{timestamp}"

        # Sort by date if requested
        if sort == "date":
            url = f"{self.ALGOLIA_URL}/search_by_date"
        else:
            url = f"{self.ALGOLIA_URL}/search"

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            signals = []
            for hit in data.get("hits", []):
                # Skip if below score threshold
                if hit.get("points", 0) < min_score:
                    continue

                signal = Signal(
                    signal_id=f"hn_{hit.get('objectID')}",
                    source="hackernews",
                    title=hit.get("title", ""),
                    url=hit.get("url")
                    or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                    snippet=hit.get("story_text", "")[:500] if hit.get("story_text") else None,
                    timestamp=datetime.fromtimestamp(hit.get("created_at_i", 0)),
                    author=hit.get("author"),
                    score=hit.get("points", 0),
                    comment_count=hit.get("num_comments", 0),
                    keywords=[query],
                )

                signals.append(signal)

            return signals

        except requests.RequestException as e:
            raise Exception(f"Failed to search Hacker News: {e}")

    def get_recent(
        self, hours: int = 24, keywords: Optional[List[str]] = None, min_score: int = 10
    ) -> List[Signal]:
        """
        Get recent stories from the last N hours.

        Args:
            hours: Number of hours to look back
            keywords: Optional keyword filter
            min_score: Minimum score threshold

        Returns:
            List of Signal objects matching criteria
        """
        # Use Algolia search with time filter and no query (gets all stories)
        timestamp = int((datetime.now() - timedelta(hours=hours)).timestamp())

        params = {
            "tags": "story",
            "numericFilters": f"created_at_i>{timestamp}",
            "hitsPerPage": 100,
        }

        url = f"{self.ALGOLIA_URL}/search_by_date"

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            signals = []
            for hit in data.get("hits", []):
                # Skip if below score threshold
                if hit.get("points", 0) < min_score:
                    continue

                signal = Signal(
                    signal_id=f"hn_{hit.get('objectID')}",
                    source="hackernews",
                    title=hit.get("title", ""),
                    url=hit.get("url")
                    or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                    snippet=hit.get("story_text", "")[:500] if hit.get("story_text") else None,
                    timestamp=datetime.fromtimestamp(hit.get("created_at_i", 0)),
                    author=hit.get("author"),
                    score=hit.get("points", 0),
                    comment_count=hit.get("num_comments", 0),
                    keywords=[],
                )

                # Filter by keywords if provided
                if keywords and not signal.matches_keywords(keywords):
                    continue

                # Track which keywords matched
                if keywords:
                    signal.keywords = [kw for kw in keywords if kw.lower() in signal.title.lower()]

                signals.append(signal)

            # Sort by relevance score
            signals.sort(key=lambda s: s.relevance_score, reverse=True)
            return signals

        except requests.RequestException as e:
            raise Exception(f"Failed to fetch recent HN stories: {e}")
